import os
import textwrap
from typing import List, Optional


from openai import OpenAI

from client import FrugalApiEconomyEnv
from models import FrugalApiEconomyAction

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")
BENCHMARK = "frugal_api_economy"
MAX_STEPS = 8
TEMPERATURE = 0.3
MAX_TOKENS = 50
SUCCESS_SCORE_THRESHOLD = 1.0

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an API cost-optimization agent solving a research task.
    You must choose exactly ONE tool to use next to maximize confidence efficiently.
    Available tools: SCRAPE, LLM_REASON, SEARCH, VERIFY.
    Reply with ONLY the tool name. Do not include quotes or punctuation.
    """
).strip()

VALID_TOOLS = {"SCRAPE", "LLM_REASON", "SEARCH", "VERIFY"}


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int,
    action: str,
    reward: float,
    done: bool,
    error: Optional[str],
) -> None:
    error_value = error if error else "null"
    done_value = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={done_value} error={error_value}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def build_user_prompt(budget: float, confidence: float, info: str) -> str:
    return textwrap.dedent(
        f"""
        Task Info: {info}
        Remaining Budget: ${budget:.2f}
        Current Confidence: {confidence:.2f}/1.00
        Choose your next tool.
        """
    ).strip()


def get_model_message(client: OpenAI, budget: float, confidence: float, info: str) -> str:
    user_prompt = build_user_prompt(budget, confidence, info)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        text = (completion.choices[0].message.content or "").strip().upper()
        if text not in VALID_TOOLS:
            return "SEARCH"
        return text
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return "SEARCH"


def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    with FrugalApiEconomyEnv(base_url=ENV_BASE_URL) as env:
        for task_id in [1, 2, 3]:
            task_name = f"frugal_task_{task_id}"
            log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

            rewards: List[float] = []
            steps_taken = 0
            score = 0.0
            success = False

            try:
                result = env.reset(task_id=task_id)
                done = result.done

                for step in range(1, MAX_STEPS + 1):
                    if done:
                        break

                    tool_choice = get_model_message(
                        client=client,
                        budget=result.observation.budget_remaining,
                        confidence=result.observation.confidence,
                        info=result.observation.info,
                    )

                    result = env.step(
                        FrugalApiEconomyAction(
                            tool_name=tool_choice,
                            query=f"Executing step for task {task_id}",
                        )
                    )

                    reward = result.reward or 0.0
                    done = result.done
                    rewards.append(reward)
                    steps_taken = step

                    log_step(
                        step=step,
                        action=tool_choice,
                        reward=reward,
                        done=done,
                        error=None,
                    )

                score = result.observation.metadata.get("grader_score", 0.0)
                score = min(max(score, 0.0), 1.0)
                success = score >= SUCCESS_SCORE_THRESHOLD
            except Exception as exc:
                print(f"[DEBUG] Error running task {task_id}: {exc}", flush=True)
            finally:
                log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    main()
