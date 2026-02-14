"""
REST API interface for SNRE
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from flask import Flask
from flask import jsonify
from flask import request

from snre.errors import AgentNotFoundError
from snre.errors import InvalidPathError
from snre.errors import SessionNotFoundError
from snre.models.config import Config


class APIInterface:
    """REST API interface for SNRE"""

    def __init__(self, coordinator, config: Config):
        self.coordinator = coordinator
        self.config = config
        self.app = Flask(__name__)
        self._setup_routes()

    def start_refactor_endpoint(
        self, request_data: dict[str, Any]
    ) -> tuple[dict[str, Any], int]:
        """POST /refactor/start endpoint"""
        try:
            target_path = request_data.get("target_path")
            agent_set = request_data.get("agent_set", [])
            config_overrides = request_data.get("config_overrides", {})

            if not target_path:
                return {
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "target_path required",
                    }
                }, 400

            session_id = self.coordinator.start_refactor(
                target_path, agent_set, config_overrides
            )

            return {
                "refactor_id": str(session_id),
                "status": "started",
                "timestamp": datetime.now().isoformat(),
                "agents_loaded": agent_set,
            }, 200

        except AgentNotFoundError as e:
            return {"error": {"code": e.code, "message": e.message}}, 404
        except InvalidPathError as e:
            return {"error": {"code": e.code, "message": e.message}}, 400
        except Exception as e:
            return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}}, 500

    def get_status_endpoint(self, refactor_id: str) -> tuple[dict[str, Any], int]:
        """GET /refactor/status/<refactor_id> endpoint"""
        try:
            session_id = UUID(refactor_id)
            status = self.coordinator.get_session_status(session_id)
            return status, 200

        except ValueError:
            return {
                "error": {"code": "INVALID_ID", "message": "Invalid session ID format"}
            }, 400
        except SessionNotFoundError as e:
            return {"error": {"code": e.code, "message": e.message}}, 404
        except Exception as e:
            return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}}, 500

    def get_result_endpoint(self, refactor_id: str) -> tuple[dict[str, Any], int]:
        """GET /refactor/result/<refactor_id> endpoint"""
        try:
            session_id = UUID(refactor_id)
            session = self.coordinator.get_session_result(session_id)

            # Convert session to API response format
            evolution_history = [
                {
                    "iteration": step.iteration,
                    "timestamp": step.timestamp.isoformat(),
                    "agent": step.agent,
                    "change_type": step.change_type.value,
                    "confidence": step.confidence,
                    "description": step.description,
                }
                for step in session.evolution_history
            ]

            consensus_log = [
                {
                    "timestamp": decision.timestamp.isoformat(),
                    "decision": decision.decision,
                    "votes": decision.votes,
                    "winning_agent": decision.winning_agent,
                }
                for decision in session.consensus_log
            ]

            metrics = {}
            if session.metrics:
                metrics = {
                    "lines_changed": session.metrics.lines_changed,
                    "complexity_delta": session.metrics.complexity_delta,
                    "security_improvements": session.metrics.security_improvements,
                    "performance_gains": session.metrics.performance_gains,
                }

            return {
                "refactor_id": str(session.refactor_id),
                "status": session.status.value,
                "original_code": session.original_code,
                "refactored_code": session.refactored_code,
                "diff": self.coordinator.change_tracker.create_diff(
                    session.original_code,
                    session.refactored_code or session.original_code,
                ),
                "evolution_history": evolution_history,
                "consensus_log": consensus_log,
                "metrics": metrics,
            }, 200

        except ValueError:
            return {
                "error": {"code": "INVALID_ID", "message": "Invalid session ID format"}
            }, 400
        except SessionNotFoundError as e:
            return {"error": {"code": e.code, "message": e.message}}, 404
        except Exception as e:
            return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}}, 500

    def list_sessions_endpoint(self) -> tuple[dict[str, Any], int]:
        """GET /refactor/sessions endpoint"""
        try:
            sessions = self.coordinator.list_active_sessions()
            return {"active_sessions": sessions}, 200
        except Exception as e:
            return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}}, 500

    def cancel_session_endpoint(self, refactor_id: str) -> tuple[dict[str, Any], int]:
        """DELETE /refactor/session/<refactor_id> endpoint"""
        try:
            session_id = UUID(refactor_id)
            success = self.coordinator.cancel_session(session_id)

            if success:
                return {
                    "refactor_id": refactor_id,
                    "status": "cancelled",
                    "timestamp": datetime.now().isoformat(),
                }, 200
            else:
                return {
                    "error": {
                        "code": "CANCELLATION_FAILED",
                        "message": "Failed to cancel session",
                    }
                }, 400

        except ValueError:
            return {
                "error": {"code": "INVALID_ID", "message": "Invalid session ID format"}
            }, 400
        except Exception as e:
            return {"error": {"code": "INTERNAL_ERROR", "message": str(e)}}, 500

    def _setup_routes(self) -> None:
        """Setup Flask routes"""

        @self.app.route("/refactor/start", methods=["POST"])
        def start_refactor():
            result = self.start_refactor_endpoint(request.get_json() or {})
            return jsonify(result[0]), result[1]

        @self.app.route("/refactor/status/<refactor_id>", methods=["GET"])
        def get_status(refactor_id):
            result = self.get_status_endpoint(refactor_id)
            return jsonify(result[0]), result[1]

        @self.app.route("/refactor/result/<refactor_id>", methods=["GET"])
        def get_result(refactor_id):
            result = self.get_result_endpoint(refactor_id)
            return jsonify(result[0]), result[1]

        @self.app.route("/refactor/sessions", methods=["GET"])
        def list_sessions():
            result = self.list_sessions_endpoint()
            return jsonify(result[0]), result[1]

        @self.app.route("/refactor/session/<refactor_id>", methods=["DELETE"])
        def cancel_session(refactor_id):
            result = self.cancel_session_endpoint(refactor_id)
            return jsonify(result[0]), result[1]

        @self.app.route("/health", methods=["GET"])
        def health():
            return jsonify({"status": "healthy", "service": "SNRE"}), 200

    def run(self, host: str = "localhost", port: int = 8000) -> None:
        """Start the Flask API server"""
        self.app.run(host=host, port=port, debug=False)


def create_app(coordinator=None, config: Config = None) -> Flask:
    """Create Flask application with SNRE API routes"""
    if config is None:
        config = Config()

    if coordinator is None:
        from core.swarm_coordinator import SwarmCoordinator

        coordinator = SwarmCoordinator(config)

    api_interface = APIInterface(coordinator, config)
    return api_interface.app
