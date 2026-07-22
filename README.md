# HSBC WhatsApp Banking Assistant

AI-powered WhatsApp banking assistant that accepts voice and text messages, processes them through a LangGraph AI agent, and responds with real banking information. Built with FastAPI, LangGraph, Groq LLM, Groq Whisper, PostgreSQL, Redis, and OpenWA.

---

## Architecture

```mermaid
flowchart TD
    A[WhatsApp User\nSends text or voice] -->|WhatsApp message| B[OpenWA Gateway\nPort 2785]
    B -->|Webhook POST| C[ngrok Public HTTPS URL]
    C -->|Forwards to| D[FastAPI App\nPort 8001]
    D --> E[Message Handler]
    E -->|voice message| F[Groq Whisper\nwhisper-large-v3-turbo\nVoice to Text]
    E -->|text message| G[LangGraph Agent]
    F -->|transcribed text| G
    G --> H[Groq LLM\nllama-3.3-70b-versatile\nTool selection and reasoning]
    H -->|tool call| I[Banking Tools]
    I --> J[(PostgreSQL\nAccounts and Transactions)]
    G --> K[(Redis\nSession Memory\n1 hour TTL per phone)]
    G -->|response text| D
    D -->|send reply via OpenWA API| B
    B -->|WhatsApp reply| A
    D --> L[Trace ID Logging\nDaily rotating logs\n7 day retention]
    D --> M[Metrics Endpoint\nGET /metrics]
```

---

## Prerequisites

- Docker and Docker Compose
- Groq API key — free at [console.groq.com](https://console.groq.com)
- ngrok account — free at [dashboard.ngrok.com](https://dashboard.ngrok.com)
- A phone with WhatsApp installed
- A second WhatsApp number to receive replies

---

## Setup — Step by Step

### Step 1 — Clone and configure

```bash
git clone https://github.com/dinnyhub/whatsapp-banking-agent.git
cd whatsapp-banking-agent
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_WHISPER_MODEL=whisper-large-v3-turbo

DATABASE_URL=postgresql://banking_user:banking_pass@localhost:5433/banking_db
REDIS_URL=redis://localhost:6380

OPENWA_URL=http://localhost:2785
OPENWA_API_KEY=get_this_after_step_2
OPENWA_SESSION_ID=get_this_after_step_3

WEBHOOK_SECRET=
```

---

### Step 2 — Start infrastructure and get OpenWA API key

Start PostgreSQL, Redis and OpenWA first:

```bash
docker compose up postgres redis openwa -d
```

Wait 30 seconds then get the auto-generated API key:

```bash
docker exec whatsapp_openwa cat /app/data/.api-key
```

Copy the key and update `.env`:

```env
OPENWA_API_KEY=owa_k1_xxxxxxxxxxxxxxxxxxxx
```

---

### Step 3 — Create WhatsApp session

Open the OpenWA dashboard at **http://localhost:2785**

Enter the API key from Step 2 to login.

Then:
1. Click **Sessions** in the left menu
2. Click **New Session**
3. Name it: `hsbc-assistant`
4. Click **Create**
5. Click **Start** on the session
6. Scan the QR code with WhatsApp on your phone — WhatsApp → Linked Devices → Link a Device
7. Wait for status to show **Connected**

Copy the Session ID shown in the dashboard and update `.env`:

```env
OPENWA_SESSION_ID=a02d3dd1-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

### Step 4 — Build and start the FastAPI app

```bash
docker compose build app
docker compose up app -d
```

Verify it is running:

```bash
curl http://localhost:8001/health
```

Expected response:

```json
{
  "status": "healthy",
  "components": {
    "api": "healthy",
    "redis": "connected",
    "postgres": "connected"
  }
}
```

---

### Step 5 — Set up ngrok tunnel

OpenWA requires a public HTTPS URL for webhooks — local URLs are blocked by SSRF protection.

Install ngrok:

```bash
brew install ngrok
```

Add your auth token from [dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken):

```bash
ngrok config add-authtoken YOUR_NGROK_TOKEN
```

Start the tunnel in a separate terminal — keep it running:

```bash
ngrok http 8001
```

Copy the public URL shown — looks like:

```
https://2cb6-5-151-181-20.ngrok-free.app
```

---

### Step 6 — Register the webhook

Replace the values with your actual OpenWA API key, Session ID and ngrok URL:

```bash
curl -X POST http://localhost:2785/api/sessions/YOUR_SESSION_ID/webhooks \
  -H "X-API-Key: YOUR_OPENWA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://YOUR_NGROK_URL/webhook/whatsapp",
    "events": ["message.received"]
  }'
```

Expected response:

```json
{
  "id": "ed897686-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "active": true,
  "url": "https://YOUR_NGROK_URL/webhook/whatsapp",
  "events": ["message.received"]
}
```

---

### Step 7 — Test the full flow

Send a WhatsApp message to the linked number:

```
What is my balance for account GB12HSBC00010001234567?
```

You should receive a reply with the account balance.

Check the logs to see the full trace:

```bash
docker logs whatsapp_app --tail=50
```

---

## Test Without WhatsApp

Test the agent directly without going through WhatsApp using Swagger UI at **http://localhost:8001/docs**

Or via curl:

```bash
curl -X POST http://localhost:8001/api/test/message \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "447812345678",
    "message": "What is my balance for account GB12HSBC00010001234567?"
  }'
