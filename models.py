# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Data contracts for the Frugal Api Economy environment."""

from typing import Literal

from openenv.core.env_server.types import Action, Observation
from pydantic import Field, field_validator


class FrugalApiEconomyAction(Action):
    """One marketplace decision made by the agent."""

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
    """Observable state after each action."""

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
