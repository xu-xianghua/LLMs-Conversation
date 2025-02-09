from flask import Flask, render_template_string, request, jsonify
import requests
import threading
import time
import openai

app = Flask(__name__)

# Ollama API endpoints
OLLAMA_API_1 = "http://localhost:11434/api/chat"
model_1 = "qwen2.5:32b"
OLLAMA_API_2 = "http://localhost:11434/api/chat"
model_2 = "deepseek-r1:32b"

# openai-like api setting
api_url_1 = "https://integrate.api.nvidia.com/v1"
api_key_1 = "YOUR_API_KEY"
api_model_1 = "deepseek-ai/deepseek-r1"
api_client_1 = None

api_url_2 = "https://integrate.api.nvidia.com/v1"
api_key_2 = "YOUR_API_KEY"
api_model_2 = "deepseek-ai/deepseek-r1"
api_client_2 = None

# Global variables to control the conversation
conversation_active = False
conversation_history = []
stop_event = threading.Event()
conversation_lock = threading.Lock()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Conversation</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
            display: flex;
            flex-direction: row;
        }
        .container {
            width: 100%;
            display: flex;
            flex-direction: row;
        }
        .settings {
            width: 30%;
            padding: 20px;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            margin-right: 10px; 
        }
        .conversation {
            width: 60%;
            padding: 20px;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            margin-left: 10px;
        }
        .chat-box {
            min-height: 300px;
            max-height: calc(100vh - 150px);
            overflow-y: auto;
            border: 1px solid #ddd;
            margin-top: 20px;
            padding: 10px;
            border-radius: 5px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .message {
            display: flex;
            align-items: flex-start; 
            gap: 10px;
        }
        .message.me {
            flex-direction: row-reverse;
        }
        .message .username {
            font-weight: bold;
            padding: 5px 10px;
            border-radius: 10px;
        }
        .message .username.me {
            background-color: #007bff;
            color: white;
        }
        .message .username.other {
            background-color: #f0f0f0;
            color: black;
        }
        .message .text {
            padding: 10px;
            border-radius: 10px;
            max-width: 70%;
            word-wrap: break-word;
        }
        .message .text.me {
            background-color: #e0f7ff;
            color: black;
        }
        .message .text.other {
            background-color: #f0f0f0;
            color: black;
        }
        .controls {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
        }
        .controls button {
            padding: 10px 15px;
            margin-right: 5px;
            border: none;
            border-radius: 5px;
            background-color: #007bff;
            color: white;
            cursor: pointer;
        }
        .controls button:last-child {
            margin-right: 0;
        }
        .controls button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .user {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 10px;
        }
        .user label {
            flex: 1;
            margin-bottom: 5px;
        }
        .user input {
            flex: 2;
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .scene {
            margin-bottom: 10px;
        }
        .scene label {
            display: block;
            margin-bottom: 5px;
        }
        .scene textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            resize: vertical;
            font-size: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="settings">
            <h1>Settings</h1>
            <form id="settings-form">
                <div class="user">
                    <label for="model1-identity">角色1:</label>
                    <input type="text" id="model1-identity" name="model1_identity" value="孔子" required>
                    <label for="model1-type">模型:</label>
                    <select id="model1-type" name="model1_type">
                        <option value="ollama">Ollama</option>
                        <option value="openai">API</option>
                    </select>
                </div>
                <div class="user">
                    <label for="model2-identity">角色2:</label>
                    <input type="text" id="model2-identity" name="model2_identity" value="老子" required>
                    <label for="model2-type">模型:</label>
                    <select id="model2-type" name="model2_type">
                        <option value="ollama">Ollama</option>
                        <option value="openai">API</option>
                    </select>
                </div>
                <div class="scene">
                    <label for="scene">场景:</label>
                    <textarea id="scene" rows="4" name="scene">相传春秋时，孔子和老子有过一次相遇，他们聊了些什么呢？现在模拟他们当时的对话，你只需要说自己角色的对话，一人一句。对话10轮后，如果想结束谈话，则在对话的最后输出<end>标记。</textarea>
                </div>
            </form>
            <div class="controls">
                <button id="start-btn" onclick="startConversation()">Start</button>
                <button id="stop-btn" onclick="stopConversation()" disabled>Stop</button>
                <button id="clear-btn" onclick="clearConversation()">Clear</button>
            </div>
        </div>
        <div class="conversation">
            <h1>Conversation</h1>
            <div class="chat-box" id="chat-box"></div>
        </div>
    </div>

    <script>
        const chatBox = document.getElementById("chat-box");
        const startBtn = document.getElementById("start-btn");
        const stopBtn = document.getElementById("stop-btn");
        const clearBtn = document.getElementById("clear-btn");

        function updateChatBox() {
            fetch("/get_conversation")
                .then(response => response.json())
                .then(data => {
                    chatBox.innerHTML = "";
                    data.conversation.forEach((message, index) => {
                        const messageDiv = document.createElement("div");
                        messageDiv.classList.add("message");
                        if (index % 2 === 0) {
                            messageDiv.classList.add("other");
                        } else {
                            messageDiv.classList.add("me");
                        }
                        const username = document.createElement("div");
                        username.classList.add("username");
                        if (index % 2 === 0) {
                            username.classList.add("other");
                            username.textContent = document.getElementById("model1-identity").value;
                        } else {
                            username.classList.add("me");
                            username.textContent = document.getElementById("model2-identity").value;
                        }

                        const text = document.createElement("div");
                        text.classList.add("text");
                        if (index % 2 === 0) {
                            text.classList.add("other");
                        } else {
                            text.classList.add("me");
                        }
                        text.textContent = message;

                        messageDiv.appendChild(username);
                        messageDiv.appendChild(text);
                        chatBox.appendChild(messageDiv);
                    });

                    if (!data.active) {
                        startBtn.disabled = false;
                        stopBtn.disabled = true;
                        if (data.conversation.length > 0) {
                            const endMessage = document.createElement("div");
                            endMessage.classList.add("message", "other");
                            const endText = document.createElement("div");
                            endText.classList.add("text", "other");
                            endText.textContent = "对话已结束。";
                            endMessage.appendChild(endText);
                            chatBox.appendChild(endMessage);
                        }
                    }
                    // chatBox.scrollTop = chatBox.scrollHeight;
                });
        }

        function startConversation() {
            const model1Identity = document.getElementById("model1-identity").value;
            const model2Identity = document.getElementById("model2-identity").value;
            const model1Type = document.getElementById("model1-type").value;
            const model2Type = document.getElementById("model2-type").value;
            const scene = document.getElementById("scene").value;

            fetch("/start_conversation", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    model1_identity: model1Identity,
                    model2_identity: model2Identity,
                    model1_type: model1Type,
                    model2_type: model2Type,
                    scene: scene
                })
            }).then(() => {
                startBtn.disabled = true;
                stopBtn.disabled = false;
                updateChatBox();
            });
        }

        function stopConversation() {
            fetch("/stop_conversation", {
                method: "POST"
            }).then(() => {
                startBtn.disabled = false;
                stopBtn.disabled = true;
            });
        }

        function clearConversation() {
            fetch("/clear_conversation", {
                method: "POST"
            }).then(updateChatBox);
        }

        document.getElementById("settings-form").addEventListener("submit", function(event) {
            event.preventDefault();
            startConversation();
        });

        // Polling to update chat box in real-time
        setInterval(updateChatBox, 500);
    </script>
