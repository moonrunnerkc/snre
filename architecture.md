// filepath: [architecture.md](http://_vscodecontentref_/23)
# Author: Bradley R. Kinnard
# SNRE Architecture Documentation

## Overview

SNRE is a distributed agent-based code refactoring engine. Specialized agents analyze
Python source code, propose concrete changes with confidence scores, vote via consensus,
and produce refactored output with full evolution tracking.

## Data Flow

```
User Input (file path + agent selection)
    |
    v
SwarmCoordinator
    |-- reads source file
    |-- creates RefactorSession
    |-- iterative loop:
    |       |
    |       v
    |   Agents (analyze + suggest_changes)
    |       |
    |       v
    |   ConsensusEngine (vote + threshold filter)
    |       |
    |       v
    |   Apply best change to code
    |       |
    |       v
    |   EvolutionRecorder (snapshot + history via event hook)
    |       |
    |       v
    |   ChangeTracker (diff + metrics)
    |
    v
Output (refactored code + session record)
```

## Package Structure

```
snre/
    __init__.py              # package root, version
    __main__.py              # python -m snre entry point
    errors.py                # SNREError hierarchy
    di.py                    # Container -- explicit dependency injection

    models/
        __init__.py
        config.py            # SNREConfig (pydantic-settings, env/yaml)
        enums.py             # RefactorStatus, ChangeType
        changes.py           # Change, ConsensusDecision, AgentAnalysis
        session.py           # RefactorSession, EvolutionStep, RefactorMetrics
        profiles.py          # AgentProfile

    agents/
        __init__.py
        protocol.py          # RefactoringAgent Protocol (runtime-checkable)
        base.py              # shared helpers -- parse_code, calculate_complexity
        pattern_optimizer.py # list/dict comprehensions, f-strings, context managers
        security_enforcer.py # SQL injection, secrets, eval, os.system
        loop_simplifier.py   # sum/any/all builtins, enumerate, loop flattening
        registry.py          # AgentRegistry -- plugin discovery via entry points

    core/
        __init__.py
        coordinator.py       # SwarmCoordinator -- async orchestration, event hooks
        consensus.py         # ConsensusEngine -- stateless pure-function pipeline
        tracker.py           # ChangeTracker -- diff computation, metrics
        recorder.py          # EvolutionRecorder -- snapshots, history persistence

    ports/
        __init__.py
        cli.py               # Click-based CLI -- start, status, validate, api commands
        api.py               # FastAPI app factory -- /refactor/start, /status, /result, /metrics

    adapters/
        __init__.py
        repository.py        # SessionRepository protocol + FileSessionRepository + SQLiteSessionRepository
        git_hook.py          # IntegrationHook -- git branch creation, pre/post commit
        parser.py            # CodeParser -- libcst wrapper, lazy-loaded
```

## Component Details

### Models ([models](http://_vscodecontentref_/24))

Pure data definitions using pydantic `BaseModel`. No business logic.

- **SNREConfig**: validated configuration via `pydantic-settings`. supports env vars
  (`SNRE_` prefix), YAML files, and `.env` files. all fields have `Field` constraints.
