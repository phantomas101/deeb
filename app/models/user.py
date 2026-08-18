from app.extensions import db
from flask_login import UserMixin
from datetime import datetime

# ============================================================
# User model
# ============================================================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='cashier')
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))

    sales = db.relationship('Sale', backref='created_by_user', foreign_keys='Sale.created_by')


# ============================================================
# 3. جدول العملاء
# ============================================================
