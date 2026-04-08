const TASKS = {
  1: {
    label: "Easy",
    goal: "Find Reliance stock price",
    description: "Low-friction fact lookup with a generous wallet and a 0.40 confidence target.",
    startingBudget: 1.0,
    targetConfidence: 0.4,
  },
  2: {
    label: "Medium",
    goal: "Analyze HDFC Q3 revenue",
    description: "Balanced research task with tighter budget and a full-confidence finish line.",
    startingBudget: 0.6,
    targetConfidence: 1.0,
  },
  3: {
    label: "Hard",
    goal: "Verify Palantir dividend",
    description: "Tight budget, strict target, and almost no room for waste.",
    startingBudget: 0.25,
    targetConfidence: 1.0,
  },
};

const TOOLS = [
  {
    key: "SCRAPE",
    cost: 0.01,
    gain: 0.2,
    summary: "Cheap, noisy collection for early orientation and low-cost confidence.",
  },
  {
    key: "LLM_REASON",
    cost: 0.05,
    gain: 0.25,
    summary: "Structured reasoning pass for synthesis when context starts to form.",
  },
  {
    key: "SEARCH",
    cost: 0.1,
    gain: 0.4,
    summary: "High-value retrieval step with strong confidence lift per click.",
  },
  {
    key: "VERIFY",
    cost: 0.2,
    gain: 0.6,
    summary: "High-cost confirmation tool, gated until confidence reaches 0.50.",
  },
];

const state = {
  taskId: 1,
  budget: 1.0,
  startingBudget: 1.0,
  targetConfidence: 0.4,
  confidence: 0.0,
  stepCount: 0,
  episodeReturn: 0.0,
  graderScore: 0.0,
  done: false,
  terminationReason: "",
};

const els = {
  taskSelector: document.getElementById("task-selector"),
  resetButton: document.getElementById("resetButton"),
  taskTitle: document.getElementById("taskTitle"),
  taskDescription: document.getElementById("taskDescription"),
  statusBadge: document.getElementById("statusBadge"),
  episodeReturn: document.getElementById("episodeReturn"),
  targetConfidenceLabel: document.getElementById("targetConfidenceLabel"),
  budgetValue: document.getElementById("budgetValue"),
  budgetPercent: document.getElementById("budgetPercent"),
  budgetWarning: document.getElementById("budgetWarning"),
  walletCard: document.getElementById("walletCard"),
  confidenceValue: document.getElementById("confidenceValue"),
  confidenceFill: document.getElementById("confidenceFill"),
  targetMarker: document.getElementById("targetMarker"),
  targetLegend: document.getElementById("targetLegend"),
  stepCount: document.getElementById("stepCount"),
  graderScore: document.getElementById("graderScore"),
  toolGrid: document.getElementById("toolGrid"),
  logList: document.getElementById("logList"),
};

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatSigned(value) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}

function nowTime() {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function addLog(message, tone = "system") {
  const item = document.createElement("article");
  item.className = `log-item ${tone}`;
  item.innerHTML = `
    <div class="log-topline">
      <span>${nowTime()}</span>
      <span>${tone.toUpperCase()}</span>
    </div>
    <div class="log-message">${message}</div>
  `;
  els.logList.prepend(item);
}

function taskForCurrentState() {
  return TASKS[state.taskId];
}

function toolEnabled(tool) {
  if (state.done) {
    return false;
  }
  if (state.budget < tool.cost) {
    return false;
  }
  if (tool.key === "VERIFY" && state.confidence < 0.5) {
    return false;
  }
  return true;
}

function toolReason(tool) {
  if (state.done) {
    return "Episode completed";
  }
  if (state.budget < tool.cost) {
    return "Insufficient budget";
  }
  if (tool.key === "VERIFY" && state.confidence < 0.5) {
    return "Locked until confidence 0.50";
  }
  return "Available now";
}

function renderTools() {
  els.toolGrid.innerHTML = "";

  TOOLS.forEach((tool) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `tool-card ${toolEnabled(tool) ? "" : "disabled"}`;
    card.disabled = !toolEnabled(tool);
    const lockLabel =
      tool.key === "VERIFY" && state.confidence < 0.5
        ? `<div class="tool-lock">Locked until 0.50 confidence</div>`
        : "";

    card.innerHTML = `
      <span class="tool-badge">${tool.key}</span>
      <h4>${tool.key.replace("_", " ")}</h4>
      <p>${tool.summary}</p>
      <div class="tool-meta">
        <span>Cost ${formatCurrency(tool.cost)}</span>
        <span>Gain +${tool.gain.toFixed(2)}</span>
      </div>
      ${lockLabel}
      <div class="tool-action">${toolReason(tool)}</div>
    `;

    card.addEventListener("click", () => runStep(tool));
    els.toolGrid.appendChild(card);
  });
}