</body>
</html>
"""

def strip_think(response):
    """ strip the think part between <think> and </think> from the response """
    start = response.find("<think>")
    end = response.find("</think>")
    if start != -1 and end != -1:
        return response[:start] + response[end + len("</think>"):]
    return response

def generate_response_ollama(prompt, api_url, model):
    try:
        response = requests.post(api_url, json={"model": model, "messages": prompt, "stream": False}, stream=False)
        response.raise_for_status()
        response = response.json()["message"]["content"]
        response = strip_think(response)
        return response, True
    except requests.exceptions.RequestException as e:
        print(f"Ollama Error: {e}")
        return f"Error: Unable to generate response. Please check the Ollama server. Error: {e}", False

def generate_response_api(prompt, model, api_client):
    try:
        response = api_client.chat.completions.create(
            model=model,
            messages=prompt,
            stream = False
        )
        return strip_think(response.choices[0].message.content), True
    except Exception as e:
        print(f"API Error: {e}")
        return f"Error: Unable to generate response. Please check the API settings. Error: {e}", False

def start_conversation(model1_identity, model2_identity, scene, model1_type, model2_type):
    global conversation_active, conversation_history, api_client_1, api_client_2
    with conversation_lock:
        conversation_active = True
        conversation_history = []
        conversation_history_1 = [{"role": "user", "content": f"{scene} 你的角色是 {model1_identity}, 你将要和 {model2_identity} 开展一场对话。你先开始吧。"}]
        conversation_history_2 = [{"role": "user", "content": f"{scene} 你的角色是 {model2_identity}, 你将要和 {model1_identity} 开展一场对话。他先开口说话了。"}]
        end1, end2 = False, False
        if model1_type != "ollama":
            api_client_1 = openai.OpenAI(base_url=api_url_1, api_key=api_key_1)
        if model2_type != "ollama":
            api_client_2 = openai.OpenAI(base_url=api_url_2, api_key=api_key_2)

    while conversation_active and not stop_event.is_set():
        # Model 1 generates a response
        if model1_type == "ollama":
            response1, status = generate_response_ollama(conversation_history_1, OLLAMA_API_1, model_1)
        else:
            response1, status = generate_response_api(conversation_history_1, api_model_1, api_client_1)
        conversation_history.append(response1)
        if not status:
            break
        conversation_history_1.append({"role": "assistant", "content": response1})
        conversation_history_2.append({"role": "user", "content": response1})
        if "<end>" in response1:
            end1 = True
        if end1 and end2:
            break
        time.sleep(0.5)  # Simulate real-time response

        if stop_event.is_set():
            break

        # Model 2 generates a response
        if model2_type == "ollama":
            response2, status = generate_response_ollama(conversation_history_2, OLLAMA_API_2, model_2)
        else:
            response2, status = generate_response_api(conversation_history_2, api_model_2, api_client_2)
        conversation_history.append(response2)
        if not status:
            break
        conversation_history_2.append({"role": "assistant", "content": response2})
        conversation_history_1.append({"role": "user", "content": response2})
        if "<end>" in response2:
            end2 = True
        if end1 and end2:
            break
        time.sleep(0.5)  # Simulate real-time response

        if stop_event.is_set():
            break

    with conversation_lock:
        conversation_active = False
    stop_event.clear()

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/start_conversation", methods=["POST"])
def start_conversation_route():
    data = request.json
    model1_identity = data.get("model1_identity")
    model2_identity = data.get("model2_identity")
    scene = data.get("scene")
    model1_type = data.get("model1_type")
    model2_type = data.get("model2_type")

    thread = threading.Thread(target=start_conversation, args=(model1_identity, model2_identity, scene, model1_type, model2_type))
    thread.start()
    return jsonify({"status": "started"})

@app.route("/stop_conversation", methods=["POST"])
def stop_conversation_route():
    global conversation_active
    stop_event.set()
    return jsonify({"status": "stopped"})

@app.route("/clear_conversation", methods=["POST"])
def clear_conversation_route():
    global conversation_history
    with conversation_lock:
        conversation_history = []
    return jsonify({"status": "cleared"})

@app.route("/get_conversation", methods=["GET"])
def get_conversation():
    return jsonify({"conversation": conversation_history, "active": conversation_active})

if __name__ == "__main__":
    app.run(debug=True, port=5001)