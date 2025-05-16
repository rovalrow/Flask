from flask import Flask, request, jsonify, render_template, Response
import os
import re
import requests
import uuid
import json
import base64
from supabase import create_client
import hashlib
import time

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "0x4AAAAAABZAawAfCPe3waqvkG4X_MxVenY")

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ikxxvgflnpfyncnaqfxx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlreHh2Z2ZsbnBmeW5jbmFxZnh4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDYxOTE3NTMsImV4cCI6MjA2MTc2Nzc1M30.YiF46ggItUYuKLfdD_6oOxq2xGX7ac6yqqtEGeM_dg8")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Obfuscator API Config
OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "bf4f5e8e-291b-2a5f-dc7f-2b5fabdeab1eb69f")
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

def sanitize_filename(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def obfuscate_lua_code(code):
    try:
        new_script_headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "content-type": "text"
        }
        session_response = requests.post(NEW_SCRIPT_URL, headers=new_script_headers, data=code)
        if session_response.status_code != 200:
            return {"error": "Failed to create session"}, False

        session_data = session_response.json()
        if not session_data.get("sessionId"):
            return {"error": "Session ID not returned"}, False

        session_id = session_data["sessionId"]

        obfuscate_headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "sessionId": session_id,
            "content-type": "application/json"
        }

        obfuscation_options = {
            "MinifyAll": True,
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

        obfuscate_response = requests.post(OBFUSCATE_URL, headers=obfuscate_headers, data=json.dumps(obfuscation_options))
        if obfuscate_response.status_code != 200:
            return {"error": "Failed to obfuscate code"}, False

        obfuscate_data = obfuscate_response.json()
        if not obfuscate_data.get("code"):
            return {"error": "Obfuscation returned no code"}, False

        return {"obfuscated_code": obfuscate_data["code"]}, True

    except Exception as e:
        return {"error": str(e)}, False

def encode_script_name(script_name):
    timestamp = str(int(time.time()))
    combined = f"{script_name}|{timestamp}|ScriptGuardian"
    hashed = hashlib.sha256(combined.encode()).hexdigest()[:16]
    encoded = base64.urlsafe_b64encode(f"{script_name}|{timestamp}|{hashed}".encode()).decode()
    return encoded

def decode_script_name(encoded_string):
    try:
        decoded = base64.urlsafe_b64decode(encoded_string.encode()).decode()
        parts = decoded.split('|')
        if len(parts) != 3:
            return None
        script_name, timestamp, hash_value = parts
        expected_combined = f"{script_name}|{timestamp}|ScriptGuardian"
        expected_hash = hashlib.sha256(expected_combined.encode()).hexdigest()[:16]
        if hash_value == expected_hash:
            if int(time.time()) - int(timestamp) < 86400:
                return script_name
        return None
    except Exception:
        return None

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def generate():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.json
    script_content = data.get("script", "").strip()
    custom_name = sanitize_filename(data.get("name", "").strip())

    if not script_content:
        return jsonify({"error": "No script provided"}), 400

    obfuscation_result, success = obfuscate_lua_code(script_content)
    if not success:
        return jsonify(obfuscation_result), 500

    obfuscated_script = obfuscation_result["obfuscated_code"]
    script_name = custom_name if custom_name else uuid.uuid4().hex

    existing_scripts = supabase.table("scripts").select("name").eq("name", script_name).execute()
    if existing_scripts.data:
        counter = 1
        while True:
            new_name = f"{script_name}{counter}"
            name_check = supabase.table("scripts").select("name").eq("name", new_name).execute()
            if not name_check.data:
                script_name = new_name
                break
            counter += 1

    supabase.table("scripts").insert({
        "name": script_name,
        "content": obfuscated_script,
        "unobfuscated": script_content,
        "created_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }).execute()

    encoded_name = encode_script_name(script_name)
    response_data = {
        "link_parts": {
            "host": request.host_url.rstrip('/'),
            "path": "scriptguardian/files/scripts/loaders",
            "id": encoded_name
        }
    }
    return jsonify(response_data), 200

@app.route('/scriptguardian/files/scripts/loaders/<encoded_script_name>')
def execute(encoded_script_name):
    script_name = decode_script_name(encoded_script_name)
    if not script_name:
        return 'game.Players.LocalPlayer:Kick("Invalid or expired script URL. Please generate a new one.")', 200, {'Content-Type': 'text/plain'}

    script_name = sanitize_filename(script_name)
    response = supabase.table("scripts").select("content").eq("name", script_name).execute()

    if response.data:
        user_agent = request.headers.get("User-Agent", "").lower()
        if not ("roblox" in user_agent or "robloxapp" in user_agent):
            return render_template("unauthorized.html"), 403

        script_content = response.data[0]["content"]

        def generate_script():
            yield "--SCRIPT_GUARDIAN_BOUNDARY\n"
            for i in range(0, len(script_content), 1024):
                yield script_content[i:i+1024]
            yield "\n--SCRIPT_GUARDIAN_END"

        headers = {
            'Content-Type': 'text/plain',
            'X-Anti-Spy': 'true',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache'
        }
        return Response(generate_script(), headers=headers)

    return 'game.Players.LocalPlayer:Kick("This Script is No Longer Existing on Our Database. Please Contact the Developer of the Script.")', 200, {'Content-Type': 'text/plain'}

@app.route('/api/obfuscate', methods=['POST'])
def api_obfuscate():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    script_content = request.json.get("script", "")
    if not script_content:
        return jsonify({"error": "No script provided"}), 400

    obfuscation_result, success = obfuscate_lua_code(script_content)
    if not success:
        return jsonify(obfuscation_result), 500

    return jsonify({"obfuscated_code": obfuscation_result["obfuscated_code"]}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
