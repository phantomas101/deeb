from app.extensions import db
from datetime import datetime

# ============================================================
# Product model
# ============================================================
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=True)
    category = db.Column(db.String(50), default='Laptops')
    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    wholesale_price = db.Column(db.Float, nullable=False, default=0.0)
    quantity = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=5)
    image_filename = db.Column(db.String(200), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))

    sale_items = db.relationship('SaleItem', backref='product', lazy=True)
    purchase_items = db.relationship('PurchaseItem', backref='product', lazy=True)
    stock_movements = db.relationship('StockMovement', backref='product', lazy=True)


# ============================================================
# StockMovement model
# ============================================================
class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    from_branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)
    to_branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)
    quantity_change = db.Column(db.Integer)
    movement_type = db.Column(db.String(20))  # PURCHASE, SALE, TRANSFER, RETURN
    notes = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), nullable=True)

    from_branch = db.relationship('Branch', foreign_keys=[from_branch_id], backref='outgoing_movements')
    to_branch = db.relationship('Branch', foreign_keys=[to_branch_id], backref='incoming_movements')
    sale = db.relationship('Sale', backref='stock_movements')
    purchase = db.relationship('Purchase', backref='stock_movements')