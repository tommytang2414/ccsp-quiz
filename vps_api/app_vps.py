from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, uuid, secrets, string, json, time, threading

app = Flask(__name__)
CORS(app)
DB_PATH = '/home/ubuntu/ccsp-quiz/auth.db'
lock = threading.Lock()

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def code_exists(code):
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT id FROM codes WHERE code = ?', (code,))
        return cur.fetchone() is not None

def get_user_id_by_code(code):
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT used_by FROM codes WHERE code = ?', (code,))
        r = cur.fetchone()
        return r['used_by'] if r else None

def get_user_by_token(token):
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT * FROM users WHERE token = ?', (token,))
        return cur.fetchone()

def get_user_by_id(user_id):
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return cur.fetchone()

def create_user(exam, code):
    user_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    with get_db() as db:
        db.execute('INSERT INTO users (id, exam, token, created_at, updated_at) VALUES (?, ?, ?, ?, ?)', (user_id, exam, token, now, now))
        db.execute('UPDATE codes SET used_by = ?, used_at = ? WHERE code = ?', (user_id, now, code))
        db.commit()
    return user_id, token

def generate_code(exam, length=8):
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(chars) for _ in range(length))
        with get_db() as db:
            cur = db.cursor()
            cur.execute('SELECT id FROM codes WHERE code = ?', (code,))
            if cur.fetchone() is None:
                return code

def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS codes (id INTEGER PRIMARY KEY AUTOINCREMENT, exam TEXT NOT NULL DEFAULT 'CCSP', code TEXT UNIQUE NOT NULL, used_by TEXT, used_at INTEGER, created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, exam TEXT NOT NULL DEFAULT 'CCSP', token TEXT UNIQUE NOT NULL, data TEXT NOT NULL DEFAULT '{}', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_codes_code ON codes(code);
            CREATE INDEX IF NOT EXISTS idx_users_token ON users(token);
        ''')

def setup():
    import os
    os.makedirs('/home/ubuntu/ccsp-quiz', exist_ok=True)
    init_db()
    now = int(time.time())
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT id FROM users WHERE id = ?', ('admin',))
        if not cur.fetchone():
            admin_token = secrets.token_urlsafe(32)
            db.execute('INSERT INTO users (id, exam, token, created_at, updated_at) VALUES (?, ?, ?, ?, ?)', ('admin', 'ADMIN', admin_token, now, now))
            for code in ['ALPWBB36', '5KN3WTNX']:
                db.execute('INSERT INTO codes (exam, code, created_at) VALUES (?, ?, ?)', ('CCSP', code, now))
            db.commit()
            print(f'ADMIN_TOKEN={admin_token}')
            with open('/tmp/admin_token.txt', 'w') as f:
                f.write(admin_token)

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
        existing = get_user_id_by_code(code)
        if existing:
            user = get_user_by_id(existing)
            if user:
                return jsonify({'token': user['token'], 'userId': user['id'], 'exam': user['exam'], 'reused': True})
        user_id, token = create_user(exam, code)
    return jsonify({'token': token, 'userId': user_id, 'exam': exam, 'reused': False})

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
    now = int(time.time())
    with get_db() as db:
        db.execute('UPDATE users SET data = ?, updated_at = ? WHERE token = ?', (json.dumps(request.get_json() or {}), now, auth[7:]))
        db.commit()
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
    if not row or row['token'] != auth[7:]:
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
    if not row or row['token'] != auth[7:]:
        return jsonify({'error': 'Unauthorized'}), 401
    exam = request.args.get('exam', 'CCSP')
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT code, used_by, used_at, created_at FROM codes WHERE exam = ? ORDER BY created_at DESC', (exam,))
        rows = cur.fetchall()
    return jsonify({'codes': [{'code': r['code'], 'used': r['used_by'] is not None, 'used_by': r['used_by'], 'used_at': r['used_at'], 'created_at': r['created_at']} for r in rows]})

@app.route('/api/admin/stats', methods=['GET'])
def stats():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    with get_db() as db:
        cur = db.cursor()
        cur.execute('SELECT token FROM users WHERE id = ?', ('admin',))
        row = cur.fetchone()
    if not row or row['token'] != auth[7:]:
        return jsonify({'error': 'Unauthorized'}), 401
    result = {}
    for exam in ['CCSP', 'CISSP', 'AAIA']:
        cur = db.cursor()
        cur.execute('SELECT COUNT(*) FROM codes WHERE exam = ? AND used_by IS NOT NULL', (exam,))
        active = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM codes WHERE exam = ?', (exam,))
        total = cur.fetchone()[0]
        result[exam] = {'active_codes': active, 'total_codes': total}
    return jsonify(result)

if __name__ == '__main__':
    setup()
    app.run(host='0.0.0.0', port=5001, debug=False)
