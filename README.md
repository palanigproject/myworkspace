# MyWorkspace Microservices Application

Production-ready microservices workspace with:

- `mcp-server` (FastAPI): central tool router/orchestrator
- `project-service` (FastAPI): external Convex API integration
- `slack-service` (FastAPI): Slack event handling + webhook delivery
- `frontend` (React + Vite + Axios): dashboard UI that calls MCP only

## Architecture

All tool communication is routed through MCP:

- Frontend -> MCP Server -> Chat API (`https://chatbotinsightsdev.ckdigital.in/api/chat`)
- MCP tools attach bearer auth and send `query`/`feature` form data

No direct frontend calls to `project-service`.

## Tools exposed by MCP

`POST /mcp/tools`

Supported tools (mapped to prompt requests):

- `get_projects` -> sends prompt with project context
- `slack_send_message` -> sends prompt with slack context
- `get_slack_channel_history` -> sends prompt with slack context
- `get_slack_channels` -> sends prompt with slack context

Sample request:

```json
{
  "name": "get_slack_channels",
  "input": {
    "query": "list out channel",
    "feature": "slack"
  }
}
```

## Folder Structure

```text
myworkspace/
  mcp-server/
  project-service/
  slack-service/
  frontend/
  docker-compose.yml
```

## Prerequisites

- Docker Desktop (Compose v2)
- Optional local runtime:
  - Python 3.12+
  - Node.js 20+

## Run with Docker Compose

1. Copy environment template:

```bash
cp .env.example .env
```

2. Update `.env`:
   - `SLACK_WEBHOOK_URL` (optional but required for actual Slack delivery)
   - `VITE_MCP_BASE_URL` (default `http://localhost:8000`)

3. Start all services:

```bash
docker compose up --build -d
```

4. Verify:

- Frontend: `http://localhost:8080`
- MCP Health: `http://localhost:8000/health`
- Project Health: `http://localhost:8001/health`
- Slack Health: `http://localhost:8002/health`

5. Stop:

```bash
docker compose down
```

## Local Development (without Docker)

Run each service in a separate terminal.

### MCP Server

```bash
cd mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Project Service

```bash
cd project-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8001
```

### Slack Service

```bash
cd slack-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8002
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend URL: `http://localhost:5173`

## API Smoke Tests

### 1) Fetch projects through MCP

```bash
curl -X POST http://localhost:8000/mcp/tools \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"get_projects\",\"input\":{}}"
```

### 2) Send Slack message through MCP tool

```bash
curl -X POST http://localhost:8000/mcp/tools \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"slack_send_message\",\"input\":{\"text\":\"Hello from MCP\"}}"
```

### 3) Simulate slash command event in Slack service

```bash
curl -X POST http://localhost:8002/slack/events \
  -H "Content-Type: application/json" \
  -d "{\"event_type\":\"slash_command\",\"payload\":{\"command\":\"/projects\"}}"
```

## Production Notes

- Centralized orchestration is enforced by MCP tool routing.
- All services use environment-based configuration.
- Structured logging is enabled across services.
- HTTP timeouts and upstream error handling are included.
- Container restart policy is `unless-stopped`.

## Optional Enhancements

- Add JWT auth at MCP layer and service-to-service auth.
- Add Redis cache in `project-service` for upstream API responses.
- Add Kafka for async event fan-out and retry workflows.
