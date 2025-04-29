<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Script Guardian</title>
    <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            background: #020c1b;
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            overflow: hidden;
            position: relative;
        }

        .top-buttons {
            position: absolute;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 20px;
        }

        .top-buttons button {
            background: black;
            color: white;
            font-family: 'Fredoka', sans-serif;
            font-size: 18px;
            font-weight: bold;
            padding: 14px 30px;
            width: 200px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: 0.3s;
            text-align: center;
            box-shadow: 0 0 15px rgba(0, 255, 255, 0.8);
        }

        .top-buttons button:hover {
            background: #0a0a0a;
            box-shadow: 0 0 20px cyan;
        }

        footer {
            position: absolute;
            bottom: 10px;
            left: 50%;
            transform: translateX(-50%);
            text-align: center;
            font-family: 'Fredoka', sans-serif;
            background: rgba(0, 0, 0, 0.6);
            padding: 10px 20px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
            width: max-content;
        }

        .footer-top {
            font-size: 16px;
            font-weight: 600;
            color: #00ffea;
            margin-bottom: 5px;
            transition: opacity 1s ease-in-out;
        }

        .footer-bottom {
            font-size: 14px;
            font-weight: 400;
            color: #cccccc;
        }

        .footer-powered {
            font-size: 13px;
            color: #888;
            margin-top: 3px;
        }

        .stars, .meteors, .shooting-stars {
            position: absolute;
            width: 100%;
            height: 100%;
            overflow: hidden;
        }

        .star {
            position: absolute;
            width: 2px;
            height: 2px;
            background: white;
            border-radius: 50%;
            animation: moveStar linear infinite;
        }

        @keyframes moveStar {
            0% { transform: translateY(0); opacity: 1; }
            100% { transform: translateY(100vh); opacity: 0; }
        }

        .shooting-star {
            position: absolute;
            width: 3px;
            height: 3px;
            background: white;
            box-shadow: 0 0 10px white;
            border-radius: 50%;
            animation: shootingStar linear 2s;
        }

        @keyframes shootingStar {
            0% { transform: translateX(100vw) translateY(-50px); opacity: 1; }
            100% { transform: translateX(-10vw) translateY(50vh); opacity: 0; }
        }

        .meteor {
            position: absolute;
            width: 15px;
            height: 15px;
            background: orange;
            box-shadow: 0 0 15px orange;
            border-radius: 50%;
            animation: meteorFall linear 3s;
        }

        @keyframes meteorFall {
            0% { transform: translateX(100vw) translateY(-10vh); opacity: 1; }
            100% { transform: translateX(-10vw) translateY(100vh); opacity: 0; }
        }

        .container {
            background: rgba(0, 0, 0, 0.85);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            width: 80%;
            max-width: 500px;
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.8);
            opacity: 0;
            transform: scale(0.8);
            transition: opacity 1s ease, transform 1s ease;
            position: relative;
            z-index: 10;
        }

        .show {
            opacity: 1;
            transform: scale(1);
        }

        h1 {
            font-size: 26px;
            margin-bottom: 10px;
            text-shadow: 0 0 10px cyan;
        }

        textarea {
            width: 100%;
            height: 150px;
            padding: 10px;
            background-color: #111;
            color: white;
            border: none;
            border-radius: 8px;
            resize: none;
            outline: none;
            font-size: 16px;
        }

        button {
            width: 100%;
            padding: 12px;
            margin-top: 10px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            background: linear-gradient(45deg, #00d2ff, #3a7bd5);
            color: white;
            border: none;
            border-radius: 8px;
            transition: 0.3s;
        }

        button:hover {
            background: linear-gradient(45deg, #3a7bd5, #00d2ff);
            box-shadow: 0 0 15px cyan;
        }

        #customNameContainer {
            display: none;
            margin-top: 10px;
        }

        #customNameBox {
            width: 100%;
            padding: 10px;
            background-color: #222;
            color: white;
            border: none;
            border-radius: 8px;
            outline: none;
            font-size: 16px;
            text-align: center;
        }

        #output {
            margin-top: 15px;
            font-size: 16px;
            font-weight: bold;
            color: #00ffea;
            word-wrap: break-word;
            white-space: pre-wrap;
            background: rgba(0, 0, 0, 0.85);
            padding: 10px;
            border-radius: 8px;
            display: none;
            box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
        }
    </style>
