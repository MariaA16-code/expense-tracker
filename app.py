from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# ── DATABASE CONFIG ──

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:M%40riaSQL%2189@localhost/expense_tracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ── MODEL ──
class Expense(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(100), nullable=False)
    amount      = db.Column(db.Float, nullable=False)
    category    = db.Column(db.String(50), nullable=False)
    date        = db.Column(db.Date, nullable=False)
    note        = db.Column(db.String(255), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':       self.id,
            'title':    self.title,
            'amount':   self.amount,
            'category': self.category,
            'date':     str(self.date),
            'note':     self.note
        }

# ── ROUTES ──
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    return jsonify([e.to_dict() for e in expenses])

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.get_json()
    expense = Expense(
        title    = data['title'],
        amount   = data['amount'],
        category = data['category'],
        date     = datetime.strptime(data['date'], '%Y-%m-%d').date(),
        note     = data.get('note', '')
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify(expense.to_dict()), 201

@app.route('/api/expenses/<int:id>', methods=['DELETE'])
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    return jsonify({'message': 'Deleted successfully'})

@app.route('/api/expenses/<int:id>', methods=['PUT'])
def update_expense(id):
    expense = Expense.query.get_or_404(id)
    data = request.get_json()
    expense.title    = data['title']
    expense.amount   = data['amount']
    expense.category = data['category']
    expense.date     = datetime.strptime(data['date'], '%Y-%m-%d').date()
    expense.note     = data.get('note', '')
    db.session.commit()
    return jsonify(expense.to_dict())

# ── RUN ──
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)