- **Change**: a proposed code modification with `original_code`, `new_code`,
  `line_start`, `line_end`, `change_type`, `confidence`, and [description](http://_vscodecontentref_/25).
- **AgentAnalysis**: result of an agent's `analyze()` call -- `issues_found`,
  `patterns_detected`, `suggestions`.
- **ConsensusDecision**: outcome of voting -- `decision`, `votes`, `winning_agent`,
  `confidence`.
- **RefactorSession**: full session state -- `refactor_id`, `status`, `target_path`,
  `agent_set`, `evolution_history`, `metrics`.
- **RefactorMetrics**: quantitative results -- `lines_changed`, `complexity_delta`,
  `issues_fixed`, `confidence_scores`.

### Agents ([agents](http://_vscodecontentref_/26))

Strategy implementations satisfying the `RefactoringAgent` protocol:

```python
@runtime_checkable
class RefactoringAgent(Protocol):
    agent_id: str
    def analyze(self, code: str) -> AgentAnalysis: ...
    def suggest_changes(self, code: str) -> list[Change]: ...
    def vote(self, changes: list[Change]) -> dict[str, float]: ...
    def validate_result(self, original: str, modified: str) -> bool: ...
```

No inheritance required. any class matching this shape is a valid agent.

**AgentRegistry** discovers agents through:
1. [agent_profiles.yaml](http://_vscodecontentref_/27) -- built-in agent configuration
2. `importlib.metadata` entry points (`snre.agents` group) -- plugin discovery

### Core ([core](http://_vscodecontentref_/28))

Domain logic and orchestration.

- **SwarmCoordinator**: manages the iterative refactoring loop. runs agents in parallel
  via `asyncio.to_thread` with a semaphore honoring `max_concurrent_agents`. fires
  `on_step_complete` callbacks after each applied change.
- **ConsensusEngine**: `calculate_consensus()` is a pure function. takes votes and
  threshold, returns `ConsensusDecision`. no mutable state.
- **ChangeTracker**: computes unified diffs and calculates `RefactorMetrics` between
  original and modified code. stateless.
- **EvolutionRecorder**: subscribes to coordinator events via callback. persists
  snapshots and evolution history through the repository.

### Ports ([ports](http://_vscodecontentref_/29))

Inbound adapters -- how users interact with the system.

- **CLI** (`cli.py`): Click command groups. `start`, `status`, `validate`, `api`.
  testable with `CliRunner`.
- **API** (`api.py`): FastAPI app factory. `create_app(container)` returns a configured
  `FastAPI` instance. testable with `TestClient` + `httpx`.

### Adapters ([adapters](http://_vscodecontentref_/30))

Outbound adapters -- how the system interacts with external resources.

- **SessionRepository protocol**: `save`, `load`, `list_active`, `delete`.
- **FileSessionRepository**: JSON files on disk with `filelock` for concurrent safety.
- **SQLiteSessionRepository**: SQLite-backed storage. same protocol.
- **CodeParser**: libcst wrapper. lazy-loaded to avoid import-time overhead.
- **IntegrationHook**: git operations via `pygit2` -- branch creation, hooks.

### Dependency Injection ([di.py](http://_vscodecontentref_/31))

Explicit `Container` class wires all components:

```python
class Container:
    def __init__(self, config: SNREConfig) -> None:
        self.config = config
        self.repository = FileSessionRepository(config.sessions_dir)
        self.registry = AgentRegistry.from_profiles("config/agent_profiles.yaml", config)
        self.consensus = ConsensusEngine(config)
        self.tracker = ChangeTracker(config)
        self.recorder = EvolutionRecorder(config, self.repository)
        self.coordinator = SwarmCoordinator(
            config=config, registry=self.registry, repository=self.repository,
            consensus=self.consensus, tracker=self.tracker, recorder=self.recorder,
        )
```

No framework. no global state. tests create their own containers with mock
implementations.

### Error Hierarchy ([errors.py](http://_vscodecontentref_/32))

```
SNREError
    AgentError
    ConsensusError
    SessionError
    ConfigError
    AgentNotFoundError
    SessionNotFoundError
```

All errors carry descriptive messages. no generic "Invalid input" style messages.

## Agent Priority System

| Agent | Priority | Confidence Threshold |
|---|---|---|
| security_enforcer | 9 | 0.8 |
| pattern_optimizer | 7 | 0.7 |
| loop_simplifier | 6 | 0.7 |

Higher priority agents can override lower priority suggestions when confidence
exceeds the threshold.

## Consensus Mechanism

1. Each agent votes on all proposed changes with a float score (0.0 to 1.0).
2. Votes are aggregated per change.
3. Changes below `consensus_threshold` (default 0.6) are rejected.
4. The highest-confidence accepted change is applied per iteration.
5. The loop repeats until no changes pass consensus or `max_iterations` is reached.

## Session Lifecycle

```
PENDING --> IN_PROGRESS --> COMPLETED
                |
                v
             FAILED
```

Sessions are persisted after each state transition. the coordinator saves
session state through the repository after every iteration.

## Observability

- **structlog**: JSON-formatted structured logs with correlation IDs bound per session.
  console output in development, JSON in production.
- **Prometheus**: counters, histograms, and gauges exposed at `/metrics`.
  - `snre_refactor_sessions_total`
  - `snre_agent_latency_seconds` (labeled by `agent_id`)
  - `snre_active_sessions`
  - `snre_consensus_rounds_total`

## Configuration Hierarchy

Configuration is resolved in this order (later overrides earlier):

1. Field defaults in `SNREConfig`
2. [settings.yaml](http://_vscodecontentref_/33)
3. `.env` file
4. Environment variables (`SNRE_` prefix)

## Legacy Directories

The [agents](http://_vscodecontentref_/34), [core](http://_vscodecontentref_/35), and [interface](http://_vscodecontentref_/36) directories at the project root are the
pre-overhaul implementations. they remain for backwards compatibility with
[main.py](http://_vscodecontentref_/37) but all new development targets the [snre](http://_vscodecontentref_/38) package.

## Dependencies

| Package | Purpose |
|---|---|
| pydantic + pydantic-settings | model validation, typed config |
| click | CLI framework |
| fastapi + uvicorn | async API server |
| libcst | concrete syntax tree transforms |
| pygit2 | git integration |
| pyyaml | YAML config parsing |
| filelock | concurrent file access safety |
| structlog | structured logging |
| prometheus-client | metrics exposition |
