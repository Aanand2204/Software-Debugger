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
    FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT") # Path to JSON or JSON string
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # AutoGen configuration
    MODEL = "gemini-2.0-flash" # Verified functional model ID for v1beta
    
    @classmethod
    def validate(cls):
        missing = []
        if not cls.GOOGLE_API_KEY:
            missing.append("GOOGLE_API_KEY")
        if missing:
            logger.warning(f"Missing environment variables: {', '.join(missing)}")
        else:
            logger.info("Configuration validated successfully.")

Config.validate()
