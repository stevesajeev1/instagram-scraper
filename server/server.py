from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room
import json

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
socketio = SocketIO(app)

with open('config.json') as f:
    accounts = json.load(f)['accounts']

retried = []

class State:
    def __init__(self):
        self.loaded = False
        self.current_account = None
        self.screenshot_ready = False
        self.screenshot_finished = False
        self.finished = False

states = {
    "posts": State(),
    "captions": State()
}

@app.before_request
def check_headers():
    if request.path.startswith("/accounts/"):
        return

    profile = request.headers.get("X-Profile")
    if profile not in states.keys():
        return f"X-Profile header is required and must be one of: {list(states.keys())}", 401

    if request.path != "/screenshot" and len(retried) != 0 and profile not in retried:
        retried.append(profile)

        if len(retried) == len(states):
            retried.clear()

        return "retry"


@app.route("/accounts/<profile>")
def render_accounts(profile):
    return render_template('accounts.html', accounts=accounts, profile=profile)

@socketio.on("join")
def on_join(profile: str):
    join_room(profile)

@socketio.on("load")
def handle_load(data):
    profile_state = states[data["profile"]]
    profile_state.loaded = True

@socketio.on("account")
def handle_account(data):
    profile_state = states[data["profile"]]
    profile_state.current_account = data["data"]

@socketio.on("screenshot_ready")
def handle_screenshot_ready(data):
    profile_state = states[data["profile"]]
    profile_state.screenshot_ready = True

@socketio.on("screenshot_finish")
def handle_screenshot_finish(data):
    profile_state = states[data["profile"]]
    profile_state.screenshot_finished = True

@socketio.on("finish")
def handle_finish(data):
    profile_state = states[data["profile"]]
    profile_state.finished = True

@app.route("/status")
def status():
    profile_state = states[request.headers.get("X-Profile")] # type: ignore

    if profile_state.loaded:
        profile_state.loaded = False
        return "true"
    return ""

@app.route("/info")
def info():
    profile_state = states[request.headers.get("X-Profile")] # type: ignore

    if profile_state.finished:
        profile_state.finished = False
        return "finish"
    if profile_state.current_account:
        account = profile_state.current_account
        profile_state.current_account = None
        return account
    return ""

@app.route("/ready")
def ready():
    profile_state = states[request.headers.get("X-Profile")] # type: ignore

    if profile_state.screenshot_finished:
        profile_state.screenshot_finished = False
        return "finish"
    if profile_state.screenshot_ready:
        profile_state.screenshot_ready = False
        return "ready"
    return ""

@app.route("/screenshot")
def screenshot():
    profile = request.headers.get("X-Profile")
    socketio.emit("screenshot", to=profile)
    return "ok"

@app.route("/retry")
def retry():
    profile = request.headers.get("X-Profile")
    profile_state = states[profile] # type: ignore

    profile_state.loaded = False
    profile_state.current_account = None
    profile_state.screenshot_ready = False
    profile_state.screenshot_finished = False
    profile_state.finished = False

    retried.append(profile)

    return ""


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)