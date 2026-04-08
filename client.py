
from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import FrugalApiEconomyAction, FrugalApiEconomyObservation


class FrugalApiEconomyEnv(
    EnvClient[FrugalApiEconomyAction, FrugalApiEconomyObservation, State]
):
    def _step_payload(self, action: FrugalApiEconomyAction) -> Dict:
        return {
            "tool_name": action.tool_name,
            "query": action.query,
        }

    def _parse_result(self, payload: Dict) -> StepResult[FrugalApiEconomyObservation]:
        obs_data = payload.get("observation", {})
        observation = FrugalApiEconomyObservation(
            budget_remaining=obs_data.get("budget_remaining", 1.0),
            confidence=obs_data.get("confidence", 0.0),
            info=obs_data.get("info", ""),
            termination_reason=obs_data.get("termination_reason", ""),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
