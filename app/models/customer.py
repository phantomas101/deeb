from app.extensions import db
from flask_login import UserMixin
from datetime import datetime

# ============================================================
# Customer model
# ============================================================

class Customer(db.Model):
    phone = db.Column(db.String(20), primary_key=True, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    balance = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sales = db.relationship('Sale', backref='customer', foreign_keys='Sale.customer_phone')


# ============================================================
# 4. جدول الموردين
# ============================================================
