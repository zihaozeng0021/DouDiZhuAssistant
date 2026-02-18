const RANKS = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2", "X", "D"];

let gameId = null;
let currentState = null;
let currentRecommendation = null;
const clickCounts = Object.fromEntries(RANKS.map((rank) => [rank, 0]));

const messageBox = document.getElementById("message-box");
const gameCard = document.getElementById("game-card");
const setupCard = document.getElementById("setup-card");
const startForm = document.getElementById("start-form");
const historyList = document.getElementById("history-list");
const actionTextInput = document.getElementById("action-text-input");

function setMessage(message) {
  messageBox.textContent = message;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw data;
  }
  return data;
}

function activeInputMode() {
  const checked = document.querySelector('input[name="input-mode"]:checked');
  return checked ? checked.value : "text";
}

function syncInputModePanels() {
  const mode = activeInputMode();
  document.getElementById("text-input-panel").classList.toggle("hidden", mode !== "text");
  document.getElementById("click-input-panel").classList.toggle("hidden", mode !== "click");
}

function updateClickPreview() {
  const parts = [];
  for (const rank of RANKS) {
    for (let i = 0; i < clickCounts[rank]; i += 1) {
      parts.push(rank);
    }
  }
  document.getElementById("click-preview").textContent = parts.length ? parts.join("") : "PASS";
}

function resetClickCounts() {
  for (const rank of RANKS) {
    clickCounts[rank] = 0;
    const slot = document.querySelector(`[data-rank-count="${rank}"]`);
    if (slot) slot.textContent = "0";
  }
  updateClickPreview();
}

function buildRankGrid() {
  const container = document.getElementById("rank-grid");
  for (const rank of RANKS) {
    const cell = document.createElement("div");
    cell.className = "rank-cell";

    const value = document.createElement("div");
    value.className = "value";
    value.textContent = rank;
    cell.appendChild(value);

    const counter = document.createElement("div");
    counter.className = "counter";

    const minusBtn = document.createElement("button");
    minusBtn.type = "button";
    minusBtn.textContent = "-";
    minusBtn.addEventListener("click", () => {
      if (clickCounts[rank] > 0) clickCounts[rank] -= 1;
      document.querySelector(`[data-rank-count="${rank}"]`).textContent = String(clickCounts[rank]);
      updateClickPreview();
    });

    const num = document.createElement("span");
    num.dataset.rankCount = rank;
    num.textContent = "0";

    const plusBtn = document.createElement("button");
    plusBtn.type = "button";
    plusBtn.textContent = "+";
    plusBtn.addEventListener("click", () => {
      clickCounts[rank] += 1;
      document.querySelector(`[data-rank-count="${rank}"]`).textContent = String(clickCounts[rank]);
      updateClickPreview();
    });

    counter.appendChild(minusBtn);
    counter.appendChild(num);
    counter.appendChild(plusBtn);
    cell.appendChild(counter);
    container.appendChild(cell);
  }
}

function renderStateEnvelope(envelope) {
  const state = envelope.state;
  currentState = state;
  currentRecommendation = envelope.recommendation ? envelope.recommendation.text : null;

  gameCard.classList.remove("hidden");
  document.getElementById("game-id").textContent = envelope.game_id;
  document.getElementById("acting-role").textContent = state.acting_role;
  document.getElementById("user-role").textContent = state.user_role;
  document.getElementById("bomb-num").textContent = String(state.bomb_num);
  document.getElementById("my-hand").textContent = state.my_hand_text;
  document.getElementById("three-landlord-cards").textContent = state.three_landlord_cards_text;
  document.getElementById("left-landlord").textContent = String(state.num_cards_left_dict.landlord);
  document.getElementById("left-landlord-down").textContent = String(state.num_cards_left_dict.landlord_down);
  document.getElementById("left-landlord-up").textContent = String(state.num_cards_left_dict.landlord_up);

  if (envelope.recommendation) {
    document.getElementById("recommend-text").textContent = envelope.recommendation.text;
  } else if (envelope.recommendation_error) {
    document.getElementById("recommend-text").textContent = `Unavailable: ${envelope.recommendation_error}`;
  } else {
    document.getElementById("recommend-text").textContent = "-";
  }

  const recommendBtn = document.getElementById("use-recommend-btn");
  recommendBtn.disabled = !(state.need_user_action && currentRecommendation);

  historyList.innerHTML = "";
  for (const item of state.action_log) {
    const li = document.createElement("li");
    li.textContent = `${item.step}. ${item.actor}: ${item.text}`;
    historyList.appendChild(li);
  }
  if (state.action_log.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No actions yet";
    historyList.appendChild(li);
  }

  if (state.game_over) {
    setMessage(`Game over. Winner: ${state.winner}`);
  } else if (state.need_user_action) {
    setMessage("Your turn.");
  } else {
    setMessage("Please input opponents' action.");
  }
}

