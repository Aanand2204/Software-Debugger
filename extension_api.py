import sys
import json
import os
import contextlib
import io
from src.agents.orchestrator import Orchestrator
from src.config import logger

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command provided"}))
        return

    command = sys.argv[1]
    workspace_path = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    
    print(f"--- Process Started: {command} on {workspace_path} ---", file=sys.stderr, flush=True)
    
    orchestrator = Orchestrator()
    
    # Capture stdout to avoid internal library prints from polluting the JSON channel
    f = io.StringIO()
    try:
        with contextlib.redirect_stdout(sys.stderr):
            if command == "analyze":
                print("--- Scanning Workspace ---", file=sys.stderr, flush=True)
                # Check for granular diagram flags
                diagram_types = []
                if "--system" in sys.argv: diagram_types.append("System Design")
                if "--class" in sys.argv: diagram_types.append("Class Diagram")
                if "--usecase" in sys.argv: diagram_types.append("Use Case Diagram")
                if "--sequence" in sys.argv: diagram_types.append("Sequence Diagram")
                if "--activity" in sys.argv: diagram_types.append("Activity Diagram")
                if "--state" in sys.argv: diagram_types.append("State Diagram")
                if "--er" in sys.argv: diagram_types.append("ER Diagram")
                
                should_gen_diagrams = len(diagram_types) > 0
                
                from src.utils.workspace_utils import WorkspaceUtils
                repo_summary = WorkspaceUtils.get_workspace_summary(workspace_path)
                results = orchestrator.run_debugging_session(
                    repo_summary, 
                    generate_diagrams=should_gen_diagrams, 
                    diagram_types=diagram_types
                )
                print("--- Writing Result to Stream ---", file=sys.stderr, flush=True)
                # Use a clear dedicated block for the JSON result
                sys.__stdout__.write("\n\n==DEBUGGER_RESULT_START==\n")
                sys.__stdout__.write(json.dumps(results))
                sys.__stdout__.write("\n==DEBUGGER_RESULT_END==\n")
                sys.__stdout__.flush()
            
            elif command == "chat":
                # chat <workspace_path> <query> <repo_context>
                query = sys.argv[3] if len(sys.argv) > 3 else ""
                repo_context = sys.argv[4] if len(sys.argv) > 4 else ""
                
                if not repo_context and workspace_path:
                    from src.utils.workspace_utils import WorkspaceUtils
                    repo_context = WorkspaceUtils.get_workspace_summary(workspace_path)
                
                response = orchestrator.chat_with_repo(repo_context, query)
                sys.__stdout__.write("\n\n==DEBUGGER_RESULT_START==\n")
                sys.__stdout__.write(json.dumps(response))
                sys.__stdout__.write("\n==DEBUGGER_RESULT_END==\n")
                sys.__stdout__.flush()

            elif command == "diagrams":
                # diagrams <workspace_summary> <flags...>
                repo_summary = sys.argv[2]
                diagram_types = []
                if "--system" in sys.argv: diagram_types.append("System Design")
                if "--class" in sys.argv: diagram_types.append("Class Diagram")
                if "--usecase" in sys.argv: diagram_types.append("Use Case Diagram")
                if "--sequence" in sys.argv: diagram_types.append("Sequence Diagram")
                if "--activity" in sys.argv: diagram_types.append("Activity Diagram")
                if "--state" in sys.argv: diagram_types.append("State Diagram")
                if "--er" in sys.argv: diagram_types.append("ER Diagram")
                
                result = orchestrator.generate_diagrams_only(repo_summary, diagram_types)
                sys.__stdout__.write("\n\n==DEBUGGER_RESULT_START==\n")
                sys.__stdout__.write(json.dumps([result]))
                sys.__stdout__.write("\n==DEBUGGER_RESULT_END==\n")
                sys.__stdout__.flush()
    except Exception as e:
        sys.__stdout__.write("\n\n==DEBUGGER_RESULT_START==\n")
        sys.__stdout__.write(json.dumps({"error": str(e)}))
        sys.__stdout__.write("\n==DEBUGGER_RESULT_END==\n")
        sys.__stdout__.flush()

if __name__ == "__main__":
    main()
