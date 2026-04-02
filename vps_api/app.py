from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import threading

app = Flask(__name__)
CORS(app)

DATA_FILE = '/opt/ccsp-quiz/data.json'
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

lock = threading.Lock()

def read_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def write_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/api/data', methods=['GET'])
def get_data():
    device_id = request.args.get('deviceId', 'unknown')
    data = read_data()
    record = data.get(device_id, {
        'wrongIds': [],
        'totalAnswered': 0,
        'totalCorrect': 0,
        'lastUpdated': 0,
    })
    return jsonify(record)

@app.route('/api/data', methods=['POST'])
def save_data():
    body = request.get_json()
    device_id = body.get('deviceId', 'unknown')
    record = {
        'wrongIds': body.get('wrongIds', []),
        'totalAnswered': body.get('totalAnswered', 0),
        'totalCorrect': body.get('totalCorrect', 0),
        'lastUpdated': body.get('lastUpdated', 0),
    }
    with lock:
        data = read_data()
        existing = data.get(device_id, {})
        # Only update if new data is newer
        if record.get('lastUpdated', 0) >= existing.get('lastUpdated', 0):
            data[device_id] = record
            write_data(data)
    return jsonify({'ok': True})

@app.route('/api/reset', methods=['POST'])
def reset_data():
    body = request.get_json()
    device_id = body.get('deviceId', 'unknown')
    with lock:
        data = read_data()
        if device_id in data:
            data[device_id] = {'wrongIds': [], 'totalAnswered': 0, 'totalCorrect': 0, 'lastUpdated': 0}
            write_data(data)
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