async function postAction(action, sourceMode) {
  if (!gameId) {
    setMessage("Please start a game first.");
    return;
  }
  try {
    const data = await fetchJson(`/api/game/${gameId}/action`, {
      method: "POST",
      body: JSON.stringify({ action, source_mode: sourceMode }),
    });
    renderStateEnvelope(data);
    actionTextInput.value = "";
    resetClickCounts();
  } catch (err) {
    if (err && err.validation_error) {
      setMessage(`Invalid action: ${err.validation_error}`);
      if (err.state) {
        renderStateEnvelope({
          ok: true,
          game_id: gameId,
          state: err.state,
          recommendation: null,
          recommendation_error: null,
          need_user_action: err.state.need_user_action,
        });
      }
      return;
    }
    setMessage(`Submit failed: ${JSON.stringify(err)}`);
  }
}

startForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = {
      role: document.getElementById("role-select").value,
      my_hand: document.getElementById("my-hand-input").value.trim(),
      landlord_cards: document.getElementById("landlord-cards-input").value.trim(),
      input_mode: activeInputMode(),
    };
    const data = await fetchJson("/api/game/start", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    gameId = data.game_id;
    setupCard.classList.add("hidden");
    renderStateEnvelope(data);
  } catch (err) {
    setMessage(`Start failed: ${err.error || JSON.stringify(err)}`);
  }
});

document.querySelectorAll('input[name="input-mode"]').forEach((node) => {
  node.addEventListener("change", syncInputModePanels);
});

document.getElementById("submit-action-btn").addEventListener("click", async () => {
  if (activeInputMode() === "text") {
    const raw = actionTextInput.value.trim();
    if (!raw) {
      setMessage("Enter an action, or click PASS.");
      return;
    }
    await postAction(raw, "text");
  } else {
    await postAction({ counts: clickCounts }, "click");
  }
});

document.getElementById("pass-btn").addEventListener("click", async () => {
  await postAction("PASS", activeInputMode());
});

document.getElementById("use-recommend-btn").addEventListener("click", async () => {
  if (!currentRecommendation) {
    setMessage("No recommendation available.");
    return;
  }
  await postAction(currentRecommendation, "recommend");
});

document.getElementById("undo-btn").addEventListener("click", async () => {
  if (!gameId) {
    setMessage("Please start a game first.");
    return;
  }
  try {
    const data = await fetchJson(`/api/game/${gameId}/undo`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    renderStateEnvelope(data);
  } catch (err) {
    setMessage(`Undo failed: ${err.error || JSON.stringify(err)}`);
  }
});

document.getElementById("restart-config-btn").addEventListener("click", () => {
  gameId = null;
  currentState = null;
  currentRecommendation = null;
  actionTextInput.value = "";
  resetClickCounts();
  gameCard.classList.add("hidden");
  setupCard.classList.remove("hidden");
  setMessage("请重新配置开局信息。");
});

document.getElementById("clear-click-btn").addEventListener("click", resetClickCounts);

window.addEventListener("beforeunload", (event) => {
  if (currentState && !currentState.game_over) {
    event.preventDefault();
    event.returnValue = "";
  }
});

buildRankGrid();
syncInputModePanels();
updateClickPreview();