```

---

## URLs

| URL | Description |
|---|---|
| http://localhost:8001 | FastAPI application |
| http://localhost:8001/docs | Swagger UI |
| http://localhost:8001/health | Health check |
| http://localhost:8001/metrics | System metrics |
| http://localhost:2785 | OpenWA dashboard |
| http://127.0.0.1:4040 | ngrok inspector |

---

## Test Accounts

| Account Number | Holder | Balance |
|---|---|---|
| GB12HSBC00010001234567 | John Smith | £2,543.67 |
| GB12HSBC00010007654321 | Sarah Johnson | £15,750.00 |
| GB12HSBC00010009876543 | Michael Brown | £892.34 |

---

## Example Queries

Send these as WhatsApp messages or test via Swagger:

```
What is my balance for account GB12HSBC00010001234567?
Show me the last 5 transactions for account GB12HSBC00010007654321
What is my account balance?
```

---

## Docker Services

| Container | Image | Port |
|---|---|---|
| whatsapp_postgres | postgres:15 | 5433 |
| whatsapp_redis | redis:7-alpine | 6380 |
| whatsapp_openwa | ghcr.io/rmyndharis/openwa:latest | 2785 |
| whatsapp_app | whatsapp-banking-app | 8001 |

---

## Project Structure

**app/** — Application code
- `main.py` — FastAPI entry point and webhook receiver
- `agent/agent.py` — LangGraph agent with Redis memory
- `agent/tools.py` — Banking tools — balance and transactions
- `services/whatsapp.py` — OpenWA client to send messages
- `services/transcription.py` — Groq Whisper voice to text
- `services/message_handler.py` — Routes voice and text, runs agent, sends response
- `api/routes.py` — REST API endpoints
- `database.py` — PostgreSQL queries
- `memory.py` — Redis session memory per phone number
- `metrics.py` — Metrics tracking with trace ID
- `logger.py` — Daily rotating logs

**infra/postgres/init.sql** — Database schema and seed data

**Root files**
- `docker-compose.yml` — All 4 services
- `Dockerfile` — Non-root Python container
- `.env.example` — Environment variable template
- `README.md` — This file

---

## Important Notes

**ngrok URL changes on every restart.** Each time you restart ngrok you get a new public URL and must re-register the webhook. To get a permanent URL upgrade to a paid ngrok plan or deploy to a cloud server.

**OpenWA session persists** in the `whatsapp_openwa_data` Docker volume. If you delete the volume you need to scan the QR code again.

**Groq rate limits** — llama-3.3-70b-versatile has 100K daily tokens on the free tier. Switch to `qwen/qwen3-32b` in `.env` for 500K daily tokens.

**WEBHOOK_SECRET is optional.** Leave it empty for development. Set a random string in production for webhook authentication.