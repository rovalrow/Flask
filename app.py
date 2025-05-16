from flask import Flask, request, jsonify, render_template
import os
import re
import requests
import uuid
import json
import time
from supabase import create_client
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "0x4AAAAAABZAawAfCPe3waqvkG4X_MxVenY")

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ikxxvgflnpfyncnaqfxx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlreHh2Z2ZsbnBmeW5jbmFxZnh4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDYxOTE3NTMsImV4cCI6MjA2MTc2Nzc1M30.YiF46ggItUYuKLfdD_6oOxq2xGX7ac6yqqtEGeM_dg8")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Obfuscator API Config
OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "bf4f5e8e-291b-2a5f-dc7f-2b5fabdeab1eb69f")
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

RATE_LIMIT = {}

def sanitize_filename(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def obfuscate_lua_code(code):
    try:
        new_script_headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "content-type": "text"
        }
        session_response = requests.post(NEW_SCRIPT_URL, headers=new_script_headers, data=code)
        session_data = session_response.json()
        if not session_data.get("sessionId"):
            return {"error": "Failed to create session"}, False

        session_id = session_data["sessionId"]

        obfuscate_headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "sessionId": session_id,
            "content-type": "application/json"
        }

        obfuscation_options = {
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

        obfuscate_response = requests.post(OBFUSCATE_URL, headers=obfuscate_headers, data=json.dumps(obfuscation_options))
        obfuscate_data = obfuscate_response.json()
        if not obfuscate_data.get("code"):
            return {"error": "Failed to obfuscate code"}, False

        return {"obfuscated_code": obfuscate_data["code"]}, True

    except Exception as e:
        return {"error": str(e)}, False

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    script_content = data.get("script", "").strip()
    custom_name = sanitize_filename(data.get("name", "").strip())

    if not script_content:
        return jsonify({"error": "No script provided"}), 400

    # Auto-detect Discord webhook and replace with proxy
    discord_webhook_match = re.search(r'https://discord(?:app)?\.com/api/webhooks/\d+/[\w-]+', script_content)
    if discord_webhook_match:
        original_webhook = discord_webhook_match.group(0)
        path_id = uuid.uuid4().hex[:12]

                # Check if webhook already exists
        existing = supabase.table("discord_webhooks").select("id").eq("webhook", original_webhook).execute()
        if existing.data:
            path_id = existing.data[0]["id"]
        else:
            path_id = uuid.uuid4().hex[:12]
            supabase.table("discord_webhooks").insert({
                "id": path_id,
                "webhook": original_webhook,
                "created_at": "now()"
            }).execute()

        script_content = script_content.replace(original_webhook, f"{request.host_url}scriptguardian/webhooks/{path_id}")

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
        "created_at": "now()"
    }).execute()

    return jsonify({"link": f"{request.host_url}scriptguardian/files/scripts/loaders/{script_name}"}), 200

@app.route('/scriptguardian/files/scripts/loaders/<script_name>')
def execute(script_name):
    script_name = sanitize_filename(script_name)
    response = supabase.table("scripts").select("content").eq("name", script_name).execute()

    if response.data:
        user_agent = request.headers.get("User-Agent", "").lower()
        if not ("roblox" in user_agent or "robloxapp" in user_agent):
            return render_template("unauthorized.html"), 403

        return response.data[0]["content"], 200, {'Content-Type': 'text/plain'}

    return 'game.Players.LocalPlayer:Kick("This Script is No Longer Existing on Our Database. Please Contact the Developer of the Script.")', 200, {'Content-Type': 'text/plain'}

@app.route('/scriptguardian/webhooks/<path_id>', methods=['POST'])
def trigger_hidden_webhook(path_id):
    path_id = re.sub(r"[^a-zA-Z0-9]", "", path_id)
    client_ip = request.remote_addr
    now = time.time()

    if client_ip in RATE_LIMIT and now - RATE_LIMIT[client_ip] < 20:
        return jsonify({"error": "Please wait before triggering again."}), 429
    RATE_LIMIT[client_ip] = now

    try:
        result = supabase.table("discord_webhooks").select("webhook").eq("id", path_id).execute()
        if not result.data or not result.data[0].get("webhook"):
            return jsonify({"error": "Invalid webhook"}), 404

        webhook_url = result.data[0]["webhook"]
        payload = request.get_json(force=True)

        if "content" not in payload:
            payload = {
                "content": json.dumps(payload, indent=2)
            }

        headers = {'Content-Type': 'application/json'}
        discord_response = requests.post(webhook_url, json=payload, headers=headers, timeout=5)

        if 200 <= discord_response.status_code < 300:
            return jsonify({"status": "Webhook triggered"}), 200
        else:
            return jsonify({"error": f"Discord webhook returned status code {discord_response.status_code}"}), 502

    except Exception as e:
        return jsonify({"error": f"Failed to send webhook: {str(e)}"}), 500

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
