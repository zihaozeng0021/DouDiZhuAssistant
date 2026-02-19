from app.engine.parser import parse_action_text
from app.engine.state import GameState
from app.server import app, sessions


def test_submit_action_validation_error_includes_recommendation(monkeypatch):
    game_id = "test_game_validation_error_includes_recommendation"
    state = GameState.create(
        "landlord",
        parse_action_text("33334444556678910J"),
        parse_action_text("QXD"),
    )
    sessions[game_id] = state

    def fake_recommendation_payload(_state):
        return {"text": "3"}, None

    monkeypatch.setattr("app.server._recommendation_payload", fake_recommendation_payload)

    try:
        client = app.test_client()
        response = client.post(
            f"/api/game/{game_id}/action",
            json={"action": "PASS", "source_mode": "text"},
        )
        data = response.get_json()

        assert response.status_code == 400
        assert data["ok"] is False
        assert data["recommendation"] == {"text": "3"}
        assert data["recommendation_error"] is None
        assert data["state"]["need_user_action"] is True
    finally:
        sessions.pop(game_id, None)
