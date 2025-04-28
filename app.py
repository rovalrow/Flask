from flask import Flask, request, jsonify, render_template
import os
import re

app = Flask(__name__)
SCRIPTS_DIR = "scripts"

# Create scripts folder if it doesn't exist
os.makedirs(SCRIPTS_DIR, exist_ok=True)

def sanitize_filename(name):
    """Removes invalid characters from a filename."""
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def get_next_script_id():
    """Returns the next available script number."""
    existing_files = [f.split(".")[0] for f in os.listdir(SCRIPTS_DIR) if f.endswith(".py")]
    script_numbers = [int(f) for f in existing_files if f.isdigit()]
    return max(script_numbers, default=0) + 1

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

    script_name = custom_name if custom_name else str(get_next_script_id())
    script_path = os.path.join(SCRIPTS_DIR, f"{script_name}.py")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    return jsonify({"link": f"{request.host_url}scriptguardian.shinzou/{script_name}"}), 200

@app.route('/scriptguardian.shinzou/<script_name>')
def execute(script_name):
    script_path = os.path.join(SCRIPTS_DIR, f"{script_name}.py")

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

if __name__ == '__main__':
    import os

    port = int(os.environ.get('PORT', 8080))  # for Render, use $PORT
    app.run(host="0.0.0.0", port=port)
