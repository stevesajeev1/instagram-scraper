from flask import Flask, render_template
from flask_socketio import SocketIO
import json

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
socketio = SocketIO(app)

with open('config.json') as f:
    accounts = json.load(f)['accounts']

loaded = False
current_account = None
screenshot_ready = False
screenshot_finished = False
finished = False

@app.route("/accounts")
def render_accounts():
    return render_template('accounts.html', accounts=accounts)

@socketio.on("load")
def handle_load():
    global loaded
    loaded = True

@socketio.on("account")
def handle_account(data: str):
    global current_account
    current_account = data

@socketio.on("screenshot_ready")
def handle_screenshot_ready():
    global screenshot_ready
    screenshot_ready = True

@socketio.on("screenshot_finish")
def handle_screenshot_finish():
    global screenshot_finished
    screenshot_finished = True

@socketio.on("finish")
def handle_finish():
    global finished
    finished = True

@app.route("/status")
def status():
    global loaded
    if loaded:
        loaded = False
        return "true"
    return "false"

@app.route("/info")
def info():
    global current_account, finished
    if finished:
        finished = False
        return "finish"
    if current_account:
        account = current_account
        current_account = None
        return account
    return ""

@app.route("/ready")
def ready():
    global screenshot_ready, screenshot_finished
    if screenshot_finished:
        screenshot_finished = False
        return "finish"
    if screenshot_ready:
        screenshot_ready = False
        return "ready"
    return ""

@app.route("/screenshot")
def screenshot():
    socketio.emit("screenshot")
    return "ok"


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)