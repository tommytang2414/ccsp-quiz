"""
CCSP Quiz Backend API
Run on VPS: python3 app.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
import secrets
import string
import json
import time
import threading
from contextlib import contextmanager

app = Flask(__name__)
CORS(app)

DB_PATH = '/opt/ccsp-quiz/auth.db'
lock = threading.Lock()

# ─── Database ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam TEXT NOT NULL DEFAULT 'CCSP',
                code TEXT UNIQUE NOT NULL,
                used_by TEXT,
                used_at INTEGER,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                exam TEXT NOT NULL DEFAULT 'CCSP',
                token TEXT UNIQUE NOT NULL,
                data TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_codes_code ON codes(code);
            CREATE INDEX IF NOT EXISTS idx_users_token ON users(token);
        ''')

@contextmanager
def get_cursor():
    db = get_db()
    try:
        yield db.cursor()
        db.commit()
    finally:
        db.close()

# ─── Helpers ────────────────────────────────────────────────────────────────

def code_exists(code):
    with get_cursor() as cur:
        cur.execute('SELECT id FROM codes WHERE code = ?', (code,))
        return cur.fetchone() is not None

def code_used(code):
    with get_cursor() as cur:
        cur.execute('SELECT used_by FROM codes WHERE code = ?', (code,))
        row = cur.fetchone()
        return row is not None and row['used_by'] is not None

def use_code(code, user_id):
    with get_cursor() as cur:
        cur.execute(
            'UPDATE codes SET used_by = ?, used_at = ? WHERE code = ?',
            (user_id, int(time.time()), code)
        )

def create_user(exam, code):
    user_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    with get_cursor() as cur:
        cur.execute(
            'INSERT INTO users (id, exam, token, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
            (user_id, exam, token, now, now)
        )
    use_code(code, user_id)
    return user_id, token

def get_user_by_token(token):
    with get_cursor() as cur:
        cur.execute('SELECT * FROM users WHERE token = ?', (token,))
        return cur.fetchone()

def save_user_data(token, data):
    now = int(time.time())
    data_json = json.dumps(data)
    with get_cursor() as cur:
        cur.execute(
            'UPDATE users SET data = ?, updated_at = ? WHERE token = ?',
            (data_json, now, token)
        )

def generate_code(exam, length=8):
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(chars) for _ in range(length))
        if not code_exists(code):
            return code

def admin_require():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    admin_token = auth[7:]
    with get_cursor() as cur:
        cur.execute('SELECT token FROM users WHERE id = ?', ('admin',))
        row = cur.fetchone()
    if not row or admin_token != row['token']:
        return None
    return True

# ─── Auth ──────────────────────────────────────────────────────────────────

@app.route('/api/register', methods=['POST'])
def register():
    """
    Body: { "code": "XXXXXX", "exam": "CCSP" }
    Returns: { "token": "...", "userId": "...", "data": {...} }
    """
    body = request.get_json() or {}
    code = (body.get('code') or '').strip().upper()
    exam = (body.get('exam') or 'CCSP').strip().upper()

    if not code:
        return jsonify({'error': 'Code is required'}), 400

    if len(code) < 4:
        return jsonify({'error': 'Invalid code'}), 400

    with lock:
        if not code_exists(code):
            return jsonify({'error': 'Invalid code'}), 401
        if code_used(code):
            return jsonify({'error': 'Code already used'}), 409

        user_id, token = create_user(exam, code)

    return jsonify({
        'token': token,
        'userId': user_id,
        'data': {},
        'exam': exam,
    })

# ─── Quiz Data ─────────────────────────────────────────────────────────────

@app.route('/api/data', methods=['GET'])
def get_data():
    """Header: Authorization: Bearer <token>"""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401

    token = auth[7:]
    user = get_user_by_token(token)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        data = json.loads(user['data'])
    except:
        data = {}

    return jsonify({
        'exam': user['exam'],
        'data': data,
    })

@app.route('/api/data', methods=['PUT'])
def save_data():
    """Header: Authorization: Bearer <token>"""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401

    token = auth[7:]
    user = get_user_by_token(token)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    body = request.get_json() or {}
    save_user_data(token, body)

    return jsonify({'ok': True})

# ─── Admin ──────────────────────────────────────────────────────────────────

@app.route('/api/admin/gen-code', methods=['POST'])
def gen_code():
    """
    Header: Authorization: Bearer <admin_token>
    Body: { "exam": "CCSP", "count": 5 }
    Returns: { "codes": [...] }
    """
    if not admin_require():
        return jsonify({'error': 'Unauthorized'}), 401

    body = request.get_json() or {}
    exam = (body.get('exam') or 'CCSP').strip().upper()
    count = min(body.get('count', 1), 50)

    now = int(time.time())
    codes = []
    with lock:
        with get_cursor() as cur:
            for _ in range(count):
                code = generate_code(exam)
                cur.execute(
                    'INSERT INTO codes (exam, code, created_at) VALUES (?, ?, ?)',
                    (exam, code, now)
                )
                codes.append(code)

    return jsonify({'codes': codes, 'exam': exam})

@app.route('/api/admin/codes', methods=['GET'])
def list_codes():
    """List all codes with status."""
    if not admin_require():
        return jsonify({'error': 'Unauthorized'}), 401

    exam = request.args.get('exam', 'CCSP')
    with get_cursor() as cur:
        cur.execute(
            'SELECT code, used_by, used_at, created_at FROM codes WHERE exam = ? ORDER BY created_at DESC',
            (exam,)
        )
        rows = cur.fetchall()

    return jsonify({
        'codes': [
            {
                'code': r['code'],
                'used': r['used_by'] is not None,
                'used_by': r['used_by'],
                'used_at': r['used_at'],
                'created_at': r['created_at'],
            }
            for r in rows
        ]
    })

@app.route('/api/admin/users', methods=['GET'])
def list_users():
    """List all registered users."""
    if not admin_require():
        return jsonify({'error': 'Unauthorized'}), 401

    exam = request.args.get('exam', 'CCSP')
    with get_cursor() as cur:
        cur.execute(
            'SELECT id, exam, data, created_at, updated_at FROM users WHERE id != ? ORDER BY created_at DESC',
            ('admin',)
        )
        rows = cur.fetchall()

    return jsonify({
        'users': [
            {
                'id': r['id'][:8] + '...',
                'exam': r['exam'],
                'data_keys': list(json.loads(r['data'] or '{}').keys()),
                'created_at': r['created_at'],
                'updated_at': r['updated_at'],
            }
            for r in rows
        ]
    })

@app.route('/api/admin/stats', methods=['GET'])
def stats():
    """Overall stats."""
    if not admin_require():
        return jsonify({'error': 'Unauthorized'}), 401

    with get_cursor() as cur:
        exams = ['CCSP', 'CISSP', 'AAIA']
        result = {}
        for exam in exams:
            cur.execute('SELECT COUNT(*) FROM codes WHERE exam = ? AND used_by IS NOT NULL', (exam,))
            active = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM codes WHERE exam = ?', (exam,))
            total = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM users WHERE exam = ? AND id != ?', (exam, 'admin'))
            users = cur.fetchone()[0]
            result[exam] = {'active_codes': active, 'total_codes': total, 'users': users}
        return jsonify(result)

# ─── Setup ─────────────────────────────────────────────────────────────────

def setup():
    """Create admin user and some initial CCSP codes."""
    import os
    os.makedirs('/opt/ccsp-quiz', exist_ok=True)
    init_db()

    now = int(time.time())
    with get_cursor() as cur:
        cur.execute('SELECT id FROM users WHERE id = ?', ('admin',))
        if not cur.fetchone():
            admin_token = secrets.token_urlsafe(32)
            cur.execute(
                'INSERT INTO users (id, exam, token, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                ('admin', 'ADMIN', admin_token, now, now)
            )
            # Generate 20 initial codes
            for _ in range(20):
                code = generate_code('CCSP')
                cur.execute(
                    'INSERT INTO codes (exam, code, created_at) VALUES (?, ?, ?)',
                    ('CCSP', code, now)
                )
            print(f'Admin token: {admin_token}')
            print('Initial codes generated.')

if __name__ == '__main__':
    setup()
    app.run(host='0.0.0.0', port=5001, debug=False)
