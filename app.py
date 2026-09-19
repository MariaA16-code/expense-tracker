import csv
import io
import os
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()
app = Flask(__name__)
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL must be configured. Copy .env.example to .env and set a MySQL connection URL.")
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

CATEGORIES = ("Food", "Transport", "Shopping", "Health", "Education", "Entertainment", "Bills", "Other")
MAX_TITLE_LENGTH = 100
MAX_NOTE_LENGTH = 255


class Expense(db.Model):
    # Keep Float to remain compatible with the existing MySQL expense table.
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "amount": round(float(self.amount), 2), "category": self.category, "date": self.date.isoformat(), "note": self.note or ""}


def error(message, status=400):
    return jsonify({"error": message}), status


def parse_iso_date(value, label):
    if not value:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must use YYYY-MM-DD format.")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{label} must use YYYY-MM-DD format.") from exc


def parse_filters(args):
    start_date = parse_iso_date(args.get("start_date"), "Start date")
    end_date = parse_iso_date(args.get("end_date"), "End date")
    category = args.get("category", "").strip()
    if start_date and end_date and start_date > end_date:
        raise ValueError("Start date cannot be after end date.")
    if category and category not in CATEGORIES:
        raise ValueError("Category is not valid.")
    return start_date, end_date, category


def filtered_expenses(args):
    start_date, end_date, category = parse_filters(args)
    query = Expense.query
    if start_date:
        query = query.filter(Expense.date >= start_date)
    if end_date:
        query = query.filter(Expense.date <= end_date)
    if category:
        query = query.filter(Expense.category == category)
    return query.order_by(Expense.date.desc(), Expense.id.desc()).all()


def parse_expense_payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("A JSON object is required.")
    title, category, note, raw_amount = data.get("title"), data.get("category"), data.get("note", ""), data.get("amount")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Title is required.")
    title = title.strip()
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(f"Title must be {MAX_TITLE_LENGTH} characters or fewer.")
    if category not in CATEGORIES:
        raise ValueError("Please select a valid category.")
    if not isinstance(note, str):
        raise ValueError("Note must be text.")
    note = note.strip()
    if len(note) > MAX_NOTE_LENGTH:
        raise ValueError(f"Note must be {MAX_NOTE_LENGTH} characters or fewer.")
    try:
        amount = Decimal(str(raw_amount))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Amount must be a valid number.") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount > Decimal("99999999.99"):
        raise ValueError("Amount is too large.")
    expense_date = parse_iso_date(data.get("date"), "Date")
    if not expense_date:
        raise ValueError("Date is required.")
    return {"title": title, "amount": float(amount), "category": category, "date": expense_date, "note": note}


def money(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def safe_csv_value(value):
    """Prevent spreadsheet applications from treating user text as a formula."""
    text = value or ""
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def database_error_response():
    db.session.rollback()
    return error("The database operation could not be completed. Please try again.", 500)


@app.errorhandler(404)
def not_found(_):
    return error("Resource not found.", 404) if request.path.startswith("/api/") else ("Not found", 404)


@app.route("/")
def index():
    return render_template("index.html", categories=CATEGORIES)


@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    try:
        return jsonify([expense.to_dict() for expense in filtered_expenses(request.args)])
    except ValueError as exc:
        return error(str(exc))


@app.route("/api/expenses", methods=["POST"])
def add_expense():
    try:
        expense = Expense(**parse_expense_payload())
    except ValueError as exc:
        return error(str(exc))
    try:
        db.session.add(expense)
        db.session.commit()
    except SQLAlchemyError:
        return database_error_response()
    return jsonify(expense.to_dict()), 201


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    expense = db.session.get(Expense, expense_id)
    if not expense:
        return error("Expense not found.", 404)
    try:
        db.session.delete(expense)
        db.session.commit()
    except SQLAlchemyError:
        return database_error_response()
    return jsonify({"message": "Expense deleted."})


@app.route("/api/expenses/<int:expense_id>", methods=["PUT"])
def update_expense(expense_id):
    expense = db.session.get(Expense, expense_id)
    if not expense:
        return error("Expense not found.", 404)
    try:
        payload = parse_expense_payload()
    except ValueError as exc:
        return error(str(exc))
    try:
        for field, value in payload.items():
            setattr(expense, field, value)
        db.session.commit()
    except SQLAlchemyError:
        return database_error_response()
    return jsonify(expense.to_dict())


@app.route("/api/analytics", methods=["GET"])
def analytics():
    try:
        expenses = filtered_expenses(request.args)
    except ValueError as exc:
        return error(str(exc))
    total, category_totals, category_counts, monthly_totals = Decimal("0"), defaultdict(Decimal), defaultdict(int), defaultdict(Decimal)
    for expense in expenses:
        amount = Decimal(str(expense.amount))
        total += amount
        category_totals[expense.category] += amount
        category_counts[expense.category] += 1
        monthly_totals[expense.date.strftime("%Y-%m")] += amount
    ranked_categories = sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
    highest_category = ranked_categories[0][0] if ranked_categories else None
    average = total / len(expenses) if expenses else Decimal("0")
    if expenses:
        peak_month, peak_total = max(monthly_totals.items(), key=lambda item: item[1])
        insights = [f"{highest_category} accounts for the largest share of spending.", f"Your average transaction is RM {money(average):,.2f} across {len(expenses)} transactions.", f"Your highest-spending month is {datetime.strptime(peak_month, '%Y-%m').strftime('%B %Y')} at RM {money(peak_total):,.2f}."]
    else:
        insights = ["Add an expense to start building spending insights."]
    return jsonify({
        "kpis": {"total_spending": money(total), "average_expense": money(average), "total_transactions": len(expenses), "highest_spending_category": highest_category},
        "spending_by_category": [{"category": category, "amount": money(amount)} for category, amount in ranked_categories],
        "expense_count_by_category": [{"category": category, "count": category_counts[category]} for category in sorted(category_counts)],
        "monthly_spending": [{"month": month, "amount": money(amount)} for month, amount in sorted(monthly_totals.items())],
        "recent_expenses": [expense.to_dict() for expense in expenses[:8]], "insights": insights,
    })


@app.route("/api/expenses/export", methods=["GET"])
def export_expenses():
    try:
        expenses = filtered_expenses(request.args)
    except ValueError as exc:
        return error(str(exc))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Amount (RM)", "Category", "Date", "Note"])
    for expense in expenses:
        writer.writerow([expense.id, safe_csv_value(expense.title), f"{money(expense.amount):.2f}", expense.category, expense.date.isoformat(), safe_csv_value(expense.note)])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f'attachment; filename="expense-export-{date.today().isoformat()}.csv"'})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run()
