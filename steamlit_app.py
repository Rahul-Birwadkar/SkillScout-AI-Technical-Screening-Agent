# app.py

import json
import re
from pathlib import Path
from typing import Dict, List

import streamlit as st

from llm_client import (
    generate_role_summary,
    generate_skill_summary,
    generate_category_question,
    generate_fallback_response,
)
from ui import setup_page, render_sidebar_profile, render_chat_history

# -----------------------------
# Constants & Skill Category Map
# -----------------------------

MAX_TOTAL_QUESTIONS = 15  # Global hard cap for technical questions

EXIT_KEYWORDS = {"exit", "quit", "bye", "goodbye", "stop", "end"}

REQUIRED_FIELDS = [
    "full_name",
    "email",
    "phone",
    "years_experience",
    "desired_positions",
    "current_location",
    "tech_stack",
]

FIELD_LABELS = {
    "full_name": "Full name",
    "email": "Email address",
    "phone": "Phone number",
    "years_experience": "Years of professional experience",
    "desired_positions": "Desired role(s) or job title(s)",
    "current_location": "Current location (city, country)",
    "tech_stack": "Tech stack (technologies, tools, frameworks)",
}

# Rule-based skill categorization
SKILL_CATEGORY_RULES: Dict[str, str] = {
    # Backend
    "python": "Backend",
    "java": "Backend",
    "c#": "Backend",
    "csharp": "Backend",
    "node": "Backend",
    "node.js": "Backend",
    "nodejs": "Backend",
    "spring": "Backend",
    "django": "Backend",
    "fastapi": "Backend",
    ".net": "Backend",
    "dotnet": "Backend",
    "php": "Backend",
    "laravel": "Backend",
    "express": "Backend",
    "nest": "Backend",
    "nest.js": "Backend",
    "nestjs": "Backend",
    "golang": "Backend",
    "go": "Backend",
    "ruby": "Backend",
    "rails": "Backend",

    # Frontend
    "javascript": "Frontend",
    "typescript": "Frontend",
    "react": "Frontend",
    "react.js": "Frontend",
    "reactjs": "Frontend",
    "vue": "Frontend",
    "vue.js": "Frontend",
    "vuejs": "Frontend",
    "angular": "Frontend",
    "svelte": "Frontend",
    "next.js": "Frontend",
    "nextjs": "Frontend",
    "nuxt": "Frontend",
    "html": "Frontend",
    "css": "Frontend",
    "tailwind": "Frontend",
    "bootstrap": "Frontend",

    # Data / ML
    "pandas": "Data/ML",
    "numpy": "Data/ML",
    "scikit-learn": "Data/ML",
    "sklearn": "Data/ML",
    "tensorflow": "Data/ML",
    "pytorch": "Data/ML",
    "keras": "Data/ML",
    "mlflow": "Data/ML",
    "airflow": "Data/ML",
    "spark": "Data/ML",
    "pyspark": "Data/ML",
    "sql": "Data/ML",
    "postgres": "Data/ML",
    "postgresql": "Data/ML",
    "mysql": "Data/ML",
    "bigquery": "Data/ML",
    "snowflake": "Data/ML",
    "databricks": "Data/ML",
    "lookml": "Data/ML",
    "dbt": "Data/ML",

    # DevOps / Cloud
    "docker": "DevOps/Cloud",
    "kubernetes": "DevOps/Cloud",
    "k8s": "DevOps/Cloud",
    "aws": "DevOps/Cloud",
    "azure": "DevOps/Cloud",
    "gcp": "DevOps/Cloud",
    "google cloud": "DevOps/Cloud",
    "terraform": "DevOps/Cloud",
    "ansible": "DevOps/Cloud",
    "jenkins": "DevOps/Cloud",
    "github actions": "DevOps/Cloud",
    "gitlab ci": "DevOps/Cloud",
    "ci/cd": "DevOps/Cloud",
    "linux": "DevOps/Cloud",

    # QA / Testing
    "pytest": "QA/Testing",
    "junit": "QA/Testing",
    "selenium": "QA/Testing",
    "cypress": "QA/Testing",
    "playwright": "QA/Testing",
    "postman": "QA/Testing",
    "restassured": "QA/Testing",

    # Mobile
    "android": "Mobile",
    "kotlin": "Mobile",
    "swift": "Mobile",
    "ios": "Mobile",
    "react native": "Mobile",
    "flutter": "Mobile",
}

