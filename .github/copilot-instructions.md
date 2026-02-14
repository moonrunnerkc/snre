# SNRE Overhaul Guide -- Copilot Instructions

Author: Bradley R. Kinnard
Project: Swarm Neural Refactoring Engine (SNRE)
License: Apache-2.0
Last updated: 2026-02-13

This file is the single source of truth for all coding, documentation, architecture,
and agent behavior rules for the SNRE overhaul. Read it fully before writing any code.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Current State Audit](#2-current-state-audit)
3. [Target Architecture](#3-target-architecture)
4. [Phase 1 -- Stabilization and Cleanup](#4-phase-1----stabilization-and-cleanup)
5. [Phase 2 -- Structural Refactoring](#5-phase-2----structural-refactoring)
6. [Phase 3 -- System Modernization](#6-phase-3----system-modernization)
7. [Reliability Strategy](#7-reliability-strategy)
8. [Coding Rules](#8-coding-rules)
9. [Writing and Documentation Rules](#9-writing-and-documentation-rules)
10. [Agent Behavior Rules](#10-agent-behavior-rules)
11. [File Manifest](#11-file-manifest)
12. [Dependency Manifest](#12-dependency-manifest)

---

## 1. System Overview

SNRE is a distributed agent-based code refactoring engine. Multiple specialized agents
(pattern optimization, security enforcement, loop simplification) analyze Python source
code, propose changes, vote via a consensus mechanism, and produce a refactored output.

Core data flow:

```
User Input --> SwarmCoordinator --> Agents (analyze + suggest) --> ConsensusEngine --> ChangeTracker --> EvolutionRecorder --> Output
```

Key components:

- **Agents**: strategy implementations that detect patterns, vulnerabilities, or
  inefficiencies in source code and propose concrete `Change` objects.
- **SwarmCoordinator**: orchestrates agent lifecycle, session management, and the
  iterative refactoring loop.
- **ConsensusEngine**: collects votes from agents on proposed changes and determines
  which changes meet the confidence threshold.
- **ChangeTracker**: computes diffs and metrics between original and refactored code.
- **EvolutionRecorder**: persists snapshots and evolution history to disk.
- **Interfaces**: CLI (argparse-based) and REST API (Flask-based) entry points.

---

## 2. Current State Audit

This section is the honest assessment of the codebase as of 2026-02-13. Every item
listed here is a verified defect or architectural problem, not speculation.

### 2.1 God-File: contracts.py (828 lines)

`contracts.py` mixes the following concerns into one file:

- Abstract base classes (`BaseAgent`, `PatternOptimizer`, `SecurityEnforcer`, `LoopSimplifier`)
- Concrete dataclasses (`Config`, `Change`, `AgentAnalysis`, `ConsensusDecision`,
  `EvolutionStep`, `RefactorMetrics`, `RefactorSession`, `AgentProfile`)
- Enums (`RefactorStatus`, `ChangeType`)
- Stub implementations (every method in `CLIInterface`, `APIInterface`,
  `IntegrationHook`, `EvolutionRecorder`, `ChangeTracker`, `SwarmCoordinator`,
  `FileManager`, `CodeParser`, `AgentFactory` is `pass`)
- Error hierarchy (`SNREError` and six subclasses)
- A validation function (`validate_contracts`)

The file declares itself "FROZEN" but there is no enforcement mechanism. Downstream
implementations silently diverge from these stubs.

### 2.2 Broken Inheritance

Agents in `agents/` do not actually inherit from the contract ABCs:

- `agents/pattern_optimizer.py` declares `class PatternOptimizer` as a standalone class.
  It does not subclass `contracts.PatternOptimizer` or `agents.base_agent.BaseAgent`.
- Same applies to `agents/security_enforcer.py` and `agents/loop_simplifier.py`.
- `agents/base_agent.py` declares its own `BaseAgent(ABC)` that duplicates the one in
  `contracts.py` but imports `Config`, `AgentAnalysis`, `Change` from contracts.
- The contract tests use `hasattr` checks, which prove nothing about behavior.

### 2.3 Triple Entry Points

Three files do the same thing:

| File             | Mechanism                              | Status         |
|------------------|----------------------------------------|----------------|
| `main.py`        | `SNREApplication` class, argparse      | Primary        |
| `snre_cli.py`    | Manual bootstrap, argparse             | Redundant      |
| `snre_direct.py` | Copy-pasted argparse + handler logic   | Redundant      |

Every bug fix must be applied in three places. `snre_direct.py` alone is 400+ lines of
duplicated logic.

### 2.4 Config Anti-Pattern

`Config.__init__` uses a blind `setattr` loop:

```python
def __init__(self, **kwargs):
    for key, value in kwargs.items():
        setattr(self, key, value)
```

No validation. No type checking. Any typo silently becomes an attribute. The dataclass
field defaults are never applied because `__init__` is overridden.

### 2.5 Session State Problems

- Sessions are JSON files on disk (`data/refactor_logs/sessions/`).
- No file locking. Concurrent CLI invocations can corrupt session state.
- `RefactorSession.to_dict()` / `from_dict()` is hand-rolled serialization with no
  schema validation.
- `SwarmCoordinator` reads/writes directly to the filesystem with no repository
  abstraction.

### 2.6 Synchronous Pipeline

The `parallel_agent_execution` flag exists in `config/settings.yaml` but there is zero
implementation of parallel execution anywhere. The entire refactoring loop in
`SwarmCoordinator._execute_refactoring` is a sequential `for` loop over agents.

### 2.7 Tight Coupling Summary

| Problem                                         | Location                        |
|--------------------------------------------------|---------------------------------|
| `Config` uses `setattr` with no validation       | `contracts.py:37-42`           |
| Agents import from contracts but skip ABCs       | `agents/*.py`                  |
| `SwarmCoordinator` hardcodes filesystem paths    | `core/swarm_coordinator.py:43` |
| `CLIInterface` takes raw coordinator, no type    | `interface/cli.py:20`          |
| `APIInterface` creates Flask app in `__init__`   | `interface/api.py:24`          |
| `libcst` is required for all agents at import    | `agents/base_agent.py:7`       |
| `ConsensusEngine` stores no config reference     | `core/consensus_engine.py`     |
| `EvolutionRecorder` hardcodes `data/` paths      | `core/evolution_recorder.py`   |

### 2.8 Testing Gaps

- `test_contracts.py`: tests `hasattr` on classes, not behavior.
- `test_functional.py`: wraps imports in `try/except ImportError` with `None` fallbacks.
  Tests skip silently when modules break.
- `test_working_components.py`: exists only because the real tests are unreliable.
- No mocking of file I/O.
- No fixture isolation.
- No property-based testing.
- Zero tests for session persistence, concurrent access, or error recovery.

### 2.9 Maintainability Scores

| Dimension      | Score | Rationale                                                    |
|----------------|-------|--------------------------------------------------------------|
| Modularity     | 3/10  | god-file contracts, duplicated entry points, no DI           |
| Type Safety    | 4/10  | `Config(**kwargs)` + `setattr`, agents skip contract ABCs    |
| Testability    | 3/10  | Flask in `__init__`, no repository pattern, `hasattr` tests  |
| Scalability    | 2/10  | synchronous pipeline, file-based state, no locking           |
| Correctness    | 5/10  | agents work individually but integration untested            |
| DRY            | 2/10  | three entry points, duplicated argparse, copy-pasted logic   |

---

## 3. Target Architecture

### 3.1 Target Directory Structure

```
snre/
    models/
        __init__.py
        config.py           # pydantic-settings SNREConfig (replaces Config dataclass)
        session.py           # RefactorSession, EvolutionStep, RefactorMetrics
        changes.py           # Change, ConsensusDecision, AgentAnalysis
        enums.py             # RefactorStatus, ChangeType
        profiles.py          # AgentProfile

    agents/
        __init__.py
        protocol.py          # RefactoringAgent Protocol (runtime-checkable, replaces ABC)
        base.py              # shared helpers (parse code, calculate complexity)
        pattern_optimizer.py
        security_enforcer.py
        loop_simplifier.py
        registry.py          # AgentRegistry (auto-discovery from agent_profiles.yaml)

    core/
        __init__.py
        coordinator.py       # SwarmCoordinator (takes Repository + AgentRegistry via DI)
        consensus.py         # ConsensusEngine (pure function pipeline, no mutable state)
        tracker.py           # ChangeTracker (stateless diff and metrics)
        recorder.py          # EvolutionRecorder (takes Repository via DI, event hooks)

    ports/
        __init__.py
        cli.py               # single CLI entry point (Click-based command groups)
        api.py               # FastAPI app factory (replaces Flask, async-ready)

    adapters/
        __init__.py
        repository.py        # SessionRepository protocol + FileSessionRepository impl
        git_hook.py           # git integration (replaces IntegrationHook)
        parser.py             # CodeParser (libcst wrapper, lazy-loaded)

    errors.py                # SNREError hierarchy (one file)
    di.py                    # dependency injection container
    __main__.py              # single entry: python -m snre

config/
    settings.yaml
    agent_profiles.yaml

tests/
    __init__.py
    conftest.py              # shared fixtures, in-memory repository, mock agents
    unit/
        __init__.py
        test_agents.py
        test_consensus.py
        test_tracker.py
        test_repository.py
        test_config.py
        test_recorder.py
    integration/
        __init__.py
        test_coordinator.py
        test_cli.py
        test_api.py
    regression/
        __init__.py
        test_golden_files.py
        test_schema_compat.py
        test_determinism.py
    fixtures/
        sample_input.py
        expected_output.py
        old_session.json

docs/
    architecture.md
```

### 3.2 Design Patterns

**Protocol over ABC (Strategy Pattern)**

Replace broken inheritance with `typing.Protocol` + `@runtime_checkable`:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class RefactoringAgent(Protocol):
    agent_id: str

    def analyze(self, code: str) -> AgentAnalysis: ...
    def suggest_changes(self, code: str) -> list[Change]: ...
    def vote(self, changes: list[Change]) -> dict[str, float]: ...
    def validate_result(self, original: str, modified: str) -> bool: ...
```

Any class matching this shape is a valid agent. No inheritance required. Registration
validates at runtime via `isinstance(agent, RefactoringAgent)`.

**Pydantic Settings for Config**

Replace `Config(**kwargs)` with:

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class SNREConfig(BaseSettings):
    max_concurrent_agents: int = Field(5, ge=1, le=50)
    consensus_threshold: float = Field(0.6, ge=0.0, le=1.0)
    max_iterations: int = Field(10, ge=1, le=100)
    timeout_seconds: int = Field(300, ge=10)
    enable_evolution_log: bool = True
    snapshot_frequency: int = Field(5, ge=1)
    max_snapshots: int = Field(100, ge=1)
    git_auto_commit: bool = False
    backup_original: bool = True
    create_branch: bool = True
    sessions_dir: str = "data/refactor_logs/sessions"
    snapshots_dir: str = "data/snapshots"
    logs_dir: str = "data/refactor_logs"

    model_config = SettingsConfigDict(
        env_prefix="SNRE_",
        yaml_file="config/settings.yaml",
    )
```

Validated, typed, env-overridable. Rejects invalid input at construction time.

**Repository Pattern for Session State**

```python
from typing import Protocol

class SessionRepository(Protocol):
    def save(self, session: RefactorSession) -> None: ...
    def load(self, session_id: UUID) -> RefactorSession: ...
    def list_active(self) -> list[UUID]: ...
    def delete(self, session_id: UUID) -> None: ...
```

`FileSessionRepository` uses `filelock` for safe concurrent access. Swappable to
SQLite without touching domain logic.

**Pipeline Data Flow**

```
Analyze (agents) --> Suggest (agents) --> Consensus (engine) --> Validate (agents)
       |                   |                    |                      |
       v                   v                    v                      v
                        EvolutionRecorder (observes via event hooks)
```

Each phase is a pure function: input in, output out. The coordinator wires them.
`EvolutionRecorder` subscribes to `on_step_complete` callbacks, not inline calls.

**Single Entry Point**

```bash
python -m snre start --path code.py --agents security_enforcer
python -m snre status <session-id>
python -m snre api --host 0.0.0.0 --port 8000
```

Click-based command groups. `pyproject.toml` points to `snre.__main__:main`.

---

## 4. Phase 1 -- Stabilization and Cleanup

**Goal**: stop the bleeding. make what exists actually work correctly.

**Exit criteria**: all tests pass without `skipif` guards. `mypy` clean on `agents/`
and `core/`. single working entry point. no `pass` stubs in active code.

### 4.1 Delete Redundant Entry Points

| Action                    | Detail                                               |
|---------------------------|------------------------------------------------------|
| Delete `snre_direct.py`   | 400+ lines of copy-pasted CLI logic                  |
| Delete `snre_cli.py`      | manual bootstrap duplicating `main.py`               |
| Verify `main.py` works    | `python main.py cli start --path examples/sample_refactor.py --agents pattern_optimizer` |

After deletion, there is exactly one way to invoke SNRE: `python main.py`.

### 4.2 Fix Agent Inheritance

Current state: `agents/pattern_optimizer.py` declares `class PatternOptimizer` as a
standalone class that does not inherit from `agents/base_agent.py:BaseAgent`.

Required changes:

- `PatternOptimizer` must inherit from `BaseAgent` in `agents/base_agent.py`.
- `SecurityEnforcer` must inherit from `BaseAgent` in `agents/base_agent.py`.
- `LoopSimplifier` must inherit from `BaseAgent` in `agents/base_agent.py`.
- Each must call `super().__init__(agent_id, config)`.
- Each must implement all abstract methods: `analyze`, `suggest_changes`, `vote`,
  `validate_result`.
- `get_priority` and `get_confidence_threshold` are already implemented in `BaseAgent`
  and do not need overrides unless the agent uses non-default values.

Verify: after changes, `isinstance(PatternOptimizer("test", config), BaseAgent)` must
return `True`.

### 4.3 Fix Config Validation

Replace the blind `setattr` loop in `Config.__init__`:

```python
@dataclass
class Config:
    max_concurrent_agents: int = 5
    consensus_threshold: float = 0.6
    max_iterations: int = 10
    timeout_seconds: int = 300
    enable_evolution_log: bool = True
    snapshot_frequency: int = 5
    max_snapshots: int = 100
    git_auto_commit: bool = False
    backup_original: bool = True
    create_branch: bool = True

    def __post_init__(self):
        if not 0.0 <= self.consensus_threshold <= 1.0:
            raise ValueError(f"consensus_threshold must be 0.0-1.0, got {self.consensus_threshold}")
        if self.max_concurrent_agents < 1:
            raise ValueError(f"max_concurrent_agents must be >= 1, got {self.max_concurrent_agents}")
        if self.max_iterations < 1:
            raise ValueError(f"max_iterations must be >= 1, got {self.max_iterations}")
        if self.timeout_seconds < 10:
            raise ValueError(f"timeout_seconds must be >= 10, got {self.timeout_seconds}")
```

Remove the custom `__init__`. Let `@dataclass` generate it. Use `__post_init__`
for validation. Update all call sites that pass arbitrary kwargs.

### 4.4 Add File Locking to Session Persistence

In `core/swarm_coordinator.py`, wrap session file reads and writes with `filelock`:

```python
from filelock import FileLock

def save_session(self, session: RefactorSession) -> None:
    session_file = os.path.join(self.sessions_dir, f"{session.refactor_id}.json")
    lock = FileLock(f"{session_file}.lock")
    with lock:
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
```

Add `filelock>=3.13.0` to `requirements.txt`.

### 4.5 Replace hasattr Contract Tests

Delete all `hasattr(SomeClass, "some_method")` tests. Replace with:

```python
def test_pattern_optimizer_satisfies_base_agent():
    config = Config()
    agent = PatternOptimizer("test", config)
    assert isinstance(agent, BaseAgent)
    result = agent.analyze("x = 1")
    assert isinstance(result, AgentAnalysis)
    assert isinstance(result.agent_id, str)
    assert isinstance(result.issues_found, int)
```

Every test must instantiate the class, call a real method, and assert on the return type
and content. No `hasattr`. No `try/except ImportError`.

### 4.6 Delete fix_quality_issues.py

`fix_quality_issues.py` is a band-aid script. Apply any legitimate fixes it contains
directly to the source files, then delete the script.

### 4.7 Fix RefactorMetrics Consistency

Some call sites expect `RefactorMetrics` as a dict, others as a dataclass. Standardize:
`RefactorMetrics` is always a dataclass. Use `.to_dict()` explicitly where JSON
serialization is needed. Remove all `isinstance(metrics, dict)` checks.

### 4.8 Run Type Checking

Run `mypy --strict` on `agents/` and `core/`. Fix all errors. Add `py.typed` marker
to the package root.

### 4.9 Remove Print Statements

Replace all `print(f"Warning: ...")` and `print(f"...")` in production code with
structured logging using the `logging` module. Use the format:

```python
import logging
logger = logging.getLogger(__name__)
logger.warning("failed to save session %s: %s", session.refactor_id, e)
```

No print statements in any module under `core/`, `agents/`, or `interface/`.

### 4.10 Phase 1 Verification

After all phase 1 tasks:

```bash
# all tests must pass
pytest tests/ -v --tb=short

# type checking must pass
mypy agents/ core/ --strict --ignore-missing-imports

# linting must pass
ruff check .

# single entry point must work
python main.py cli validate --path examples/sample_refactor.py

# no redundant files
test ! -f snre_direct.py
test ! -f snre_cli.py
test ! -f fix_quality_issues.py
```

---

## 5. Phase 2 -- Structural Refactoring

**Goal**: decouple components. introduce proper design patterns. delete `contracts.py`.

**Exit criteria**: `contracts.py` is deleted. no circular imports. every component is
independently testable with mock dependencies. all tests pass.

### 5.1 Extract models/ Package

Split `contracts.py` into focused modules:

| Target file         | Contents from contracts.py                                    |
|---------------------|---------------------------------------------------------------|
| `snre/models/enums.py`    | `RefactorStatus`, `ChangeType`                          |
| `snre/models/config.py`   | `SNREConfig` (pydantic-settings, replaces `Config`)     |
| `snre/models/changes.py`  | `Change`, `ConsensusDecision`, `AgentAnalysis`          |
| `snre/models/session.py`  | `RefactorSession`, `EvolutionStep`, `RefactorMetrics`   |
| `snre/models/profiles.py` | `AgentProfile`                                          |

Each model must:
- use pydantic `BaseModel` (not raw dataclass) for automatic validation and serialization
- expose `.model_dump()` instead of hand-rolled `.to_dict()`
- expose `model_validate(data)` instead of hand-rolled `.from_dict()`
- include type annotations for every field
- validate fields in validators where constraints exist

### 5.2 Create agents/protocol.py

Define the `RefactoringAgent` Protocol:

```python
from typing import Protocol, runtime_checkable
from snre.models.changes import AgentAnalysis, Change

@runtime_checkable
class RefactoringAgent(Protocol):
    agent_id: str

    def analyze(self, code: str) -> AgentAnalysis: ...
    def suggest_changes(self, code: str) -> list[Change]: ...
    def vote(self, changes: list[Change]) -> dict[str, float]: ...
    def validate_result(self, original: str, modified: str) -> bool: ...
```

Remove `BaseAgent` ABC from contracts. The `agents/base.py` file may still contain
shared helper methods (parse code, calculate complexity) as a mixin or standalone
functions, but it is no longer required as a base class.

### 5.3 Create agents/registry.py

```python
class AgentRegistry:
    """discovers and holds agent instances"""

    def __init__(self) -> None:
        self._agents: dict[str, RefactoringAgent] = {}

    def register(self, agent: RefactoringAgent) -> None:
        if not isinstance(agent, RefactoringAgent):
            raise TypeError(f"{type(agent).__name__} does not satisfy RefactoringAgent protocol")
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: str) -> RefactoringAgent:
        if agent_id not in self._agents:
            raise AgentNotFoundError(agent_id)
        return self._agents[agent_id]

    def all(self) -> dict[str, RefactoringAgent]:
        return dict(self._agents)

    @classmethod
    def from_profiles(cls, profiles_path: str, config: SNREConfig) -> "AgentRegistry":
        """load agent_profiles.yaml, instantiate and register all enabled agents"""
        ...
```

### 5.4 Create adapters/repository.py

```python
from typing import Protocol
from uuid import UUID

class SessionRepository(Protocol):
    def save(self, session: RefactorSession) -> None: ...
    def load(self, session_id: UUID) -> RefactorSession: ...
    def list_active(self) -> list[UUID]: ...
    def delete(self, session_id: UUID) -> None: ...

class FileSessionRepository:
    """file-based session storage with filelock"""

    def __init__(self, sessions_dir: str) -> None:
        self._dir = sessions_dir
        os.makedirs(self._dir, exist_ok=True)

    def save(self, session: RefactorSession) -> None:
        path = os.path.join(self._dir, f"{session.refactor_id}.json")
        lock = FileLock(f"{path}.lock")
        with lock:
            path_obj = Path(path)
            path_obj.write_text(session.model_dump_json(indent=2), encoding="utf-8")

    def load(self, session_id: UUID) -> RefactorSession:
        path = os.path.join(self._dir, f"{session_id}.json")
        if not os.path.exists(path):
            raise SessionNotFoundError(str(session_id))
        lock = FileLock(f"{path}.lock")
        with lock:
            raw = Path(path).read_text(encoding="utf-8")
        return RefactorSession.model_validate_json(raw)

    def list_active(self) -> list[UUID]:
        ...

    def delete(self, session_id: UUID) -> None:
        ...
```

### 5.5 Create di.py Dependency Container

```python
class Container:
    """lightweight DI wiring. no framework, just explicit construction."""

    def __init__(self, config: SNREConfig) -> None:
        self.config = config
        self.repository = FileSessionRepository(config.sessions_dir)
        self.registry = AgentRegistry.from_profiles("config/agent_profiles.yaml", config)
        self.consensus = ConsensusEngine(config)
        self.tracker = ChangeTracker(config)
        self.recorder = EvolutionRecorder(config, self.repository)
        self.coordinator = SwarmCoordinator(
            config=config,
            registry=self.registry,
            repository=self.repository,
            consensus=self.consensus,
            tracker=self.tracker,
            recorder=self.recorder,
        )
```

Every dependency is injected explicitly. No global state. Tests create their own
`Container` with mock implementations.

### 5.6 Replace Flask with FastAPI

Create `snre/ports/api.py`:

```python
from fastapi import FastAPI

def create_app(coordinator: SwarmCoordinator) -> FastAPI:
    app = FastAPI(title="SNRE", version="1.0.0")

    @app.post("/refactor/start")
    async def start_refactor(request: StartRefactorRequest) -> StartRefactorResponse:
        ...

    @app.get("/refactor/status/{refactor_id}")
    async def get_status(refactor_id: UUID) -> SessionStatusResponse:
        ...

    return app
```

App factory pattern. No Flask app created in `__init__`. Testable with `TestClient`.

### 5.7 Replace argparse with Click

Create `snre/ports/cli.py`:

```python
import click

@click.group()
def cli():
    """snre - swarm neural refactoring engine"""
    pass

@cli.command()
@click.option("--path", required=True, type=click.Path(exists=True))
@click.option("--agents", default="pattern_optimizer", help="comma-separated agent ids")
def start(path: str, agents: str):
    ...

@cli.command()
@click.argument("refactor_id")
def status(refactor_id: str):
    ...
```

Single file. Composable command groups. Testable with `CliRunner`.

### 5.8 Make ConsensusEngine Stateless

`ConsensusEngine.calculate_consensus` should be a pure function:

```python
def calculate_consensus(
    votes: dict[str, dict[str, float]],
    threshold: float,
) -> ConsensusDecision:
    ...
```

Input in, output out. No `self.config` reference inside the calculation. The threshold
is passed explicitly. This makes it trivially testable with parameterized inputs.

### 5.9 Add Event Hooks to SwarmCoordinator

```python
from typing import Callable

class SwarmCoordinator:
    def __init__(self, ..., on_step_complete: Callable[[EvolutionStep], None] | None = None):
        self._on_step_complete = on_step_complete or (lambda step: None)

    def _execute_refactoring(self, session_id: UUID) -> None:
        ...
        # after applying a change:
        self._on_step_complete(step)
```

`EvolutionRecorder` subscribes via this callback. No inline coupling. The coordinator
does not know about the recorder.

### 5.10 Delete contracts.py

After all models, protocols, and errors are extracted:

- Delete `contracts.py` from the project root.
- Delete `scripts/check_contract.py` (replaced by Protocol-based tests).
- Remove `refactored.py` if it is dead code.
- Update all import statements project-wide.

### 5.11 Phase 2 Verification

```bash
# contracts.py must not exist
test ! -f contracts.py

# no circular imports
python -c "from snre.models.config import SNREConfig; from snre.agents.registry import AgentRegistry; from snre.core.coordinator import SwarmCoordinator"

# all tests pass
pytest tests/ -v --tb=short

# type checking
mypy snre/ --strict

# linting
ruff check .
```

---

## 6. Phase 3 -- System Modernization

**Goal**: production-grade performance, observability, and extensibility.

**Exit criteria**: `docker compose up` runs API. parallel agent execution works.
structured logs with correlation IDs. zero `pass` stubs in the entire codebase.

### 6.1 Migrate Config to pydantic-settings

Replace the interim `Config` dataclass with full `pydantic-settings` model:

- environment variable overrides via `SNRE_` prefix
- YAML file loading via `yaml_file` setting
- `.env` file support
- all fields validated with `Field` constraints
- tests for boundary values and invalid input rejection

Add `pydantic-settings>=2.1.0` to dependencies.

### 6.2 Add asyncio to Coordinator

```python
import asyncio

async def _execute_refactoring(self, session_id: UUID) -> None:
    ...
    # run agents in parallel
    sem = asyncio.Semaphore(self.config.max_concurrent_agents)

    async def run_agent(agent_id: str) -> list[Change]:
        async with sem:
            agent = self.registry.get(agent_id)
            return await asyncio.to_thread(agent.suggest_changes, current_code)

    tasks = [run_agent(aid) for aid in session.agent_set]
    results = await asyncio.gather(*tasks)
    all_changes = [c for changes in results for c in changes]
```

Agents remain synchronous (libcst is CPU-bound). `asyncio.to_thread` offloads them.
The semaphore honors `max_concurrent_agents`.

### 6.3 Add Structured Logging

Replace all `print` and basic `logging` calls with `structlog`:

```python
import structlog

logger = structlog.get_logger()

logger.info("refactoring.step_applied",
    session_id=str(session_id),
    iteration=iteration,
    agent=best_change.agent_id,
    confidence=best_change.confidence,
)
```

- JSON output in production, console output in development.
- Correlation IDs bound per session via `structlog.contextvars`.
- No PII in log output. No secrets.

Add `structlog>=24.1.0` to dependencies.

### 6.4 Add Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

refactor_sessions_total = Counter("snre_refactor_sessions_total", "total sessions started")
agent_latency = Histogram("snre_agent_latency_seconds", "agent execution time", ["agent_id"])
active_sessions = Gauge("snre_active_sessions", "currently active sessions")
consensus_rounds = Counter("snre_consensus_rounds_total", "total consensus rounds")
```

Expose via `/metrics` endpoint on the FastAPI app.

Add `prometheus-client>=0.20.0` to dependencies.

### 6.5 Add SQLite Repository Adapter

```python
class SQLiteSessionRepository:
    """sqlite-based session storage. same SessionRepository protocol."""

    def __init__(self, db_path: str = "data/snre.db") -> None:
        ...
```

Optional upgrade from file-based storage. Same Protocol. Configured via
`SNREConfig.storage_backend` field (`"file"` or `"sqlite"`).

### 6.6 Add Agent Plugin System

Use `importlib.metadata` entry points:

```toml
# in a third-party agent's pyproject.toml:
[project.entry-points."snre.agents"]
my_agent = "my_package.agent:MyAgent"
```

`AgentRegistry.from_profiles` discovers installed plugins automatically.
Built-in agents are also registered via entry points.

### 6.7 Docker Multi-Stage Build

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS production
COPY snre/ snre/
COPY config/ config/
CMD ["python", "-m", "snre", "api", "--host", "0.0.0.0", "--port", "8000"]
```

Slim production image. Dev image adds test and lint tools.

### 6.8 Add Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: ruff check
        language: system
        types: [python]
      - id: ruff-format
        name: ruff format
        entry: ruff format --check
        language: system
        types: [python]
      - id: mypy
        name: mypy
        entry: mypy --strict
        language: system
        types: [python]
        pass_filenames: false
```

### 6.9 Phase 3 Verification

```bash
# docker
docker compose up -d
curl -s http://localhost:8000/docs | head -5

# parallel execution
python -m snre start --path examples/sample_refactor.py --agents pattern_optimizer,security_enforcer,loop_simplifier

# structured logs present
python -m snre start --path examples/sample_refactor.py --agents pattern_optimizer 2>&1 | python -c "import sys,json; [json.loads(l) for l in sys.stdin]"

# metrics endpoint
curl -s http://localhost:8000/metrics | grep snre_

# full test suite
pytest tests/ -v --tb=short
```

---

## 7. Reliability Strategy

### 7.1 Testing Pyramid

```
                    /\
                   /  \         E2E (2-3 tests)
                  /----\        CLI -> Coordinator -> Agents -> Disk
                 /      \
                /--------\      Integration (15-20 tests)
               /          \    Coordinator + real agents, mock repository
              /------------\
             /              \   Unit (50+ tests)
            /----------------\  Each agent, consensus, tracker, repository
```

### 7.2 Unit Test Requirements

| Component              | Strategy                                                | Key Assertions                                         |
|------------------------|---------------------------------------------------------|--------------------------------------------------------|
| Each Agent             | feed known code patterns, assert exact `Change` output  | correct `line_start`, `confidence`, `change_type`      |
| `ConsensusEngine`      | pure function, parameterized tests with edge cases      | tie-breaking, below-threshold rejection, empty votes   |
| `ChangeTracker`        | diff known strings, assert metrics                      | `lines_changed`, `complexity_delta` accuracy           |
| `FileSessionRepository`| `tmp_path` fixture, assert JSON schema                  | round-trip `save -> load`, concurrent access           |
| `SNREConfig`           | validate boundaries, env override, invalid rejection    | `ValidationError` on `consensus_threshold=1.5`         |
| `AgentRegistry`        | register valid/invalid agents, assert Protocol check    | `TypeError` on non-conforming class                    |

### 7.3 Integration Test Requirements

| Scenario                          | Components Under Test             | Mock                   |
|-----------------------------------|-----------------------------------|------------------------|
| Full refactor of sample_refactor.py| Coordinator + all agents + consensus | Repository (in-memory) |
| Session persistence across restart | Coordinator + FileRepository      | None                   |
| Agent failure mid-session          | Coordinator + one broken agent    | Agent that raises      |
| Concurrent session access          | Two coordinators, same repository | None (tests locking)   |
| CLI end-to-end                     | Click CLI + Coordinator           | Repository (in-memory) |
| API end-to-end                     | FastAPI TestClient + Coordinator  | Repository (in-memory) |

### 7.4 Regression Test Requirements

| Trigger                  | Test                                                              |
|--------------------------|-------------------------------------------------------------------|
| Any change to `models/`  | schema compat: old session JSON deserializes with new model       |
| Any change to `agents/`  | golden file tests: known input produces expected output           |
| Any change to `consensus`| determinism: same input always produces same ranked output        |
| CI on every PR           | full pyramid runs. no `skipif`. failures are failures.            |

### 7.5 Contract Enforcement via Protocol

Replace `scripts/check_contract.py` and `hasattr` tests with:

```python
def test_all_agents_satisfy_protocol():
    for agent_cls in [PatternOptimizer, SecurityEnforcer, LoopSimplifier]:
        config = SNREConfig()
        agent = agent_cls("test", config)
        assert isinstance(agent, RefactoringAgent), \
            f"{agent_cls.__name__} does not satisfy RefactoringAgent protocol"
```

One test. Catches everything. No file-reading hacks.

### 7.6 Test Rules

- no trivial tests. every test must execute real logic.
- no `try/except ImportError` in test files.
- no `hasattr` assertions.
- no `skipif` unless the skip reason is a documented platform limitation.
- use `tmp_path` for all file I/O in tests. never write to the real filesystem.
- use deterministic seeds where randomness is involved. log the seed.
- tests must run offline. no network calls.
- use `pytest.raises` with `match=` for error assertions.

---

## 8. Coding Rules

These rules apply to every line of code written during the overhaul.

### 8.1 Real Systems Only

- no demos, no mocks in production code, no placeholder logic.
- everything must run and produce real output.
- if a feature is not implemented, it does not exist in the codebase.
- roadmap items are clearly marked as NOT IMPLEMENTED in docs, never in code.

### 8.2 No Pseudocode

- all code must be concrete, runnable, and specific to SNRE.
- no `# TODO: implement this` with a `pass` body.
- no `raise NotImplementedError` in any shipped code.
- no `...` (Ellipsis) as a function body outside of Protocol definitions.

### 8.3 Deterministic Where Possible

- same input and seed must produce the same result inside the software boundary.
- seeds are logged when randomness is used.
- any nondeterministic behavior (timestamps, UUIDs) is documented and isolated.

### 8.4 Verifiable Behavior

- claims must be provable through tests, logs, or reproducible runs.
- if it cannot be proven, it does not get claimed.
- no "this is fast" without a benchmark. no "this is secure" without a scan.

### 8.5 Phase-Based Building

- build in clear phases (see sections 4, 5, 6).
- each phase must run, test, and verify before moving forward.
- never start phase N+1 until phase N passes all verification checks.

### 8.6 Test Coverage Required

- core modules (`core/`, `agents/`, `models/`) must have real tests.
- no trivial tests that assert `True == True` or `hasattr(cls, "method")`.
- minimum 80% line coverage for `core/` and `agents/`.
- coverage does not count toward the target if the tests are meaningless.

### 8.7 Offline-First

- system must run locally without network access unless explicitly required.
- all dependencies pinned in `requirements.txt` with exact versions.
- no hidden cloud reliance. no telemetry. no call-home.

### 8.8 Explicit Structure

Clear separation:

| Directory     | Purpose                                |
|---------------|----------------------------------------|
| `snre/models/`   | pure data definitions. zero logic.     |
| `snre/agents/`   | strategy implementations.              |
| `snre/core/`     | domain logic, orchestration.           |
| `snre/ports/`    | inbound adapters (CLI, API).           |
| `snre/adapters/` | outbound adapters (filesystem, git).   |
| `tests/`         | all tests. no test code in `snre/`.    |
| `config/`        | YAML configuration files.              |

No random utility sprawl. No `utils.py` or `helpers.py` junk drawers.

### 8.9 Production-Grade Style

- PEP 8 formatting. enforced by `ruff`.
- consistent naming: `snake_case` for functions and variables, `PascalCase` for classes,
  `ALL_CAPS` for constants.
- lowercase comments. no decorative comments. no comment banners.
- concise docstrings: explain the why, not the what.
  - good: `"extract owner/repo from various GitHub URL formats. strips .git cruft."`
  - bad: `"Parses the GitHub repository URL into owner and repository components.
    Returns a tuple of two strings representing the owner and repository."`
- no em dashes in any writing. use `--` if needed.
- type hints on all public functions, methods, and class attributes.
- use `#` for inline comments. triple quotes only for docstrings.
- prefer walrus operator (`if match := ...`) when it improves clarity.
- raise precise errors with blunt, helpful messages.

### 8.10 No Invented Architecture

- do not create modules or features that do not exist in the target architecture.
- the file manifest in section 11 is the source of truth.
- if a file is not listed there, it should not be created.
- roadmap items must be clearly marked as not implemented in documentation.

### 8.11 Logging and Traceability

- important state changes must be traceable via structured logs.
- use `structlog` (phase 3) or `logging` (phases 1-2).
- format: `%(asctime)s | %(levelname)s | %(name)s | %(message)s` (phases 1-2).
- runs should be reproducible. log configuration, seeds, and agent set at session start.

### 8.12 Dependency Discipline

- pin exact versions in `requirements.txt`.
- avoid unnecessary libraries. justify every dependency.
- document why each dependency exists in section 12.

### 8.13 Clean Clone Requirement

System must run from a fresh clone:

```bash
git clone <repo>
cd snre
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py cli validate --path examples/sample_refactor.py
pytest tests/ -v
```

If it does not work from a clean clone, it is broken.

### 8.14 Author Attribution

Include at the top of every new file:

```python
# Author: Bradley R. Kinnard
```

### 8.15 Human-Written Code Style

- vary coding style naturally. avoid perfectly uniform structures.
- use manual loops where they are clearer than one-liners.
- do not use AI-typical patterns (excessive chained functional calls, overly
  symmetrical code, robotically consistent formatting beyond PEP 8).

---

## 9. Writing and Documentation Rules

### 9.1 Literal and Accurate

- docs must reflect reality of the code. no exaggeration.
- no speculative claims about performance or capabilities.

### 9.2 No Marketing Tone

- technical, direct, professional.
- no hype language. no "revolutionary", "cutting-edge", "state-of-the-art".

### 9.3 No AI-Style Filler

- no generic explanations that could apply to any project.
- no motivational fluff.
- no decorative writing.
- no em dashes.

### 9.4 README Must Match System

- if behavior changes, README updates in the same commit.
- never imply features that do not exist.
- never claim capabilities that are not tested.

### 9.5 Evidence-Backed Claims

- performance claims require benchmarks.
- security claims require scan results.
- determinism claims require reproducible test runs.
- if proof is missing, the claim is removed.

### 9.6 Clear Instructions

Every README and doc must include:

- install steps
- run steps
- test steps
- architecture overview
- known limitations
- verification method

### 9.7 Human-Written Tone

- natural but serious. not overly polished.
- no obvious AI phrasing ("I'd be happy to", "Let me explain", "As you can see").

### 9.8 Consistent Naming

- use stable naming across code, docs, and architecture.
- if the code calls it `SwarmCoordinator`, the docs call it `SwarmCoordinator`.
- no renaming without updating all references.

### 9.9 Update Docs Per Phase

- documentation updates happen at the end of completed phases.
- never update docs for features that have not been implemented.
- never update docs mid-build.

---

## 10. Agent Behavior Rules

These rules govern how Copilot (or any AI agent) must behave when working on this
codebase.

### 10.1 Read Instructions First

- agent must read this file (`.github/copilot-instructions.md`) before writing any code.
- agent must not generate code until it has demonstrated understanding of the current
  phase and the target architecture.

### 10.2 Prove Understanding

- before implementing any change, agent must state:
  - which phase the task belongs to
  - what files will be created/modified/deleted
  - what the verification steps are

### 10.3 No Invention

- agent cannot invent features, modules, or architectural patterns not described here.
- agent cannot add dependencies not listed in section 12.
- agent cannot create files not listed in section 11.
- if something is needed that is not in this document, agent must stop and request
  approval.

### 10.4 Test After Each Change

- every phase must run and pass tests after each task completion.
- `pytest tests/ -v --tb=short` must pass before moving to the next task.
- if tests fail, agent must fix the failure before proceeding.

### 10.5 Stop on Conflict

- if instructions in this file conflict with the actual codebase state, agent must
  stop and report the conflict.
- do not silently resolve conflicts by inventing workarounds.
- do not guess. ask.

### 10.6 No Large Unverified Drops

- incremental implementation only.
- maximum one task (from the phase tables) per change set.
- each change set must be independently testable and verifiable.

### 10.7 Update Docs As You Go

- after each verified phase completion, update:
  - `README.md` (if behavior changed)
  - `docs/architecture.md` (if structure changed)
  - this file (mark completed tasks)
- never update docs before the code is verified.

### 10.8 No Stubs

- never leave `pass` as a function body.
- never leave `raise NotImplementedError`.
- never leave `...` (Ellipsis) except in Protocol method signatures.
- if a function cannot be fully implemented yet, do not create it.

### 10.9 No Debugging Leftovers

- no `print()` debug statements in committed code.
- no `breakpoint()` calls.
- no commented-out code blocks.
- no scratch files.
- no temporary test files.

---

## 11. File Manifest

Files that must exist in the target architecture. No files outside this list should be
created during the overhaul. Files marked [DELETE] must be removed during the
appropriate phase.

### Root

| File                 | Phase   | Purpose                              |
|----------------------|---------|--------------------------------------|
| `pyproject.toml`     | 1       | package metadata and tool config     |
| `requirements.txt`   | 1       | pinned dependencies                  |
| `Makefile`           | 1       | build/test/lint commands             |
| `Dockerfile`         | 3       | multi-stage container build          |
| `docker-compose.yml` | 3       | service orchestration                |
| `ruff.toml`          | 1       | linter/formatter config              |
| `README.md`          | 1,2,3   | project documentation                |
| `LICENSE.md`         | --      | license file                         |
| `NOTICE.md`          | --      | attribution notices                  |
| `setup.py`           | 1       | setuptools compatibility (may remove)|
| `.pre-commit-config.yaml` | 3  | pre-commit hook definitions          |

### [DELETE] in Phase 1

| File                    | Reason                         |
|-------------------------|--------------------------------|
| `snre_direct.py`        | redundant CLI entry point      |
| `snre_cli.py`           | redundant CLI entry point      |
| `fix_quality_issues.py` | band-aid script                |
| `refactored.py`         | dead code / artifact           |

### [DELETE] in Phase 2

| File                       | Reason                                 |
|----------------------------|----------------------------------------|
| `contracts.py`             | god-file, replaced by `snre/models/`   |
| `scripts/check_contract.py`| replaced by Protocol-based tests       |

### snre/ Package (Phase 2+)

| File                            | Purpose                                      |
|---------------------------------|----------------------------------------------|
| `snre/__init__.py`              | package root                                 |
| `snre/__main__.py`              | `python -m snre` entry point                 |
| `snre/errors.py`                | error hierarchy                              |
| `snre/di.py`                    | dependency injection container               |
| `snre/models/__init__.py`       | models package                               |
| `snre/models/config.py`         | SNREConfig (pydantic-settings)               |
| `snre/models/enums.py`          | RefactorStatus, ChangeType                   |
| `snre/models/changes.py`        | Change, ConsensusDecision, AgentAnalysis     |
| `snre/models/session.py`        | RefactorSession, EvolutionStep, RefactorMetrics |
| `snre/models/profiles.py`       | AgentProfile                                 |
| `snre/agents/__init__.py`       | agents package                               |
| `snre/agents/protocol.py`       | RefactoringAgent Protocol                    |
| `snre/agents/base.py`           | shared helpers (parser, complexity calc)     |
| `snre/agents/pattern_optimizer.py` | pattern optimization agent                |
| `snre/agents/security_enforcer.py` | security enforcement agent                |
| `snre/agents/loop_simplifier.py`   | loop simplification agent                 |
| `snre/agents/registry.py`       | AgentRegistry                                |
| `snre/core/__init__.py`         | core package                                 |
| `snre/core/coordinator.py`      | SwarmCoordinator                             |
| `snre/core/consensus.py`        | ConsensusEngine                              |
| `snre/core/tracker.py`          | ChangeTracker                                |
| `snre/core/recorder.py`         | EvolutionRecorder                            |
| `snre/ports/__init__.py`        | ports package                                |
| `snre/ports/cli.py`             | Click CLI                                    |
| `snre/ports/api.py`             | FastAPI app factory                          |
| `snre/adapters/__init__.py`     | adapters package                             |
| `snre/adapters/repository.py`   | SessionRepository protocol + impl           |
| `snre/adapters/git_hook.py`     | git integration                              |
| `snre/adapters/parser.py`       | CodeParser (libcst wrapper)                  |

### Tests (Phase 1+)

| File                                | Purpose                                |
|-------------------------------------|----------------------------------------|
| `tests/__init__.py`                 | test package                           |
| `tests/conftest.py`                 | shared fixtures                        |
| `tests/unit/__init__.py`            | unit test package                      |
| `tests/unit/test_agents.py`         | agent behavior tests                   |
| `tests/unit/test_consensus.py`      | consensus engine tests                 |
| `tests/unit/test_tracker.py`        | change tracker tests                   |
| `tests/unit/test_repository.py`     | file repository tests                  |
| `tests/unit/test_config.py`         | config validation tests                |
| `tests/unit/test_recorder.py`       | evolution recorder tests               |
| `tests/integration/__init__.py`     | integration test package               |
| `tests/integration/test_coordinator.py` | coordinator integration tests      |
| `tests/integration/test_cli.py`     | CLI integration tests                  |
| `tests/integration/test_api.py`     | API integration tests                  |
| `tests/regression/__init__.py`      | regression test package                |
| `tests/regression/test_golden_files.py` | golden file comparison tests       |
| `tests/regression/test_schema_compat.py`| session schema compatibility tests |
| `tests/regression/test_determinism.py`  | determinism verification tests     |
| `tests/fixtures/sample_input.py`    | known input for golden file tests      |
| `tests/fixtures/expected_output.py` | expected output for golden file tests  |
| `tests/fixtures/old_session.json`   | old-format session for schema compat   |

### Config

| File                       | Purpose                     |
|----------------------------|-----------------------------|
| `config/settings.yaml`     | runtime configuration       |
| `config/agent_profiles.yaml` | agent profile definitions |

### Docs

| File                    | Purpose                  |
|-------------------------|--------------------------|
| `docs/architecture.md`  | architecture overview    |

---

## 12. Dependency Manifest

Every dependency must be justified. No unnecessary packages.

### Production Dependencies

| Package              | Version   | Justification                                     |
|----------------------|-----------|----------------------------------------------------|
| `click`              | `>=8.1.7` | CLI framework. replaces argparse. testable.        |
| `fastapi`            | `>=0.109.0`| async API framework. replaces Flask. phase 2+.    |
| `uvicorn`            | `>=0.27.0`| ASGI server for FastAPI. phase 2+.                |
| `libcst`             | `>=1.1.0` | concrete syntax tree for Python code transforms.  |
| `pydantic`           | `>=2.5.0` | data validation for models. already in use.       |
| `pydantic-settings`  | `>=2.1.0` | config from env/yaml/files. replaces raw Config.  |
| `pygit2`             | `>=1.13.0`| git integration for hooks and branches.           |
| `pyyaml`             | `>=6.0.1` | YAML config file parsing.                         |
| `filelock`           | `>=3.13.0`| file-based locking for session persistence.       |
| `structlog`          | `>=24.1.0`| structured logging. phase 3.                      |
| `prometheus-client`  | `>=0.20.0`| metrics exposition. phase 3.                      |
| `typing-extensions`  | `>=4.8.0` | backport typing features for 3.9/3.10.           |

### Development Dependencies

| Package              | Version    | Justification                               |
|----------------------|------------|----------------------------------------------|
| `pytest`             | `>=7.4.3`  | test framework.                              |
| `pytest-cov`         | `>=4.1.0`  | coverage reporting.                          |
| `pytest-asyncio`     | `>=0.23.0` | async test support. phase 3.                |
| `httpx`              | `>=0.27.0` | FastAPI TestClient dependency. phase 2+.     |
| `ruff`               | `>=0.1.6`  | linter and formatter.                        |
| `mypy`               | `>=1.7.1`  | static type checker.                         |
| `bandit`             | `>=1.7.5`  | security scanner.                            |
| `types-pyyaml`       | `>=6.0.12` | type stubs for pyyaml.                       |

### Dependencies to Remove

| Package              | Reason                                            |
|----------------------|---------------------------------------------------|
| `flask`              | replaced by FastAPI in phase 2                    |
| `ast-decompiler`     | unused in any module                              |
| `uuid`               | stdlib `uuid` is sufficient, pypi package not needed |
| `python-dateutil`    | stdlib `datetime.fromisoformat` is sufficient     |
| `types-python-dateutil` | removed with `python-dateutil`                 |
| `safety`             | use `pip-audit` instead if needed                 |
| `black`              | ruff handles formatting                           |

---

## Phase Completion Tracker

Mark each task as it is completed. Do not mark tasks that have not been verified.

### Phase 1

- [x] 4.1 Delete redundant entry points
- [x] 4.2 Fix agent inheritance
- [x] 4.3 Fix Config validation
- [x] 4.4 Add file locking to session persistence
- [x] 4.5 Replace hasattr contract tests
- [x] 4.6 Delete fix_quality_issues.py
- [x] 4.7 Fix RefactorMetrics consistency
- [x] 4.8 Run type checking (mypy --strict on agents/ and core/)
- [x] 4.9 Remove print statements (replace with logging)
- [x] 4.10 Phase 1 verification passes

### Phase 2

- [x] 5.1 Extract models/ package
- [x] 5.2 Create agents/protocol.py
- [x] 5.3 Create agents/registry.py
- [x] 5.4 Create adapters/repository.py
- [x] 5.5 Create di.py dependency container
- [x] 5.6 Replace Flask with FastAPI
- [x] 5.7 Replace argparse with Click
- [x] 5.8 Make ConsensusEngine stateless
- [x] 5.9 Add event hooks to SwarmCoordinator
- [x] 5.10 Delete contracts.py
- [x] 5.11 Phase 2 verification passes

### Phase 3

- [x] 6.1 Migrate Config to pydantic-settings
- [x] 6.2 Add asyncio to coordinator
- [x] 6.3 Add structured logging (structlog)
- [x] 6.4 Add Prometheus metrics
- [x] 6.5 Add SQLite repository adapter
- [x] 6.6 Add agent plugin system
- [x] 6.7 Docker multi-stage build
- [x] 6.8 Add pre-commit hooks
- [x] 6.9 Phase 3 verification passes
