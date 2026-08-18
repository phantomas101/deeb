from app import db
from app.models import *
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
# 3. جدول العملاء (جديد - رقم الهاتف هو المفتاح الأساسي)
# ============================================================
class Customer(db.Model):
    phone = db.Column(db.String(20), primary_key=True, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    balance = db.Column(db.Float, default=0.0)  # موجب = عليه دين (مديونية)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sales = db.relationship('Sale', backref='customer', foreign_keys='Sale.customer_phone')


# ============================================================
# 4. جدول الموردين (معدل - رقم الهاتف هو المفتاح الأساسي)
# ============================================================
class Supplier(db.Model):
    phone = db.Column(db.String(20), primary_key=True, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    balance = db.Column(db.Float, default=0.0)  # موجب = له علينا (مستحق له)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    purchases = db.relationship('Purchase', backref='supplier', foreign_keys='Purchase.supplier_phone')


# ============================================================
# 5. جدول المنتجات (معدل - إضافة سعر الجملة)
# ============================================================
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='Laptops')
    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)  # سعر القطاعي
    wholesale_price = db.Column(db.Float, nullable=False, default=0.0)  # سعر الجملة (جديد)
    quantity = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=5)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))

    sale_items = db.relationship('SaleItem', backref='product', lazy=True)
    purchase_items = db.relationship('PurchaseItem', backref='product', lazy=True)


# ============================================================
# 6. جدول حركة المخزون
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


# ============================================================
# 7. جدول المبيعات (معدل - إضافة العميل ونوع الدفع ونوع البيع)
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
    payment_type = db.Column(db.String(20), default='cash')  # cash / credit
    sale_type = db.Column(db.String(20), default='retail')   # retail / wholesale (جديد)
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
    unit_price = db.Column(db.Float)  # السعر الفعلي (قطاعي أو جملة)
    total = db.Column(db.Float)


# ============================================================
# 9. جدول المشتريات (معدل - إضافة المورد ونوع الدفع)
# ============================================================
class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_phone = db.Column(db.String(20), db.ForeignKey('supplier.phone'), nullable=True)
    total_cost = db.Column(db.Float, default=0.0)
    payment_type = db.Column(db.String(20), default='cash')  # cash / credit (جديد)
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
    transaction_type = db.Column(db.String(20))  # IN / OUT
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