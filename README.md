# 🚀 Autonomous Software Debugging Assistant

A powerful, multi-agent AI system designed to analyze GitHub repositories, detect logical flaws, generate production-ready patches, and test them in a secure sandbox. Built with **AutoGen**, **Google Gemini**, and **Groq**, this assistant provides a comprehensive suite of debugging, patching, and visualization tools.

---

## ✨ Key Features

### 🛠️ Intelligent Debugging
- **Multi-Agent Orchestration**: Sequential handoffs between specialized agents: `Code_Parser`, `Bug_Detection`, `Patch_Generator`, `Reviewer`, and `Patch_Applier`.
- **Repo Chat**: Conversational AI interface to ask specific questions about any part of your codebase based on the parsed context.

### 🛡️ Safe Patching Workflow
- **Isolated Sandbox**: Suggested code patches are first applied to a temporary, isolated clone of your repository.
- **Dry-Run Testing**: Install dependencies and execute test scripts safely within the UI without affecting your main workspace.
- **One-Click Apply**: Once testing is verified and successful, changes can be directly synced to your original local directory.

### 🖼️ Advanced System Visualizations
- **Architectural Rendering**: Dynamically generates Flowcharts, Class Diagrams, Sequence Diagrams, ER Diagrams, and more using an intelligent `DiagramRenderer`.
- **JSON-to-SVG Pipeline**: Leverages LLMs to output structured JSON topologies, which are then deterministically rendered into clean, beautiful, non-overlapping SVG graphics.
- **Hot-Reloading**: Independent visualization generation that supports mid-session regeneration and tweak iterations gracefully.

### 💾 Persistent History
- **Firestore Integration**: All analyses and generated diagrams are automatically synced and stored in Firebase.
- **Unified History Tab**: Revisit past analysis sessions with a clean, searchable interface.

### ⚡ Performance & Stability
- **Multi-Model Fallback & Rotation**: Primary integration with **Groq** for speed, with robust fallback to **Google Gemini**. Automatically rotates API keys to bypass rate limits gracefully.
- **Anti-Hallucination Guard**: A strict AST-based "Nuclear" guard prevents agents from inventing non-existent packages or malicious imports.

---

## 📂 Project Structure
```text
/
├── app.py              # Main Streamlit Dashboard (Tabbed UI)
├── credentials/        # Firebase Service Account JSON (ignored by git)
├── .env                # API Keys & Configuration
├── requirements.txt    # Project Dependencies
└── src/                # Core Application Logic
    ├── agents/         # AutoGen Agent & Orchestrator Definitions
    ├── database/       # Firebase/Firestore Management
    ├── utils/          # Diagram Rendering & Repo Handling
    └── config.py       # Enhanced Configuration & Logging
```

---

## ⚙️ Setup & Installation

### 1. Configure Environment
Create a `.env` file in the root directory:
```env
# AI API Keys
GOOGLE_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key_1,your_groq_key_2 (supports comma-separated keys)

# GitHub Token (for remote cloning)
GITHUB_TOKEN=your_github_pat

# Firebase Configuration
FIREBASE_SERVICE_ACCOUNT=credentials/firebase.json
DATABASE_URL=https://your-project.firebaseio.com
```

### 2. Setup Firebase
1. Create a project in the [Firebase Console](https://console.firebase.google.com/).
2. Enable **Firestore Database**.
3. Generate a **Service Account JSON** and place it in the `credentials/` folder as `firebase.json`.

### 3. Run Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Start the dashboard
streamlit run app.py
```

---

## 🛡️ Usage Tips
- **Analysis Time**: On Free Tier keys, the system might include delays between phases to avoid rate limits. A full run typically takes ~1-3 minutes.
- **Visualization Tab**: Use the multi-select menu in the **Visualizations** tab to choose specific architectural views, then click **"Regenerate Selected Diagrams"** to map them out instantly.
- **Patch Testing**: The testing sandbox is primarily active for local repository paths (`Local Repo Path`). Remote GitHub patches are presented as suggestions only.

---
*Developed for Advanced Autonomous Software Debugging.*
