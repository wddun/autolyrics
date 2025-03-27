import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
socketio = SocketIO(app)

SONGS_FOLDER = "songs"
rooms = {}  # Dictionary to store room-specific data

def get_room_data(room_name):
    """Get or create room data."""
    if room_name not in rooms:
        rooms[room_name] = {
            "song_name": None,
            "lyrics": [],
            "index": 0,
        }
    return rooms[room_name]

@app.route("/")
def index():
    """Redirect to room selection for viewer."""
    return render_template("room_select.html", is_admin=False)

@app.route("/admin")
def admin():
    """Redirect to room selection for admin."""
    return render_template("room_select.html", is_admin=True)

@app.route("/<room_name>")
def viewer_room(room_name):
    """Client interface to view live lyrics."""
    return render_template("client.html", room_name=room_name)

@app.route("/admin/<room_name>")
def admin_room(room_name):
    """Admin interface to control lyrics."""
    return render_template("admin.html", songs=os.listdir(SONGS_FOLDER), room_name=room_name)

@app.route("/load_song", methods=["POST"])
def load_song():
    """Load a song's lyrics."""
    song_name = request.json.get("song_name")
    room_name = request.json.get("room_name")
    if not song_name or not room_name:
        return jsonify({"error": "Missing song name or room name"}), 400
    
    song_path = os.path.join(SONGS_FOLDER, song_name)
    if not os.path.exists(song_path):
        return jsonify({"error": "Song not found"}), 404

    with open(song_path, "r") as file:
        lyrics = file.readlines()

    room_data = get_room_data(room_name)
    room_data["song_name"] = song_name
    room_data["lyrics"] = [line.strip() for line in lyrics]
    
    # Allow starting from a specific index if provided
    start_index = request.json.get("start_index", 0)
    room_data["index"] = min(start_index, len(room_data["lyrics"]) - 1)

    send_lyrics_update(room_name)
    return jsonify({"message": "Song loaded successfully"})

@app.route("/next_lyric", methods=["POST"])
def next_lyric():
    """Move to the next lyric."""
    room_name = request.json.get("room_name")
    if not room_name:
        return jsonify({"error": "Missing room name"}), 400

    room_data = get_room_data(room_name)
    if room_data["index"] < len(room_data["lyrics"]) - 1:
        room_data["index"] += 1
    send_lyrics_update(room_name)
    return jsonify({"message": "Next lyric sent"})

@app.route("/previous_lyric", methods=["POST"])
def previous_lyric():
    """Move to the previous lyric."""
    room_name = request.json.get("room_name")
    if not room_name:
        return jsonify({"error": "Missing room name"}), 400

    room_data = get_room_data(room_name)
    if room_data["index"] > 0:
        room_data["index"] -= 1
    send_lyrics_update(room_name)
    return jsonify({"message": "Previous lyric sent"})

@app.route("/custom_message", methods=["POST"])
def custom_message():
    """Send a custom message."""
    message = request.json.get("message", "")
    room_name = request.json.get("room_name")
    if not room_name:
        return jsonify({"error": "Missing room name"}), 400

    socketio.emit("custom_message", {"message": message}, room=room_name)
    return jsonify({"message": "Custom message sent"})

def send_lyrics_update(room_name):
    """Emit current and next lyrics to clients."""
    room_data = get_room_data(room_name)
    update_data = {
        "current": room_data["lyrics"][room_data["index"]],
        "next": room_data["lyrics"][room_data["index"] + 1]
        if room_data["index"] + 1 < len(room_data["lyrics"])
        else "",
        "all_lyrics": room_data["lyrics"],
        "current_index": room_data["index"]
    }
    socketio.emit("update_lyrics", update_data, room=room_name)

@socketio.on('join')
def on_join(data):
    """Handle client joining a room."""
    room_name = data['room_name']
    join_room(room_name)
    
    # Send current lyrics state to the new client
    room_data = get_room_data(room_name)
    if room_data["lyrics"]:  # Only send if there are lyrics loaded
        send_lyrics_update(room_name)
    
    emit('status', {'msg': f'Joined room {room_name}'}, room=room_name)

@socketio.on('leave')
def on_leave(data):
    """Handle client leaving a room."""
    room_name = data['room_name']
    leave_room(room_name)
    emit('status', {'msg': f'Left room {room_name}'}, room=room_name)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=80)