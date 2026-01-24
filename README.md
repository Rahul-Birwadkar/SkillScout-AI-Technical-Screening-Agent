# 🏆 SkillScout – AI Technical Screening Agent

SkillScout is an **AI-powered technical screening assistant** built with **Streamlit** and **LLMs**. It simulates an initial recruiter-led technical interview by collecting candidate details, understanding their tech stack, and dynamically asking **context-aware technical questions**.

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

SkillScout uses multiple specialized LLM agents, orchestrated by the application:

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

## 🛠️ Installation & Run (Local)

```bash
# 1. Clone the repository
git clone https://github.com/Rahul-Birwadkar/SkillScout-AI-Technical-Screening-Agent.git
cd SkillScout-AI-Technical-Screening-Agent

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

1. Open the Streamlit app in your browser
2. Enter candidate profile details
3. Provide your tech stack (free text)
4. Give consent (Yes / No)
5. Answer technical questions like a real interview
6. Type `exit` anytime to stop the screening

A live candidate profile and detected skills are shown in the sidebar during the interview.

---

## 🎯 Design Philosophy

* Stateless LLMs with predictable application logic
* Prompt engineering over fine-tuning
* Human-like interview flow
* Clear separation of concerns:

  * Flow & logic → `app.py`
  * UI → `ui.py`
  * LLM calls → `llm_client.py`
  * Prompts → `prompts.py`

---

## ☁️ GCP Deployment (Cloud Run)

SkillScout is deployed on **Google Cloud Platform (GCP)** using a modern, serverless, container-based workflow.

### Deployment Stack

* **Docker** – Containerization
* **Cloud Build** – Cloud-based Docker image build
* **Artifact Registry** – Container image storage
* **Cloud Run** – Serverless application hosting

### Key Characteristics

* Fully serverless (no VM management)
* Automatic scaling
* Secure secret handling via environment variables
* Production-style deployment pipeline

### Deployment Flow

1. Streamlit app is packaged using Docker
2. Cloud Build builds the container image
3. Image is stored in Artifact Registry
4. Cloud Run deploys the image as a managed service
5. OpenAI API key is injected securely at runtime

### Live Deployments

* **Streamlit Cloud (Demo):**
  [https://skillscout-ai-technical-screening-agent-pi9anz2z5rhcgappvsn57j.streamlit.app/](https://skillscout-ai-technical-screening-agent-pi9anz2z5rhcgappvsn57j.streamlit.app/)

* **GCP Cloud Run (Production-style):**
  [https://skillscout-app-821864398756.europe-west3.run.app](https://skillscout-app-821864398756.europe-west3.run.app)

This demonstrates both **rapid prototyping** and **production-ready cloud deployment**.

---

## 🔐 Secrets Management

* API keys are **never hard-coded**
* Secrets are injected via environment variables
* Safe for public GitHub repositories

---

## 📘 Documentation

Additional technical documentation:

* `docs/ARCHITECTURE.md` – System & agent architecture
* `docs/PROMPTS.md` – Prompt engineering strategy
* `docs/GCP_DEPLOYMENT.md` – Step-by-step GCP deployment

---

## 📜 License

Educational and demonstration use only. Free to modify and extend.

---

## 🙌 Acknowledgements

Built as an AI/ML hiring assistant demo and extended into a **production-style, cloud-deployed system** using Streamlit, OpenAI LLMs, and Google Cloud Platform.
