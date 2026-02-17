"""
LLM client layer for the SkillScout multi-agent hiring assistant.

Design decisions:
- Model selection is explicit per agent (no hidden defaults).
- Different agents use different models based on reasoning needs.
- The application (Streamlit + session_state) owns the interview state.
- This module ONLY talks to the LLM and returns strings.

Agents:
1. Role Understanding Agent
2. Skill Summary Agent
3. Category Question Agent (context-aware)
4. Fallback / Guardrail Agent

This version is production-safe:
- Exponential backoff
- Graceful degradation
- Never crashes the Streamlit app
"""

from typing import Optional, List
import time
import os

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
# Model configuration
# -------------------------------------------------------------------

ROLE_AGENT_MODEL = "gpt-5.2"
SKILL_SUMMARY_MODEL = "gpt-4o-mini"
QUESTION_AGENT_MODEL = "gpt-4o-mini"
FALLBACK_AGENT_MODEL = "gpt-4o-mini"

# -------------------------------------------------------------------
# OpenAI client (lazy init)
# -------------------------------------------------------------------

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


# -------------------------------------------------------------------
# Centralized Safe LLM Call
# -------------------------------------------------------------------

def _safe_chat_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.3,
    max_retries: int = 3,
    base_sleep: int = 2,
) -> str:
    """
    Production-safe OpenAI call with:
    - Exponential backoff
    - Graceful fallback
    - No app crashes
    """

    client = get_client()
    last_exception: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            return response.choices[0].message.content.strip()

        except RateLimitError as e:
            last_exception = e
            sleep_time = base_sleep * (2 ** (attempt - 1))
            time.sleep(sleep_time)

        except (APITimeoutError, APIError) as e:
            last_exception = e
            sleep_time = base_sleep * attempt
            time.sleep(sleep_time)

        except Exception as e:
            last_exception = e
            time.sleep(base_sleep)

    # ---------------------------
    # Graceful Degradation
    # ---------------------------

    print("LLM ERROR:", last_exception)

    # Fallback question instead of crashing
    return (
        "I’m currently experiencing a temporary issue generating the next "
        "question. Could you briefly elaborate more on your last answer?"
    )


def _chat_completion(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.3,
) -> str:
    return _safe_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
    )


# -------------------------------------------------------------------
# Agent 1: Role Understanding
# -------------------------------------------------------------------

def generate_role_summary(desired_positions: str, years_experience: str) -> str:
    user_prompt = build_role_agent_user_prompt(desired_positions, years_experience)

    return _chat_completion(
        system_prompt=ROLE_AGENT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=ROLE_AGENT_MODEL,
        temperature=0.2,
    )


# -------------------------------------------------------------------
# Agent 2: Skill Summary
# -------------------------------------------------------------------

def generate_skill_summary(raw_tech_stack: str) -> str:
    user_prompt = build_skill_summary_user_prompt(raw_tech_stack)

    return _chat_completion(
        system_prompt=SKILL_SUMMARY_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=SKILL_SUMMARY_MODEL,
        temperature=0.3,
    )


# -------------------------------------------------------------------
# Agent 3: Technical Question Generator
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

    # Append answer history for follow-up depth
    extra_context_parts: List[str] = []

    if answers_in_category:
        joined_answers = "\n".join(
            f"- {a}" for a in answers_in_category if a.strip()
        )
        if joined_answers:
            extra_context_parts.append(
                "\n\nRecent answers in this category:\n" + joined_answers
            )

    if last_answer:
        extra_context_parts.append(
            "\n\nMost recent answer:\n" + last_answer
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
# Agent 4: Fallback / Guardrail
# -------------------------------------------------------------------

def generate_fallback_response(user_message: str, current_state: str) -> str:
    user_prompt = build_fallback_user_prompt(user_message, current_state)

    return _chat_completion(
        system_prompt=FALLBACK_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=FALLBACK_AGENT_MODEL,
        temperature=0.4,
    )
