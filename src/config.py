import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
if os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("SoftwareDebugger")

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT", "").strip('\"\'')
    if FIREBASE_SERVICE_ACCOUNT:
        FIREBASE_SERVICE_ACCOUNT = os.path.abspath(os.path.normpath(FIREBASE_SERVICE_ACCOUNT))
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # AutoGen configuration
    MODEL = "gemini-2.5-flash" # Default Gemini model
    GROQ_MODEL = "llama-3.3-70b-versatile" # Recommended Groq model
    
    @classmethod
    def get_groq_keys(cls):
        """Returns a list of all GROQ API keys found in environment variables."""
        keys = []
        # Check for standard GROQ_API_KEY
        main_key = os.getenv("GROQ_API_KEY")
        if main_key:
            keys.append(main_key)
        
        # Check for numbered keys like GROQ_API_KEY_1, GROQ_API_KEY_2...
        i = 1
        while True:
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if not key:
                break
            if key not in keys:
                keys.append(key)
            i += 1
        return keys

    @classmethod
    def validate(cls):
        missing = []
        if not cls.GOOGLE_API_KEY and not cls.get_groq_keys():
            missing.append("GOOGLE_API_KEY or GROQ_API_KEY")
        if missing:
            logger.warning(f"Missing environment variables: {', '.join(missing)}")
        else:
            logger.info("Configuration validated successfully.")

Config.validate()
