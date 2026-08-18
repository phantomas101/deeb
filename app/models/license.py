from app.extensions import db
from flask_login import UserMixin
from datetime import datetime

# ============================================================
# License model
# ============================================================

class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String(100), unique=True, nullable=False)
    license_key = db.Column(db.String(50), unique=True, nullable=False)
    license_type = db.Column(db.String(20), default='trial')
    activated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<License {self.license_key} - {self.license_type}>'


# ============================================================
# 15. جدول السيريالات
# ============================================================
