"""Bridge between GameState infoset and DouZero checkpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ModelBridgeError(RuntimeError):
    """Raised when model loading/inference fails."""


class ModelRegistry:
    """Lazy cache for landlord/landlord_up/landlord_down models."""

    def __init__(self, ckpt_root: str | Path):
        self.ckpt_root = Path(ckpt_root)
        self.ckpt_map = {
            "landlord": self.ckpt_root / "landlord.ckpt",
            "landlord_up": self.ckpt_root / "landlord_up.ckpt",
            "landlord_down": self.ckpt_root / "landlord_down.ckpt",
        }
        self.models: dict[str, Any] = {}
        self.device = None
        self.torch = None
        self._model_dict = None
        self._get_obs = None

    def _ensure_imports(self) -> None:
        if self.torch is not None:
            return

        try:
            import torch
            from douzero.dmc.models import model_dict
            from douzero.env.env import get_obs
        except Exception as exc:  # pragma: no cover - runtime dependency
            raise ModelBridgeError(
                "DouZero dependencies are missing. Please install requirements (`pip install -r requirements.txt`)."
            ) from exc

        self.torch = torch
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self._model_dict = model_dict
        self._get_obs = get_obs

    def _load_model(self, position: str):
        self._ensure_imports()
        ckpt = self.ckpt_map.get(position)
        if ckpt is None:
            raise ModelBridgeError(f"Unsupported position: {position}")
        if not ckpt.exists():
            raise ModelBridgeError(f"Checkpoint not found: {ckpt}")

        model = self._model_dict[position]()
        model_state_dict = model.state_dict()
        pretrained = self.torch.load(str(ckpt), map_location=self.device)
        pretrained = {key: value for key, value in pretrained.items() if key in model_state_dict}
        model_state_dict.update(pretrained)
        model.load_state_dict(model_state_dict)
        if self.device != "cpu":
            model.cuda()
        model.eval()
        return model

    def get(self, position: str):
        if position not in self.models:
            self.models[position] = self._load_model(position)
        return self.models[position]

    def recommend(self, infoset) -> list[int]:
        self._ensure_imports()
        legal_actions = infoset.legal_actions
        if not legal_actions:
            raise ModelBridgeError("No legal actions available.")
        if len(legal_actions) == 1:
            return legal_actions[0]

        model = self.get(infoset.player_position)
        obs = self._get_obs(infoset)

        z_batch = self.torch.from_numpy(obs["z_batch"]).float()
        x_batch = self.torch.from_numpy(obs["x_batch"]).float()
        if self.device != "cpu":
            z_batch = z_batch.cuda()
            x_batch = x_batch.cuda()

        with self.torch.no_grad():
            y_pred = model.forward(z_batch, x_batch, return_value=True)["values"]

        values = y_pred.detach().cpu().numpy()
        best_action_index = values.argmax(axis=0)[0]
        return legal_actions[int(best_action_index)]

