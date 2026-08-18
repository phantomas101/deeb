from app.extensions import db
from flask_login import UserMixin
from datetime import datetime

# ============================================================
# Branch model
# ============================================================

class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_main = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship('Product', backref='branch', lazy=True)
    users = db.relationship('User', backref='branch', lazy=True)


# ============================================================
# 2. جدول المستخدمين
# ============================================================
