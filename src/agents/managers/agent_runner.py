import sys
import time
from src.config import Config

class AgentRunner:
    def __init__(self, factory):
        self.factory = factory

    def validate_msg(self, user_proxy, agent):
        msg = user_proxy.last_message(agent)
        content = msg.get("content", "") if msg else ""
        if any(err in content.lower() for err in ["upstream request", "429", "rate limit", "quota exceeded", "api key invalid"]):
            return f"⚠️ **AI Agent Error ({agent.name})**: The AI provider returned an error: {content[:100]}..."
        return content

    def run_step_with_rotation(self, agent_creator, user_proxy, message, phase_name, clear_history=True):
        """Runs an AI step with automatic key rotation on 429/quota errors."""
        max_attempts = len(self.factory.groq_keys) if self.factory.groq_keys else 1
        if Config.GOOGLE_API_KEY:
            max_attempts += 1

        for attempt in range(max_attempts):
            try:
                agent = agent_creator()
                if clear_history:
                    user_proxy.clear_history(agent)
                
                masked_key = self.factory.get_masked_key()
                # Determine model name from agent config
                model_name = "N/A"
                if hasattr(agent, "llm_config") and agent.llm_config.get("config_list"):
                    model_name = agent.llm_config["config_list"][0].get("model", "unknown")
                
                print(f"--- Phase: {phase_name} | Key: {masked_key} | Model: {model_name} ---", file=sys.stderr, flush=True)
                
                # Forced Pacing to prevent RPM (Requests Per Minute) spikes
                time.sleep(1.5) 
                
                user_proxy.initiate_chat(agent, message=message, silent=True, clear_history=False)
                result = self.validate_msg(user_proxy, agent)
                
                if "⚠️" in result:
                    if any(err in result.lower() for err in ["429", "quota", "rate limit"]):
                        if self.factory.rotate_key():
                            next_key = self.factory.get_masked_key()
                            print(f"--- ⚠️ Rate limit hit. Cooling down & Rotating to: {next_key} ---", file=sys.stderr, flush=True)
                            time.sleep(3)
                            continue
                return result, False
            except Exception as e:
                err_msg = str(e)
                if any(err in err_msg.lower() for err in ["429", "quota", "rate limit"]):
                    if self.factory.rotate_key():
                        next_key = self.factory.get_masked_key()
                        print(f"--- ⚠️ Rate limit exception. Cooling down & Rotating to: {next_key} ---", file=sys.stderr, flush=True)
                        time.sleep(3)
                        continue
                return f"⚠️ API Error: {err_msg}", True
        return "⚠️ Quota exhausted across all configured keys.", True
