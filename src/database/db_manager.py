import firebase_admin
import os
from firebase_admin import credentials, firestore
from src.config import Config, logger

_db = None

def init_firebase():
    global _db
    if _db is not None:
        return _db
        
    try:
        if not firebase_admin._apps:
            service_account_path = Config.FIREBASE_SERVICE_ACCOUNT
            if not service_account_path or not os.path.exists(service_account_path):
                logger.warning(f"Firebase service account file not found at: {service_account_path}. Persistence disabled.")
                return None
                
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': Config.DATABASE_URL
            })
            logger.info("Firebase initialized successfully.")
        
        _db = firestore.client()
        return _db
    except Exception as e:
        logger.error(f"Error initializing Firebase: {e}")
        return None

def save_analysis_result(repo_url, results):
    """Saves analysis results to Firestore."""
    db = init_firebase()
    if not db:
        return False
    
    try:
        doc_data = {
            'repo_url': repo_url,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'results': results
        }
        db.collection('analyses').add(doc_data)
        logger.info(f"Analysis for {repo_url} saved to Firestore.")
        return True
    except Exception as e:
        logger.error(f"Failed to save analysis to Firestore: {e}")
        return False

def get_analysis_history(limit=10):
    """Retrieves recent analysis history from Firestore."""
    db = init_firebase()
    if not db:
        return []
    
    try:
        docs = db.collection('analyses').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
        history = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            history.append(data)
        return history
    except Exception as e:
        logger.error(f"Failed to fetch history from Firestore: {e}")
        return []

if __name__ == "__main__":
    db = init_firebase()
    if db:
        print("Connected to Firestore!")
    else:
        print("Could not connect to Firebase. Check credentials/firebase.json and .env")
