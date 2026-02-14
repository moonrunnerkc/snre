"""
Consensus engine for agent voting and decision making
"""

from datetime import datetime

from agents.base_agent import BaseAgent
from snre.models.changes import Change
from snre.models.changes import ConsensusDecision
from snre.models.config import Config


class ConsensusEngine:
    """Handles agent voting and consensus mechanisms"""

    def __init__(self, config: Config):
        self.config = config

    def collect_votes(
        self, agents: dict[str, BaseAgent], changes: list[Change]
    ) -> dict[str, dict[str, float]]:
        """Collect votes from all agents on proposed changes"""
        all_votes = {}

        for agent_id, agent in agents.items():
            try:
                agent_votes = agent.vote(changes)
                all_votes[agent_id] = agent_votes
            except Exception:
                # Agent failed to vote, assign neutral scores
                all_votes[agent_id] = {f"change_{i}": 0.5 for i in range(len(changes))}

        return all_votes

    def calculate_consensus(
        self, votes: dict[str, dict[str, float]]
    ) -> ConsensusDecision:
        """Calculate consensus from agent votes"""
        if not votes:
            return ConsensusDecision(
                timestamp=datetime.now(),
                decision="no_consensus",
                votes={},
                winning_agent="none",
                confidence=0.0,
            )

        # Calculate weighted average scores
        vote_scores: dict[str, list[float]] = {}
        agent_weights: dict[str, float] = {}

        # Assign equal weights for now (could be priority-based)
        num_agents = len(votes)
        for agent_id in votes:
            agent_weights[agent_id] = 1.0 / num_agents

        # Aggregate votes across all changes
        for agent_id, agent_votes in votes.items():
            for vote_key, score in agent_votes.items():
                if vote_key not in vote_scores:
                    vote_scores[vote_key] = []
                vote_scores[vote_key].append(score * agent_weights[agent_id])

        # Find consensus decision
        if not vote_scores:
            decision = "no_changes"
            winning_agent = "none"
            confidence = 0.0
        else:
            # Average all vote scores
            avg_score = sum(sum(scores) for scores in vote_scores.values()) / len(
                vote_scores
            )

            if avg_score >= self.config.consensus_threshold:
                decision = "accept_changes"
                # Find agent with highest average vote
                agent_averages = {}
                for agent_id in votes:
                    if votes[agent_id]:
                        agent_averages[agent_id] = sum(votes[agent_id].values()) / len(
                            votes[agent_id]
                        )
                    else:
                        agent_averages[agent_id] = 0.0

                winning_agent = max(agent_averages, key=lambda k: agent_averages[k])
                confidence = avg_score
            else:
                decision = "reject_changes"
                winning_agent = "none"
                confidence = 1.0 - avg_score

        return ConsensusDecision(
            timestamp=datetime.now(),
            decision=decision,
            votes=votes,
            winning_agent=winning_agent,
            confidence=confidence,
        )

    def apply_overrides(
        self, decision: ConsensusDecision, priority_agents: list[str]
    ) -> ConsensusDecision:
        """Apply priority agent overrides"""
        if not priority_agents:
            return decision

        # Check if any priority agent has strong opposition
        for agent_id in priority_agents:
            if agent_id in decision.votes:
                agent_votes = decision.votes[agent_id]
                avg_vote = (
                    sum(agent_votes.values()) / len(agent_votes) if agent_votes else 0.0
                )

                # Priority agent can override with strong confidence
                if avg_vote > 0.9:
                    decision.decision = "priority_override_accept"
                    decision.winning_agent = agent_id
                    decision.confidence = avg_vote
                elif avg_vote < 0.1:
                    decision.decision = "priority_override_reject"
                    decision.winning_agent = agent_id
                    decision.confidence = 1.0 - avg_vote

        return decision

    def validate_consensus(self, decision: ConsensusDecision) -> bool:
        """Validate that consensus meets threshold requirements"""
        if decision.decision in ["accept_changes", "priority_override_accept"]:
            return decision.confidence >= self.config.consensus_threshold
        elif decision.decision in ["reject_changes", "priority_override_reject"]:
            return decision.confidence >= 0.5
        else:
            return True
