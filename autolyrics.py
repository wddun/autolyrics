import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

SONGS_FOLDER = "songs"
current_lyrics = {
    "song_name": None,
    "lyrics": [],
    "index": 0,
}


@app.route("/")
def index():
    """Client interface to view live lyrics."""
    return render_template("client.html")


@app.route("/admin")
def admin():
    """Admin interface to control lyrics."""
    return render_template("admin.html", songs=os.listdir(SONGS_FOLDER))


@app.route("/load_song", methods=["POST"])
def load_song():
    """Load a song's lyrics."""
    song_name = request.json.get("song_name")
    if not song_name:
        return jsonify({"error": "No song name provided"}), 400
    
    song_path = os.path.join(SONGS_FOLDER, song_name)
    if not os.path.exists(song_path):
        return jsonify({"error": "Song not found"}), 404

    with open(song_path, "r") as file:
        lyrics = file.readlines()

    current_lyrics["song_name"] = song_name
    current_lyrics["lyrics"] = [line.strip() for line in lyrics]
    
    # Allow starting from a specific index if provided
    start_index = request.json.get("start_index", 0)
    current_lyrics["index"] = min(start_index, len(current_lyrics["lyrics"]) - 1)

    send_lyrics_update()
    return jsonify({"message": "Song loaded successfully"})


@app.route("/next_lyric", methods=["POST"])
def next_lyric():
    """Move to the next lyric."""
    if current_lyrics["index"] < len(current_lyrics["lyrics"]) - 1:
        current_lyrics["index"] += 1
    send_lyrics_update()
    return jsonify({"message": "Next lyric sent"})


@app.route("/previous_lyric", methods=["POST"])
def previous_lyric():
    """Move to the previous lyric."""
    if current_lyrics["index"] > 0:
        current_lyrics["index"] -= 1
    send_lyrics_update()
    return jsonify({"message": "Previous lyric sent"})


@app.route("/custom_message", methods=["POST"])
def custom_message():
    """Send a custom message."""
    message = request.json.get("message", "")
    socketio.emit("custom_message", {"message": message})
    return jsonify({"message": "Custom message sent"})


def send_lyrics_update():
    """Emit current and next lyrics to clients."""
    update_data = {
        "current": current_lyrics["lyrics"][current_lyrics["index"]],
        "next": current_lyrics["lyrics"][current_lyrics["index"] + 1]
        if current_lyrics["index"] + 1 < len(current_lyrics["lyrics"])
        else "",
        "all_lyrics": current_lyrics["lyrics"],
        "current_index": current_lyrics["index"]
    }
    socketio.emit("update_lyrics", update_data)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=80)