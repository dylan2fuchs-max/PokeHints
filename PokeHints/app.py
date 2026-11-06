import json
import os
import random
import string
import uuid
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = (
    os.urandom(24) if "os" in globals() else "pokehints-super-secret-key"
)

# Load the master JSON database
DATA_FILE = os.path.join(os.path.dirname(__file__), "pokemon_data.json")

if os.path.exists(DATA_FILE):
  with open(DATA_FILE, "r", encoding="utf-8") as f:
    POKEMON_DATABASE = json.load(f)
    MASTER_POKEMON_DATABASE = (
        POKEMON_DATABASE.get("pokemon", [])
        + POKEMON_DATABASE.get("characters", [])
        + POKEMON_DATABASE.get("items", [])
        + POKEMON_DATABASE.get("locations", [])
        + POKEMON_DATABASE.get("games", [])
    )
else:
  MASTER_POKEMON_DATABASE = ["Krabby", "Dragonite", "Premier ball"]

# In-memory storage for lobbies
LOBBIES = {}
PUBLIC_QUEUE = []

def generate_lobby_code():
  """Generates a random 7-digit alphanumeric code for private lobbies."""
  characters = string.ascii_uppercase + string.digits
  return "".join(random.choices(characters, k=7))


def start_game_session(room, room_code):
    """Initializes the game when full: picks a random hinter and 10 target words with terminal logs."""
    players = room["players"]
    if not players:
        print(f"[GAME ERROR] Room {room_code} tried to start, but player list is empty!")
        return

    # Reset tracking flags for all players
    for p in players:
        p["has_been_hinter"] = False
        p["is_hinter"] = False

    ## Randomly pick exactly ONE hinter index
    hinter_idx = random.randint(0, len(players) - 1)
    players[hinter_idx]["is_hinter"] = True
    players[hinter_idx]["has_been_hinter"] = True
    hinter_name = players[hinter_idx]["name"]

    room["target_words"] = random.sample(
        MASTER_POKEMON_DATABASE, min(10, len(MASTER_POKEMON_DATABASE))
    )
    room["current_word_index"] = 0
    room["current_round"] = 1
    room["status"] = "in_game"

    print(f"\n========================================")
    print(f"🎮 GAME STARTED FOR ROOM: {room_code}")
    print(f"👑 Assigned Hinter: {hinter_name}")
    print(f"🕵️‍♂️ Guessers: {[p['name'] for p in players if not p['is_hinter']]}")
    print(f"🎯 Target Words Loaded: {len(room['target_words'])} words")
    print(f"========================================\n")

def rotate_hinter_or_advance_round(room):
    """Rotates to the next hinter who hasn't been one yet in this round cycle.
       If all players have been hinter, starts a new round or ends the game.
    """
    players = room["players"]
    
    # Reset current hinter flags
    for p in players:
        p["is_hinter"] = False

    # Find players who haven't been a hinter yet in this cycle
    eligible_players = [p for p in players if not p.get("has_been_hinter", False)]

    if eligible_players:
        # Pick the next hinter from eligible players
        next_hinter = random.choice(eligible_players)
        next_hinter["is_hinter"] = True
        next_hinter["has_been_hinter"] = True
        
        # Load new target words for the next hinter's turn
        room["target_words"] = random.sample(
            MASTER_POKEMON_DATABASE, min(10, len(MASTER_POKEMON_DATABASE))
        )
        room["current_word_index"] = 0
    else:
        # Everyone has been a hinter once this round! Check round limits.
        current_round = room.get("current_round", 1)
        max_rounds = room.get("rounds", 1)

        if current_round < max_rounds:
            # Advance to next round, reset hinter tracking for everyone, keep scores intact!
            room["current_round"] = current_round + 1
            for p in players:
                p["has_been_hinter"] = False
            
            # Pick the first new hinter for the new round
            first_hinter = random.choice(players)
            first_hinter["is_hinter"] = True
            first_hinter["has_been_hinter"] = True

            room["target_words"] = random.sample(
                MASTER_POKEMON_DATABASE, min(10, len(MASTER_POKEMON_DATABASE))
            )
            room["current_word_index"] = 0
        else:
            # Game Over - All rounds completed
            room["status"] = "game_over"

