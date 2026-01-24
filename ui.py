# ui.py

"""
The SkillScout – AI Technical Screening Agent.

This module contains ONLY Streamlit UI and presentation logic.
The main app (app.py) handles all interview state, LLM calls, and control flow.
"""

import os
import streamlit as st


def setup_page() -> None:
    """Set page config, global styles, and sidebar instructions."""
    st.set_page_config(
        page_title="SkillScout – AI Technical Screening Agent",
        page_icon="🧑‍💻",
        layout="wide",
    )

    # -------- Global UI Styling --------
    st.markdown(
        """
<style>
.card {
    background: linear-gradient(135deg, #f8f9ff, #ffffff);
    border: 1px solid #e4e7f2;
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 16px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.04);
}
.card h4 {
    margin-bottom: 8px;
    color: #2b2f77;
}
.card p {
    margin: 4px 0;
    font-size: 0.9rem;
}
.muted {
    color: #6b7280;
    font-size: 0.85rem;
}
.skill-tag {
    display: inline-block;
    background-color: #eef2ff;
    color: #3730a3;
    padding: 4px 8px;
    margin: 3px 4px 0 0;
    border-radius: 6px;
    font-size: 0.75rem;
}
.phase-pill {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    background-color: #eef2ff;
    color: #3730a3;
    font-size: 0.8rem;
    margin-bottom: 6px;
}
.question-counter {
    color: #6b7280;
    font-size: 0.8rem;
    margin-bottom: 12px;
}
.hero-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 14px;
}
.hero-card h3 {
    margin-bottom: 8px;
}
.hero-card ul {
    margin-top: 6px;
    padding-left: 20px;
}
</style>
        """,
        unsafe_allow_html=True,
    )

    # -------- Sidebar Instructions --------
    st.sidebar.title("🧑‍💻 SkillScout – AI Technical Screening Agent")
    st.sidebar.markdown(
        """
**Purpose:** Initial AI-driven technical screening  

✔ Answer naturally, like in a real interview  
✔ It's okay to say when something is unclear  
✔ You will be asked for consent before data is stored  
✔ Type **`exit`** anytime to end the interview  

Your profile will update live as you answer.
        """
    )

    if not os.getenv("OPENAI_API_KEY"):
        st.sidebar.error(
            "OPENAI_API_KEY is not set. Please configure it before running the app."
        )
        st.sidebar.caption("This is a system setup issue, not your fault.")


def render_sidebar_profile() -> None:
    """Render candidate profile preview as a set of cards."""
    cd = st.session_state.candidate_data

    st.sidebar.markdown("---")
    st.sidebar.subheader("Candidate Profile")

    years = cd.get("years_experience")
    exp_text = f"{years} years" if years else "—"
    seniority = st.session_state.seniority_label or "Unknown"
    desired = cd.get("desired_positions") or "—"

    # Decide if we should show the experience block at all
    show_experience_block = (
        bool(years)
        or (seniority and seniority != "Unknown")
        or desired != "—"
    )

    # -------- Candidate Card HTML (no leading spaces, so not treated as code) --------
    basic_html = (
        f"<div class='card'>"
        f"<h4>👤 Basic Information</h4>"
        f"<p><strong>Name:</strong> {cd.get('full_name') or '—'}</p>"
        f"<p><strong>Email:</strong> {cd.get('email') or '—'}</p>"
        f"<p><strong>Phone:</strong> {cd.get('phone') or '—'}</p>"
        f"<p><strong>Location:</strong> {cd.get('current_location') or '—'}</p>"
    )

    if show_experience_block:
        basic_html += (
            "<hr style='border:none;border-top:1px solid #eee;margin:10px 0'>"
            "<h4>💼 Experience</h4>"
            f"<p><strong>Total:</strong> {exp_text}</p>"
            f"<p><strong>Level:</strong> {seniority}</p>"
            f"<p><strong>Target Role(s):</strong> {desired}</p>"
        )

    basic_html += "</div>"

    st.sidebar.markdown(basic_html, unsafe_allow_html=True)

    # -------- Agent Insights Card --------
    role_summary = (st.session_state.role_summary or "").strip()
    skill_summary = (st.session_state.skill_summary or "").strip()

    insights_html = "<div class='card'><h4>🧠 Agent Insights</h4>"

    if role_summary:
        insights_html += (
            "<p class='muted'><strong>Profile Summary</strong></p>"
            f"<p>{role_summary}</p>"
        )

    if skill_summary:
        insights_html += (
            "<p class='muted' style='margin-top:8px;'><strong>Skill Summary</strong></p>"
            f"<p>{skill_summary}</p>"
        )

    if not role_summary and not skill_summary:
        insights_html += (
            "<p class='muted'>Once you share your profile and tech stack, "
            "a short AI-generated summary will appear here.</p>"
        )

    insights_html += "</div>"

    st.sidebar.markdown(insights_html, unsafe_allow_html=True)

    # -------- Skills Card --------
    skill_categories = st.session_state.skill_categories
    if skill_categories:
        all_skills = sorted(
            {
                skill
                for skills in skill_categories.values()
                for skill in skills
                if skill
            }
        )

        if all_skills:
            skills_html = "".join(
                f"<span class='skill-tag'>{skill}</span>"
                for skill in all_skills
            )

            st.sidebar.markdown(
                "<div class='card'><h4>🛠️ Skills</h4>" + skills_html + "</div>",
                unsafe_allow_html=True,
            )

    # -------- Consent Card --------
    consent = st.session_state.consent_status

    if consent == "granted":
        msg = "✅ Consent granted. Your profile is stored for this demo."
    elif consent == "denied":
        msg = "⚠️ Consent not granted. Your profile will not be stored."
    else:
        msg = "ℹ️ Consent pending. You will be asked before anything is saved."

    st.sidebar.markdown(
        "<div class='card'><h4>🔐 Data & Consent</h4><p>" + msg + "</p></div>",
        unsafe_allow_html=True,
    )


