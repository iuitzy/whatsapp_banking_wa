import os
import re
import time
from typing import Any
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.utils.utils import convert_to_secret_str
from langchain_core.tools import StructuredTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict
from app.agent.tools import tool_get_account_balance, tool_get_last_transactions
from app.memory import get_session_history, append_to_session
from app.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


class AgentState(TypedDict):
    messages: list
    phone_number: str
    trace_id: str


def get_llm() -> ChatGroq:
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(
        model=model,
        api_key=convert_to_secret_str(os.getenv("GROQ_API_KEY", "")),
        temperature=0
    )


def make_tools(trace_id: str) -> list:
    return [
        StructuredTool.from_function(
            func=lambda account_number: tool_get_account_balance(account_number, trace_id),
            name="get_account_balance",
            description="Get the current balance for a bank account. Use when user asks about their balance or account details. Requires account number."
        ),
        StructuredTool.from_function(
            func=lambda account_number: tool_get_last_transactions(account_number, trace_id),
            name="get_last_transactions",
            description="Get the last 5 transactions for a bank account. Use when user asks about recent transactions, payments, or spending. Requires account number."
        ),
    ]


def build_agent(trace_id: str) -> Any:
    tools = make_tools(trace_id)
    llm = get_llm()
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: AgentState) -> dict:  # type: ignore
        start = time.time()
        system_message = SystemMessage(content="""You are a helpful HSBC banking assistant on WhatsApp.
You help customers check their account balance and view recent transactions.

When a customer asks about their balance or transactions, ask for their account number if not provided.
Always be polite, concise, and professional.
Format currency amounts clearly with the currency symbol.
For balances: "Your current balance is £1,234.56"
For transactions: List them clearly with date, description, and amount.

Important: Keep responses short and suitable for WhatsApp messages.""")

        messages = [system_message] + state["messages"]

        try:
            response = llm_with_tools.invoke(messages)
            duration = (time.time() - start) * 1000
            logger.info(f"[{state['trace_id']}] LLM call successful | duration={duration:.2f}ms")
            return {"messages": [response]}
        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"[{state['trace_id']}] LLM call failed | error={e} | duration={duration:.2f}ms")
            raise

    def should_continue(state: AgentState) -> str:  # type: ignore
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    graph: StateGraph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)  # type: ignore
    graph.add_node("tools", ToolNode(make_tools(trace_id)))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=None)


async def run_agent(
    query: str,
    phone_number: str,
    trace_id: str
) -> str:
    start = time.time()
    logger.info(f"[{trace_id}] Agent started | phone={phone_number[-4:]} | query={query[:50]}")

    try:
        # Get session history from Redis
        history = get_session_history(phone_number)

        # Build past messages
        past_messages = []
        for msg in history[-6:]:
            if msg["role"] == "user":
                past_messages.append(HumanMessage(content=msg["content"][:300]))
            elif msg["role"] == "assistant":
                past_messages.append(AIMessage(content=msg["content"][:300]))

        agent = build_agent(trace_id)

        initial_state: AgentState = {
            "messages": past_messages + [HumanMessage(content=query)],
            "phone_number": phone_number,
            "trace_id": trace_id
        }

        result = await agent.ainvoke(  # type: ignore
            initial_state,
            config={"recursion_limit": 10}
        )

        final_message = result["messages"][-1]
        tools_called = [
            m.name for m in result["messages"]
            if hasattr(m, "name") and m.name is not None
        ]

        response_content = str(
            final_message.content if hasattr(final_message, "content")
            else final_message
        )

        # Strip XML tags some models add
        response_content = re.sub(r'<[^>]+>', '', response_content).strip()

        duration = (time.time() - start) * 1000
        logger.info(f"[{trace_id}] Agent completed | duration={duration:.2f}ms | tools={tools_called}")

        # Save to Redis memory
        append_to_session(phone_number, "user", query)
        append_to_session(phone_number, "assistant", response_content[:500])

        return response_content

    except Exception as e:
        duration = (time.time() - start) * 1000
        logger.error(f"[{trace_id}] Agent failed | error={e} | duration={duration:.2f}ms")
        error_str = str(e)
        if "rate_limit_exceeded" in error_str or "429" in error_str:
            return "I'm sorry, the service is temporarily busy. Please try again in a few minutes."
        return "I'm sorry, I encountered an error processing your request. Please try again."
