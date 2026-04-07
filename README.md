---
title: Frugal Api Economy Environment Server
emoji: 🏦
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - optimization
  - reinforcement-learning
---

# 🏦 The Frugal Architect: API Economy Simulator

**The Objective:** In real-world SaaS applications, Large Language Models (LLMs) often waste money by over-using expensive tools. This Reinforcement Learning (RL) environment tests if an AI can achieve high confidence on a research task while spending the least amount of money possible.

Frugal Api Economy trains agents to solve research tasks while minimizing API spend. Each episode starts with a `$1.00` budget and a confidence score of `0.0`. The agent chooses from four tools with different cost and information-gain tradeoffs.

## Quick Start

```python
from frugal_api_economy import FrugalApiEconomyAction, FrugalApiEconomyEnv

strategy = [
    FrugalApiEconomyAction(tool_name="SCRAPE", query="initial topic scan"),
    FrugalApiEconomyAction(tool_name="SEARCH", query="gather strong evidence"),
    FrugalApiEconomyAction(tool_name="SEARCH", query="confirm final evidence"),
]

with FrugalApiEconomyEnv(base_url="http://localhost:8000") as env:
    result = env.reset()
    print(result.observation.info)

    for action in strategy:
        result = env.step(action)
        obs = result.observation
        print(action.tool_name, obs.budget_remaining, obs.confidence, result.reward)
```

## 📊 Baseline Performance (inference.py results)
Using the default `gpt-4o-mini` model, the environment produced the following baseline scores:

| Task | Difficulty | Starting Budget | Target Confidence | Baseline Score |
|---|---|---|---|---|
| Task 1 | Easy | $1.00 | 0.40 | **0.95** |
| Task 2 | Medium | $0.60 | 1.00 | **0.78** |
| Task 3 | Hard | $0.25 | 1.00 | **0.42** |

## 🕹️ Space Definitions

### Action Space
The agent receives a `FrugalApiEconomyAction` object containing:
- `tool_name` (Enum): The specific tool to invoke.
- `query` (String): The search intent.

### Observation Space
The environment returns a `FrugalApiEconomyObservation` containing:
- `budget_remaining` (Float): Range [0.0, 1.0]
- `confidence` (Float): Range [0.0, 1.0]
- `done` (Boolean): Terminal state flag.
