const BLACK = 1;
const WHITE = -1;

const elements = {
  board: document.getElementById("board"),
  headline: document.getElementById("headline"),
  message: document.getElementById("message"),
  meta: document.getElementById("meta"),
  score: document.getElementById("score"),
  size: document.getElementById("size"),
  mode: document.getElementById("mode"),
  ruleset: document.getElementById("ruleset"),
  komi: document.getElementById("komi"),
  humanColor: document.getElementById("human-color"),
  newGame: document.getElementById("new-game"),
  pass: document.getElementById("pass"),
  undo: document.getElementById("undo"),
  resumePlay: document.getElementById("resume-play"),
  finalizeScoring: document.getElementById("finalize-scoring"),
  resign: document.getElementById("resign"),
};

const ctx = elements.board.getContext("2d");
let state = null;

function playerLabel(player) {
  return player === BLACK ? "黒" : "白";
}

function starPoints(size) {
  if (size === 9) return [2, 4, 6];
  if (size === 13) return [3, 6, 9];
  return [3, 9, 15];
}

function drawBoard() {
  if (!state) return;
  const size = state.size;
  const width = elements.board.width;
  const margin = 56;
  const step = (width - margin * 2) / (size - 1);

  ctx.clearRect(0, 0, width, width);
  const gradient = ctx.createLinearGradient(0, 0, width, width);
  gradient.addColorStop(0, "#d6a85b");
  gradient.addColorStop(1, "#bc7f2d");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, width);

  ctx.strokeStyle = "#533313";
  ctx.lineWidth = 2;
  for (let i = 0; i < size; i += 1) {
    const offset = margin + i * step;
    ctx.beginPath();
    ctx.moveTo(margin, offset);
    ctx.lineTo(width - margin, offset);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(offset, margin);
    ctx.lineTo(offset, width - margin);
    ctx.stroke();
  }

  const stars = starPoints(size);
  const points = new Set();
  points.add(`${stars[0]},${stars[0]}`);
  points.add(`${stars[0]},${stars[stars.length - 1]}`);
  points.add(`${stars[stars.length - 1]},${stars[0]}`);
  points.add(`${stars[stars.length - 1]},${stars[stars.length - 1]}`);
  points.add(`${stars[1]},${stars[1]}`);
  if (size >= 13) {
    points.add(`${stars[0]},${stars[1]}`);
    points.add(`${stars[1]},${stars[0]}`);
    points.add(`${stars[1]},${stars[stars.length - 1]}`);
    points.add(`${stars[stars.length - 1]},${stars[1]}`);
  }

  points.forEach((entry) => {
    const [x, y] = entry.split(",").map(Number);
    const px = margin + x * step;
    const py = margin + y * step;
    ctx.fillStyle = "#533313";
    ctx.beginPath();
    ctx.arc(px, py, 5, 0, Math.PI * 2);
    ctx.fill();
  });

  state.board.forEach((row, y) => {
    row.forEach((stone, x) => {
      if (stone === 0) return;
      const px = margin + x * step;
      const py = margin + y * step;
      const radius = step * 0.42;
      const stoneGradient = ctx.createRadialGradient(px - radius * 0.3, py - radius * 0.4, radius * 0.2, px, py, radius);
      if (stone === BLACK) {
        stoneGradient.addColorStop(0, "#707070");
        stoneGradient.addColorStop(1, "#111111");
      } else {
        stoneGradient.addColorStop(0, "#ffffff");
        stoneGradient.addColorStop(1, "#d8d3ca");
      }
      ctx.fillStyle = stoneGradient;
      ctx.beginPath();
      ctx.arc(px, py, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = stone === BLACK ? "#000000" : "#aaa195";
      ctx.lineWidth = 2;
      ctx.stroke();
    });
  });

  if (state.marked_dead) {
    state.marked_dead.forEach(([x, y]) => {
      const px = margin + x * step;
      const py = margin + y * step;
      ctx.strokeStyle = "#cf2f1e";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(px - 10, py - 10);
      ctx.lineTo(px + 10, py + 10);
      ctx.moveTo(px + 10, py - 10);
      ctx.lineTo(px - 10, py + 10);
      ctx.stroke();
    });
  }

  if (state.last_move && Number.isInteger(state.last_move[0])) {
    const [x, y] = state.last_move;
    const px = margin + x * step;
    const py = margin + y * step;
    ctx.strokeStyle = "#ec3d25";
    ctx.lineWidth = 2;
    ctx.strokeRect(px - 7, py - 7, 14, 14);
  }
}