def _phase_text(state: str) -> str:
    if state == "collecting_info":
        return "Step 1 of 3 · Profile details"
    if state == "awaiting_consent":
        return "Step 2 of 3 · Data consent"
    if state == "screening":
        return "Step 3 of 3 · Technical screening"
    if state == "ended":
        return "Screening completed"
    return "Screening"


def render_chat_history(
    messages,
    state: str,
    total_questions_asked: int,
    max_total_questions: int,
    first_name: str,
    role_summary: str,
    skill_summary: str,
) -> None:
    """
    Render the main panel: header, phase info, optional hero/closing text, and chat.
    """
    st.header("🧑‍💻 SkillScout – AI Technical Screening Agent")

    # Phase pill + subtle question counter
    st.markdown(
        f"<span class='phase-pill'>{_phase_text(state)}</span>",
        unsafe_allow_html=True,
    )

    if state == "screening" and total_questions_asked > 0:
        st.markdown(
            f"<div class='question-counter'>Technical questions answered: "
            f"{total_questions_asked} / {max_total_questions} (approx.)</div>",
            unsafe_allow_html=True,
        )
    elif state == "collecting_info":
        st.markdown(
            "<div class='question-counter'>We’ll first capture your basic profile, "
            "then move to technical questions.</div>",
            unsafe_allow_html=True,
        )

    # Hero intro for very beginning (no user messages yet)
    has_user_messages = any(m["role"] == "user" for m in messages)
    if state == "collecting_info" and not has_user_messages:
        st.markdown(
            """
<div class="hero-card">
    <h3>Welcome to SkillScout – AI Technical Screening Agent</h3>
    <p>I’ll ask you a short series of questions about your experience and skills.</p>
    <ul>
        <li>Step 1: Share your profile and tech stack</li>
        <li>Step 2: Confirm data consent</li>
        <li>Step 3: Answer a small set of technical questions</li>
    </ul>
    <p class="muted">You can type <code>exit</code> at any time to end the interview.</p>
</div>
            """,
            unsafe_allow_html=True,
        )

    # If screening has ended, show a closing panel at the top
    if state == "ended":
        name_part = f"{first_name}, " if first_name and first_name.lower() != "there" else ""
        closing_text = (
            f"Thank you {name_part}your screening is now complete. "
            "A recruiter will review your answers and, if there’s a suitable match, "
            "contact you about next steps. You can close this window now."
        )
        st.success(closing_text)

        # Optional final summary card if we have data
        if role_summary or skill_summary:
            with st.expander("View a short summary of your profile (AI-generated)", expanded=False):
                if role_summary:
                    st.markdown("**Profile Summary**")
                    st.markdown(role_summary)
                if skill_summary:
                    st.markdown("**Skill Summary**")
                    st.markdown(skill_summary)

    # --- Chat transcript ---
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Tip below chat
    if state != "ended":
        st.caption("💡 Tip: You can type `exit` at any time to end the interview.")
