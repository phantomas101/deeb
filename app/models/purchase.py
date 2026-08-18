from app.extensions import db
from flask_login import UserMixin
from datetime import datetime

# ============================================================
# Purchase model
# ============================================================

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_phone = db.Column(db.String(20), db.ForeignKey('supplier.phone'), nullable=True)
    total_cost = db.Column(db.Float, default=0.0)
    payment_type = db.Column(db.String(20), default='cash')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('PurchaseItem', backref='purchase', lazy=True)


# ============================================================
# PurchaseItem model
# ============================================================

class PurchaseItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    cost_price = db.Column(db.Float)
    total = db.Column(db.Float)