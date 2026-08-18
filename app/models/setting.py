from app.extensions import db
from flask_login import UserMixin
from datetime import datetime

# ============================================================
# Setting model
# ============================================================

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# 14. جدول التفعيل
# ============================================================