</head>
<body>

    <footer>
        <p class="footer-top" id="changingText">The safest way to secure your scripts</p>
        <p class="footer-bottom">Made by: Shinzou | Script Guardian created on March 23, 2025</p>
        <p class="footer-powered">Powered by Replit</p>
    </footer>

  <div class="stars"></div>
    <div class="meteors"></div>
    <div class="shooting-stars"></div>

    <div class="top-buttons">
        <button onclick="window.location.href='https://discord.gg/neBEfZvVpD'">Discord</button>
        <button>Obfuscation History [Soon]</button>
    </div>

    <div class="container" id="uiBox">
        <h1>Script Guardian</h1>
        <textarea id="scriptBox" placeholder="Enter Your Roblox Script Here!"></textarea>
        <button onclick="toggleCustomName()">Custom Name</button>
        <div id="customNameContainer">
            <input type="text" id="customNameBox" placeholder="Enter Custom Name Here!">
        </div>
        <button onclick="generateLink()">Generate</button>
        <p id="output"></p>
    </div>

    <script>
    setTimeout(() => {
        document.getElementById("uiBox")?.classList.add("show");
    }, 3000);

    const texts = [
        "✨ The Ultimate 🔒 Protection for Your Scripts! ✨",
        "🔧 Seamless Integration – Simply upload your script, click once, and get a secure, shareable link!",
        "🔒 Unmatched Security – Your scripts are safely stored.",
        "🚀 Lightning-Fast Performance – Our multi-server architecture guarantees flawless execution with a 0% error rate!"
    ];

    let index = 0;
    function changeText() {
        let textElement = document.getElementById("changingText");
        textElement.style.opacity = "0";
        setTimeout(() => {
            textElement.textContent = texts[index];
            textElement.style.opacity = "1";
            index = (index + 1) % texts.length;
        }, 1000);
    }
    setInterval(changeText, 10000);

    function toggleCustomName() {
        let container = document.getElementById("customNameContainer");
        container.style.display = container.style.display === "block" ? "none" : "block";
    }

    let isGenerating = false;
    let loadingInterval;

    document.addEventListener("DOMContentLoaded", () => {
        let savedLink = localStorage.getItem("generatedLink");
        let outputBox = document.getElementById("output");
        if (savedLink) {
            outputBox.innerHTML = `Link generated:<br>loadstring(game:HttpGet("${savedLink}"))()`;
            outputBox.style.display = "block";
        }

        // Handle suspension on load
        const bannedUntil = localStorage.getItem("bannedUntil");
        if (bannedUntil && Date.now() < parseInt(bannedUntil)) {
            disableButtonForBan();
        }
    });

    async function checkProfanity(text) {
        try {
            let response = await fetch(`https://www.purgomalum.com/service/containsprofanity?text=${encodeURIComponent(text)}`);
            let isProfane = await response.text();
            return isProfane === "true";
        } catch (error) {
            console.error("Error checking profanity:", error);
            return false;
        }
    }

    async function generateLink() {
        if (isGenerating) return;

        const bannedUntil = localStorage.getItem("bannedUntil");
        if (bannedUntil && Date.now() < parseInt(bannedUntil)) return;

        let scriptContent = document.getElementById("scriptBox").value.trim();
        let customName = document.getElementById("customNameBox").value.trim();
        let outputBox = document.getElementById("output");
        let generateButton = document.querySelector('button[onclick="generateLink()"]');

        if (!scriptContent) {
            alert("Please enter a script.");
            return;
        }

        let isProfane = await checkProfanity(customName);
        if (isProfane) {
            alert("Inappropriate name detected! You are suspended for 1 day.");
            let bannedUntil = Date.now() + 86400000; // 1 day in ms
            localStorage.setItem("bannedUntil", bannedUntil.toString());
            disableButtonForBan();
            return;
        }

        isGenerating = true;
        generateButton.disabled = true;

        // Animate "Generating..." dots
        let dots = 1;
        generateButton.textContent = "Generating.";
        loadingInterval = setInterval(() => {
            dots = (dots % 3) + 1;
            generateButton.textContent = "Generating" + ".".repeat(dots);
        }, 500);

        try {
            let response = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ script: scriptContent, name: customName })
            });

            let data = await response.json();

            if (data.link) {
                outputBox.innerHTML = `Link generated:<br>loadstring(game:HttpGet("${data.link}"))()`;
                outputBox.style.display = "block";
                localStorage.setItem("generatedLink", data.link);
            } else {
                alert("Error generating link.");
            }
        } catch (error) {
            console.error('Error:', error);
            alert("An error occurred while generating.");
        }

        resetButton(generateButton);
    }

    function resetButton(button) {
        clearInterval(loadingInterval);
        isGenerating = false;
        button.disabled = false;
        button.textContent = "Generate";
    }

    function disableButtonForBan() {
        let button = document.querySelector('button[onclick="generateLink()"]');
        button.disabled = true;
        button.textContent = "Suspended: 1 Day";

        // Optional: recheck after time ends
        const checkBanInterval = setInterval(() => {
            let bannedUntil = localStorage.getItem("bannedUntil");
            if (!bannedUntil || Date.now() >= parseInt(bannedUntil)) {
                clearInterval(checkBanInterval);
                localStorage.removeItem("bannedUntil");
                button.disabled = false;
                button.textContent = "Generate";
            }
        }, 10000); // Check every 10 seconds
    }

    function createStars(count) {
        let starsContainer = document.querySelector(".stars");
        for (let i = 0; i < count; i++) {
            let star = document.createElement("div");
            star.classList.add("star");
            let size = Math.random() * 3 + 1;
            star.style.width = `${size}px`;
            star.style.height = `${size}px`;
            star.style.left = `${Math.random() * 100}vw`;
            star.style.top = `${Math.random() * 100}vh`;
            star.style.animationDuration = `${Math.random() * 5 + 5}s`;
            star.style.animationDelay = `${Math.random() * 5}s`;
            starsContainer.appendChild(star);
        }
    }

    function createMeteor() {
        let meteor = document.createElement("div");
        meteor.classList.add("meteor");
        meteor.style.left = `${Math.random() * 100}vw`;
        document.querySelector(".meteors").appendChild(meteor);
        setTimeout(() => meteor.remove(), 3000);
    }
    setInterval(createMeteor, 10000);

    function createShootingStar() {
        let star = document.createElement("div");
        star.classList.add("shooting-star");
        star.style.right = "0";
        star.style.top = `${Math.random() * 100}vh`;
        document.querySelector(".shooting-stars").appendChild(star);
        setTimeout(() => star.remove(), 2000);
    }
    setInterval(createShootingStar, 7000);

    createStars(150);
</script>
</body>
</html>
