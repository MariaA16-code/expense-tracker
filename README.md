# Expense Analytics Dashboard

A Data Analyst portfolio project for recording RM expenses and turning everyday transactions into practical spending insights. It preserves the original Flask, SQLAlchemy, MySQL, HTML, CSS, and vanilla JavaScript architecture.

## Features

- Add and delete expenses with server-side validation
- Filter every result by start date, end date, and category
- KPI cards for total spending, average expense, transaction count, and top spending category
- Chart.js visualisations for category spending, monthly trend, and category transaction count
- Recent filtered expenses and descriptive spending insights
- Export the current filtered expense data to CSV
- Safe text rendering in the browser; user-entered values are not inserted with HTML interpolation

## Technology stack

- Python, Flask, Flask-SQLAlchemy
- MySQL with PyMySQL
- HTML, CSS, vanilla JavaScript
- Chart.js loaded from CDN

## Setup

1. Create a virtual environment and install packages:

   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`.
3. Set `DATABASE_URL` in `.env` to your own MySQL SQLAlchemy connection URL.
4. Run locally:

   ```bash
   python app.py
   ```

The application creates its table only if it does not already exist. It does not recreate or migrate an existing expense table.

## Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | Yes | SQLAlchemy MySQL connection URL, for example `mysql+pymysql://USER:PASSWORD@HOST/DATABASE`. |

Never commit a real `.env` file. It is excluded by `.gitignore`.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/expenses` | List expenses, optionally filtered |
| POST | `/api/expenses` | Create a validated expense |
| PUT | `/api/expenses/<id>` | Update a validated expense |
| DELETE | `/api/expenses/<id>` | Delete an expense |
| GET | `/api/analytics` | Return KPI, chart, insight, and recent-expense data |
| GET | `/api/expenses/export` | Download filtered expenses as CSV |

The GET endpoints accept optional `start_date`, `end_date` (both `YYYY-MM-DD`), and `category` parameters. Valid categories are Food, Transport, Shopping, Health, Education, Entertainment, Bills, and Other.

## Analytics

Analytics are calculated from the active filtered dataset. This makes it easy to compare periods, inspect an individual category, find the dominant category, monitor monthly patterns, and export the exact records behind each dashboard view.
