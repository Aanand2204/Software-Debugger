# Autonomous Software Debugger VS Code Extension

This extension brings the power of AI-driven codebase analysis and diagram generation directly into your VS Code workspace.

## Features
- **Analyze Local Workspace**: Scans your active folder and identifies bugs, suggests patches, and generates documentation.
- **Agentic Pipeline**: Uses specialized agents (Parser, Detector, Patcher, Reviewer) to debug your code.
- **Live Mermaid Diagrams**: Generates and renders System Design, Class, and Use Case diagrams in the sidebar.

## Prerequisites
- **Python 3.10+** installed and available in your PATH.
- **Node.js 18+** and **npm** installed.
- **API Keys**: Ensure your `.env` file in the root directory contains valid `GROQ_API_KEY` or `GOOGLE_API_KEY`.

## How to Test (Development)
1. Open this `vscode-extension` folder in VS Code.
2. Run `npm install` to install dependencies.
3. Run `npm run compile` to build the extension.
4. Press `F5` (or go to **Run and Debug** and click **Run Extension**).
5. A new **Extension Development Host** window will open.
6. In the new window, open any folder you want to analyze.
7. Click the **Autonomous Debugger** icon (the "D" logo) in the Activity Bar (left sidebar).
8. Click **Analyze Workspace**.

## How to Install (Production)
To install the extension permanently in your VS Code:

1. **Install VSCE**:
   ```bash
   npm install -g @vscode/vsce
   ```
2. **Package the Extension**:
   From the `vscode-extension` directory, run:
   ```bash
   vsce package
   ```
   This will create a `.vsix` file (e.g., `software-debugger-0.0.1.vsix`).
3. **Install in VS Code**:
   - Open VS Code.
   - Go to the **Extensions** view (`Ctrl+Shift+X`).
   - Click the **...** (Views and More Actions) menu at the top right of the Extensions panel.
   - Select **Install from VSIX...**.
   - Select the `.vsix` file you just generated.

## Troubleshooting
- **Python Not Found**: Ensure `python` command works in your terminal.
- **Missing Dependencies**: Run `pip install -r requirements.txt` in the root directory.
