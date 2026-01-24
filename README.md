# 🏆 SkillScout – AI Technical Screening Agent

SkillScout is an **AI-powered technical screening assistant** built with **Streamlit** and **LLMs**. It simulates an initial recruiter-led technical interview by collecting candidate details, understanding their tech stack, and dynamically asking context-aware technical questions.

This project is a **production-style demo** of AI-assisted hiring workflows that is simple to run locally and easy to extend.

---

## 🚀 Tech Stack

* **Language:** Python 3.10+
* **UI:** Streamlit (chat-style interface)
* **LLM Provider:** OpenAI API
* **Models:** `gpt-5.2`, `gpt-4o-mini`
* **State Management:** `st.session_state`
* **Storage (Demo):** Local JSON (`candidates.json`)

---

## ✨ Key Features

* Conversational candidate intake (profile + consent)
* Free-text tech stack understanding and cleanup
* Automatic skill grouping (rule-based, deterministic)
* Context-aware technical questions with follow-ups
* Global screening limit (**max 20 questions**)
* Stateless LLMs with stateful app control
* Clean interview-style UI (no exposed internal labels)

---

## 🧠 High-Level Architecture

SkillScout uses multiple specialized LLM agents, orchestrated by the app:

* **Role Understanding Agent** – normalizes desired roles and infers seniority
* **Skill Summary Agent** – cleans and summarizes the tech stack
* **Technical Question Agent** – generates category-based interview questions
* **Fallback Agent** – handles unclear or off-topic input

All agents are **stateless**. The application manages memory, flow, and limits.

---

## 📂 Project Structure

```text
.
├── app.py          # Main Streamlit app & interview flow
├── ui.py           # UI components and layout helpers
├── llm_client.py   # LLM agent interface
├── prompts.py      # Prompt templates (prompt engineering layer)
├── requirements.txt
├── candidates.json # Demo storage (created at runtime)
└── README.md
```

---

## 🛠️ Installation & Run

```bash
# 1. Clone the repository
git clone https://github.com/your-username/skillscout-ai-hiring-assistant.git
cd skillscout-ai-hiring-assistant

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set OpenAI API key
export OPENAI_API_KEY="your_api_key"   # macOS / Linux
setx OPENAI_API_KEY "your_api_key"      # Windows

# 5. Run the app
streamlit run app.py
```

---

## 🧪 How to Use

1. Open the Streamlit app in your browser.
2. Enter candidate profile details.
3. Provide your tech stack (free text).
4. Give consent (Yes / No).
5. Answer technical questions like a real interview.
6. Type `exit` anytime to stop the screening.

A live candidate profile and detected skills are shown in the sidebar during the interview.

---

## 🎯 Design Philosophy

* Stateless LLMs, predictable app logic
* Prompt engineering over fine-tuning
* Human-like interview flow
* Clear separation of concerns:

  * Flow & logic → `app.py`
  * UI → `ui.py`
  * LLM calls → `llm_client.py`
  * Prompts → `prompts.py`

---

## 📜 License

This project is provided for **educational and demonstration purposes**. You are free to modify and extend it for personal or academic use.

---

## 🙌 Acknowledgements

Built as an AI/ML hiring assistant demo using **Streamlit** and
