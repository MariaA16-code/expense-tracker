// Fetch and display expenses
async function loadExpenses() {
  const res = await fetch('/api/expenses');
  const expenses = await res.json();

  const table = document.getElementById('expenseTable');
  table.innerHTML = '';

  if (expenses.length === 0) {
    table.innerHTML = `<tr><td colspan="6" class="empty">No expenses yet. Add one above!</td></tr>`;
    return;
  }

  expenses.forEach(exp => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${exp.title}</td>
      <td>RM ${exp.amount.toFixed(2)}</td>
      <td>${exp.category}</td>
      <td>${exp.date}</td>
      <td>${exp.note || ''}</td>
      <td>
        <button onclick="deleteExpense(${exp.id})">Delete</button>
      </td>
    `;
    table.appendChild(row);
  });

  // Update summary
  document.getElementById('totalAmount').textContent =
    'RM ' + expenses.reduce((sum, e) => sum + e.amount, 0).toFixed(2);
  document.getElementById('totalCount').textContent = expenses.length;
}

// Add new expense
async function addExpense() {
  const title = document.getElementById('title').value;
  const amount = parseFloat(document.getElementById('amount').value);
  const category = document.getElementById('category').value;
  const date = document.getElementById('date').value;
  const note = document.getElementById('note').value;

  if (!title || !amount || !category || !date) {
    alert('Please fill all required fields');
    return;
  }

  const res = await fetch('/api/expenses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, amount, category, date, note })
  });

  if (res.ok) {
    loadExpenses();
    document.getElementById('title').value = '';
    document.getElementById('amount').value = '';
    document.getElementById('category').value = '';
    document.getElementById('date').value = '';
    document.getElementById('note').value = '';
  }
}

// Delete expense
async function deleteExpense(id) {
  const res = await fetch(`/api/expenses/${id}`, { method: 'DELETE' });
  if (res.ok) loadExpenses();
}

// Load on startup
window.onload = loadExpenses;