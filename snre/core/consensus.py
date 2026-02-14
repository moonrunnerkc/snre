# Author: Bradley R. Kinnard
"""
Stateless consensus engine. Pure functions -- input in, output out.
The threshold is passed explicitly, not stored on self.
"""

from datetime import datetime

from snre.models.changes import ConsensusDecision


def calculate_consensus(
    votes: dict[str, dict[str, float]],
    threshold: float,
) -> ConsensusDecision:
    """Determine consensus from agent votes. Pure function, no mutable state."""
    if not votes:
        return ConsensusDecision(
            timestamp=datetime.now(),
            decision="no_consensus",
            votes={},
            winning_agent="none",
            confidence=0.0,
        )

    # equal weight per agent
    num_agents = len(votes)
    agent_weights = {aid: 1.0 / num_agents for aid in votes}

    # aggregate weighted scores per vote key
    vote_scores: dict[str, list[float]] = {}
    for agent_id, agent_votes in votes.items():
        w = agent_weights[agent_id]
        for vote_key, score in agent_votes.items():
            vote_scores.setdefault(vote_key, []).append(score * w)

    if not vote_scores:
        return ConsensusDecision(
            timestamp=datetime.now(),
            decision="no_changes",
            votes=votes,
            winning_agent="none",
            confidence=0.0,
        )

    avg_score = sum(sum(s) for s in vote_scores.values()) / len(vote_scores)

    if avg_score >= threshold:
        # find agent with strongest average vote
        agent_averages: dict[str, float] = {}
        for agent_id, agent_votes in votes.items():
            if agent_votes:
                agent_averages[agent_id] = sum(agent_votes.values()) / len(agent_votes)
            else:
                agent_averages[agent_id] = 0.0

        winning_agent = max(agent_averages, key=lambda k: agent_averages[k])
        return ConsensusDecision(
            timestamp=datetime.now(),
            decision="accept_changes",
            votes=votes,
            winning_agent=winning_agent,
            confidence=avg_score,
        )

    return ConsensusDecision(
        timestamp=datetime.now(),
        decision="reject_changes",
        votes=votes,
        winning_agent="none",
        confidence=1.0 - avg_score,
    )


def collect_votes(
    agents: dict[str, object],
    changes: list,
) -> dict[str, dict[str, float]]:
    """Collect votes from all agents. Agents that fail get neutral scores."""
    all_votes: dict[str, dict[str, float]] = {}

    for agent_id, agent in agents.items():
        try:
            agent_votes = agent.vote(changes)  # type: ignore[union-attr]
            all_votes[agent_id] = agent_votes
        except Exception:
            all_votes[agent_id] = {f"change_{i}": 0.5 for i in range(len(changes))}

    return all_votes
