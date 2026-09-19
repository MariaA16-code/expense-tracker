const state = { charts: {} };
const currency = new Intl.NumberFormat("en-MY", { style: "currency", currency: "MYR", minimumFractionDigits: 2 });
const colors = ["#a78bfa", "#ec4899", "#38bdf8", "#34d399", "#fbbf24", "#fb7185", "#818cf8", "#94a3b8"];

function queryString() {
  const params = new URLSearchParams();
  const start = document.getElementById("startDate").value;
  const end = document.getElementById("endDate").value;
  const category = document.getElementById("filterCategory").value;
  if (start) params.set("start_date", start);
  if (end) params.set("end_date", end);
  if (category) params.set("category", category);
  return params.toString();
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}

function setStatus(message = "", isError = false) {
  const element = document.getElementById("statusMessage");
  element.textContent = message;
  element.classList.toggle("error", isError);
}

function setText(id, value) { document.getElementById(id).textContent = value; }

function renderKpis(kpis) {
  setText("totalSpending", currency.format(kpis.total_spending));
  setText("averageExpense", currency.format(kpis.average_expense));
  setText("transactionCount", kpis.total_transactions.toLocaleString());
  setText("topCategory", kpis.highest_spending_category || "—");
}

function buildChart(id, type, labels, values, label, options = {}) {
  if (state.charts[id]) state.charts[id].destroy();
  state.charts[id] = new Chart(document.getElementById(id), {
    type,
    data: { labels, datasets: [{ label, data: values, backgroundColor: type === "line" ? "rgba(167,139,250,.2)" : colors, borderColor: type === "line" ? "#a78bfa" : colors, borderWidth: 2, fill: type === "line", tension: .35 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: type === "doughnut", labels: { color: "#d8d4e8" } }, tooltip: { callbacks: { label: context => label.includes("RM") ? context.label + ": " + currency.format(context.parsed.y ?? context.parsed) : context.label + ": " + (context.parsed.y ?? context.parsed) } } }, scales: type === "doughnut" ? {} : { x: { ticks: { color: "#a8a6bb" }, grid: { color: "rgba(167,139,250,.08)" } }, y: { beginAtZero: true, ticks: { color: "#a8a6bb", callback: value => options.currency ? "RM " + value : value }, grid: { color: "rgba(167,139,250,.08)" } } } }
  });
}

function renderCharts(data) {
  const categories = data.spending_by_category;
  buildChart("categoryChart", "doughnut", categories.map(item => item.category), categories.map(item => item.amount), "RM spending");
  const months = data.monthly_spending;
  buildChart("trendChart", "line", months.map(item => new Date(item.month + "-01T00:00:00").toLocaleDateString("en-MY", { month: "short", year: "numeric" })), months.map(item => item.amount), "RM spending", { currency: true });
  const counts = data.expense_count_by_category;
  buildChart("countChart", "bar", counts.map(item => item.category), counts.map(item => item.count), "Transactions");
}

function renderInsights(insights) {
  const list = document.getElementById("insightsList");
  list.replaceChildren();
  insights.forEach(insight => { const item = document.createElement("li"); item.textContent = insight; list.appendChild(item); });
}

function renderExpenses(expenses, total) {
  const table = document.getElementById("expenseTable");
  table.replaceChildren();
  setText("tableSummary", total ? "Showing " + Math.min(expenses.length, 8) + " recent expenses from " + total + " filtered transaction" + (total === 1 ? "" : "s") : "No expenses match the current filters");
  if (!expenses.length) {
    const row = document.createElement("tr"), cell = document.createElement("td");
    cell.colSpan = 5; cell.className = "empty"; cell.textContent = "No expenses found. Add one or reset your filters.";
    row.appendChild(cell); table.appendChild(row); return;
  }
  expenses.forEach(expense => {
    const row = document.createElement("tr");
    const title = document.createElement("td"); title.textContent = expense.title;
    const category = document.createElement("td"), badge = document.createElement("span"); badge.className = "badge"; badge.textContent = expense.category; category.appendChild(badge);
    const date = document.createElement("td"); date.textContent = expense.date;
    const amount = document.createElement("td"); amount.className = "amount-cell"; amount.textContent = currency.format(expense.amount);
    const action = document.createElement("td"), button = document.createElement("button"); button.type = "button"; button.className = "delete-button"; button.textContent = "Delete"; button.addEventListener("click", () => deleteExpense(expense.id, expense.title)); action.appendChild(button);
    row.append(title, category, date, amount, action); table.appendChild(row);
  });
}

async function loadDashboard() {
  const query = queryString();
  try {
    setStatus("Updating analytics…");
    const data = await requestJson("/api/analytics" + (query ? "?" + query : ""));
    renderKpis(data.kpis); renderCharts(data); renderInsights(data.insights); renderExpenses(data.recent_expenses, data.kpis.total_transactions);
    setStatus("");
  } catch (error) { setStatus(error.message, true); }
}

async function deleteExpense(id, title) {
  if (!window.confirm('Delete "' + title + '"? This cannot be undone.')) return;
  try {
    await requestJson("/api/expenses/" + id, { method: "DELETE" });
    setStatus("Expense deleted."); await loadDashboard();
  } catch (error) { setStatus(error.message, true); }
}

async function addExpense(event) {
  event.preventDefault();
  const error = document.getElementById("formError");
  error.textContent = "";
  const payload = { title: document.getElementById("title").value, amount: document.getElementById("amount").value, category: document.getElementById("category").value, date: document.getElementById("date").value, note: document.getElementById("note").value };
  try {
    await requestJson("/api/expenses", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    event.target.reset(); setStatus("Expense added successfully."); await loadDashboard();
  } catch (requestError) { error.textContent = requestError.message; }
}

function resetFilters() {
  document.getElementById("startDate").value = "";
  document.getElementById("endDate").value = "";
  document.getElementById("filterCategory").value = "";
  loadDashboard();
}

function exportCsv() {
  const query = queryString();
  window.location.assign("/api/expenses/export" + (query ? "?" + query : ""));
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("expenseForm").addEventListener("submit", addExpense);
  document.getElementById("applyFilters").addEventListener("click", loadDashboard);
  document.getElementById("resetFilters").addEventListener("click", resetFilters);
  document.getElementById("exportButton").addEventListener("click", exportCsv);
  loadDashboard();
});
