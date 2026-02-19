const RANKS = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2", "X", "D"];
const ROLE_LABELS = {
  landlord: "地主",
  landlord_down: "下家农民",
  landlord_up: "上家农民",
  farmer: "农民",
};
const ERROR_TEXT_MAP = [
  ["Game not found or expired.", "对局不存在或已过期。"],
  ["Failed to start game", "开局失败"],
  ["Recommendation failed", "推荐失败"],
  ["my_hand", "手牌"],
  ["landlord_cards", "底牌"],
  ["combined known cards", "已知牌组合"],
];

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

function localizeText(text, fallback = "") {
  if (text === null || text === undefined || text === "") {
    return fallback;
  }
  let localized = String(text)
    .replaceAll("landlord_down", "下家农民")
    .replaceAll("landlord_up", "上家农民")
    .replaceAll("landlord", "地主");
  for (const [source, target] of ERROR_TEXT_MAP) {
    localized = localized.replaceAll(source, target);
  }

  const latinWithoutPass = localized.replace(/PASS/g, "");
  if (/[A-Za-z]/.test(latinWithoutPass)) {
    return fallback;
  }
  return localized;
}

function toRoleLabel(role) {
  if (!role) {
    return "-";
  }
  return ROLE_LABELS[role] || localizeText(role, "未知");
}

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

function renderStateEnvelope(envelope, options = {}) {
  const preserveMessage = Boolean(options.preserveMessage);
  const state = envelope.state;
  currentState = state;
  if (Object.prototype.hasOwnProperty.call(envelope, "recommendation")) {
    currentRecommendation = envelope.recommendation ? envelope.recommendation.text : null;
  }

  gameCard.classList.remove("hidden");
  document.getElementById("acting-role").textContent = toRoleLabel(state.acting_role);
  document.getElementById("user-role").textContent = toRoleLabel(state.user_role);
  document.getElementById("bomb-num").textContent = String(state.bomb_num);
  document.getElementById("my-hand").textContent = state.my_hand_text;
  document.getElementById("three-landlord-cards").textContent = state.three_landlord_cards_text;
  document.getElementById("left-landlord").textContent = String(state.num_cards_left_dict.landlord);
  document.getElementById("left-landlord-down").textContent = String(state.num_cards_left_dict.landlord_down);
  document.getElementById("left-landlord-up").textContent = String(state.num_cards_left_dict.landlord_up);

  if (envelope.recommendation) {
    document.getElementById("recommend-text").textContent = envelope.recommendation.text;
  } else if (envelope.recommendation_error) {
    document.getElementById("recommend-text").textContent = localizeText(envelope.recommendation_error, "推荐暂不可用");
  } else {
    document.getElementById("recommend-text").textContent = "-";
  }

  const recommendBtn = document.getElementById("use-recommend-btn");
  recommendBtn.disabled = !(state.need_user_action && currentRecommendation);

  historyList.innerHTML = "";
  for (const item of state.action_log) {
    const li = document.createElement("li");
    li.textContent = `${item.step}. ${toRoleLabel(item.actor)}：${item.text}`;
    historyList.appendChild(li);
  }
  if (state.action_log.length === 0) {
    const li = document.createElement("li");
    li.textContent = "暂无出牌记录";
    historyList.appendChild(li);
  }

  if (!preserveMessage) {
    if (state.game_over) {
      setMessage(`对局结束，胜方：${toRoleLabel(state.winner)}`);
    } else if (state.need_user_action) {
      setMessage("轮到你出牌。");
    } else {
      setMessage("请录入对手动作。");
    }
  }
}

async function postAction(action, sourceMode) {
  if (!gameId) {
    setMessage("请先开始对局。");
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
      if (err.state) {
        renderStateEnvelope({
          ok: true,
          game_id: gameId,
          state: err.state,
          recommendation: err.recommendation,
          recommendation_error: err.recommendation_error,
          need_user_action: err.state.need_user_action,
        }, { preserveMessage: true });
      }
      const detail = localizeText(err.validation_error);
      setMessage(detail ? `动作不合法：${detail}` : "动作不合法，请检查后重试。");
      return;
    }
    setMessage("提交失败，请稍后重试。");
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
    const detail = localizeText(err && err.error);
    setMessage(detail ? `开局失败：${detail}` : "开局失败，请检查输入后重试。");
  }
});

document.querySelectorAll('input[name="input-mode"]').forEach((node) => {
  node.addEventListener("change", syncInputModePanels);
});

document.getElementById("submit-action-btn").addEventListener("click", async () => {
  if (activeInputMode() === "text") {
    const raw = actionTextInput.value.trim();
    if (!raw) {
      setMessage("请输入动作，或点击 PASS。");
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
    setMessage("当前没有可用推荐。");
    return;
  }
  await postAction(currentRecommendation, "recommend");
});

document.getElementById("undo-btn").addEventListener("click", async () => {
  if (!gameId) {
    setMessage("请先开始对局。");
    return;
  }
  try {
    const data = await fetchJson(`/api/game/${gameId}/undo`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    renderStateEnvelope(data);
  } catch (err) {
    const detail = localizeText(err && err.error);
    setMessage(detail ? `撤销失败：${detail}` : "撤销失败，请稍后重试。");
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