@app.route("/")
def index():
  """Main Menu: Choose from Public Lobby, Host Private, or Join Private."""
  return render_template("index.html")


@app.route("/lobby/public", methods=["POST"])
def join_public_lobby():
    """Handles matching players into public lobbies (4 players max per room)."""
    player_name = request.form.get("player_name", "Trainer")
    player_icon = request.form.get("player_icon", "default")
    player_id = str(uuid.uuid4())

    public_room_id = "PUBLIC_MAIN"
    if public_room_id not in LOBBIES:
        LOBBIES[public_room_id] = {
            "host": "Server",
            "players": [],
            "rounds": 1,
            "max_players": 4,
            "status": "waiting",
        }

    room = LOBBIES[public_room_id]
    print(f"\n[PUBLIC LOBBY] Player '{player_name}' attempting to join. Current count: {len(room['players'])}/{room['max_players']}")

    if len(room["players"]) < room["max_players"] and room["status"] == "waiting":
        player_data = {
            "id": player_id,
            "name": player_name,
            "icon": player_icon,
            "score": 0,
            "is_hinter": False,
            "has_been_hinter": False,
        }
        room["players"].append(player_data)
        session["room_code"] = public_room_id
        session["player_name"] = player_name
        session["player_id"] = player_id

        print(f"[PUBLIC LOBBY] Successfully added '{player_name}' (ID: {player_id[:8]}...). Total players: {len(room['players'])}")

        if len(room["players"]) == room["max_players"]:
            print(f"[PUBLIC LOBBY] Room {public_room_id} is full ({room['max_players']}/{room['max_players']}). Starting session...")
            start_game_session(room, public_room_id)

    return redirect(url_for("game_room", room_code=public_room_id))


@app.route("/lobby/host", methods=["GET", "POST"])
def host_private_lobby():
    """Allows a user to configure and host a private game lobby."""
    if request.method == "POST":
        custom_code = request.form.get("room_code", "").strip().upper()
        room_code = custom_code if custom_code else generate_lobby_code()

        max_players = int(request.form.get("max_players", 4))
        rounds = int(request.form.get("rounds", 1))
        host_name = request.form.get("player_name", "HostTrainer")
        player_icon = request.form.get("player_icon", "default")
        player_id = str(uuid.uuid4())

        # DEBUG: Print host setup parameters
        print(f"--- HOSTING PRIVATE LOBBY ({room_code}) ---")
        print(f"Max Players Set: {max_players} | Rounds: {rounds}")

        LOBBIES[room_code] = {
            "host": host_name,
            "players": [{
                "id": player_id,
                "name": host_name,
                "icon": player_icon,
                "score": 0,
                "is_hinter": False,
                "has_been_hinter": False,
            }],

            "rounds": rounds,
            "max_players": max_players,
            "status": "waiting",
        }

        session["room_code"] = room_code
        session["player_name"] = host_name
        session["player_id"] = player_id
        return redirect(url_for("game_room", room_code=room_code))

    return render_template("host_lobby.html")

@app.route("/lobby/join", methods=["POST"])
def join_private_lobby():
    """Allows a user to join an existing private lobby with detailed terminal logs."""
    room_code = request.form.get("room_code", "").strip().upper()
    player_name = request.form.get("player_name", "").strip() or "Trainer"
    player_icon = request.form.get("player_icon", "default")
    player_id = str(uuid.uuid4())

    print(f"\n[PRIVATE JOIN] Player '{player_name}' trying to join room '{room_code}'")

    if room_code not in LOBBIES:
        print(f"[PRIVATE JOIN ERROR] Room '{room_code}' not found!")
        return "Lobby not found! Please check the code and try again.", 404

    room = LOBBIES[room_code]
    print(f"[PRIVATE JOIN] Room found. Status: {room['status']} | Players: {len(room['players'])}/{room['max_players']}")

    if len(room["players"]) >= room["max_players"]:
        print(f"[PRIVATE JOIN ERROR] Room '{room_code}' is full!")
        return "Lobby is full!", 400

    if room["status"] != "waiting":
        print(f"[PRIVATE JOIN ERROR] Game in room '{room_code}' has already started!")
        return "Game has already started!", 400

    room["players"].append({
        "id": player_id,
        "name": player_name,
        "icon": player_icon,
        "score": 0,
        "is_hinter": False,
        "has_been_hinter": False,
    })

    session["room_code"] = room_code
    session["player_name"] = player_name
    session["player_id"] = player_id

    print(f"[PRIVATE JOIN] Successfully added '{player_name}' to '{room_code}'. Total players now: {len(room['players'])}/{room['max_players']}")

    if len(room["players"]) == room["max_players"]:
        print(f"[PRIVATE JOIN] Room '{room_code}' has reached max capacity! Triggering game start...")
        start_game_session(room, room_code)

    return redirect(url_for("game_room", room_code=room_code))

