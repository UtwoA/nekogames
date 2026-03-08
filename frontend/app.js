const modesEl = document.getElementById("modes");
const statusEl = document.getElementById("play-status");
const warningEl = document.getElementById("warning");
const debugEl = document.getElementById("debug");
const profileEl = document.getElementById("profile");

const tabs = document.querySelectorAll(".tab");
const panels = {
  play: document.getElementById("tab-play"),
  leaderboard: document.getElementById("tab-leaderboard"),
  profile: document.getElementById("tab-profile"),
};

let currentSessionId = null;
let debugSent = false;

function switchTab(tab) {
  tabs.forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tab));
  Object.entries(panels).forEach(([key, panel]) => {
    panel.classList.toggle("hidden", key !== tab);
  });
}

tabs.forEach((btn) => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));

function getInitData() {
  if (!window.Telegram || !window.Telegram.WebApp) {
    return null;
  }
  return window.Telegram.WebApp.initData;
}

function showDebugInfo(force = false) {
  const params = new URLSearchParams(window.location.search);
  if (!force && !params.has("debug")) {
    return;
  }
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  const info = {
    hasTelegram: Boolean(window.Telegram),
    hasWebApp: Boolean(tg),
    platform: tg ? tg.platform : null,
    version: tg ? tg.version : null,
    initDataLength: tg && tg.initData ? tg.initData.length : 0,
    initDataUnsafe: tg && tg.initDataUnsafe ? Object.keys(tg.initDataUnsafe) : [],
    location: window.location.href,
    userAgent: navigator.userAgent,
  };
  debugEl.textContent = JSON.stringify(info, null, 2);
  debugEl.classList.remove("hidden");
  if (tg && typeof tg.sendData === "function" && !debugSent) {
    tg.sendData(JSON.stringify({ type: "debug", info }));
    debugSent = true;
  }
}

async function api(path, options = {}) {
  const initData = getInitData();
  if (!initData) {
    throw new Error("INITDATA_MISSING");
  }
  const headers = options.headers || {};
  headers["Content-Type"] = "application/json";
  headers["X-Telegram-Init-Data"] = initData;
  const res = await fetch(`/api${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    const msg = text ? `${res.status} ${text}` : `HTTP_${res.status}`;
    throw new Error(msg);
  }
  return res.json();
}

async function loadProfile() {
  const user = await api("/me");
  profileEl.innerHTML = `
    <div><strong>ID:</strong> ${user.tg_id}</div>
    <div><strong>Username:</strong> ${user.username || "-"}</div>
    <div><strong>Имя:</strong> ${user.first_name || "-"}</div>
  `;
}

async function loadModes() {
  const modes = await api("/modes");
  modesEl.innerHTML = "";
  modes.forEach((mode) => {
    const btn = document.createElement("button");
    btn.className = "mode-btn";
    btn.innerHTML = `<strong>${mode.name}</strong>Шансов: ${mode.shots} бросков`;
    btn.addEventListener("click", () => startSession(mode.id, mode.shots));
    modesEl.appendChild(btn);
  });
}

async function startSession(modeId, shots) {
  statusEl.textContent = "Создаем сессию...";
  const session = await api("/sessions", {
    method: "POST",
    body: JSON.stringify({ mode_id: modeId }),
  });
  currentSessionId = session.id;
  statusEl.innerHTML = `
    Сессия создана (#${session.id}).
    Открой личные сообщения с ботом — сейчас придут ${shots} бросков.
    После этого вернись и нажми «Проверить результат».
    <div class="actions">
      <button id="check-result">Проверить результат</button>
    </div>
  `;
  document.getElementById("check-result").addEventListener("click", checkResult);
}

async function checkResult() {
  if (!currentSessionId) {
    statusEl.textContent = "Сначала начни игру.";
    return;
  }
  const session = await api(`/sessions/${currentSessionId}`);
  if (session.status === "pending" || session.status === "running") {
    statusEl.textContent = "Броски еще идут...";
    return;
  }
  const throwsText = session.throws
    .map((t) => `${t.shot_index}: ${t.dice_value} ${t.is_hit ? "✅" : "❌"}`)
    .join("<br>");
  statusEl.innerHTML = `
    Результат: ${session.status === "won" ? "победа" : "поражение"} (${session.hits}/${session.shots})
    <div class="muted" style="margin-top:8px;">${throwsText}</div>
  `;
}

async function init() {
  try {
    const initData = getInitData();
    if (!initData) {
      warningEl.textContent = "Открой приложение внутри Telegram, чтобы начать игру.";
      warningEl.classList.remove("hidden");
      showDebugInfo(true);
      return;
    }
    await loadProfile();
    await loadModes();
    showDebugInfo();
  } catch (err) {
    warningEl.textContent = `Ошибка загрузки: ${err.message}. Проверь, что бот активирован через /start.`;
    warningEl.classList.remove("hidden");
    showDebugInfo(true);
  }
}

init();
