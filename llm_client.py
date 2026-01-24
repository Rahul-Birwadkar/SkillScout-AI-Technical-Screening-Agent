# llm_client.py

"""LLM client layer for the SkillScout multi-agent hiring assistant.

Design decisions:
- Model selection is explicit per agent (no hidden defaults).
- Different agents use different models based on reasoning needs.
- The application (Streamlit + session_state) owns the interview state.
- This module ONLY talks to the LLM and returns strings.

Agents:
1. Role Understanding Agent          -> normalizes desired roles / seniority
2. Skill Summary Agent               -> rewrites raw tech stack for UI
3. Category Question Agent (context-aware) -> generates ONE question per call
4. Fallback / Guardrail Agent        -> handles off-track messages

To keep the agent from "forgetting" context, the app passes
short-term memory explicitly (e.g., previously asked questions, key answers)
into the user prompt for the Category Question Agent.
"""

from typing import Optional, List

import time
from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from prompts import (
    ROLE_AGENT_SYSTEM_PROMPT,
    SKILL_SUMMARY_SYSTEM_PROMPT,
    TECH_QUESTION_SYSTEM_PROMPT,
    FALLBACK_SYSTEM_PROMPT,
    build_role_agent_user_prompt,
    build_skill_summary_user_prompt,
    build_category_question_user_prompt,
    build_fallback_user_prompt,
)


# -------------------------------------------------------------------
# Model configuration (single source of truth)
# -------------------------------------------------------------------

# Higher-reasoning model for intent / role understanding
ROLE_AGENT_MODEL = "gpt-5.2"

# Deterministic, cost-effective models for structured tasks
SKILL_SUMMARY_MODEL = "gpt-4o-mini"
QUESTION_AGENT_MODEL = "gpt-4o-mini"
FALLBACK_AGENT_MODEL = "gpt-4o-mini"


# -------------------------------------------------------------------
# OpenAI client (lazy initialization)
# -------------------------------------------------------------------

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Create the OpenAI client once and reuse it."""
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


# -------------------------------------------------------------------
# Internal helpers – NO default model on purpose
# -------------------------------------------------------------------

def _safe_chat_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.3,
    max_retries: int = 2,
    base_sleep: int = 4,
) -> str:
    """Centralized OpenAI call with retry + backoff.

    Tuned for interactive use:
    - Fail fast enough that the user is not waiting 60+ seconds.
    - Still retries briefly on transient rate limits or network hiccups.
    """
    client = get_client()
    last_exception: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content.strip()

        except RateLimitError as e:
            # Short exponential backoff on rate limits (e.g. 4s, then 8s)
            last_exception = e
            sleep_time = base_sleep * attempt
            time.sleep(sleep_time)

        except (APITimeoutError, APIError) as e:
            # Smaller backoff on generic API issues
            last_exception = e
            time.sleep(3 * attempt)

    # If we reach here, all retries failed
    raise RuntimeError(
        "LLM request failed after retries. Likely due to sustained rate limits or API instability."
    ) from last_exception


def _chat_completion(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.3,
) -> str:
    """Thin wrapper for backward compatibility.

    All agents should go through this function; it delegates to
    :func:`_safe_chat_completion` so that retry behaviour is consistent.
    """
    return _safe_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
    )


# -------------------------------------------------------------------
# Agent 1: Role Understanding Agent (GPT-5.2)
# -------------------------------------------------------------------

def generate_role_summary(desired_positions: str, years_experience: str) -> str:
    """Normalize desired roles and seniority from free-form candidate input."""
    user_prompt = build_role_agent_user_prompt(desired_positions, years_experience)

    return _chat_completion(
        system_prompt=ROLE_AGENT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=ROLE_AGENT_MODEL,
        temperature=0.2,
    )


# -------------------------------------------------------------------
# Agent 2: Skill Summary Agent (GPT-4o-mini)
# -------------------------------------------------------------------

def generate_skill_summary(raw_tech_stack: str) -> str:
    """Produce a clean, recruiter-friendly summary of the candidate's tech stack."""
    user_prompt = build_skill_summary_user_prompt(raw_tech_stack)

    return _chat_completion(
        system_prompt=SKILL_SUMMARY_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=SKILL_SUMMARY_MODEL,
        temperature=0.3,
    )


# -------------------------------------------------------------------
# Agent 3: Category-based Question Generator (context-aware)
# -------------------------------------------------------------------

def generate_category_question(
    full_name: str,
    years_experience: str,
    seniority_label: str,
    role_summary: str,
    category: str,
    skills_in_category: List[str],
    question_number: int,
    previously_asked_questions: List[str],
    answers_in_category: Optional[List[str]] = None,
    last_answer: str = "",
) -> str:
    """Generate ONE technical question for a specific skill category.

    IMPORTANT:
    - The LLM itself is stateless.
    - Short-term memory (previous questions / answers) is managed by the app
      and passed explicitly here.
    - `prompts.build_category_question_user_prompt` builds the core prompt,
      and we optionally enrich it with a compact view of recent answers so
      that the model can ask follow-up questions.
    """
    user_prompt = build_category_question_user_prompt(
        full_name=full_name,
        years_experience=years_experience,
        seniority_label=seniority_label,
        role_summary=role_summary,
        category=category,
        skills_in_category=skills_in_category,
        question_number=question_number,
        previously_asked_questions=previously_asked_questions,
    )

    # Optionally append a short answer history block for follow-ups
    extra_context_parts: List[str] = []
    if answers_in_category:
        joined_answers = "\n".join(
            f"- {a}" for a in answers_in_category if a.strip()
        )
        if joined_answers:
            extra_context_parts.append(
                (
                    "\n\nHere are the candidate's recent answers in this category "
                    "(most recent last):\n"
                    f"{joined_answers}"
                )
            )

    if last_answer:
        extra_context_parts.append(
            "\n\nMost recent answer in this category "
            "(for immediate follow-up):\n"
            f"{last_answer}"
        )

    if extra_context_parts:
        user_prompt = f"{user_prompt}{''.join(extra_context_parts)}"

    return _chat_completion(
        system_prompt=TECH_QUESTION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=QUESTION_AGENT_MODEL,
        temperature=0.35,
    )


# -------------------------------------------------------------------
# Agent 4: Fallback / Guardrail Agent (GPT-4o-mini)
# -------------------------------------------------------------------

def generate_fallback_response(user_message: str, current_state: str) -> str:
    """Handle unclear or unrelated candidate messages and steer back to screening."""
    user_prompt = build_fallback_user_prompt(user_message, current_state)

    return _chat_completion(
        system_prompt=FALLBACK_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=FALLBACK_AGENT_MODEL,
        temperature=0.4,
    )
