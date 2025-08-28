# Swarm Neural Refactoring Engine (SNRE)

A distributed agent-based refactoring engine with consensus and evolution tracking.

---

**Author:** Bradley R. Kinnard ([moonrunnerkc](https://github.com/moonrunnerkc))  
**Organization:** Aftermath Technologies Ltd.  
**License:** Apache 2.0 — Free to use, modify, and distribute, with required attribution.  


### Installation
```bash
git clone <repository>
cd snre
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Basic Usage
```bash
# Start refactoring
snre start --path mycode.py --agents security_enforcer

# View refactored code
snre show <session_id>

# Apply changes to file
snre apply <session_id>
```

## CLI Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `start` | Begin refactoring session | `snre start --path <file> --agents <agent_list>` |
| `status` | Check session progress | `snre status <session_id>` |
| `result` | View refactoring summary | `snre result <session_id>` |
| `show` | Display refactored code | `snre show <session_id> [--diff] [--line-numbers]` |
| `apply` | Write changes to file | `snre apply <session_id> [--no-backup] [--force]` |
| `list` | Show active sessions | `snre list` |
| `cancel` | Cancel running session | `snre cancel <session_id>` |
| `validate` | Check code syntax | `snre validate --path <file>` |

### Command Examples
```bash
# Start with multiple agents
snre start --path code.py --agents security_enforcer,pattern_optimizer

# View changes as diff
snre show abc-123-def --diff

# Apply without creating backup
snre apply abc-123-def --no-backup

# Force apply even if file was modified
snre apply abc-123-def --force
```

## Available Agents

- **security_enforcer**: Detects SQL injection, hardcoded secrets, unsafe eval usage
- **pattern_optimizer**: Improves code patterns and structures  
- **loop_simplifier**: Optimizes loops and reduces complexity

## Core Features

### Session Persistence
- Sessions automatically saved to `data/refactor_logs/sessions/`
- Commands work across separate CLI invocations
- Sessions survive application restarts
- Complete refactoring history preserved

### Smart Refactoring
- **Multi-Agent Consensus**: Agents vote on proposed changes
- **Convergence Detection**: Stops when no more improvements possible
- **Change Validation**: Prevents duplicate or ineffective modifications
- **Syntax Safety**: Validates code before and after changes

### Workflow Integration
```bash
# Complete workflow example
snre start --path app.py --agents security_enforcer
# Returns: Started refactoring session: abc-123-def

snre show abc-123-def --diff        # Review changes
snre apply abc-123-def              # Apply to file (creates backup)
snre result abc-123-def             # View final metrics
```

## Configuration

### System Settings (`config/settings.yaml`)
```yaml
swarm:
  max_concurrent_agents: 5
  consensus_threshold: 0.6
  max_iterations: 10
  enable_evolution_log: true
```

### Agent Profiles (`config/agent_profiles.yaml`)
```yaml
agents:
  security_enforcer:
    priority: 9
    confidence_threshold: 0.8
```

## API Server

### Start Server
```bash
python main.py api localhost 8000
```

### REST Endpoints
```bash
# Start refactoring
curl -X POST http://localhost:8000/refactor/start \
  -H "Content-Type: application/json" \
  -d '{"target_path": "code.py", "agent_set": ["security_enforcer"]}'

# Get status
curl http://localhost:8000/refactor/status/<session_id>

# Get results  
curl http://localhost:8000/refactor/result/<session_id>
```

## Security Features

### Vulnerability Detection
- **SQL Injection**: Detects unsafe query construction
- **Command Injection**: Identifies unsafe system calls
- **Hardcoded Secrets**: Finds passwords, API keys in code
- **Path Traversal**: Detects unsafe file operations

### Automatic Fixes
- Converts to parameterized queries
- Migrates secrets to environment variables
- Removes dangerous eval() usage
- Adds input validation

## Data Storage

```
data/
├── refactor_logs/
│   ├── sessions/           # Persistent session data (JSON)
│   └── evolution_logs/     # Change history
└── snapshots/              # Code snapshots for rollback
```

## Development

### Adding Custom Agents
```python
from agents.base_agent import BaseAgent
from contracts import AgentAnalysis, Change

class CustomAgent(BaseAgent):
    def analyze(self, code: str) -> AgentAnalysis:
        # Implement analysis logic
        pass
        
    def suggest_changes(self, code: str) -> list[Change]:
        # Implement change suggestions
        pass
        
    def vote(self, changes: list[Change]) -> dict[str, float]:
        # Implement voting logic  
        pass
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Contract validation
python scripts/check_contract.py

# Code quality
ruff check .
mypy . --ignore-missing-imports
```

## Troubleshooting

### Session Issues
```bash
# List all sessions
snre list

# Check session files
ls -la data/refactor_logs/sessions/

# Clear Python cache
find . -name "__pycache__" -exec rm -rf {} +
```

### Common Problems
- **Session not found**: Check if session ID is correct with `snre list`
- **Apply fails**: Use `--force` flag if file was modified
- **Agent errors**: Verify agent registration in main.py

## Performance Tuning

### Configuration Options
- `consensus_threshold`: Higher values require stronger agent agreement
- `max_iterations`: Limits refactoring cycles  
- `snapshot_frequency`: Controls storage vs history granularity
- `timeout_seconds`: Maximum session duration

### Monitoring
- Evolution history tracks all changes
- Agent voting records show consensus process
- Metrics include lines changed, complexity delta, security improvements

## Contributing

### Setup
```bash
git clone <repository>
cd snre
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Workflow  
1. Run contract validation: `python scripts/check_contract.py`
2. Run tests: `pytest tests/ -v`
3. Test session persistence: Create session, restart, verify recovery
4. Submit PR with clear description

## License

Licensed under the Apache License 2.0.  
Free to use, modify, and distribute, with attribution required.  

© 2025 Bradley R. Kinnard ([moonrunnerkc](https://github.com/moonrunnerkc)), Aftermath Technologies Ltd.
