import time
from app.database import get_account_by_number, get_transactions
from app.logger import get_logger

logger = get_logger(__name__)


def tool_get_account_balance(account_number: str, trace_id: str = "") -> dict:
    """
    Get account balance for a given account number.
    Queries PostgreSQL accounts table.
    Returns balance, account type, account holder name, currency.
    """
    start = time.time()
    try:
        account = get_account_by_number(account_number.strip())
        duration = (time.time() - start) * 1000

        if not account:
            logger.info(f"[{trace_id}] TOOL | get_account_balance | not_found | account={account_number}")
            return {
                "found": False,
                "message": f"Account {account_number} not found or inactive."
            }

        logger.info(f"[{trace_id}] TOOL | get_account_balance | success | duration={duration:.2f}ms")
        return {
            "found": True,
            "account_number": account["account_number"],
            "account_holder": account["account_holder"],
            "account_type": account["account_type"],
            "balance": float(account["balance"]),
            "currency": account["currency"],
            "status": account["status"]
        }
    except Exception as e:
        duration = (time.time() - start) * 1000
        logger.error(f"[{trace_id}] TOOL | get_account_balance | error={e} | duration={duration:.2f}ms")
        return {"found": False, "message": f"Error retrieving account: {str(e)}"}


def tool_get_last_transactions(account_number: str, trace_id: str = "") -> dict:
    """
    Get last 5 transactions for a given account number.
    """
    start = time.time()
    try:
        account = get_account_by_number(account_number.strip())
        if not account:
            return {
                "found": False,
                "message": f"Account {account_number} not found or inactive."
            }

        transactions = get_transactions(account["id"], limit=5)
        duration = (time.time() - start) * 1000

        logger.info(f"[{trace_id}] TOOL | get_last_transactions | success | count={len(transactions)} | duration={duration:.2f}ms")

        formatted = []
        for t in transactions:
            formatted.append({
                "type": t["transaction_type"],
                "amount": float(t["amount"]),
                "description": t["description"],
                "date": str(t["created_at"])[:10],
                "balance_after": float(t["balance_after"])
            })

        return {
            "found": True,
            "account_number": account_number,
            "account_holder": account["account_holder"],
            "transactions": formatted,
            "total": len(formatted)
        }
    except Exception as e:
        logger.error(f"[{trace_id}] TOOL | get_last_transactions | error={e}")
        return {"found": False, "message": f"Error retrieving transactions: {str(e)}"}
