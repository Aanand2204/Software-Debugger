import * as vscode from 'vscode';
import * as path from 'path';
import { spawn } from 'child_process';

const SIDEBAR_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        body { padding: 10px; color: var(--vscode-foreground); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--vscode-sideBar-background); display: flex; flex-direction: column; height: 100vh; overflow: hidden; margin: 0; }
        .tab-container { display: flex; border-bottom: 1px solid var(--vscode-widget-border); margin-bottom: 15px; background: rgba(0,0,0,0.1); border-radius: 4px; padding: 2px; }
        .tab { flex: 1; padding: 6px; text-align: center; cursor: pointer; opacity: 0.7; font-size: 11px; font-weight: bold; border-radius: 3px; transition: all 0.2s; }
        .tab.active { opacity: 1; background: var(--vscode-button-background); color: var(--vscode-button-foreground); }
        .view { flex: 1; overflow-y: auto; display: none; }
        .view.active { display: block; }

        .config-section { margin-bottom: 20px; }
        .section-label { font-size: 11px; font-weight: 700; opacity: 0.6; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        .multi-select-container { position: relative; width: 100%; margin-bottom: 10px; }
        .select-trigger { 
            background: var(--vscode-input-background); 
            border: 1px solid var(--vscode-input-border); 
            border-radius: 4px; 
            padding: 8px 12px; 
            min-height: 38px;
            display: flex; 
            align-items: center; 
            justify-content: space-between; 
            cursor: pointer;
            font-size: 13px;
        }
        .select-trigger:hover { border-color: var(--vscode-focusBorder); }
        .trigger-text { opacity: 0.7; }
        .chevron { width: 10px; height: 10px; border-right: 2px solid currentColor; border-bottom: 2px solid currentColor; transform: rotate(45deg); margin-top: -4px; transition: transform 0.2s; }
        .open .chevron { transform: rotate(-135deg); margin-top: 4px; }
        
        .dropdown-menu { 
            position: absolute; 
            top: 100%; 
            left: 0; 
            right: 0; 
            background: var(--vscode-dropdown-background); 
            border: 1px solid var(--vscode-dropdown-border); 
            border-radius: 4px; 
            margin-top: 4px; 
            z-index: 100; 
            display: none; 
            max-height: 200px; 
            overflow-y: auto;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .open .dropdown-menu { display: block; }
        .option { padding: 8px 12px; cursor: pointer; display: flex; align-items: center; gap: 10px; font-size: 13px; }
        .option:hover { background: var(--vscode-list-hoverBackground); }
        .option.selected { background: var(--vscode-list-activeSelectionBackground); color: var(--vscode-list-activeSelectionForeground); }
        .option-check { width: 12px; height: 12px; border: 1px solid currentColor; border-radius: 2px; position: relative; }
        .selected .option-check::after { content: "\u2713"; position: absolute; top: -2px; left: 1px; font-size: 10px; }

        .selected-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
        .tag { background: var(--vscode-badge-background); color: var(--vscode-badge-foreground); padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 600; display: flex; align-items: center; gap: 4px; }
        .tag-remove { cursor: pointer; opacity: 0.6; font-size: 12px; }
        .tag-remove:hover { opacity: 1; }

        .btn-group { display: flex; flex-direction: column; gap: 8px; margin-top: 20px; }
        button { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; padding: 10px; cursor: pointer; border-radius: 4px; font-weight: 600; font-size: 12px; display: flex; align-items: center; justify-content: center; gap: 8px; }
        button:hover { background: var(--vscode-button-hoverBackground); }
        button.secondary { background: var(--vscode-button-secondaryBackground, #3a3d41); color: var(--vscode-button-secondaryForeground, #ffffff); }
        button.secondary:hover { background: var(--vscode-button-secondaryHoverBackground, #45494e); }
        button:disabled { opacity: 0.4; cursor: not-allowed; }
        
        .status-area { margin-top: 15px; border-top: 1px solid var(--vscode-widget-border); padding-top: 10px; }
        .status-msg { font-size: 11px; opacity: 0.6; font-style: italic; text-align: center; }
        
        #chat-input-area { display: flex; gap: 5px; padding: 10px 0; }
        #chat-input { flex: 1; background: var(--vscode-input-background); border: 1px solid var(--vscode-input-border); padding: 8px; border-radius: 4px; color: var(--vscode-input-foreground); }
    </style>
</head>
<body>
    <div class="tab-container">
        <div class="tab active" onclick="switchTab('analyze')">ANALYZE</div>
        <div class="tab" onclick="switchTab('chat')">CHAT</div>
    </div>

    <div id="analyze-view" class="view active">
        <div class="config-section">
            <div class="section-label">Architecture & Flow Diagrams</div>
            <div class="multi-select-container" id="diagram-select">
                <div class="select-trigger" onclick="toggleDropdown()">
                    <span class="trigger-text" id="trigger-text">Choose options</span>
                    <span class="chevron"></span>
                </div>
                <div class="dropdown-menu">
                    <div class="option" onclick="toggleOption('System Design')"><div class="option-check"></div><span>System Design</span></div>
                    <div class="option" onclick="toggleOption('Class Diagram')"><div class="option-check"></div><span>Class Diagram</span></div>
                    <div class="option" onclick="toggleOption('Use Case Diagram')"><div class="option-check"></div><span>Use Case Diagram</span></div>
                    <div class="option" onclick="toggleOption('Sequence Diagram')"><div class="option-check"></div><span>Sequence Diagram</span></div>
                    <div class="option" onclick="toggleOption('Activity Diagram')"><div class="option-check"></div><span>Activity Diagram</span></div>
                    <div class="option" onclick="toggleOption('State Diagram')"><div class="option-check"></div><span>State Diagram</span></div>
                    <div class="option" onclick="toggleOption('ER Diagram')"><div class="option-check"></div><span>ER Diagram</span></div>
                </div>
                <div class="selected-tags" id="selected-tags"></div>
            </div>
        </div>

        <div class="btn-group">
            <button id="analyze-btn" onclick="analyze()">\uD83D\uDE80 Analyze Codebase</button>
            <button id="blueprint-btn" class="secondary" onclick="generateBlueprints()" disabled>\uD83D\uDD04 Regenerate Selected Diagrams</button>
        </div>

        <div class="status-area">
            <div id="status" class="status-msg">Ready for visualization</div>
        </div>
    </div>

    <div id="chat-view" class="view">
        <div id="chat-messages" style="flex:1; overflow-y:auto; font-size:12px; padding:5px;"></div>
        <div id="chat-input-area">
            <input type="text" id="chat-input" placeholder="Ask about code..." onkeypress="if(event.key==='Enter')sendChat()">
            <button style="width:auto" onclick="sendChat()">\u27A4</button>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        let selectedOptions = [];

        function toggleDropdown() {
            document.getElementById('diagram-select').classList.toggle('open');
        }

        function toggleOption(val) {
            const index = selectedOptions.indexOf(val);
            if (index > -1) {
                selectedOptions.splice(index, 1);
            } else {
                selectedOptions.push(val);
            }
            updateSelectionUi();
        }

        function updateSelectionUi() {
            const tagsContainer = document.getElementById('selected-tags');
            const triggerText = document.getElementById('trigger-text');
            const options = document.querySelectorAll('.option');
            
            tagsContainer.innerHTML = '';
            options.forEach(opt => {
                const text = opt.querySelector('span').innerText;
                if (selectedOptions.includes(text)) {
                    opt.classList.add('selected');
                    const tag = document.createElement('div');
                    tag.className = 'tag';
                    tag.innerHTML = '<span>' + text + '</span><span class="tag-remove" onclick="toggleOption(\\'' + text + '\\')">\u00D7</span>';
                    tagsContainer.appendChild(tag);
                } else {
                    opt.classList.remove('selected');
                }
            });

            triggerText.innerText = selectedOptions.length > 0 ? selectedOptions.length + ' selected' : "Choose options";
        }

        function switchTab(t) {
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
            if (t === 'analyze') {
                document.querySelector('.tab:nth-child(1)').classList.add('active');
                document.getElementById('analyze-view').classList.add('active');
            } else {
                document.querySelector('.tab:nth-child(2)').classList.add('active');
                document.getElementById('chat-view').classList.add('active');
            }
        }

        function analyze() {
            const config = {
                system: selectedOptions.includes('System Design'),
                class: selectedOptions.includes('Class Diagram'),
                usecase: selectedOptions.includes('Use Case Diagram'),
                sequence: selectedOptions.includes('Sequence Diagram'),
                activity: selectedOptions.includes('Activity Diagram'),
                state: selectedOptions.includes('State Diagram'),
                er: selectedOptions.includes('ER Diagram')
            };
            document.getElementById('analyze-btn').disabled = true;
            document.getElementById('status').innerText = 'Starting Discovery...';
            vscode.postMessage({ type: 'analyze', config });
        }

        function generateBlueprints() {
            const config = {
                system: selectedOptions.includes('System Design'),
                class: selectedOptions.includes('Class Diagram'),
                usecase: selectedOptions.includes('Use Case Diagram'),
                sequence: selectedOptions.includes('Sequence Diagram'),
                activity: selectedOptions.includes('Activity Diagram'),
                state: selectedOptions.includes('State Diagram'),
                er: selectedOptions.includes('ER Diagram')
            };
            if (selectedOptions.length === 0) {
                document.getElementById('status').innerText = 'Select diagrams first!';
                return;
            }
            document.getElementById('blueprint-btn').disabled = true;
            document.getElementById('status').innerText = 'Regenerating...';
            vscode.postMessage({ type: 'generateBlueprints', config });
        }

        function sendChat() {
            const input = document.getElementById('chat-input');
            const msg = input.value.trim();
            if (!msg) return;
            addBubble(msg, 'user');
            input.value = '';
            vscode.postMessage({ type: 'chat', message: msg });
        }

        function addBubble(t, s) {
            const container = document.getElementById('chat-messages');
            const div = document.createElement('div');
            div.style.padding = '8px';
            div.style.margin = '5px 0';
            div.style.background = s === 'user' ? 'var(--vscode-button-background)' : 'var(--vscode-editor-background)';
            div.style.borderRadius = '4px';
            div.innerText = t;
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
        }

        window.addEventListener('message', e => {
            const m = e.data;
            if (m.type === 'analysisResults') {
                document.getElementById('analyze-btn').disabled = false;
                document.getElementById('blueprint-btn').disabled = false;
                document.getElementById('status').innerText = 'Synthesis Complete';
            } else if (m.type === 'progress') {
                document.getElementById('status').innerText = m.message;
            } else if (m.type === 'error') {
                document.getElementById('analyze-btn').disabled = false;
                document.getElementById('blueprint-btn').disabled = false;
                document.getElementById('status').innerHTML = '<span style="color:var(--vscode-errorForeground)">⚠️ ' + m.message + '</span>';
            } else if (m.type === 'chatResponse') {
                addBubble(m.data.content, 'ai');
            }
        });

        window.onclick = function(event) {
            if (!event.target.closest('#diagram-select')) {
                document.getElementById('diagram-select').classList.remove('open');
            }
        }
    </script>
</body>
</html>`;

const RESULT_VIEW_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        :root {
            --accent: #6366f1;
            --bg: var(--vscode-editor-background);
            --card-bg: var(--vscode-sideBar-background);
            --border: var(--vscode-widget-border);
            --code-bg: rgba(30, 30, 30, 0.4);
            --code-border: rgba(99, 102, 241, 0.15);
        }
        body { padding: 30px; color: var(--vscode-foreground); font-family: 'Inter', -apple-system, sans-serif; background: var(--bg); line-height: 1.5; max-width: 1100px; margin: 0 auto; }
        .hero { margin-bottom: 25px; }
        .hero h1 { font-size: 32px; margin: 0; font-weight: 800; color: var(--vscode-foreground); letter-spacing: -0.5px; }
        .hero p { font-size: 16px; opacity: 0.6; margin: 5px 0; }
        .section-grid { display: flex; flex-direction: column; gap: 20px; }
        .card { background: var(--card-bg); border: 1px solid var(--border); padding: 22px; border-radius: 12px; box-shadow: 0 2px 15px rgba(0,0,0,0.1); }
        .card-header { font-size: 18px; font-weight: 800; margin-bottom: 12px; color: var(--vscode-foreground); display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
        .card-content { font-size: 14px; color: var(--vscode-foreground); opacity: 0.95; }
        
        .vsc-code-block { background: var(--code-bg); border: 1px solid var(--code-border); border-radius: 6px; margin: 15px 0; overflow: hidden; }
        .vsc-code-header { background: rgba(255,255,255,0.03); padding: 5px 12px; font-size: 10px; text-transform: uppercase; font-weight: 800; opacity: 0.5; border-bottom: 1px solid var(--code-border); display: flex; justify-content: space-between; }
        pre { margin: 0; padding: 12px; overflow-x: auto; }
        code { font-family: 'Fira Code', 'Monaco', monospace; font-size: 12px; }
        .inline-code { background: rgba(129, 140, 248, 0.12); color: #a5b4fc; padding: 1px 5px; border-radius: 4px; font-weight: 500; font-family: monospace; }

        .mermaid { background: #ffffff; padding: 15px; border-radius: 8px; margin: 15px 0; color: #000; border: 1px solid #e2e8f0; text-align: center; }
        h3 { color: #f8fafc; background: rgba(99, 102, 241, 0.1); font-size: 17px; font-weight: 800; margin-top: 25px; margin-bottom: 10px; border-left: 4px solid var(--accent); padding: 8px 12px; border-radius: 4px; }
        h4 { font-size: 15px; font-weight: 700; margin-top: 15px; margin-bottom: 6px; color: #a5b4fc; }
        strong { color: #818cf8; font-weight: 700; }
        .badge { background: var(--accent); color: white; padding: 2px 8px; border-radius: 4px; font-size: 9px; font-weight: 800; }
        
        .p-block { display: block; margin: 8px 0; }
    </style>
</head>
<body>
    <div class="hero"><h1>Analysis Studio</h1><p>System blueprints and repository intelligence.</p></div>
    <div id="results-container" class="section-grid"><p style="text-align: center; opacity: 0.4; padding: 60px;">Synthesizing results...</p></div>
    <script>
        const vscode = acquireVsCodeApi();
        mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });
        
        window.onload = function() { 
            console.log('Analysis Studio: Webview loaded');
            vscode.postMessage({ type: 'viewReady' }); 
        };

        window.addEventListener('message', function(event) {
            const m = event.data;
            if (m.type === 'renderAnalysis') {
                console.log('Analysis Studio: Received results', m.data.length);
                renderResults(m.data, m.isAppend).catch(e => {
                    console.error('Analysis Studio: Render failed', e);
                    document.getElementById('results-container').innerHTML = '<p style="color:red; padding: 20px;">Render Error: ' + e.message + '</p>';
                });
            }
        });

        async function renderResults(data, isAppend) {
            const container = document.getElementById('results-container');
            if (!isAppend) container.innerHTML = '';
            
            if (!data || data.length === 0) {
                container.innerHTML = '<p style="text-align: center; opacity: 0.4; padding: 60px;">No results found.</p>';
                return;
            }

            for (const item of data) {
                const card = document.createElement('div');
                card.className = 'card';
                const safeName = (item.name || 'Analysis').replace(/_/g, ' ');
                card.innerHTML = '<div class="card-header"><span>' + safeName + '</span><span class="badge">Verified</span></div>' +
                                 '<div class="card-content">' + formatText(item.content) + '</div>';
                container.appendChild(card);
            }
            
            try { 
                if (document.querySelectorAll('.mermaid').length > 0) {
                    console.log('Analysis Studio: Running mermaid...');
                    await mermaid.run(); 
                }
            } catch (e) { console.error('Mermaid error:', e); }
        }

        function formatText(content) {
            try {
                if (!content) return '';
                let text = String(content).trim();
                
                // Triple backslashes needed because this is a string inside a template string
                const regex = /\\x60{3}(\\w*)\\n([\\s\\S]*?)\\n\\x60{3}/g;
                
                const blocks = [];
                text = text.replace(regex, function(match, lang, code) {
                    const id = '___BLOCK_' + blocks.length + '___';
                    if (lang === 'mermaid') {
                        blocks.push('<div class="mermaid">' + code.trim() + '</div>');
                    } else {
                        blocks.push('<div class="vsc-code-block">' + 
                                    '<div class="vsc-code-header"><span>' + (lang || 'code') + '</span><span>Snippet</span></div>' +
                                    '<pre><code>' + escapeHtml(code.trim()) + '</code></pre>' +
                                    '</div>');
                    }
                    return id;
                });

                let html = text
                    .replace(/### (.*)/g, '<h3>$1</h3>')
                    .replace(/#### (.*)/g, '<h4>$1</h4>')
                    .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>')
                    .replace(/\\x60([^\\x60]+)\\x60/g, '<code class="inline-code">$1</code>')
                    .replace(/\\n\\n/g, '<div class="p-block"></div>')
                    .replace(/\\n/g, '<br>');

                blocks.forEach(function(block, i) {
                    html = html.replace('___BLOCK_' + i + '___', block);
                });

                return html;
            } catch (err) {
                console.error('Format error:', err);
                return '<pre>' + escapeHtml(String(content)) + '</pre>';
            }
        }

        function escapeHtml(t) {
            return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
        }
    </script>
</body>
</html>`;

export function activate(context: vscode.ExtensionContext) {
    const provider = new DebuggerViewProvider(context.extensionUri);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider(DebuggerViewProvider.viewType, provider));
}

class DebuggerViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'software-debugger.view';
    private _view?: vscode.WebviewView;
    private _workspaceSummary: string = "";
    private _outputChannel: vscode.OutputChannel;
    private _lastResults: any[] = [];

    constructor(private readonly _extensionUri: vscode.Uri) {
        this._outputChannel = vscode.window.createOutputChannel("Autonomous Debugger");
    }

    public resolveWebviewView(webviewView: vscode.WebviewView, context: vscode.WebviewViewResolveContext, _token: vscode.CancellationToken) {
        this._view = webviewView;
        webviewView.webview.options = { enableScripts: true, localResourceRoots: [this._extensionUri] };
        webviewView.webview.html = SIDEBAR_HTML;
        webviewView.webview.onDidReceiveMessage((data: any) => {
            if (data.type === 'analyze') { this.analyzeWorkspace(data.config); }
            else if (data.type === 'generateBlueprints') { this.generateIndependentDiagrams(data.config); }
            else if (data.type === 'chat') { this.chatWithRepo(data.message); }
        });
    }

    public analyzeWorkspace(config: any) {
        if (!this._view) return;
        const folders = vscode.workspace.workspaceFolders;
        if (!folders) return;
        this._outputChannel.clear();
        this._outputChannel.show(true);
        this._view.webview.postMessage({ type: 'analysisStarted' });
        const args = ['analyze', folders[0].uri.fsPath];
        if (config.system) args.push('--system');
        if (config.class) args.push('--class');
        if (config.usecase) args.push('--usecase');
        if (config.sequence) args.push('--sequence');
        if (config.activity) args.push('--activity');
        if (config.state) args.push('--state');
        if (config.er) args.push('--er');

        this.runPythonProcess(args, (res) => {
            this._lastResults = res;
            this._workspaceSummary = res.map((r: any) => `### ${r.name}\n${r.content}`).join("\n\n").substring(0, 20000);
            this._view?.webview.postMessage({ type: 'analysisResults' });
            ResultPanel.createOrShow(res, false);
        });
    }

    public generateIndependentDiagrams(config: any) {
        if (!this._view || !this._workspaceSummary) return;
        const args = ['diagrams', this._workspaceSummary];
        if (config.system) args.push('--system');
        if (config.class) args.push('--class');
        if (config.usecase) args.push('--usecase');
        if (config.sequence) args.push('--sequence');
        if (config.activity) args.push('--activity');
        if (config.state) args.push('--state');
        if (config.er) args.push('--er');
        this.runPythonProcess(args, (newRes) => {
            this._lastResults = [...this._lastResults, ...newRes];
            this._lastResults = this._lastResults.filter((v, i, a) => a.findIndex(t => (t.name === v.name && t.content === v.content)) === i);
            this._view?.webview.postMessage({ type: 'analysisResults' });
            ResultPanel.createOrShow(newRes, true);
        });
    }

    private runPythonProcess(args: string[], onSuccess: (r: any) => void) {
        const proc = spawn('python', [path.join(this._extensionUri.fsPath, '..', 'extension_api.py'), ...args]);
        let out = '';
        proc.stdout.on('data', (d) => { out += d.toString(); });
        proc.stderr.on('data', (d) => {
            const line = d.toString();
            this._outputChannel.appendLine(`[LOG]: ${line}`);
            if (line.includes('---')) this._view?.webview.postMessage({ type: 'progress', message: line.replace(/---/g, '').trim() });
        });
        proc.on('close', (c) => {
            this._outputChannel.appendLine(`[LOG]: Python process exited with code ${c}`);
            const match = out.match(/==DEBUGGER_RESULT_START==([\s\S]*?)==DEBUGGER_RESULT_END==/);
            if (match && match[1]) {
                try {
                    const parsed = JSON.parse(match[1].trim());
                    onSuccess(parsed);
                } catch (e) {
                    this._outputChannel.appendLine(`[ERROR]: Failed to parse JSON result: ${e}`);
                    this._view?.webview.postMessage({ type: 'error', message: 'Failed to parse result.' });
                }
            } else {
                this._outputChannel.appendLine(`[ERROR]: No result markers found in stdout.`);
                if (c !== 0) this._view?.webview.postMessage({ type: 'error', message: 'Engine failed.' });
                else this._view?.webview.postMessage({ type: 'error', message: 'Process finished but no results were returned.' });
            }
        });
    }

    public chatWithRepo(q: string) {
        const proc = spawn('python', [path.join(this._extensionUri.fsPath, '..', 'extension_api.py'), 'chat', '', q, this._workspaceSummary]);
        let out = '';
        proc.stdout.on('data', (d) => { out += d.toString(); });
        proc.on('close', () => {
            const match = out.match(/==DEBUGGER_RESULT_START==([\s\S]*?)==DEBUGGER_RESULT_END==/);
            if (match && match[1]) this._view?.webview.postMessage({ type: 'chatResponse', data: JSON.parse(match[1].trim()) });
        });
    }
}

class ResultPanel {
    public static currentPanel: ResultPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _results: any;

    private constructor(panel: vscode.WebviewPanel, results: any) {
        this._panel = panel;
        this._results = results;
        this._panel.onDidDispose(() => { ResultPanel.currentPanel = undefined; }, null, []);
        this._panel.webview.html = RESULT_VIEW_HTML;
        this._panel.webview.onDidReceiveMessage(m => {
            if (m.type === 'viewReady') this._panel.webview.postMessage({ type: 'renderAnalysis', data: this._results, isAppend: false });
        });
    }

    public static createOrShow(results: any, isAppend: boolean) {
        if (ResultPanel.currentPanel) {
            ResultPanel.currentPanel._results = isAppend ? [...ResultPanel.currentPanel._results, ...results] : results;
            ResultPanel.currentPanel._panel.reveal(vscode.ViewColumn.One);
            ResultPanel.currentPanel._panel.webview.postMessage({ type: 'renderAnalysis', data: results, isAppend: isAppend });
            return;
        }
        const panel = vscode.window.createWebviewPanel('analysisResults', 'Analysis Studio', vscode.ViewColumn.One, { enableScripts: true });
        ResultPanel.currentPanel = new ResultPanel(panel, results);
    }
}
