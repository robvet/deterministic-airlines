
#Activate virtual environment
.\.venv\Scripts\activate.ps1

# launch web server
cd src2
python run.py
(starts fastapi on 8000)
http://localhost:8000/docs

# launch ui
cd src2/ui
streamlit run streamlit_app.py (UI on 8501)

# kill process
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force


az login
az account show

### Merge to branches from main
git checkout deterministic-airline-developer-v1
git merge main
git push



# Install packages
# located in root folder
pip install -r requirements.txt

# Invoke REST endpoint from PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Running the System

## Entry Points: main.py vs run.py

Both entry points use the same `OrchestratorAgent` but serve different purposes:

| Entry Point | Flow |
|-------------|------|
| `main.py` | REPL loop → `OrchestratorAgent.process_request()` → Tool |
| `run.py` | FastAPI → `/chat` endpoint → `OrchestratorAgent.process_request()` → Tool |

### When to Use Each

**main.py** - Use for debugging:
- Direct console access (type prompts, see responses immediately)
- Easier breakpoint stepping (no async/HTTP overhead)
- Single-threaded execution for predictable debugging
- Set breakpoint on `orchestrator.process_request()` line 78, then F5

**run.py** - Use for production/UI:
- Exposes REST API on port 8000
- Powers the Streamlit frontend
- Supports concurrent requests
- Health check endpoint for infrastructure probes

### Debugging Workflow

1. Open `main.py` in VS Code
2. Set breakpoint in `orchestrator.py` on `_build_request()` (around line 135)
3. Press F5 to start debugging
4. Type a booking request: "I want to book a flight to LA"
5. Step through to see intent classification → request building → tool execution