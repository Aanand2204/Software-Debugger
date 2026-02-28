# 🚀 Autonomous Software Debugging Assistant

A powerful, multi-agent AI system designed to analyze GitHub repositories, detect logical flaws, and generate production-ready patches. Built with **AutoGen**, **Google Gemini**, and **Groq**, this assistant provides a comprehensive suite of debugging and visualization tools.

---

## ✨ Key Features

### 🛠️ Intelligent Debugging
- **Multi-Agent Flow**: Sequential orchestration between specialized agents: `Code_Parser`, `Bug_Detection`, `Patch_Generator`, and `Reviewer`.
- **Repo Chat**: Conversational AI interface to ask specific questions about any part of your codebase.

### 🖼️ Advanced Visualizations
- **8+ Diagram Types**: Generate Flowcharts, Class Diagrams, Sequence Diagrams, ER Diagrams, and more using **Mermaid 10.9.5**.
- **Dark Mode Optimization**: Specialized rendering ensures high contrast for arrows and lines on dark backgrounds.
- **Independent Generation**: Tweak and regenerate diagrams without re-analyzing the entire codebase.

### 💾 Persistent History
- **Firestore Integration**: All analyses and generated diagrams are automatically synced and stored in Firebase.
- **Unified History Tab**: Revisit past analysis sessions with a clean, searchable interface.

### ⚡ Performance & Stability
- **Multi-Model Fallback**: Primary integration with **Groq** for speed, with **Google Gemini** as a robust fallback.
- **Quota Management**: Built-in throttling to ensure stability on Free Tier API limits.

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
    ├── utils/          # GitHub Repo Handling
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

# GitHub Token (for private/public cloning)
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
- **Analysis Time**: On Free Tier keys, the system includes a 20-40s delay between phases to avoid rate limits. A full run typically takes ~2-3 minutes.
- **Visualization Tab**: Use the multi-select menu in the **Visualizations** tab to choose specific diagrams, then click **"Generate Selected Diagrams"** to visualize them instantly.

---
*Developed for Advanced Autonomous Software Debugging.*