function renderState(nextState) {
  state = nextState;
  elements.headline.textContent = state.headline;
  elements.message.textContent = state.message;
  elements.size.value = String(state.size);
  elements.mode.value = state.mode;
  elements.ruleset.value = state.ruleset;
  elements.komi.value = state.komi;
  elements.humanColor.value = String(state.human_color);

  elements.meta.innerHTML = `
    <div>手番</div><strong>${playerLabel(state.turn)}</strong>
    <div>手数</div><strong>${state.move_number}</strong>
    <div>黒アゲハマ</div><strong>${state.captures[BLACK]}</strong>
    <div>白アゲハマ</div><strong>${state.captures[WHITE]}</strong>
    <div>ルール</div><strong>${state.rules_label}</strong>
    <div>コミ</div><strong>${state.komi}</strong>
  `;

  elements.score.innerHTML = `
    <div>黒地</div><strong>${state.score.black_territory}</strong>
    <div>白地</div><strong>${state.score.white_territory}</strong>
    <div>黒の石数</div><strong>${state.score.black_stones}</strong>
    <div>白の石数</div><strong>${state.score.white_stones}</strong>
    <div>黒の死石</div><strong>${state.score.dead_black}</strong>
    <div>白の死石</div><strong>${state.score.dead_white}</strong>
    <div>黒アゲハマ</div><strong>${state.score.captures_black}</strong>
    <div>白アゲハマ</div><strong>${state.score.captures_white}</strong>
    <div>中立点</div><strong>${state.score.neutral_points}</strong>
    <div>黒スコア</div><strong>${state.score.black_score.toFixed(1)}</strong>
    <div>白スコア</div><strong>${state.score.white_score.toFixed(1)}</strong>
    <div>暫定勝者</div><strong>${playerLabel(state.score.winner)}</strong>
  `;

  elements.pass.disabled = state.scoring_mode;
  elements.resign.disabled = state.scoring_mode;
  elements.resumePlay.disabled = !state.scoring_mode;
  elements.finalizeScoring.disabled = !state.scoring_mode;

  drawBoard();
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  renderState(payload);
  if (!response.ok) {
    throw new Error(payload.message || "Request failed");
  }
  return payload;
}

function boardCoordinate(event) {
  if (!state || state.game_over) return null;
  const rect = elements.board.getBoundingClientRect();
  const scaleX = elements.board.width / rect.width;
  const scaleY = elements.board.height / rect.height;
  const x = (event.clientX - rect.left) * scaleX;
  const y = (event.clientY - rect.top) * scaleY;
  const margin = 56;
  const step = (elements.board.width - margin * 2) / (state.size - 1);
  const boardX = Math.round((x - margin) / step);
  const boardY = Math.round((y - margin) / step);
  if (boardX < 0 || boardX >= state.size || boardY < 0 || boardY >= state.size) return null;
  const px = margin + boardX * step;
  const py = margin + boardY * step;
  if (Math.abs(px - x) > step * 0.45 || Math.abs(py - y) > step * 0.45) return null;
  return { x: boardX, y: boardY };
}

elements.board.addEventListener("click", async (event) => {
  const move = boardCoordinate(event);
  if (!move) return;
  try {
    await requestJson("/api/play", {
      method: "POST",
      body: JSON.stringify(move),
    });
  } catch (error) {
    console.error(error);
  }
});

elements.newGame.addEventListener("click", async () => {
  try {
    await requestJson("/api/new-game", {
      method: "POST",
      body: JSON.stringify({
        size: Number(elements.size.value),
        mode: elements.mode.value,
        ruleset: elements.ruleset.value,
        komi: Number(elements.komi.value),
        human_color: Number(elements.humanColor.value),
      }),
    });
  } catch (error) {
    console.error(error);
  }
});

elements.pass.addEventListener("click", async () => {
  try {
    await requestJson("/api/pass", { method: "POST", body: "{}" });
  } catch (error) {
    console.error(error);
  }
});

elements.undo.addEventListener("click", async () => {
  try {
    await requestJson("/api/undo", { method: "POST", body: "{}" });
  } catch (error) {
    console.error(error);
  }
});

elements.resign.addEventListener("click", async () => {
  try {
    await requestJson("/api/resign", { method: "POST", body: "{}" });
  } catch (error) {
    console.error(error);
  }
});

elements.resumePlay.addEventListener("click", async () => {
  try {
    await requestJson("/api/resume-play", { method: "POST", body: "{}" });
  } catch (error) {
    console.error(error);
  }
});

elements.finalizeScoring.addEventListener("click", async () => {
  try {
    await requestJson("/api/finalize-scoring", { method: "POST", body: "{}" });
  } catch (error) {
    console.error(error);
  }
});

requestJson("/api/state").catch((error) => console.error(error));