function updateStatus() {
  const task = taskForCurrentState();
  const budgetRatio = state.startingBudget === 0 ? 0 : state.budget / state.startingBudget;
  const statusClass = state.done
    ? state.terminationReason === "confidence_reached"
      ? "status-success"
      : "status-failure"
    : "status-live";

  els.taskTitle.textContent = task.goal;
  els.taskDescription.textContent = task.description;
  els.targetConfidenceLabel.textContent = task.targetConfidence.toFixed(2);
  els.targetLegend.textContent = `Target ${task.targetConfidence.toFixed(2)}`;
  els.budgetValue.textContent = formatCurrency(state.budget);
  els.budgetPercent.textContent = `${Math.max(0, Math.round(budgetRatio * 100))}% available`;
  els.budgetWarning.textContent =
    budgetRatio <= 0.3 ? "Low runway" : budgetRatio <= 0.6 ? "Budget tightening" : "Healthy runway";
  els.walletCard.classList.toggle("warning", budgetRatio <= 0.3 && !state.done);
  els.confidenceValue.textContent = state.confidence.toFixed(2);
  els.confidenceFill.style.width = `${Math.min(100, state.confidence * 100)}%`;
  els.targetMarker.style.left = `${Math.min(100, task.targetConfidence * 100)}%`;
  els.stepCount.textContent = String(state.stepCount);
  els.graderScore.textContent = state.graderScore.toFixed(2);
  els.episodeReturn.textContent = formatSigned(state.episodeReturn);
  els.statusBadge.textContent = state.done
    ? state.terminationReason === "confidence_reached"
      ? "Success"
      : "Bankrupt"
    : "In Progress";
  els.statusBadge.className = statusClass;

  renderTools();
}

async function resetEpisode() {
  const selectedTaskId = els.taskSelector.value;
  const taskId = parseInt(selectedTaskId, 10);
  const response = await fetch("/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: parseInt(selectedTaskId, 10) }),
  });
  const payload = await response.json();
  const observation = payload.observation;
  const task = TASKS[taskId];

  state.taskId = taskId;
  state.budget = observation.budget_remaining;
  state.startingBudget = task.startingBudget;
  state.targetConfidence = task.targetConfidence;
  state.confidence = observation.confidence;
  state.stepCount = 0;
  state.episodeReturn = 0;
  state.graderScore = 0;
  state.done = payload.done;
  state.terminationReason = observation.termination_reason || "";

  if (!els.logList.children.length || taskId !== Number(els.logList.dataset.taskId || "0")) {
    els.logList.innerHTML = "";
  }
  els.logList.dataset.taskId = String(taskId);

  addLog(observation.info, "system");
  updateStatus();
}

function buildQuery(tool) {
  const task = taskForCurrentState();
  return `${tool.key.toLowerCase()} for ${task.goal.toLowerCase()}`;
}

async function runStep(tool) {
  const response = await fetch("/step", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action: {
        tool_name: tool.key,
        query: buildQuery(tool),
      },
    }),
  });
  const payload = await response.json();
  const observation = payload.observation;

  state.budget = observation.budget_remaining;
  state.confidence = observation.confidence;
  state.stepCount += 1;
  state.episodeReturn += payload.reward || 0;
  state.done = payload.done;
  state.terminationReason = observation.termination_reason || "";
  state.graderScore = state.done && state.confidence >= state.targetConfidence ? 1 : state.graderScore;
  if (state.done && state.terminationReason === "budget_depleted" && state.targetConfidence > 0) {
    state.graderScore = Math.min(1, Number((state.confidence / state.targetConfidence).toFixed(2)));
  }

  addLog(
    `[Step ${state.stepCount}] Executed ${tool.key}. Budget ${formatCurrency(state.budget)}. Confidence ${state.confidence.toFixed(2)}. Reward ${formatSigned(payload.reward || 0)}.`,
    "system",
  );

  if (state.done) {
    if (state.terminationReason === "confidence_reached") {
      addLog(
        `SUCCESS. Final return ${formatSigned(state.episodeReturn)} with grader score ${state.graderScore.toFixed(2)}.`,
        "success",
      );
    } else {
      addLog(
        `BANKRUPT. Final return ${formatSigned(state.episodeReturn)} with grader score ${state.graderScore.toFixed(2)}.`,
        "failure",
      );
    }
  }

  updateStatus();
}

els.resetButton.addEventListener("click", resetEpisode);
els.taskSelector.addEventListener("change", resetEpisode);

updateStatus();
resetEpisode().catch((error) => {
  addLog(`Unable to connect to environment: ${error.message}`, "failure");
});