CATEGORY_PRIORITY = [
    "Backend",
    "Data/ML",
    "Frontend",
    "DevOps/Cloud",
    "QA/Testing",
    "Mobile",
    "Other",
]

CANDIDATE_STORE_PATH = Path("candidates.json")


# -----------------------------
# Utility & state helpers
# -----------------------------

def init_session_state() -> None:
    if "initialized" in st.session_state:
        return

    st.session_state.initialized = True

    # Question tracking
    st.session_state.total_questions_asked = 0
    st.session_state.asked_questions_by_category = {}

    # Conversation messages
    st.session_state.messages: List[Dict[str, str]] = []

    # Candidate info
    st.session_state.candidate_data: Dict[str, str] = {k: "" for k in REQUIRED_FIELDS}

    # Derived info
    st.session_state.role_summary = ""
    st.session_state.skill_summary = ""
    st.session_state.seniority_label = "Unknown"
    st.session_state.skill_categories: Dict[str, List[str]] = {}
    st.session_state.category_order: List[str] = []

    # Flow state
    st.session_state.state = "collecting_info"  # collecting_info, awaiting_consent, screening, ended
    st.session_state.current_field_index = 0

    # Consent
    st.session_state.consent_status = "unknown"  # unknown, granted, denied

    # Screening state
    st.session_state.current_category_index = 0
    st.session_state.category_question_index = 0
    st.session_state.answers: Dict[str, List[str]] = {}

    # Follow-up control
    st.session_state.awaiting_followup = False
    st.session_state.last_category_answered = None


def add_message(role: str, content: str) -> None:
    st.session_state.messages.append({"role": role, "content": content})


def candidate_name() -> str:
    n = st.session_state.candidate_data.get("full_name", "").strip()
    return n or "there"


def candidate_first_name() -> str:
    full = st.session_state.candidate_data.get("full_name", "").strip()
    if not full:
        return ""
    return full.split()[0]


def completion_message(max_reached: bool = False) -> str:
    first = candidate_first_name()
    if first:
        prefix = f"Thank you, {first}. "
    else:
        prefix = "Thank you. "
    base = (
        prefix
        + "Your screening is now complete. A recruiter will review your answers and, "
        "if there’s a suitable match, contact you about next steps. "
        "You can close this window now."
    )
    if max_reached:
        base += " (We’ve reached the maximum number of questions for this session.)"
    return base


def check_exit_keyword(user_input: str) -> bool:
    lower = user_input.lower().strip()
    return any(word in lower for word in EXIT_KEYWORDS)


def get_current_field_key() -> str:
    return REQUIRED_FIELDS[st.session_state.current_field_index]


def strip_label_prefix(text: str) -> str:
    if ":" in text:
        return text.split(":", 1)[1].strip()
    return text.strip()


def is_valid_email(text: str) -> bool:
    text = strip_label_prefix(text)
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(pattern, text) is not None


def normalize_phone(text: str) -> str:
    text = strip_label_prefix(text)
    text = text.replace(" ", "").replace("-", "")
    if text.startswith("+"):
        return "+" + re.sub(r"\D", "", text[1:])
    return re.sub(r"\D", "", text)


def is_valid_phone(text: str) -> bool:
    digits = normalize_phone(text)
    if digits.startswith("+"):
        digits = digits[1:]
    return digits.isdigit() and 8 <= len(digits) <= 15


def parse_years_experience(raw: str) -> int | None:
    raw = strip_label_prefix(raw).lower()
    match = re.search(r"(\d+(\.\d+)?)", raw)
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    value = max(0.0, min(40.0, value))
    return int(round(value))


def derive_seniority_label(years: int) -> str:
    if years < 2:
        return "Junior"
    if years < 6:
        return "Mid-level"
    return "Senior"


def parse_tech_stack(raw_tech: str) -> List[str]:
    text = strip_label_prefix(raw_tech)
    parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
    if not parts:
        parts = [p.strip() for p in text.split() if p.strip()]
    seen = set()
    unique = []
    for p in parts:
        low = p.lower()
        if low not in seen:
            seen.add(low)
            unique.append(p)
    return unique


def categorize_skills(tech_list: List[str]) -> Dict[str, List[str]]:
    categories: Dict[str, List[str]] = {}
    for tech in tech_list:
        label = tech.strip()
        if not label:
            continue
        low = label.lower()
        category = SKILL_CATEGORY_RULES.get(low, "Other")
        categories.setdefault(category, []).append(label)

    for cat, skills in categories.items():
        seen = set()
        deduped = []
        for s in skills:
            l = s.lower()
            if l not in seen:
                seen.add(l)
                deduped.append(s)
        categories[cat] = deduped

    return categories


