# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Core environment logic for the Frugal Api Economy simulator."""

from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import FrugalApiEconomyAction, FrugalApiEconomyObservation
except ImportError:
    from models import FrugalApiEconomyAction, FrugalApiEconomyObservation


class FrugalApiEconomyEnvironment(Environment):
    """Train agents to reach high confidence while minimizing API spend."""

    COSTS = {
        "SCRAPE": 0.01,
        "LLM_REASON": 0.05,
        "SEARCH": 0.10,
        "VERIFY": 0.20,
    }

    CONFIDENCE_GAINS = {
        "SCRAPE": 0.20,
        "LLM_REASON": 0.25,
        "SEARCH": 0.40,
        "VERIFY": 0.60,
    }

    STARTING_BUDGET = 1.00
    VERIFY_MIN_CONFIDENCE = 0.50
    COST_PENALTY_MULTIPLIER = 50.0
    COMPLETION_BONUS = 100.0
    BANKRUPTCY_PENALTY = 50.0
    TASK_CONFIGS = {
        1: {
            "budget": 1.00,
            "target_confidence": 0.40,
            "description": "Task 1 (Easy): Find the current stock price of Reliance.",
        },
        2: {
            "budget": 0.60,
            "target_confidence": 1.00,
            "description": "Task 2 (Medium): Analyze HDFC Bank's Q3 revenue growth.",
        },
        3: {
            "budget": 0.25,
            "target_confidence": 1.00,
            "description": "Task 3 (Hard): Verify the official dividend payout for Palantir.",
        },
    }

    # Enable concurrent WebSocket sessions.
    # Set to True if your environment isolates state between instances.
    # When True, multiple WebSocket clients can connect simultaneously, each
    # getting their own environment instance (when using factory mode in app.py).
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._done = False
        self.budget = self.STARTING_BUDGET
        self.starting_budget = self.STARTING_BUDGET
        self.confidence = 0.0
        self.action_history = []
        self.episode_return = 0.0
        self.current_task_id = 1
        self.target_confidence = 1.0
        self.task_description = self.TASK_CONFIGS[1]["description"]

    def reset(
        self,
        seed=None,
        episode_id=None,
        task_id: int = 1,
        **kwargs,
    ) -> FrugalApiEconomyObservation:
        task_config = self.TASK_CONFIGS.get(task_id, self.TASK_CONFIGS[1])
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        self._done = False
        self.current_task_id = task_id if task_id in self.TASK_CONFIGS else 1
        self.budget = task_config["budget"]
        self.starting_budget = task_config["budget"]
        self.confidence = 0.0
        self.action_history = []
        self.episode_return = 0.0
        self.target_confidence = task_config["target_confidence"]
        self.task_description = task_config["description"]
        return FrugalApiEconomyObservation(
            budget_remaining=self.budget,
            confidence=0.0,
            info=(
                f"{self.task_description} Starting budget: ${self.budget:.2f}. "
                f"Target confidence: {self.target_confidence:.2f}."
            ),
            done=False,
            reward=0.0,
            metadata={
                "task_id": self.current_task_id,
                "target_confidence": self.target_confidence,
                "grader_score": 0.0,
            },
        )

    def step(  # type: ignore[override]
        self,
        action: FrugalApiEconomyAction,
        timeout_s=None,
        **kwargs,
    ) -> FrugalApiEconomyObservation:
        self._state.step_count += 1

        if self._done:
            return self._build_observation(
                info="Episode already finished. Call reset() to start a new run.",
                reward=0.0,
                done=True,
                termination_reason="episode_already_finished",
            )

        tool = action.tool_name
        cost = self.COSTS[tool]
        reward = -(cost * self.COST_PENALTY_MULTIPLIER)
        done = False
        termination_reason = ""

        self.budget = round(max(0.0, self.budget - cost), 4)

        if tool == "VERIFY" and self.confidence < self.VERIFY_MIN_CONFIDENCE:
            info = (
                f"VERIFY blocked. Confidence {self.confidence:.2f} is below "
                f"the {self.VERIFY_MIN_CONFIDENCE:.2f} threshold."
            )
        else:
            self.confidence = round(
                min(1.0, self.confidence + self.CONFIDENCE_GAINS[tool]),
                4,
            )
            info = (
                f"Used {tool} for '{action.query}'. "
                f"Confidence increased to {self.confidence:.2f}."
            )

        self.action_history.append(
            {
                "step": self._state.step_count,
                "tool": tool,
                "query": action.query,
                "cost": cost,
                "confidence_after": self.confidence,
                "budget_after": self.budget,
            }
        )

        if self.confidence >= self.target_confidence:
            reward += self.COMPLETION_BONUS
            done = True
            termination_reason = "confidence_reached"
        elif self.budget <= 0.0:
            reward -= self.BANKRUPTCY_PENALTY
            done = True
            termination_reason = "budget_depleted"

        grader_score = self.get_grader_score()

        self.episode_return = round(self.episode_return + reward, 4)
        self._done = done

        return self._build_observation(
            info=(
                f"{info} Budget remaining: ${self.budget:.2f}. "
                f"Reward this step: {reward:+.2f}. "
                f"Episode return: {self.episode_return:+.2f}."
            ),
            reward=reward,
            done=done,
            termination_reason=termination_reason,
            metadata={
                "task_id": self.current_task_id,
                "target_confidence": self.target_confidence,
                "tool": tool,
                "query": action.query,
                "cost": cost,
                "step_count": self._state.step_count,
                "grader_score": grader_score,
                "episode_return": self.episode_return,
                "total_spent": round(self.starting_budget - self.budget, 2),
                "action_history": self.action_history,
            },
        )

    @property
    def state(self) -> State:
        return self._state

    def get_grader_score(self) -> float:
        if self.confidence >= self.target_confidence:
            return 1.0
        if self.target_confidence <= 0:
            return 0.0
        return round(min(1.0, self.confidence / self.target_confidence), 2)

    def _build_observation(
        self,
        *,
        info: str,
        reward: float,
        done: bool,
        termination_reason: str = "",
        metadata=None,
    ) -> FrugalApiEconomyObservation:
        return FrugalApiEconomyObservation(
            budget_remaining=round(self.budget, 2),
            confidence=round(self.confidence, 2),
            info=info,
            termination_reason=termination_reason,
            done=done,
            reward=reward,
            metadata=metadata or {},
        )
