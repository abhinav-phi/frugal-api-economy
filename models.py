
from typing import Literal

from openenv.core.env_server.types import Action, Observation
from pydantic import Field, field_validator


class FrugalApiEconomyAction(Action):
    tool_name: Literal["SCRAPE", "SEARCH", "LLM_REASON", "VERIFY"] = Field(
        ...,
        description="Marketplace tool to invoke for this step.",
    )
    query: str = Field(
        ...,
        min_length=3,
        max_length=512,
        description="Plain-English description of what the agent wants to research.",
    )

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query cannot be blank or whitespace-only.")
        return value


class FrugalApiEconomyObservation(Observation):
    budget_remaining: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="USD left in the wallet.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Information confidence accumulated so far.",
    )
    info: str = Field(
        default="",
        description="Human-readable result of the last tool invocation.",
    )
    termination_reason: str = Field(
        default="",
        description="Why the episode ended, if it has ended.",
    )
