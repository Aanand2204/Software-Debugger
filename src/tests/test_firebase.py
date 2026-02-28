from src.database.db_manager import init_firebase, get_analysis_history
from src.config import Config
import os

def test_connection():
    print("--- Firebase Connection Test ---")
    print(f"Configured Service Account Path: {Config.FIREBASE_SERVICE_ACCOUNT}")
    
    if os.path.exists(Config.FIREBASE_SERVICE_ACCOUNT):
        print("✅ Credentials file found.")
    else:
        print("❌ Credentials file NOT found. Integration will be disabled.")
        
    db = init_firebase()
    if db:
        print("✅ Firebase initialized successfully!")
        try:
            history = get_analysis_history(limit=1)
            print(f"✅ Firestore access successful. History count: {len(history)}")
        except Exception as e:
            print(f"❌ Firestore access failed: {e}")
    else:
        print("❌ Firebase initialization failed.")

if __name__ == "__main__":
    test_connection()
