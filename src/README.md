# Autonomous Software Debugging Assistant

This project uses AutoGen and Google Gemini to automatically analyze GitHub repositories, detect bugs, and suggest patches.

## Prerequisites

- Python 3.11+
- Google Gemini API Key
- Firebase Project

## Firebase Setup Instructions

To retrieve your `FIREBASE_SERVICE_ACCOUNT` and `DATABASE_URL`:

### 1. Create/Select a Firebase Project
- Go to the [Firebase Console](https://console.firebase.google.com/).
- Click **Add project** or select an existing one.

### 2. Generate Service Account Key (`FIREBASE_SERVICE_ACCOUNT`)
- Click the **Gear icon (⚙️)** next to **Project Overview** in the left sidebar.
- Select **Project settings**.
- Navigate to the **Service accounts** tab.
- Click **Generate new private key**.
- Click **Generate key** in the popup.
- A `.json` file will download. Move this to your project folder (e.g., `credentials/firebase-key.json`) and update the path in your `.env` file.

### 3. Get Database URL (`DATABASE_URL`)
- **For Realtime Database**:
    - Click **Build** -> **Realtime Database** in the left sidebar.
    - Click **Create Database** if you haven't already.
    - The URL (e.g., `https://your-project-id.firebaseio.com/`) will be displayed at the top of the **Data** tab.
- **For Firestore**:
    - Click **Build** -> **Firestore Database**.
    - Click **Create database**.
    - *Note: Firestore initialization usually only requires the Project ID (found in the JSON), but some admin configurations use the URL format `https://<PROJECT_ID>.firebaseio.com`.*

## Installation

1. Clone this repository.
2. Create a `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```
3. Fill in your credentials in `.env`.
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the App

```bash
streamlit run app.py
```
