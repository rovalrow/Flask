from flask import Flask, request, jsonify, render_template
from supabase import create_client, Client
import os
import re
import requests
import uuid
import json

app = Flask(__name__)

# Supabase configuration
# Note: Don't hardcode credentials in production code. Use environment variables instead.
SUPABASE_URL = "https://hafsqbqbbgrcrdpuwpel.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhhZnNxYnFiYmdyY3JkcHV3cGVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU4NDM5NTgsImV4cCI6MjA2MTQxOTk1OH0.xJ36qskYiGoH-ywbrWQZlJOvGXzS4_NYxRO0tuRyy5c"
SUPABASE_BUCKET = "scripts"  # your Supabase bucket name

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Obfuscator API Config
OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "bf4f5e8e-291b-2a5f-dc7f-2b5fabdeab1eb69f")
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

def sanitize_filename(name):
    """Removes invalid characters from a filename."""
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def obfuscate_lua_code(code):
    """Sends Lua code to obfuscation API and returns obfuscated result with maximum security."""
    try:
        # Step 1: Create new script session
        new_script_headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "content-type": "text"
        }
        session_response = requests.post(NEW_SCRIPT_URL, headers=new_script_headers, data=code)
        session_data = session_response.json()
        
        if session_data.get("message") or not session_data.get("sessionId"):
            return {"error": f"Failed to create obfuscation session: {session_data.get('message', 'Unknown error')}"}, False
        
        session_id = session_data["sessionId"]
        
        # Step 2: Obfuscate the script with enhanced settings
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

        if obfuscate_data.get("message") or not obfuscate_data.get("code"):
            return {"error": f"Failed to obfuscate code: {obfuscate_data.get('message', 'Unknown error')}"}, False
        
        return {"obfuscated_code": obfuscate_data["code"]}, True
    
    except Exception as e:
        return {"error": f"Obfuscation service error: {str(e)}"}, False

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
    
    obfuscation_result, success = obfuscate_lua_code(script_content)
    
    if not success:
        return jsonify(obfuscation_result), 500
    
    obfuscated_script = obfuscation_result["obfuscated_code"]
    script_name = custom_name if custom_name else str(uuid.uuid4())

    try:
        # Upload the obfuscated script to Supabase storage
        supabase.storage.from_(SUPABASE_BUCKET).upload(
            f"{script_name}.lua", 
            bytes(obfuscated_script, 'utf-8')
        )
    except Exception as e:
        return jsonify({"error": f"Failed to upload script: {str(e)}"}), 500

    return jsonify({"link": f"{request.host_url}scriptguardian.shinzou/{script_name}"}), 200

@app.route('/scriptguardian.shinzou/<script_name>')
def execute(script_name):
    script_name = sanitize_filename(script_name)

    try:
        # Download the file from Supabase storage
        file_data = supabase.storage.from_(SUPABASE_BUCKET).download(f"{script_name}.lua")
        content = file_data.decode('utf-8')
    except Exception as e:
        return f"Invalid script link. Error: {str(e)}", 404

    accept_header = request.headers.get("Accept", "").lower()

    if "text/html" in accept_header:
        # Return HTML version for browsers
        return """
        <html>
        <head>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&display=swap');
                body { 
                    display: flex; 
                    flex-direction: column; 
                    justify-content: center; 
                    align-items: center; 
                    height: 100vh; 
                    margin: 0; 
                    background-color: #0A0A2A;
                    font-family: 'Fredoka', sans-serif;
                }
                h1 { 
                    font-size: 40px; 
                    text-align: center; 
                    color: red; 
                }
                .discord-button { 
                    margin-top: 20px;
                    padding: 12px 24px; 
                    font-size: 20px; 
                    background-color: #000000; 
                    color: white; 
                    border: none; 
                    border-radius: 12px; 
                    cursor: pointer; 
                    font-family: 'Fredoka', sans-serif;
                    transition: 0.3s;
                }
                .discord-button:hover { 
                    background-color: #222222; 
                }
                .made-by {
                    margin-top: 15px;
                    color: red;
                    font-size: 18px;
                    font-family: 'Fredoka', sans-serif;
                }
            </style>
        </head>
        <body>
            <h1>🚫 Unauthorized to see this script. 🚫<br> Close & Proceed.</h1>
            <button class="discord-button" onclick="window.location.href='https://discord.gg/SdMXRFPUYx'">Discord</button>
            <div class="made-by">Made By: Shinzou</div>
        </body>
        </html>
        """, 403

    # Return the actual script content for non-browser requests
    return content, 200

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
