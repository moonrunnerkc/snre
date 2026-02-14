# SNRE Architecture Documentation

## Overview

The Swarm Neural Refactoring Engine (SNRE) is a distributed agent-based code refactoring system that uses consensus mechanisms and evolution tracking to automatically improve code quality, security, and performance.

## Architecture Components

### 🧠 Core System
- **SwarmCoordinator**: Orchestrates multiple agents, manages refactoring sessions
- **ConsensusEngine**: Handles agent voting and decision making with configurable thresholds
- **ChangeTracker**: Tracks code changes, generates diffs, calculates metrics
- **EvolutionRecorder**: Records refactoring evolution history and creates snapshots

### 🤖 Agent System
- **BaseAgent**: Abstract base class defining agent interface contract
- **PatternOptimizer**: Detects and optimizes code patterns (list comprehensions, etc.)
- **SecurityEnforcer**: Scans for vulnerabilities and enforces security best practices
- **LoopSimplifier**: Optimizes loops and reduces nesting complexity

### 🔌 Interfaces
- **CLI Interface**: Command-line tool for interactive refactoring
- **API Interface**: REST API for programmatic access
- **Integration Hook**: Git hooks and IDE integrations

## Data Flow

```
User Request → SwarmCoordinator → Agents → ConsensusEngine → ChangeTracker → EvolutionRecorder
     ↑                                                                              ↓
Interface (CLI/API) ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←← Results/Snapshots
```

## Agent Consensus Algorithm

1. **Analysis Phase**: Each agent analyzes the target code independently
2. **Suggestion Phase**: Agents propose specific changes with confidence scores
3. **Voting Phase**: All agents vote on all proposed changes
4. **Consensus Phase**: Engine calculates weighted consensus based on:
   - Agent priority levels
   - Confidence scores
   - Vote distributions
   - Configurable consensus threshold
5. **Application Phase**: Highest consensus changes are applied iteratively
6. **Validation Phase**: All agents validate the final result

## Agent Priority System

- **Security Enforcer**: Priority 9 (highest)
- **Pattern Optimizer**: Priority 7
- **Loop Simplifier**: Priority 6
- **Performance Optimizer**: Priority 5
- **Readability Enhancer**: Priority 4

Higher priority agents can override lower priority suggestions when confidence exceeds threshold.

## Evolution Tracking

Every refactoring session creates:
- **Evolution History**: Step-by-step record of all changes
- **Consensus Log**: Record of all agent voting decisions
- **Code Snapshots**: Periodic saves of code state (configurable frequency)
- **Metrics**: Quantitative analysis of improvements

## Configuration System

### Two-Level Configuration
1. **System Settings** (`config/settings.yaml`): Core system parameters
2. **Agent Profiles** (`config/agent_profiles.yaml`): Agent-specific configurations

### Extensibility
New configuration parameters can be added through `Config(**kwargs)` without breaking the frozen contract.

## File Structure Details

```
snre/
├── agents/           # Refactoring agent implementations
├── core/             # Core engine components  
├── interface/        # User interaction layers
├── config/           # Configuration files
├── data/             # Runtime data and logs
├── tests/            # Test suites
├── docs/             # Documentation
├── scripts/          # Utility scripts
└── .github/          # CI/CD workflows
```

## Integration Points

### Git Integration
- **Pre-commit hooks**: Validate syntax before commits
- **Post-commit hooks**: Trigger automatic refactoring
- **Branch creation**: Isolate refactoring changes

### IDE Integration  
- **VS Code**: Settings-based configuration
- **Vim**: Command and key mapping setup
- **Real-time API**: Live suggestions during editing

## Security Model

### Multi-Layer Security
1. **Agent-Level**: SecurityEnforcer scans for vulnerabilities
2. **Consensus-Level**: Multiple agents must agree on security changes
3. **Validation-Level**: Final validation before applying changes
4. **Git-Level**: Pre-commit validation prevents bad commits

### Vulnerability Detection
- SQL injection patterns
- Command injection risks
- Path traversal vulnerabilities  
- Hardcoded secrets
- Unsafe eval() usage

## Performance Characteristics

### Scalability
- **Concurrent Agents**: Configurable up to system limits
- **Session Management**: Multiple parallel refactoring sessions
- **Efficient Parsing**: Cached AST parsing for large files

### Optimization Targets
- **Code Complexity**: Reduce cyclomatic complexity
- **Runtime Performance**: Optimize algorithms and data structures
- **Memory Usage**: Identify and fix memory inefficiencies
- **I/O Operations**: Optimize file and network operations

## Extensibility Framework

### Adding New Agents
1. Inherit from `BaseAgent`
2. Implement required contract methods
3. Register with `SwarmCoordinator`
4. Add profile to `agent_profiles.yaml`

### Custom Change Types
Extend `ChangeType` enum for new categories:
- Documentation improvements
- Test coverage enhancements  
- Accessibility improvements
- API compatibility fixes

## Error Handling Strategy

### Hierarchical Error System
- **SNREError**: Base exception class
- **Specific Errors**: Domain-specific error types
- **Graceful Degradation**: System continues with reduced functionality
- **Recovery Mechanisms**: Automatic retry and fallback strategies

## Monitoring and Observability

### Metrics Collection
- **Agent Performance**: Success rates, confidence levels
- **System Performance**: Session duration, throughput
- **Code Quality**: Complexity trends, security improvements
- **User Adoption**: Feature usage, integration statistics

### Logging Strategy
- **Structured Logs**: JSON format for machine parsing
- **Multiple Levels**: DEBUG, INFO, WARN, ERROR
- **Rotation Policy**: Size and time-based log rotation
- **Centralized Collection**: Compatible with log aggregation systems

## Future Architecture Considerations

### Machine Learning Integration
- **Pattern Recognition**: Train models on successful refactoring patterns
- **Confidence Calibration**: Improve agent confidence predictions
- **Custom Agents**: Generate agents for specific codebases

### Distributed Processing
- **Agent Distribution**: Run agents on separate machines
- **Load Balancing**: Distribute workload across agent instances
- **Fault Tolerance**: Handle agent failures gracefully

### Advanced Consensus
- **Byzantine Fault Tolerance**: Handle malicious or faulty agents
- **Dynamic Weighting**: Adjust agent weights based on historical performance
- **Conflict Resolution**: Advanced algorithms for tie-breaking

---

© 2025 Bradley R. Kinnard ([moonrunnerkc](https://github.com/moonrunnerkc)) / Aftermath Technologies Ltd.  
Licensed under the Apache 2.0 License. Free to use, modify, and distribute — with attribution required.