def compute_category_order(categories: Dict[str, List[str]]) -> List[str]:
    present = set(categories.keys())
    ordered = [c for c in CATEGORY_PRIORITY if c in present]
    for c in categories.keys():
        if c not in ordered:
            ordered.append(c)
    return ordered


def advance_to_next_field() -> None:
    st.session_state.current_field_index += 1
    if st.session_state.current_field_index >= len(REQUIRED_FIELDS):
        st.session_state.current_field_index = len(REQUIRED_FIELDS) - 1


def ask_next_field_question() -> None:
    idx = st.session_state.current_field_index
    if idx >= len(REQUIRED_FIELDS):
        return
    field_key = REQUIRED_FIELDS[idx]
    label = FIELD_LABELS.get(field_key, field_key.replace("_", " ").title())
    add_message("assistant", f"Please provide your **{label}**.")


def prepare_screening_after_consent() -> None:
    if not st.session_state.skill_categories:
        raw_tech = st.session_state.candidate_data.get("tech_stack", "")
        tech_list = parse_tech_stack(raw_tech)
        st.session_state.skill_categories = categorize_skills(tech_list)

    categories = st.session_state.skill_categories
    if not categories:
        raw_tech = st.session_state.candidate_data.get("tech_stack", "")
        tech_list = parse_tech_stack(raw_tech)
        categories = {"Other": tech_list or ["(no technologies provided)"]}
        st.session_state.skill_categories = categories

    st.session_state.category_order = compute_category_order(categories)

    st.session_state.current_category_index = 0
    st.session_state.category_question_index = 0
    st.session_state.total_questions_asked = 0
    st.session_state.asked_questions_by_category = {cat: [] for cat in st.session_state.category_order}
    st.session_state.answers = {cat: [] for cat in st.session_state.category_order}
    st.session_state.awaiting_followup = False
    st.session_state.last_category_answered = None


def get_current_category() -> str | None:
    if not st.session_state.category_order:
        return None
    idx = st.session_state.current_category_index
    if idx < 0 or idx >= len(st.session_state.category_order):
        return None
    return st.session_state.category_order[idx]


def ask_next_screening_question() -> None:
    """
    Decide which category/question to ask next and call the Question Agent.

    Behaviour:
    - Global hard cap of MAX_TOTAL_QUESTIONS.
    - Natural balancing: always prefers categories with fewer questions.
    - One immediate follow-up in the same category after each answer.
    - Sends only a limited history window (recent Q/A) to keep prompts small.
    """
    if st.session_state.total_questions_asked >= MAX_TOTAL_QUESTIONS:
        add_message("assistant", completion_message(max_reached=True))
        st.session_state.state = "ended"
        return

    if not st.session_state.category_order:
        add_message("assistant", completion_message())
        st.session_state.state = "ended"
        return

    categories = st.session_state.category_order
    num_categories = len(categories)

    if not st.session_state.asked_questions_by_category:
        st.session_state.asked_questions_by_category = {cat: [] for cat in categories}
    asked_q = st.session_state.asked_questions_by_category

    # ---- Follow-up priority ----
    if st.session_state.awaiting_followup and st.session_state.last_category_answered:
        category = st.session_state.last_category_answered
        st.session_state.awaiting_followup = False
    else:
        # Balanced selection: pick a category with the fewest questions so far
        counts = {cat: len(asked_q.get(cat, [])) for cat in categories}
        min_count = min(counts.values())
        start_idx = st.session_state.current_category_index
        selected_idx = 0
        for offset in range(num_categories):
            idx = (start_idx + offset) % num_categories
            cat = categories[idx]
            if counts[cat] == min_count:
                selected_idx = idx
                break
        st.session_state.current_category_index = selected_idx
        category = categories[selected_idx]

    questions_in_cat = asked_q.get(category, [])
    question_number_for_cat = len(questions_in_cat) + 1

    all_answers_in_category = st.session_state.answers.get(category, [])
    last_answer = all_answers_in_category[-1] if all_answers_in_category else ""

    MAX_Q_HISTORY = 5
    MAX_A_HISTORY = 3
    recent_questions = questions_in_cat[-MAX_Q_HISTORY:] if questions_in_cat else []
    recent_answers = all_answers_in_category[-MAX_A_HISTORY:] if all_answers_in_category else []

    cd = st.session_state.candidate_data
    skills_in_cat = st.session_state.skill_categories.get(category, [])

    # 🔄 Show a spinner while we generate the next technical question
    with st.spinner("Analyzing your skills to prepare the next question..."):
        q = generate_category_question(
            full_name=cd.get("full_name", ""),
            years_experience=cd.get("years_experience", ""),
            seniority_label=st.session_state.seniority_label,
            role_summary=st.session_state.role_summary,
            category=category,
            skills_in_category=skills_in_cat,
            question_number=question_number_for_cat,
            previously_asked_questions=recent_questions,
            answers_in_category=recent_answers,
            last_answer=last_answer,
        )

    st.session_state.category_question_index = question_number_for_cat - 1
    st.session_state.total_questions_asked += 1
    st.session_state.asked_questions_by_category.setdefault(category, []).append(q)

    add_message("assistant", q)


