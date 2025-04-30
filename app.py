from flask import Flask, request, jsonify, render_template, Response, redirect, url_for
import os
import re
import requests
import uuid
import json
import time
import hashlib
import hmac
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "0x4AAAAAABWfDQXfye-8ewXoXpq-SQj5iF0")
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800
)

SCRIPTS_DIR = "scripts"
os.makedirs(SCRIPTS_DIR, exist_ok=True)

OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "bf4f5e8e-291b-2a5f-dc7f-2b5fabdeab1eb69f")
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

RATE_LIMIT = {"window": 60, "max_requests": 10}
request_history = {}

CSP_POLICY = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr
        now = time.time()
        request_history.setdefault(ip, [])
        request_history[ip] = [t for t in request_history[ip] if now - t < RATE_LIMIT["window"]]
        if len(request_history[ip]) >= RATE_LIMIT["max_requests"]:
            return jsonify({"error": "Rate limit exceeded"}), 429
        request_history[ip].append(now)
        return f(*args, **kwargs)
    return decorated

@app.after_request
def apply_security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['X-XSS-Protection'] = '1; mode=block'
    resp.headers['Content-Security-Policy'] = CSP_POLICY
    resp.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    resp.headers['Referrer-Policy'] = 'same-origin'
    return resp

def validate_roblox_request():
    ua = request.headers.get("User-Agent", "").lower()
    return any(k in ua for k in ["roblox", "rbxapp", "robloxapp", "rbxproxy"])

def generate_token(script_id):
    ts = str(int(time.time()))
    msg = f"{script_id}:{ts}"
    sig = hmac.new(app.secret_key.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"{ts}:{sig}"

def validate_token(script_id, token):
        ts, sig = token.split(":", 1)
        if int(time.time()) - int(ts) > 300:
            return False
        msg = f"{script_id}:{ts}"
        expected = hmac.new(app.secret_key.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    except:
        return False

def obfuscate_lua_code(code):
        session = requests.post(
            NEW_SCRIPT_URL,
            headers={"apikey": OBFUSCATOR_API_KEY, "content-type": "text"},
            data=code,
            timeout=10
        )
        if session.status_code != 200:
            return {"error": "Failed to start obfuscation"}, False
        sid = session.json().get("sessionId")
        if not sid:
            return {"error": "Session ID not returned"}, False

        options = {
            "MinifiyAll": True,
            "Virtualize": True,
            "Seed": str(uuid.uuid4().int)[:8],
            "CustomPlugins": {
                "CachedEncryptStrings": True,
                "CallRetAssignment": True,
                "ControlFlowFlattenV2AllBlocks": True,
                "DummyFunctionArgs": True,
                "FuncChopper": True,
                "Minifier2": True,
                "WowPacker": True
            }
        }

        response = requests.post(
            OBFUSCATE_URL,
            headers={"apikey": OBFUSCATOR_API_KEY, "sessionId": sid, "content-type": "application/json"},
            data=json.dumps(options),
            timeout=10
        )
        if response.status_code != 200:
            return {"error": "Obfuscation failed"}, False
        result = response.json().get("code")
        return ({"obfuscated_code": result}, True) if result else ({"error": "Empty obfuscation output"}, False)
    except Exception as e:
        return {"error": str(e)}, False

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
@rate_limit
def generate():
    if not request.is_json:
        return jsonify({"error": "JSON expected"}), 400
    script = request.json.get("script", "").strip()
    if not script:
        return jsonify({"error": "No script provided"}), 400

    result, ok = obfuscate_lua_code(script)
    if not ok:
        return jsonify(result), 500

    script_id = uuid.uuid4().hex[:32]
    with open(os.path.join(SCRIPTS_DIR, f"{script_id}.lua"), "w", encoding="utf-8") as f:
        f.write(result["obfuscated_code"])

    return jsonify({"link": f"{request.host_url}l/{script_id}.lua"})

@app.route('/l/<script_id>.lua')
def loader(script_id):
    if not re.match(r"^[a-f0-9]{32}$", script_id):
        return render_template("error.html", message="Invalid ID"), 400
    if not validate_roblox_request():
        return render_template("unauthorized.html"), 403

    token = generate_token(script_id)
    url = f"{request.host_url}_internal/{script_id}.lua?token={token}"

    return Response(f"""
local HttpService = game:GetService("HttpService")
local r = http.request({{Url="{url}", Method="GET"}})
if r.Success and r.StatusCode == 200 then
    loadstring(r.Body)()
else
    warn("Failed to load script: " .. tostring(r.StatusCode))
end
""", mimetype='text/plain')

@app.route('/_internal/<script_id>.lua')
def serve(script_id):
    if not re.match(r"^[a-f0-9]{32}$", script_id):
        return Response("-- Invalid ID", mimetype="text/plain"), 400

    if not validate_token(script_id, request.args.get("token", "")):
        return Response("-- Invalid token", mimetype="text/plain"), 403
    if not validate_roblox_request():
        return Response("-- Unauthorized", mimetype="text/plain"), 403

    path = os.path.join(SCRIPTS_DIR, f"{script_id}.lua")
    if not os.path.exists(path):
        return Response("-- Script not found", mimetype="text/plain"), 404

    with open(path, "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/plain")

@app.route('/api/obfuscate', methods=['POST'])
@rate_limit
def api():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400
    if not hmac.compare_digest(request.headers.get("X-API-Key", ""), OBFUSCATOR_API_KEY):
        return jsonify({"error": "Unauthorized"}), 401

    code = request.json.get("script", "")
    if not code:
        return jsonify({"error": "No script provided"}), 400

    result, ok = obfuscate_lua_code(code)
    return jsonify(result if ok else result), 200 if ok else 500

@app.route('/health')
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

@app.route('/scripts/<path:path>')
def deny_access(path):
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False, ssl_context='adhoc')
