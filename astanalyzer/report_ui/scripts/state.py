def build_script_state() -> str:
    return """
const initialRaw = JSON.parse(
  document.getElementById("report-data").textContent
);

const CATEGORY_LABELS = {
  STYLE: "Style and readability",
  SEM: "Semantic issues",
  SEC: "Security",
  PERF: "Performance",
  DEAD: "Dead code",
  CX: "Complexity and maintainability",
};

const state = {
  raw: initialRaw,
  findings: [],
  selected: new Map(),
  selectedActions: new Map(),
  filter: "",
  dirHandle: null,
  viewMode: "rule-first"
};

const elStatus = document.getElementById("status");
const elCounts = document.getElementById("counts");
const elList = document.getElementById("list");
const elHint = document.getElementById("hint");
const elSourceHint = document.getElementById("sourceHint");
const elSaveTarget = document.getElementById("saveTarget");
const elViewStatus = document.getElementById("viewStatus");

const fileInput = document.getElementById("fileInput");
const search = document.getElementById("search");
const btnPickDir = document.getElementById("btnPickDir");
const btnSelectAll = document.getElementById("btnSelectAll");
const btnClear = document.getElementById("btnClear");
const btnExport = document.getElementById("btnExport");
const btnRuleFirst = document.getElementById("btnRuleFirst");
const btnFileFirst = document.getElementById("btnFileFirst");
"""