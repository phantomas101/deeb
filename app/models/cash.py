from app.extensions import db
from datetime import datetime

# ============================================================
# CashDrawer model
# ============================================================

class CashDrawer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    transaction_type = db.Column(db.String(20))  # IN / OUT
    amount = db.Column(db.Float)
    reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# Expense model
# ============================================================

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    category = db.Column(db.String(50))
    amount = db.Column(db.Float)
    notes = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)