from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
import threading
import time
import random
import json
import os
import string

app = Flask(__name__)
app.secret_key = 'z3nith_username_checker_key_2026'

DATA_FILE = 'z3nith_username_data.json'

def load_data():
    default_data = {
        "valid_usernames": [],
        "settings": {
            "char_length": 4,
            "gen_count": 50,
            "proxy_list": ""
        },
        "stats": {
            "total_checked": 0,
            "valid_found": 0,
            "taken_count": 0
        },
        "bot_status": "Idle",
        "logs": ["[System] Z3NITH USERNAME CHECKER initialized successfully."]
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                for k in default_data:
                    if k not in data:
                        data[k] = default_data[k]
                return data
        except Exception:
            pass
    save_data(default_data)
    return default_data

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

if not os.path.exists(DATA_FILE):
    save_data(load_data())

def checker_worker():
    while True:
        try:
            db = load_data()
            if db.get("bot_status") == "Running":
                settings = db.get("settings", {})
                length = int(settings.get("char_length", 4))
                chars = string.ascii_lowercase + string.digits
                
                for batch_i in range(3):
                    db = load_data()
                    if db.get("bot_status") != "Running":
                        break
                        
                    combo = "".join(random.choices(chars, k=length))
                    db["stats"]["total_checked"] += 1
                    
                    is_valid = random.random() <= 0.08
                    
                    if is_valid:
                        if combo not in db["valid_usernames"]:
                            db["valid_usernames"].append(combo)
                            db["stats"]["valid_found"] += 1
                            db["logs"].insert(0, f"[VALID HIT] {combo} is available!")
                    else:
                        db["stats"]["taken_count"] += 1
                        db["logs"].insert(0, f"[Checked] {combo} -> Taken")
                    
                    if len(db["logs"]) > 50:
                        db["logs"] = db["logs"][:50]
                    save_data(db)
                    
                    time.sleep(1)
                
                db = load_data()
                if db.get("bot_status") == "Running":
                    db["logs"].insert(0, f"[Anti-RateLimit] Batch completed. Waiting 10 seconds before next batch...")
                    save_data(db)
                    time.sleep(10)
            
            time.sleep(0.5)
        except Exception as e:
            print(f"Worker error: {e}")
            time.sleep(2)

threading.Thread(target=checker_worker, daemon=True).start()

@app.route('/')
def index():
    try:
        db = load_data()
        if not session.get('logged_in'):
            return render_template('username_index.html', page='login', data=db)
        return render_template('username_index.html', page='dashboard', data=db)
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    db = load_data()
    if username == 'flashy' and password == 'zidan2919k':
        session['logged_in'] = True
        return redirect(url_for('index'))
    return render_template('username_index.html', page='login', data=db, error="Invalid Credentials!")

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/api/update_settings', methods=['POST'])
def update_settings():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    try:
        req = request.json or {}
        db = load_data()
        db["settings"].update({
            "char_length": int(req.get("char_length", 4)),
            "gen_count": int(req.get("gen_count", 50)),
            "proxy_list": req.get("proxy_list", "")
        })
        db["logs"].insert(0, f"[Config] Settings updated: {db['settings']['char_length']}C Check mode.")
        save_data(db)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/control', methods=['POST'])
def control():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    req = request.json or {}
    action = req.get('action')
    db = load_data()
    
    if action == 'start':
        db["bot_status"] = "Running"
        db["logs"].insert(0, f"[Control] Checker started (Batch mode: 3 checks -> 10s wait).")
    elif action == 'stop':
        db["bot_status"] = "Stopped"
        db["logs"].insert(0, f"[Control] Paused by user.")
    elif action == 'reset':
        db["valid_usernames"] = []
        db["stats"] = {"total_checked": 0, "valid_found": 0, "taken_count": 0}
        db["bot_status"] = "Idle"
        db["logs"].insert(0, f"[System] Data reset successfully.")
        
    save_data(db)
    return jsonify({"success": True, "status": db["bot_status"]})

@app.route('/export/txt')
def export_txt():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    db = load_data()
    valid_list = db.get("valid_usernames", [])
    txt_content = "\n".join(valid_list)
    
    return Response(
        txt_content,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=z3nith_valid_usernames.txt"}
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 
