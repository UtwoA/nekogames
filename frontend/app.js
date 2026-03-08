const statusEl = document.getElementById("status");
const btn = document.getElementById("ping");

async function check() {
  statusEl.textContent = "Проверяем...";
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    statusEl.textContent = `API: ${data.status}`;
  } catch (err) {
    statusEl.textContent = "API недоступен";
  }
}

btn.addEventListener("click", check);
check();
