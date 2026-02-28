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
            service_account_info = Config.FIREBASE_SERVICE_ACCOUNT.strip() if Config.FIREBASE_SERVICE_ACCOUNT else ""
            
            if not service_account_info:
                logger.warning("Firebase service account not configured. Persistence disabled.")
                return None
                
            # Check if it's a JSON string or a file path
                import json
                try:
                    # try standard json loading first
                    cred_dict = json.loads(service_account_info, strict=False)
                except Exception as e:
                    logger.warning(f"Standard JSON parse failed, trying literal_eval: {e}")
                    try:
                        # ast.literal_eval can often handle the backslashes in TOML-provided strings better
                        import ast
                        cred_dict = ast.literal_eval(service_account_info)
                    except Exception as e2:
                        logger.error(f"Failed to parse Firebase JSON string: {e}")
                        # Log the first 50 chars for debugging (masked for security)
                        snippet = service_account_info[:50] + "..."
                        logger.error(f"JSON Snippet: {snippet}")
                        return None
                
                try:
                    cred = credentials.Certificate(cred_dict)
                    logger.info("Initializing Firebase from JSON string/literal.")
                except Exception as e:
                    logger.error(f"Firebase certificate creation failed: {e}")
                    return None
            else:
                if not os.path.exists(service_account_info):
                    logger.warning(f"Firebase service account file not found at: {service_account_info}. Persistence disabled.")
                    return None
                cred = credentials.Certificate(service_account_info)
                logger.info(f"Initializing Firebase from file: {service_account_info}")

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
