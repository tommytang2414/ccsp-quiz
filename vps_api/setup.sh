#!/bin/bash
# Run on VPS: 18.139.210.59
# Creates dir, installs deps, starts app

set -e

DIR=/opt/ccsp-quiz
mkdir -p $DIR

# Write app.py
cat > $DIR/app.py << 'PYEOF'
from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os, threading

app = Flask(__name__)
CORS(app)

DATA_FILE = '/opt/ccsp-quiz/data.json'
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
lock = threading.Lock()

def read_data():
    if not os.path.exists(DATA_FILE): return {}
    try:
        with open(DATA_FILE) as f: return json.load(f)
    except: return {}

def write_data(d):
    with open(DATA_FILE, 'w') as f: json.dump(d, f, indent=2)

@app.route('/api/data', methods=['GET'])
def get_data():
    did = request.args.get('deviceId', 'unknown')
    rec = read_data().get(did, {'wrongIds':[],'totalAnswered':0,'totalCorrect':0,'lastUpdated':0})
    return jsonify(rec)

@app.route('/api/data', methods=['POST'])
def save_data():
    body = request.get_json()
    did = body.get('deviceId', 'unknown')
    rec = {'wrongIds':body.get('wrongIds',[]),'totalAnswered':body.get('totalAnswered',0),'totalCorrect':body.get('totalCorrect',0),'lastUpdated':body.get('lastUpdated',0)}
    with lock:
        data = read_data()
        existing = data.get(did, {})
        if rec.get('lastUpdated',0) >= existing.get('lastUpdated',0):
            data[did] = rec
            write_data(data)
    return jsonify({'ok':True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
PYEOF

# Install flask + flask-cors if not present
pip install flask flask-cors -q 2>/dev/null || pip3 install flask flask-cors -q

# Kill old instance if running
pkill -f "python.*ccsp-quiz/app.py" 2>/dev/null || true

# Start in background
nohup python3 $DIR/app.py >> /var/log/ccsp-quiz.log 2>&1 &
echo "Started PID: $!"
sleep 2
curl -s http://localhost:5000/api/data?deviceId=test
