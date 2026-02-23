from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import json
import firebase_admin
from firebase_admin import credentials, db
from firebase_config import get_db, get_portfolio_ref, DATABASE_URL
from werkzeug.security import check_password_hash

app = Flask(__name__)
# Security: Use a real secret key on Render, fallback to dev locally
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-key')

def get_db_ref():
    try:
        ref = get_portfolio_ref()
        return ref
    except Exception:
        return None

# --- PUBLIC ROUTE ---
@app.route('/')
def index():
    try:
        ref = get_portfolio_ref()
        portfolio_data = ref.get() or {}
    except Exception:
        portfolio_data = {}
    return render_template('index.html', data=portfolio_data)

# --- API ROUTES ---

@app.route('/api/data', methods=['GET'])
def api_get_data():
    ref = get_db_ref()
    if not ref:
        return jsonify({'error': 'firebase_unavailable'}), 503
    try:
        data = ref.get() or {}
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/<category>', methods=['POST'])
def api_add_entry(category):
    if 'admin' not in session: return jsonify({'error': 'unauthorized'}), 401
    entry = request.get_json() or {}
    ref = get_portfolio_ref()
    
    try:
        if category in ['profile', 'socials', 'description']:
            ref.child(category).set(entry)
            return jsonify({'success': True})
        else:
            new_ref = ref.child(category).push(entry)
            return jsonify({'success': True, 'id': new_ref.key})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/<category>/<item_id>', methods=['PUT', 'POST'])
def api_update_entry(category, item_id):
    if 'admin' not in session: return jsonify({'error': 'unauthorized'}), 401
    entry = request.get_json() or {}
    ref = get_portfolio_ref()
    try:
        ref.child(category).child(item_id).update(entry)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/<category>/<item_id>', methods=['DELETE'])
def api_delete_entry(category, item_id):
    if 'admin' not in session: return jsonify({'error': 'unauthorized'}), 401
    ref = get_portfolio_ref()
    try:
        ref.child(category).child(item_id).delete()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- ADMIN ROUTES ---

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Directly query Firebase for this specific email
        admin_data = load_admin(email)

        if not admin_data:
            error = 'Invalid credentials.'
        elif not check_password_hash(admin_data.get('password_hash', ''), password):
            error = 'Invalid credentials.'
        else:
            session['admin'] = True
            return redirect(url_for('admin'))
    return render_template('login.html', error=error)

@app.route('/admin')
def admin():
    if 'admin' not in session: 
        return redirect(url_for('login'))
    
    ref = get_portfolio_ref()
    portfolio_data = ref.get() or {}
    return render_template('admin.html', data=portfolio_data)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

# --- DIAGNOSTICS ---

@app.route('/firebase_status')
def firebase_status():
    info = {'database_url': DATABASE_URL}
    # UPDATED: Check for Render Secret Path or local
    render_path = '/etc/secrets/FIREBASE_SERVICE_ACCOUNT'
    local_path = os.path.join(os.path.dirname(__file__), 'serviceAccount.json')
    
    cred_path = render_path if os.path.exists(render_path) else local_path
    
    try:
        if os.path.exists(cred_path):
            with open(cred_path, 'r', encoding='utf-8') as f:
                sa = json.load(f)
            info['service_account_project_id'] = sa.get('project_id')
            info['path_used'] = cred_path
    except: pass

    ref = get_portfolio_ref()
    try:
        sample = ref.get()
        info['db_test'] = {'ok': True, 'connected': True}
    except Exception as e:
        info['db_test'] = {'ok': False, 'error': str(e)}
    return jsonify(info)
    
# --- CERTIFICATIONS ROUTE ---
@app.route('/certifications')
def certifications():
    try:
        ref = get_portfolio_ref()
        portfolio_data = ref.get() or {}
    except Exception:
        portfolio_data = {}
    return render_template('certifications.html', data=portfolio_data)
    
# --- HELPERS ---

def load_admin(email):
    """
    Checks Firebase directly for a registered admin with the given email.
    """
    try:
        ref = get_portfolio_ref()
        # Look for a node named 'admins' in your Firebase
        admins = ref.child('admins').get()
        
        if admins:
            for admin_id, details in admins.items():
                if details.get('email') == email:
                    return details
    except Exception as e:
        print(f"Firebase Admin Check Error: {e}")
    return None

if __name__ == '__main__':
    # Use dynamic port for deployment
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
