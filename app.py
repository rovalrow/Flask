from flask import Flask, request, jsonify, render_template
import os
import re
import requests
import uuid
import json

app = Flask(__name__)
SCRIPTS_DIR = "scripts"

# Create scripts folder if it doesn't exist
os.makedirs(SCRIPTS_DIR, exist_ok=True)

# Obfuscator API Config
OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "bf4f5e8e-291b-2a5f-dc7f-2b5fabdeab1eb69f")
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

def sanitize_filename(name):
    """Removes invalid characters from a filename."""
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def get_next_script_id():
    """Returns the next available script number."""
    existing_files = [f.split(".")[0] for f in os.listdir(SCRIPTS_DIR) if f.endswith(".lua")]
    script_numbers = [int(f) for f in existing_files if f.isdigit()]
    return max(script_numbers, default=0) + 1

def obfuscate_lua_code(code):
    """Sends Lua code to obfuscation API and returns obfuscated result."""
    try:
        # Step 1: Create new script session
        new_script_headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "content-type": "text"
        }
        
        session_response = requests.post(
            NEW_SCRIPT_URL,
            headers=new_script_headers,
            data=code
        )
        
        session_data = session_response.json()
        if session_data.get("message") is not None or not session_data.get("sessionId"):
            return {"error": f"Failed to create obfuscation session: {session_data.get('message', 'Unknown error')}"}, False
        
        session_id = session_data["sessionId"]
        
        # Step 2: Obfuscate the script
        obfuscate_headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "sessionId": session_id,
            "content-type": "application/json"
        }
        
        obfuscation_options = {
            "MinifiyAll": True,
            "Virtualize": True,
            "CustomPlugins": {
                "EncryptStrings": True,
                "MutateAllLiterals": True,
                "ConstMaker": True,
                "ControlFlowFlattenV2AllBlocks": True,
                "JunkifyAllIfStatements": True
            }
        }
        
        obfuscate_response = requests.post(
            OBFUSCATE_URL,
            headers=obfuscate_headers,
            data=json.dumps(obfuscation_options)
        )
        
        obfuscate_data = obfuscate_response.json()
        if obfuscate_data.get("message") is not None or not obfuscate_data.get("code"):
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
    
    # Process the Lua code through the obfuscator API
    obfuscation_result, success = obfuscate_lua_code(script_content)
    
    if not success:
        return jsonify(obfuscation_result), 500
    
    obfuscated_script = obfuscation_result["obfuscated_code"]
    
    script_name = custom_name if custom_name else str(get_next_script_id())
    script_path = os.path.join(SCRIPTS_DIR, f"{script_name}.lua")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(obfuscated_script)

    return jsonify({"link": f"{request.host_url}scriptguardian.shinzou/{script_name}"}), 200

@app.route('/scriptguardian.shinzou/<script_name>')
def execute(script_name):
    # Ensure we only look for .lua files
    script_path = os.path.join(SCRIPTS_DIR, f"{sanitize_filename(script_name)}.lua")

    if os.path.exists(script_path):
        accept_header = request.headers.get("Accept", "").lower()

        # If the client is expecting HTML (browser), block it
        if "text/html" in accept_header:
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

        # Otherwise, serve the script content (for Roblox HttpGet etc)
        with open(script_path, "r", encoding="utf-8") as f:
            return f.read(), 200

    return "Invalid script link.", 404

# Direct endpoint for obfuscation (API style)
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
    port = int(os.environ.get('PORT', 8080))  # for Render, use $PORT
    app.run(host="0.0.0.0", port=port, debug=False)
