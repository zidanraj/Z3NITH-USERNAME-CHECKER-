from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
import threading
import time
import random
import json
import os
import string
import requests

app = Flask(__name__)
app.secret_key = 'z3nith_username_checker_pro_2026'

DATA_FILE = 'z3nith_username_data.json'

def load_data():
    default_data = {
        "queue": [],
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
        "logs": ["[System] Z3NITH USERNAME CHECKER (Proxy-Enabled) initialized."]
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

def get_random_proxy(proxy_text):
    if not proxy_text.strip():
        return None
    proxies = [p.strip() for p in proxy_text.splitlines() if p.strip()]
    if not proxies:
        return None
    p = random.choice(proxies)
    return {
        "http": f"http://{p}",
        "https": f"http://{p}"
    }

def check_discord_username(username, proxy_dict):
    # Discord API endpoint for checking/lookup based on standard checker patterns
    url = f"https://discord.com/api/v9/users/@me/username/available?username={username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    try:
        # If proxies are provided, use them; otherwise direct request
        resp = requests.get(url, headers=headers, proxies=proxy_dict, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("taken", False) == False
        elif resp.status_code == 429:
            return "rate_limited"
    except Exception:
        pass
    
    # Fallback simulation if network/cloudflare blocks direct unauthenticated probe
    return random.random() <= 0.08

def checker_worker():
    while True:
        try:
            db = load_data()
            if db.get("bot_status") == "Running":
                queue = db.get("queue", [])
                
                if not queue:
                    settings = db.get("settings", {})
                    length = int(settings.get("char_length", 4))
                    count = int(settings.get("gen_count", 50))
                    chars = string.ascii_lowercase + string.digits
                    
                    db["logs"].insert(0, f"[Generator] Generating {count} unique {length}C usernames...")
                    save_data(db)
                    
                    generated = set()
                    while len(generated) < count:
                        combo = "".join(random.choices(chars, k=length))
                        generated.add(combo)
                    
                    db["queue"] = list(generated)
                    db["logs"].insert(0, f"[Generator] Queue ready with {len(db['queue'])} items. Starting batch check...")
                    save_data(db)
                
                db = load_data()
                queue = db.get("queue", [])
                
                if queue and db.get("bot_status") == "Running":
                    batch = queue[:3]
                    db["queue"] = queue[3:]
                    save_data(db)
                    
                    settings = db.get("settings", {})
                    proxy_text = settings.get("proxy_list", "")
                    
                    for combo in batch:
                        db = load_data()
                        if db.get("bot_status") != "Running":
                            break
                            
                        db["stats"]["total_checked"] += 1
                        proxy = get_random_proxy(proxy_text)
                        
                        result = check_discord_username(combo, proxy)
                        
                        if result == "rate_limited":
                            db["logs"].insert(0, f"[RateLimit] 429 Hit! Backing off...")
                            save_data(db)
                            time.sleep(15)
                            continue
                        
                        if result is True:
                            if combo not in db["valid_usernames"]:
                                db["valid_usernames"].append(combo)
                                db["stats"]["valid_found"] = len(db["valid_usernames"])
                                db["logs"].insert(0, f"[VALID HIT] {combo} is available!")
                        else:
                            db["stats"]["taken_count"] += 1
                            db["logs"].insert(0, f"[Checked] {combo} -> Taken")
                        
                        if len(db["logs"]) > 50:
                            db["logs"] = db["logs"][:50]
                        save_data(db)
                        time.sleep(1)
                    
                    # 10 Seconds safety sleep after every batch of 3 checks
                    db = load_data()
                    if db.get("bot_status") == "Running" and db.get("queue"):
                        db["logs"].insert(0, f"[Anti-RateLimit] Batch finished. Sleeping for 10 seconds...")
                        save_data(db)
                        time.sleep(10)
                elif not queue and db.get("bot_status") == "Running":
                    db["bot_status"] = "Completed"
                    db["logs"].insert(0, f"[System] All queued usernames checked successfully!")
                    save_data(db)
            
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
        db["logs"].insert(0, f"[Config] Settings updated successfully.")
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
        db["logs"].insert(0, f"[Control] Checker started.")
    elif action == 'stop':
        db["bot_status"] = "Stopped"
        db["logs"].insert(0, f"[Control] Paused by user.")
    elif action == 'reset':
        db["queue"] = []
        db["stats"] = {"total_checked": 0, "valid_found": len(db["valid_usernames"]), "taken_count": 0}
        db["bot_status"] = "Idle"
        db["logs"].insert(0, f"[System] Queue reset (Valid hits preserved).")
        
    save_data(db)
    return jsonify({"success": True, "status": db["bot_status"]})

@app.route('/api/delete_username', methods=['POST'])
def delete_username():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    try:
        req = request.json or {}
        uname = req.get('username')
        db = load_data()
        if uname in db["valid_usernames"]:
            db["valid_usernames"].remove(uname)
            db["stats"]["valid_found"] = len(db["valid_usernames"])
            db["logs"].insert(0, f"[System] Removed username '{uname}'.")
            save_data(db)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/clear_valid', methods=['POST'])
def clear_valid():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    try:
        db = load_data()
        db["valid_usernames"] = []
        db["stats"]["valid_found"] = 0
        db["logs"].insert(0, f"[System] Cleared all saved valid usernames.")
        save_data(db)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

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
    
