# PokeHints Web Application

PokeHints is a multiplayer Python/Flask web guessing and clue-giving game built around Pokémon data—covering Pokémon, items, and characters—designed to test franchise knowledge in an interactive setting.

## Motivation

* Built an interactive multiplayer game for the community to enjoy, inspired by ZaneGames' Hint Game.
* Pulls together a broad catalog of Pokémon, items, and characters across the franchise.
* Uses structured environment/game logic to manage rules and turn-to-turn player interactions.

## Project Structure

* `app.py` — Main Flask application entry point and routes.
* `generate_data.py` — Script used to generate/update `pokemon_data.json`.
* `pokemon_data.json` — Local dataset of franchise entries used by the game.
* `PokeHint/` — Core game logic and helper modules.
* `templates/` & `static/` — HTML templates, styling, client scripts, and assets (including custom audio).

## Features

* **Multiplayer Lobbies:** Join a public lobby or host a private game with friends (up to 4 players in normal mode and 3 players in custom mode).
* **Customizable Profiles & Avatars:** Create a profile and pick trainer avatars.
* **Rich Franchise Data:** Clues and guessing rounds draw from Pokémon, items, and characters (with Bulbapedia reference integration).
* **Original Audio:** Includes self-composed background music tracks created for the game.

## Quick Start

### 1. Clone the repository

```bash
git clone [https://github.com/dylan2fuchs-max/PokeHints.git](https://github.com/dylan2fuchs-max/PokeHints.git)
cd PokeHints
