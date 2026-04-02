#!/bin/bash
# Run this ON YOUR VPS (18.139.210.59)
# ssh -i ~/.ssh/your_key ubuntu@18.139.210.59

set -e
echo "=== CCSP Quiz API Setup ==="

# Install dependencies
pip3 install flask flask-cors -q 2>/dev/null || pip install flask flask-cors -q

# Create directory
mkdir -p /opt/ccsp-quiz

# Copy app.py
cat > /opt/ccsp-quiz/app.py << 'PYEOF'
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, uuid, secrets, string, json, time, threading

app = Flask(__name__)
CORS(app)
DB_PATH = '/opt/ccsp-quiz/auth.db'
lock = threading.Lock()

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS codes (id INTEGER PRIMARY KEY AUTOINCREMENT, exam TEXT NOT NULL DEFAULT 'CCSP', code TEXT UNIQUE NOT NULL, used_by TEXT, used_at INTEGER, created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, exam TEXT NOT NULL DEFAULT 'CCSP', token TEXT UNIQUE NOT NULL, data TEXT NOT NULL DEFAULT '{}', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_codes_code ON codes(code);
            CREATE INDEX IF NOT EXISTS idx_users_token ON users(token);
        ''')

def get_user_by_token(token):
    with get_db() as db:
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute('SELECT * FROM users WHERE token = ?', (token,))
        return cur.fetchone()

def save_user_data(token, data):
    now = int(time.time())
    with get_db() as db:
        db.execute('UPDATE users SET data = ?, updated_at = ? WHERE token = ?', (json.dumps(data), now, token))
        db.commit()

def code_exists(code):
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT id FROM codes WHERE code = ?', (code,))
        return cur.fetchone() is not None

def code_used(code):
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT used_by FROM codes WHERE code = ?', (code,))
        r = cur.fetchone()
        return r is not None and r[0] is not None

def generate_code(exam, length=8):
    chars = string.ascii_uppercase + string.digits
    with get_db() as db:
        cur = db.cursor()
        while True:
            code = ''.join(secrets.choice(chars) for _ in range(length))
            cur.execute('SELECT id FROM codes WHERE code = ?', (code,))
            if cur.fetchone() is None:
                return code

def setup():
    import os
    os.makedirs('/opt/ccsp-quiz', exist_ok=True)
    init_db()
    now = int(time.time())
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT id FROM users WHERE id = ?', ('admin',))
        if not cur.fetchone():
            admin_token = secrets.token_urlsafe(32)
            db.execute('INSERT INTO users (id, exam, token, created_at, updated_at) VALUES (?, ?, ?, ?, ?)', ('admin', 'ADMIN', admin_token, now, now))
            for _ in range(20):
                code = generate_code('CCSP')
                db.execute('INSERT INTO codes (exam, code, created_at) VALUES (?, ?, ?)', ('CCSP', code, now))
            db.commit()
            print(f'ADMIN_TOKEN={admin_token}')
            print('Admin token saved. Keep it safe!')

@app.route('/api/register', methods=['POST'])
def register():
    body = request.get_json() or {}
    code = (body.get('code') or '').strip().upper()
    exam = (body.get('exam') or 'CCSP').strip().upper()
    if not code or len(code) < 4:
        return jsonify({'error': 'Invalid code'}), 400
    with lock:
        if not code_exists(code):
            return jsonify({'error': 'Invalid code'}), 401
        if code_used(code):
            return jsonify({'error': 'Code already used'}), 409
        user_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        with get_db() as db:
            db.execute('INSERT INTO users (id, exam, token, created_at, updated_at) VALUES (?, ?, ?, ?, ?)', (user_id, exam, token, now, now))
            db.execute('UPDATE codes SET used_by = ?, used_at = ? WHERE code = ?', (user_id, now, code))
            db.commit()
    return jsonify({'token': token, 'userId': user_id, 'exam': exam})

@app.route('/api/data', methods=['GET'])
def get_data():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user_by_token(auth[7:])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    try:
        data = json.loads(user['data'])
    except:
        data = {}
    return jsonify({'exam': user['exam'], 'data': data})

@app.route('/api/data', methods=['PUT'])
def save_data():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user_by_token(auth[7:])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    save_user_data(auth[7:], request.get_json() or {})
    return jsonify({'ok': True})

@app.route('/api/admin/gen-code', methods=['POST'])
def gen_code():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT token FROM users WHERE id = ?', ('admin',))
        row = cur.fetchone()
    if not row or row[0] != auth[7:]:
        return jsonify({'error': 'Unauthorized'}), 401
    body = request.get_json() or {}
    exam = (body.get('exam') or 'CCSP').strip().upper()
    count = min(body.get('count', 1), 50)
    codes = []
    with lock:
        with get_db() as db:
            for _ in range(count):
                code = generate_code(exam)
                db.execute('INSERT INTO codes (exam, code, created_at) VALUES (?, ?, ?)', (exam, code, int(time.time())))
                codes.append(code)
            db.commit()
    return jsonify({'codes': codes})

@app.route('/api/admin/codes', methods=['GET'])
def list_codes():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT token FROM users WHERE id = ?', ('admin',))
        row = cur.fetchone()
    if not row or row[0] != auth[7:]:
        return jsonify({'error': 'Unauthorized'}), 401
    exam = request.args.get('exam', 'CCSP')
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT code, used_by, used_at, created_at FROM codes WHERE exam = ? ORDER BY created_at DESC', (exam,))
        rows = cur.fetchall()
    return jsonify({'codes': [{'code': r[0], 'used': r[1] is not None, 'used_by': r[1], 'used_at': r[2], 'created_at': r[3]} for r in rows]})

@app.route('/api/admin/users', methods=['GET'])
def list_users():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT token FROM users WHERE id = ?', ('admin',))
        row = cur.fetchone()
    if not row or row[0] != auth[7:]:
        return jsonify({'error': 'Unauthorized'}), 401
    exam = request.args.get('exam', 'CCSP')
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT id, exam, data, created_at, updated_at FROM users WHERE id != ? AND exam = ? ORDER BY created_at DESC', ('admin', exam))
        rows = cur.fetchall()
    return jsonify({'users': [{'id': r[0][:8]+'...', 'exam': r[1], 'created_at': r[3]} for r in rows]})

@app.route('/api/admin/stats', methods=['GET'])
def stats():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT token FROM users WHERE id = ?', ('admin',))
        row = cur.fetchone()
    if not row or row[0] != auth[7:]:
        return jsonify({'error': 'Unauthorized'}), 401
    result = {}
    for exam in ['CCSP', 'CISSP', 'AAIA']:
        cur = db.cursor()
        cur.execute('SELECT COUNT(*) FROM codes WHERE exam = ? AND used_by IS NOT NULL', (exam,))
        active = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM codes WHERE exam = ?', (exam,))
        total = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM users WHERE exam = ? AND id != ?', (exam, 'admin'))
        users = cur.fetchone()[0]
        result[exam] = {'active_codes': active, 'total_codes': total, 'users': users}
    return jsonify(result)

if __name__ == '__main__':
    setup()
    app.run(host='0.0.0.0', port=5001, debug=False)
PYEOF

# Kill old instance
pkill -f "python.*5001" 2>/dev/null || true

# Start
nohup python3 /opt/ccsp-quiz/app.py >> /var/log/ccsp-quiz.log 2>&1 &
echo "Started PID: $!"
sleep 2

# Test
curl -s http://localhost:5001/api/admin/stats 2>/dev/null && echo "" || echo "API not responding yet..."
echo ""
echo "=== GET ADMIN TOKEN ==="
grep -o 'ADMIN_TOKEN=[^ ]*' /var/log/ccsp-quiz.log 2>/dev/null || grep 'ADMIN_TOKEN' /var/log/ccsp-quiz.log 2>/dev/null || echo "Check /var/log/ccsp-quiz.log"
echo ""
echo "=== VPS API Ready on port 5001 ==="
echo "Test: curl http://18.139.210.59:5001/api/admin/stats -H 'Authorization: Bearer YOUR_TOKEN'"