@app.route("/room/<room_code>/api/status")
def room_status(room_code):
    """API endpoint for client polling to sync player joins and game status."""
    if room_code not in LOBBIES:
        return jsonify({"error": "Room not found"}), 404

    room = LOBBIES[room_code]

    # WATCHDOG GUARD: If room is waiting but has reached max capacity, force start it right now!
    if room["status"] == "waiting" and len(room["players"]) >= room["max_players"]:
        print(f"[WATCHDOG] Room '{room_code}' is full ({len(room['players'])}/{room['max_players']}) but still waiting. Forcing game start!")
        start_game_session(room, room_code)

    return jsonify({
        "status": room["status"],
        "players": room["players"],
        "max_players": room["max_players"],
        "host": room.get("host"),
        "current_round": room.get("current_round", 1),
        "current_word_index": room.get("current_word_index", 0)
    })

@app.route("/room/<room_code>/guess", methods=["POST"])
def submit_guess(room_code):
    """Receives a player's guess, validates it against the active target word."""
    if room_code not in LOBBIES:
        return jsonify({"success": False, "error": "Room not found"}), 404

    room = LOBBIES[room_code]
    current_player_id = session.get("player_id")

    # Prevent the active Hinter from submitting guesses
    for player in room["players"]:
        if player.get("id") == current_player_id and player.get("is_hinter", False):
            return jsonify({"success": False, "error": "Hinters cannot submit guesses!"}), 400

    data = request.get_json() or {}
    guessed_word = data.get("guess", "").strip()

    if not guessed_word:
        return jsonify({"success": False, "error": "Empty guess"})

    # Find current target word
    target_words = room.get("target_words", [])
    current_idx = room.get("current_word_index", 0)

    if current_idx >= len(target_words):
        return jsonify(
            {"success": False, "error": "All words have been guessed!"}
        )

    active_target = target_words[current_idx]

    # Check if guess matches the active target word (case-insensitive)
    is_correct = guessed_word.lower() == active_target.lower()

    response_data = {
        "success": True,
        "correct": is_correct,
        "guess": guessed_word,
    }

    if is_correct:
        # Increment to the next target word
        room["current_word_index"] += 1
        response_data["next_word_index"] = room["current_word_index"]

        # Check if all 10 words are completed for this hinter's turn
        if room["current_word_index"] >= len(target_words):
            response_data["round_complete"] = True
            # Automatically rotate to the next hinter or advance round/end game
            rotate_hinter_or_advance_round(room)
            response_data["game_status"] = room["status"]

    return jsonify(response_data)


def game_room(room_code):
    if room_code not in LOBBIES:
        return redirect(url_for("index"))

    room = LOBBIES[room_code]
    current_player_id = session.get("player_id")

    is_hinter = False
    found_player = None

    # Find the player matching the session ID
    for player in room["players"]:
        if player.get("id") == current_player_id:
            found_player = player
            is_hinter = player.get("is_hinter", False)
            break

    # FALLBACK SAFETY: If session ID isn't found in the room (e.g. shared tab cross-contamination),
    # assign the visitor to the first player who isn't already claimed, or default to Guesser.
    if not found_player and room["players"]:
        # Default to the last joined player if session is missing
        found_player = room["players"][-1]
        session["player_id"] = found_player["id"]
        is_hinter = found_player.get("is_hinter", False)

    target_words = room.get("target_words", ["Waiting for players..."] * 10)

    return render_template(
        "room.html",
        room=room,
        room_code=room_code,
        is_hinter=is_hinter,
        target_words=target_words,
        valid_words=MASTER_POKEMON_DATABASE,
    )

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)