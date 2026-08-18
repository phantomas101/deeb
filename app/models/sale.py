from app.extensions import db
from flask_login import UserMixin
from datetime import datetime

# ============================================================
# Sale model
# ============================================================

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    customer_phone = db.Column(db.String(20), db.ForeignKey('customer.phone'), nullable=True)
    total_amount = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    net_amount = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    change_amount = db.Column(db.Float, default=0.0)
    payment_type = db.Column(db.String(20), default='cash')
    sale_type = db.Column(db.String(20), default='retail')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('SaleItem', backref='sale', lazy=True)


# ============================================================
# SaleItem model
# ============================================================

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    unit_price = db.Column(db.Float)
    total = db.Column(db.Float)# العلاقة مع السيريالات