"""Flask server for DouZero Web assistant."""

from __future__ import annotations

import logging
import sys
import threading
import uuid
import webbrowser
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from .engine.parser import ParseError, action_to_text, parse_action_payload, parse_hand_payload, validate_cards_not_exceed_deck
from .engine.state import GameState, ValidationError
from .model_bridge import ModelBridgeError, ModelRegistry


HOST = "127.0.0.1"
PORT = 7860


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _bundle_root() -> Path:
    if _is_frozen():
        mei_root = getattr(sys, "_MEIPASS", None)
        if mei_root:
            return Path(mei_root)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _runtime_root() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


ROOT_DIR = _bundle_root()
CKPT_DIR = ROOT_DIR / "douzero_WP"
LOG_DIR = _runtime_root() / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    logfile = LOG_DIR / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(logfile, encoding="utf-8"), logging.StreamHandler()],
    )


setup_logging()
logger = logging.getLogger("douzero-web")

app = Flask(
    __name__,
    template_folder=str(ROOT_DIR / "app" / "templates"),
    static_folder=str(ROOT_DIR / "app" / "static"),
)

sessions: dict[str, GameState] = {}
models = ModelRegistry(CKPT_DIR)


def _json_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def _recommendation_payload(state: GameState) -> tuple[dict[str, Any] | None, str | None]:
    if not state.need_user_action():
        return None, None

    try:
        infoset = state.build_infoset_for_user()
        action = models.recommend(infoset)
        return {"text": action_to_text(action)}, None
    except ModelBridgeError as exc:
        logger.exception("Model recommendation failed: %s", exc)
        return None, str(exc)
    except Exception as exc:  # pragma: no cover - defensive runtime path
        logger.exception("Unexpected recommendation failure: %s", exc)
        return None, f"Recommendation failed: {exc}"


def _response_with_state(game_id: str, state: GameState):
    recommendation, recommendation_error = _recommendation_payload(state)
    payload = {
        "ok": True,
        "game_id": game_id,
        "state": state.snapshot(),
        "need_user_action": state.need_user_action(),
        "recommendation": recommendation,
        "recommendation_error": recommendation_error,
    }
    return jsonify(payload)


def _get_game_or_error(game_id: str) -> GameState:
    state = sessions.get(game_id)
    if state is None:
        raise ValidationError("Game not found or expired.")
    return state


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/game/start", methods=["POST"])
def start_game():
    try:
        body = request.get_json(force=True, silent=False) or {}
        role = body.get("role")
        my_hand = parse_hand_payload(body.get("my_hand"), "my_hand")
        landlord_cards = parse_hand_payload(body.get("landlord_cards"), "landlord_cards")
        input_mode = str(body.get("input_mode", "text"))

        validate_cards_not_exceed_deck(my_hand, "my_hand")
        validate_cards_not_exceed_deck(landlord_cards, "landlord_cards")
        combined = my_hand + landlord_cards
        validate_cards_not_exceed_deck(combined, "combined known cards")

        state = GameState.create(role, my_hand, landlord_cards)
        game_id = uuid.uuid4().hex
        sessions[game_id] = state
        logger.info("Game started: %s role=%s input_mode=%s", game_id, role, input_mode)
        return _response_with_state(game_id, state)
    except (ParseError, ValidationError) as exc:
        return _json_error(str(exc), status=400)
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to start game: %s", exc)
        return _json_error(f"Failed to start game: {exc}", status=500)


@app.route("/api/game/<game_id>/state", methods=["GET"])
def get_state(game_id: str):
    try:
        state = _get_game_or_error(game_id)
        return _response_with_state(game_id, state)
    except ValidationError as exc:
        return _json_error(str(exc), status=404)


@app.route("/api/game/<game_id>/action", methods=["POST"])
def submit_action(game_id: str):
    source_mode = "text"
    raw_action: Any = None
    try:
        state = _get_game_or_error(game_id)
        body = request.get_json(force=True, silent=False) or {}
        source_mode = str(body.get("source_mode", "text"))
        raw_action = body.get("action")
        action = parse_action_payload(raw_action)
        state.apply_action(action)
        logger.info(
            "Action game=%s actor=%s action=%s source_mode=%s",
            game_id,
            state.action_log[-1]["actor"] if state.action_log else "n/a",
            action_to_text(action),
            source_mode,
        )
        return _response_with_state(game_id, state)
    except (ParseError, ValidationError) as exc:
        state = sessions.get(game_id)
        recommendation, recommendation_error = _recommendation_payload(state) if state is not None else (None, None)
        logger.warning(
            "Invalid action game=%s source_mode=%s action=%r error=%s",
            game_id,
            source_mode,
            raw_action,
            exc,
        )
        response = {
            "ok": False,
            "validation_error": str(exc),
            "state": state.snapshot() if state else None,
            "recommendation": recommendation,
            "recommendation_error": recommendation_error,
        }
        return jsonify(response), 400
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to apply action game=%s: %s", game_id, exc)
        return _json_error(f"Failed to apply action: {exc}", status=500)


@app.route("/api/game/<game_id>/undo", methods=["POST"])
def undo_action(game_id: str):
    try:
        state = _get_game_or_error(game_id)
        state.undo()
        logger.info("Undo game=%s", game_id)
        return _response_with_state(game_id, state)
    except ValidationError as exc:
        return _json_error(str(exc), status=400)
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to undo game=%s: %s", game_id, exc)
        return _json_error(f"Failed to undo: {exc}", status=500)


def run_server(auto_open_browser: bool = False) -> None:
    if auto_open_browser:
        url = f"http://{HOST}:{PORT}"

        def _open_browser() -> None:
            webbrowser.open(url)

        timer = threading.Timer(1.0, _open_browser)
        timer.daemon = True
        timer.start()

    logger.info("Starting server on http://%s:%s", HOST, PORT)
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    run_server(auto_open_browser=False)
