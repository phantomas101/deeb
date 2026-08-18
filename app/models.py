from app import db
from flask_login import UserMixin
from datetime import datetime

# ============================================================
# 1. جدول الفروع
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
class Supplier(db.Model):
    phone = db.Column(db.String(20), primary_key=True, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    balance = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    purchases = db.relationship('Purchase', backref='supplier', foreign_keys='Purchase.supplier_phone')


# ============================================================
# 5. جدول المنتجات
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
# 6. جدول حركة المخزون (مع is_received)
# ============================================================
class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    from_branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)
    to_branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=True)
    quantity_change = db.Column(db.Integer)
    movement_type = db.Column(db.String(20))
    notes = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), nullable=True)
    is_received = db.Column(db.Boolean, default=False)

    from_branch = db.relationship('Branch', foreign_keys=[from_branch_id], backref='outgoing_movements')
    to_branch = db.relationship('Branch', foreign_keys=[to_branch_id], backref='incoming_movements')
    sale = db.relationship('Sale', backref='stock_movements')
    purchase = db.relationship('Purchase', backref='stock_movements')


# ============================================================
# 7. جدول المبيعات
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
# 8. جدول تفاصيل المبيعات
# ============================================================
class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    unit_price = db.Column(db.Float)
    total = db.Column(db.Float)


# ============================================================
# 9. جدول المشتريات
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
# 10. جدول تفاصيل المشتريات
# ============================================================
class PurchaseItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    cost_price = db.Column(db.Float)
    total = db.Column(db.Float)


# ============================================================
# 11. جدول الخزينة
# ============================================================
class CashDrawer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    transaction_type = db.Column(db.String(20))
    amount = db.Column(db.Float)
    reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# 12. جدول المصروفات
# ============================================================
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    category = db.Column(db.String(50))
    amount = db.Column(db.Float)
    notes = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# 13. جدول الإعدادات
# ============================================================
class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# 14. جدول التقفيل اليومي
# ============================================================
class DailyClosing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    closed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_sales = db.Column(db.Float, default=0.0)
    total_expenses = db.Column(db.Float, default=0.0)
    total_in = db.Column(db.Float, default=0.0)
    total_out = db.Column(db.Float, default=0.0)
    net_cash = db.Column(db.Float, default=0.0)
    cost_of_goods_sold = db.Column(db.Float, default=0.0)
    gross_profit = db.Column(db.Float, default=0.0)
    net_profit = db.Column(db.Float, default=0.0)
    closed_at = db.Column(db.DateTime, default=datetime.utcnow)

    branch = db.relationship('Branch', backref='daily_closings')
    user = db.relationship('User', backref='daily_closings')


# ============================================================
# 15. جدول التفعيل
# ============================================================
class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String(100), unique=True, nullable=False)
    license_key = db.Column(db.String(50), unique=True, nullable=False)
    license_type = db.Column(db.String(20), default='trial')
    activated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)