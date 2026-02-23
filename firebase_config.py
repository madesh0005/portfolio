import os
import json
import firebase_admin
from firebase_admin import credentials, db

# 1. Database URL from Render environment or fallback
DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://portfolio-madesh-default-rtdb.asia-southeast1.firebasedatabase.app/')

def initialize_firebase():
    if firebase_admin._apps:
        return

    # Vercel: Read the JSON string from the Env Var directly
    firebase_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    
    if firebase_json:
        try:
            info = json.loads(firebase_json)
            # This fix is vital for private keys in environment variables
            info['private_key'] = info['private_key'].replace('\\n', '\n')
            cred = credentials.Certificate(info)
            firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
        except Exception as e:
            print(f"Firebase Config Error: {e}")
    else:
        # Local fallback
        cred = credentials.Certificate('serviceAccount.json')
        firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})

# Run initialization
initialize_firebase()

def get_db():
    return db

def get_portfolio_ref():
    try:
        return db.reference('portfolio')
    except Exception:
        return None
