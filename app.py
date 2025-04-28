from flask import Flask, request, jsonify, render_template, make_response
import os
import re
import threading
import secrets
import hashlib
import time

app = Flask(__name__)
SCRIPTS_DIR = "scripts"
TOKEN_SECRET = secrets.token_hex(16)  # Generate a random secret for this session

os.makedirs(SCRIPTS_DIR, exist_ok=True)

def sanitize_filename(name):
    """Removes invalid characters from a filename."""
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def get_next_script_id():
    """Returns the next available script number."""
    existing_files = [f.split(".")[0] for f in os.listdir(SCRIPTS_DIR) if f.endswith(".py")]
    script_numbers = [int(f) for f in existing_files if f.isdigit()]
    return max(script_numbers, default=0) + 1

def generate_access_token(script_name, timestamp, client_id=""):
    """Generate a secure access token for script access."""
    data = f"{script_name}:{timestamp}:{client_id}:{TOKEN_SECRET}"
    return hashlib.sha256(data.encode()).hexdigest()

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    script_content = data.get("script", "").strip()
    custom_name = sanitize_filename(data.get("name", "").strip())
    client_id = sanitize_filename(data.get("client_id", "").strip())

    if not script_content:
        return jsonify({"error": "No script provided"}), 400

    script_name = custom_name if custom_name else str(get_next_script_id())
    script_path = os.path.join(SCRIPTS_DIR, f"{script_name}.py")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    timestamp = str(int(time.time()) + 86400)
    
    token = generate_access_token(script_name, timestamp, client_id)
    
    script_url = f"{request.host_url}scriptguardian.shinzou/{script_name}?t={timestamp}&token={token}"
    if client_id:
        script_url += f"&client={client_id}"
        
    return jsonify({"link": script_url})

@app.route('/scriptguardian.shinzou/<script_name>')
def execute(script_name):
    script_path = os.path.join(SCRIPTS_DIR, f"{script_name}.py")

    if not os.path.exists(script_path):
        return "Invalid script link.", 404
    
    timestamp = request.args.get('t', '')
    token = request.args.get('token', '')
    client_id = request.args.get('client', '')
    
    is_valid_token = False
    if timestamp and token:
        try:
            if int(timestamp) > int(time.time()):
                expected_token = generate_access_token(script_name, timestamp, client_id)
                is_valid_token = (token == expected_token)
        except ValueError:
            is_valid_token = False
    
    user_agent = request.headers.get("User-Agent", "").lower()
    browser_indicators = ["mozilla", "chrome", "safari", "edge", "opera", "webkit", "gecko", "msie", "trident"]
    is_browser = any(indicator in user_agent for indicator in browser_indicators)
    
    potential_tools = ["viewer", "beautify", "crawler", "spider", "bot", "http", "curl", "wget", "postman", "insomnia"]
    is_tool = any(tool in user_agent.lower() for tool in potential_tools)
    
    accepts_html = "text/html" in request.headers.get("Accept", "").lower()
    
    if is_browser or is_tool or accepts_html or not is_valid_token:
        # Create response with unauthorized message
        response = make_response("""
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
                    background-color: #0A0A2A; /* Dark Blue, Almost Black */
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
                    background-color: #000000; /* Pure Black */
                    color: white; 
                    border: none; 
                    border-radius: 12px; /* UICorner effect */
                    cursor: pointer; 
                    font-family: 'Fredoka', sans-serif;
                    transition: 0.3s;
                }
                .discord-button:hover { 
                    background-color: #222222; /* Slightly lighter black on hover */
                }
                .made-by {
                    margin-top: 15px;
                    color: red;
                    font-size: 18px;
                    font-family: 'Fredoka', sans-serif;
                }
            </style>
            <title>Unauthorized Access</title>
            <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
            <meta http-equiv="Pragma" content="no-cache">
            <meta http-equiv="Expires" content="0">
        </head>
        <body>
            <h1>🚫 Unauthorized to see this script. 🚫<br> Close & Proceed.</h1>
            <button class="discord-button" onclick="window.location.href='https://discord.gg/SdMXRFPUYx'">Discord</button>
            <div class="made-by">Made By: Shinzou</div>
        </body>
        </html>
        """, 403)
        
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' https://fonts.googleapis.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com;"
        
        return response
    
    
    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()
        
    response = make_response(script_content)
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    return response

def keep_alive():
    def run():
        app.run(host="0.0.0.0", port=8080)
    thread = threading.Thread(target=run)
    thread.daemon = True  # Kills the thread if the main script stops
    thread.start()

if __name__ == '__main__':
    keep_alive()
    while True:
        pass
