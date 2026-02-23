# 🚀 Autonomous Software Debugging Assistant

A multi-agent system powered by **Google Gemini** and **AutoGen** that automatically analyzes GitHub repositories to identify bugs and suggest patches.

## ✨ Features
- **Multi-Agent Orchestration**: Sequential analysis using Code Parser, Bug Detection, and Patch Generator agents.
- **Gemini 2.0/2.5 Support**: Optimized for the latest Google Generative AI models.
- **Quota Resilience**: Built-in 40-second throttling between analysis phases to respect Gemini Free Tier rate limits.
- **Streamlit UI**: Simple, intuitive dashboard for repository analysis and bug reporting.
- **Docker-Free**: Configured to run locally without requiring Docker for simplified setup.

## 📂 Project Structure
```text
/
├── app.py              # Main Streamlit Application
├── .env                # Environment Variables (Keys)
├── requirements.txt    # Project Dependencies
└── src/                # Core Logic & Modules
    ├── agents/         # AutoGen Agent Definitions
    ├── utils/          # GitHub Utilities
    └── config.py       # Global Configuration
```

## 🛠️ Setup & Installation

1. **Clone the Project**:
   ```bash
   git clone <your-repo-url>
   cd Software_Debugger
   ```

2. **Configure Environment**:
   Create a `.env` file in the root with:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key
   GITHUB_TOKEN=your_github_personal_access_token
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Running the App
Start the Streamlit dashboard:
```bash
streamlit run app.py
```

## 🛡️ API Quota Note (Free Tier)
To ensure stability on the Gemini Free Tier, the orchestrator includes a **40-second delay** between each phase. The analysis will take approximately 2-3 minutes to complete—this is normal and prevents "429: Quota Exceeded" errors.
