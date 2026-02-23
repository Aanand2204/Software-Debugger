import firebase_admin
from firebase_admin import credentials, firestore
from src.config import Config, logger

def init_firebase():
    try:
        if not firebase_admin._apps:
            # Assumes FIREBASE_SERVICE_ACCOUNT is a path to the JSON file
            cred = credentials.Certificate(Config.FIREBASE_SERVICE_ACCOUNT)
            firebase_admin.initialize_app(cred, {
                'databaseURL': Config.DATABASE_URL
            })
            logger.info("Firebase initialized successfully.")
        return firestore.client()
    except Exception as e:
        logger.error(f"Error initializing Firebase: {e}")
        return None

if __name__ == "__main__":
    db = init_firebase()
    if db:
        print("Connected to Firestore!")
