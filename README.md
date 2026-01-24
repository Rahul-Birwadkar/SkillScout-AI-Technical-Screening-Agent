# 🏆 SkillScout – AI Technical Screening Agent

SkillScout is an **AI-powered technical screening assistant** built with **Streamlit** and **LLMs**.  
It simulates an initial recruiter-led technical interview by:

* Collecting candidate profile information  
* Understanding the candidate’s tech stack  
* Categorizing skills automatically  
* Asking **context-aware technical questions** with **follow-ups**  
* Respecting a global screening limit (20 questions)  
* Presenting a **clean, phase-based interview UI** with loading feedback  

This project is a **production-style demo** for AI-assisted hiring workflows, while remaining simple enough to run locally.

---

## 🚀 Tech Stack

* **Language:** Python 3.10+  
* **UI Framework:** Streamlit (chat-based interface)  
* **LLM Provider:** OpenAI API  
* **Models Used:**
  * `gpt-5.2` – role understanding & seniority reasoning  
  * `gpt-4o-mini` – skill summarization, technical questions, fallback handling  
* **State Management:** Streamlit `st.session_state`  
* **Data Storage (Demo):** Local JSON file (`candidates.json`)  
* **Prompt Engineering:** Structured prompts using  
  **ROLE → GOAL → CONTEXT → INSTRUCTIONS → OUTPUT FORMAT → CONSTRAINTS**

---

## 🎙️ 1. Conversational Candidate Intake

The assistant collects:

* Full name  
* Email address (**validated**)  
* Phone number (**validated**, normalized)  
* Years of experience (parsed from free text)  
* Desired role(s)  
* Current location  
* Tech stack (free text, comma-separated or messy)

UI behaviour:

* Friendly, personalized prompts (greets by name).  
* Clear **phases** displayed in the header:
  * `Step 1 of 3 · Profile details`  
  * `Step 2 of 3 · Data consent`  
  * `Step 3 of 3 · Technical screening`  
  * `Screening completed` when done  
* Global `exit` command to end the interview at any time.

---

## 🧩 2. Automatic Skill Categorization

The assistant uses a **simple rule-based skill mapper** to group technologies into categories.

**How it works:**

1. Candidate enters tech stack as free text (e.g. `Python, Django, PostgreSQL, Docker`).  
2. The string is split and cleaned into individual skills.  
3. Each skill is:
   * lowercased  
   * compared against predefined keyword → category rules  
   * assigned to the **first matching category**  
4. If no rule matches, the skill is assigned to **Other**.

Benefits:

* Transparent and easy to debug  
* Deterministic (no LLM dependency for mapping)  
* Fast and cost-free  

Usage:

* Internally drives **which technical questions** to ask per category.  
* In the UI, candidates see a flat **“Skills”** tag list in the sidebar –  
  **no internal labels** like `Backend`, `Data/ML`, etc., to keep the interview natural.

---

## 🧠 3. Multi-Agent LLM Architecture

SkillScout uses multiple specialized LLM “agents”:

| Agent                      | Purpose                                | Model         |
| -------------------------- | -------------------------------------- | ------------- |
| Role Understanding Agent   | Normalize desired roles & seniority    | `gpt-5.2`     |
| Skill Summary Agent        | Clean & summarize tech stack           | `gpt-4o-mini` |
| Technical Question Agent   | Category-based technical questions     | `gpt-4o-mini` |
| Fallback / Guardrail Agent | Handle unclear or off-topic input      | `gpt-4o-mini` |

All agents are **stateless**.  
`app.py` passes all necessary context (profile, history, last answer, etc.) on each call.

---

## 🎯 4. Intelligent Technical Screening

### Global Rules

* **Max 20 technical questions** per candidate (`MAX_TOTAL_QUESTIONS = 20`).  
* Questions are generated dynamically using the Technical Question Agent.  
* Screening ends automatically when the cap is reached, with a clear closing message.

### Per-Category Logic

* Soft cap of **~5 questions per category**.  
* Balancing logic:
  * The app chooses categories with **fewer questions so far**.  
  * If all categories hit the soft cap but total < 20, deeper follow-ups are allowed.  

### Follow-Up Behaviour

The Question Agent receives:

* Previously asked questions in the category  
* All previous answers in the category  
* The **most recent answer** (`last_answer`)  

The prompt instructs it to:

* Avoid repeating or trivial rephrasing of earlier questions.  
* Prefer follow-ups that build on the candidate’s latest answer.  
* Adjust difficulty by seniority (Junior / Mid-level / Senior).

### Neutral Acknowledgements

To keep the tone fair regardless of answer quality, the app:

* Occasionally sends neutral responses, for example:
  * `"Thanks, I’ve noted your answer."`  
  * `"Thanks, that helps me understand your experience. Here’s the next question."`
* Does **not** assume the answer was good or bad (“let’s dive deeper”) unless explicitly needed.

---

## 🧾 5. Clean, Phase-Based UI

The UI is split between **main panel** and **sidebar**, using `ui.py`.

### Main Panel

* Header: `🧑‍💻 SkillScout – AI Technical Screening Agent`  
* Phase pill: small chip near the top (`Step 1 of 3 · Profile details`, etc.)  
* Question counter during screening (e.g. `Technical questions answered: 3 / 20 (approx.)`).  
* **Hero intro card** on first load, explaining:
  * What will happen (profile → consent → questions)  
  * That `exit` can be used at any time  