def handle_fallback(user_input: str) -> None:
    try:
        resp = generate_fallback_response(
            user_message=user_input,
            current_state=st.session_state.state,
        )
        add_message("assistant", resp)
    except Exception:
        add_message(
            "assistant",
            "I’m sorry, I couldn’t process that properly. "
            "Please answer the last question or type 'exit' to finish.",
        )


def load_candidate_store() -> List[Dict]:
    if not CANDIDATE_STORE_PATH.exists():
        return []
    try:
        with CANDIDATE_STORE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_candidate_profile(profile: Dict) -> None:
    data = load_candidate_store()
    data.append(profile)
    with CANDIDATE_STORE_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# -----------------------------
# Main Streamlit app
# -----------------------------

def main() -> None:
    setup_page()
    init_session_state()
    render_sidebar_profile()

    # Render main panel (header + phase + hero/closing + chat)
    render_chat_history(
        st.session_state.messages,
        st.session_state.state,
        st.session_state.total_questions_asked,
        MAX_TOTAL_QUESTIONS,
        candidate_first_name(),
        st.session_state.role_summary,
        st.session_state.skill_summary,
    )

    # If already ended, do not show chat input
    if st.session_state.state == "ended":
        return

    # Ask first profile field automatically
    if (
        st.session_state.state == "collecting_info"
        and st.session_state.current_field_index == 0
        and len(st.session_state.messages) == 0
    ):
        ask_next_field_question()
        st.rerun()

    user_input = st.chat_input("Type your response here...")
    if user_input is None:
        return

    add_message("user", user_input)

    # Global exit handling
    if check_exit_keyword(user_input):
        add_message("assistant", completion_message())
        st.session_state.state = "ended"
        st.rerun()

    # ---- COLLECTING INFO ----
    if st.session_state.state == "collecting_info":
        field_key = get_current_field_key()
        raw = user_input.strip()

        if field_key == "full_name":
            value = strip_label_prefix(raw)
            st.session_state.candidate_data[field_key] = value
            add_message("assistant", f"Nice to meet you, **{candidate_name()}** 👋")
            advance_to_next_field()
            ask_next_field_question()
            st.rerun()

        elif field_key == "email":
            if not is_valid_email(raw):
                add_message(
                    "assistant",
                    "That doesn’t look like a valid email. "
                    "Please enter something like `name@example.com`.",
                )
                st.rerun()
            value = strip_label_prefix(raw)
            st.session_state.candidate_data[field_key] = value
            advance_to_next_field()
            ask_next_field_question()
            st.rerun()

        elif field_key == "phone":
            if not is_valid_phone(raw):
                add_message(
                    "assistant",
                    "That doesn’t look like a valid phone number. "
                    "Please enter 8–15 digits (you can start with `+` for country code).",
                )
                st.rerun()
            value = normalize_phone(raw)
            st.session_state.candidate_data[field_key] = value
            advance_to_next_field()
            ask_next_field_question()
            st.rerun()

        elif field_key == "years_experience":
            years = parse_years_experience(raw)
            if years is None:
                add_message(
                    "assistant",
                    "Could you enter your experience roughly as a number? "
                    "For example: `1`, `2.5 years`, or `3 yrs`.",
                )
                st.rerun()
            st.session_state.candidate_data[field_key] = years
            st.session_state.seniority_label = derive_seniority_label(years)
            add_message(
                "assistant",
                f"Got it – I'll treat you as **{st.session_state.seniority_label}** based on your experience.",
            )
            advance_to_next_field()
            ask_next_field_question()
            st.rerun()

        elif field_key == "desired_positions":
            value = strip_label_prefix(raw)
            st.session_state.candidate_data[field_key] = value
            advance_to_next_field()
            ask_next_field_question()
            st.rerun()

        elif field_key == "current_location":
            value = strip_label_prefix(raw)
            st.session_state.candidate_data[field_key] = value
            advance_to_next_field()
            ask_next_field_question()
            st.rerun()

        elif field_key == "tech_stack":
            value = strip_label_prefix(raw)
            st.session_state.candidate_data[field_key] = value

            tech_list = parse_tech_stack(value)
            if not tech_list:
                add_message(
                    "assistant",
                    "I couldn't detect any technologies. "
                    "Please enter at least one, e.g. `Python, Django`.",
                )
                st.rerun()

            categories = categorize_skills(tech_list)
            st.session_state.skill_categories = categories
            st.session_state.category_order = compute_category_order(categories)

            desired_positions = st.session_state.candidate_data.get("desired_positions", "")
            years = st.session_state.candidate_data.get("years_experience", 0)

            # 🔄 Show spinner while analyzing profile and skills
            with st.spinner("Analyzing your profile and skills..."):
                try:
                    role_summary = generate_role_summary(
                        desired_positions=desired_positions,
                        years_experience=years,
                    )
                    st.session_state.role_summary = role_summary
                except Exception:
                    st.session_state.role_summary = ""

                try:
                    skill_summary = generate_skill_summary(raw_tech_stack=value)
                    st.session_state.skill_summary = skill_summary
                except Exception:
                    st.session_state.skill_summary = ""

            add_message(
                "assistant",
                "Thanks for sharing your profile and tech stack.\n\n"
                "Before we continue, do you consent to **storing your profile** "
                "(name, experience, and tech stack) for this demo screening? "
                "Please reply **Yes** or **No**.",
            )
            st.session_state.state = "awaiting_consent"
            st.rerun()

    # ---- AWAITING CONSENT ----
    if st.session_state.state == "awaiting_consent":
        answer = user_input.strip().lower()
        yes_keywords = {"yes", "y", "yeah", "yep", "sure", "of course", "i agree", "i consent"}
        no_keywords = {"no", "n", "nope", "i do not", "dont", "don't"}

        if any(k in answer for k in yes_keywords):
            st.session_state.consent_status = "granted"
            profile = {
                "candidate_data": st.session_state.candidate_data,
                "role_summary": st.session_state.role_summary,
                "skill_summary": st.session_state.skill_summary,
                "seniority_label": st.session_state.seniority_label,
                "skill_categories": st.session_state.skill_categories,
            }
            save_candidate_profile(profile)
            add_message(
                "assistant",
                "Thank you for your consent. I’ve stored your profile for this demo.\n\n"
                "Now I’ll ask you a few technical questions based on your skills.",
            )
            st.session_state.state = "screening"
            prepare_screening_after_consent()
            ask_next_screening_question()
            st.rerun()

        elif any(k in answer for k in no_keywords):
            st.session_state.consent_status = "denied"
            add_message(
                "assistant",
                "Understood – I will **not** store your profile.\n\n"
                "We can still proceed with a brief technical screening for practice. Let's continue.",
            )
            st.session_state.state = "screening"
            prepare_screening_after_consent()
            ask_next_screening_question()
            st.rerun()
        else:
            add_message(
                "assistant",
                "I didn’t clearly understand your consent choice. "
                "Please reply with **Yes** if you agree, or **No** if you do not.",
            )
            st.rerun()

    # ---- SCREENING ----
    if st.session_state.state == "screening":
        category = get_current_category()
        if category is None:
            add_message("assistant", completion_message())
            st.session_state.state = "ended"
            st.rerun()

        # Store the answer to the last question
        st.session_state.answers.setdefault(category, []).append(user_input.strip())

        # Mark that we should ask one follow-up in the same category next
        st.session_state.awaiting_followup = True
        st.session_state.last_category_answered = category

        # Move to next question index for this category
        st.session_state.category_question_index += 1

        # SMART ACK: not after EVERY answer, only occasionally
        total_answers = sum(len(v) for v in st.session_state.answers.values())
        if total_answers == 1:
            add_message("assistant", "Thanks, I’ve noted your answer.")
        elif total_answers % 5 == 0:
            add_message(
                "assistant",
                "Thanks, that helps me understand your experience. Here’s the next question.",
            )

        ask_next_screening_question()
        st.rerun()

    # ---- Fallback for unexpected state ----
    handle_fallback(user_input)
    st.rerun()


if __name__ == "__main__":
    main()