* Chat transcript:
  * Only actual interview Q&A messages are shown.
  * System/flow information is represented via UI elements, not noisy chat messages.

* Completion screen:
  * A success message thanking the candidate by first name when possible.
  * Optional expandable **AI-generated profile summary** (Role Summary + Skill Summary).

### Sidebar (Card Layout)

* **Candidate Profile** card:
  * Basic info: name, email, phone, location.  
  * Experience block (Total, Level, Target roles) **only shown** when real data exists.  

* **Agent Insights** card:
  * Profile Summary (Role Agent output) – if available.  
  * Skill Summary (Skill Summary Agent output) – if available.  
  * If nothing is ready yet, a short muted sentence explains that a summary will appear later.

* **Skills** card:
  * All detected skills as small tags: `Python`, `React`, `Docker`, etc.  
  * Flat list, no visible internal bucket labels.

* **Data & Consent** card:
  * Shows whether consent is pending, granted or denied, with short friendly text.

---

## 🔄 6. Loading & Feedback UX

To avoid the feeling that “nothing is happening” when LLM calls are running, SkillScout uses **spinners**:

* After the tech stack is entered:
  * `"Analyzing your profile and skills..."`  
  while role summary and skill summary are generated.

* Before each technical question:
  * `"Analyzing your skills to prepare the next question..."`  
  while the Technical Question Agent generates the next question.

This makes the interview feel responsive and intentional, even when the API takes a bit of time.

---

## 🔐 7. Consent & Data Handling (Demo Mode)

* After profile collection, the assistant asks explicitly for consent.  
* If the candidate answers **Yes**:
  * Profile (data + AI summaries) is **appended** to `candidates.json`.  
* If they answer **No**:
  * Nothing is persisted.
  * The technical screening still continues for practice.

> ⚠️ `candidates.json` is **demo storage only**.  
> For real hiring use, integrate proper secure and GDPR-compliant storage.

---

## 🛟 8. Robust Fallback Handling

If the candidate:

* Sends something unclear  
* Goes off-topic  
* Asks unrelated questions  

The **Fallback Agent**:

* Acknowledges their message  
* Reminds them this is a technical screening  
* Gently asks them to answer the last question or type `exit`  

It **does not** introduce new flows or questions – it only keeps the interview on track.

---

## 🧱 Project Structure

```text
.
├── app.py              # Main Streamlit application (state & flow control)
├── ui.py               # UI helpers (layout, sidebar cards, hero & closing sections)
├── llm_client.py       # LLM client + multi-agent interface
├── prompts.py          # System & user prompts (prompt engineering layer)
├── requirements.txt    # Python dependencies
├── candidates.json     # Demo storage (created at runtime)
└── README.md           # Project documentation

🛠️ Installation & Setup
1. Clone the repository
git clone https://github.com/your-username/skillscout-ai-hiring-assistant.git
cd skillscout-ai-hiring-assistant

2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # macOS / Linux
venv\Scripts\activate     # Windows

3. Install dependencies
pip install -r requirements.txt

4. Set your OpenAI API key
export OPENAI_API_KEY="your_openai_api_key"   # macOS / Linux
setx OPENAI_API_KEY "your_openai_api_key"     # Windows

5. Run the app
streamlit run app.py

🧪 How to Use

Open the Streamlit app in your browser.

Answer the profile questions (Step 1).

Enter your tech stack (e.g. Python, Django, PostgreSQL, Docker).

Answer the consent question with Yes or No.

Respond to technical questions naturally, like in a real interview.

Type exit any time to end the screening.

A live candidate profile view is shown in the sidebar throughout.

🎯 Design Philosophy

Stateless LLMs, stateful app – all memory is in st.session_state.

Prompt engineering first – no fine-tuning required.

Human-like interview flow instead of naive Q&A.

Clear separation of concerns:

Flow & business logic → app.py

UI & layout → ui.py

LLM calls → llm_client.py

Prompt templates → prompts.py

🧠 Prompt Engineering Overview

Prompts follow the same template:

ROLE → GOAL → CONTEXT → INSTRUCTIONS → OUTPUT FORMAT → CONSTRAINTS

Role Understanding Agent

Converts messy “desired roles + years of experience” into a clean, recruiter-friendly sentence.

Infers probable seniority (Junior / Mid-level / Senior).

Outputs one short line, no extra commentary.

Skill Summary Agent

Acts like a CV/LinkedIn skill optimiser.

Cleans and groups the tech stack into a single concise sentence.

Deduplicates skills and fixes casing without inventing new tech.

Technical Question Agent

Behaves like a senior interviewer for one category at a time.

Uses:

profile summary

seniority label

category & skills

previously asked questions

all previous answers

latest answer

Generates exactly one clear, self-contained technical question.

Does not answer the question or add explanations.

Fallback / Guardrail Agent

Keeps the conversation on track.

Acknowledges off-topic or unclear messages.

Politely asks the candidate to answer the last question or type exit.

Never changes the flow or introduces new steps.

This structure keeps the system predictable, transparent, and easy to extend.

📜 License

This project is provided for educational and demonstration purposes.
You are free to modify and extend it for personal or academic use.

🙌 Acknowledgements

Built as part of an AI/ML hiring assistant assignment and extended into a production-style, multi-agent demo using Streamlit and OpenAI LLMs.
