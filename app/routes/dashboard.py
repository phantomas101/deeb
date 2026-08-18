from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app import db  # <--- هذا هو السطر المفقود الذي كان يسبب الخطأ
from app.models import Sale, CashDrawer, Product, Expense
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # ١. إجمالي مبيعات اليوم (للوقت الحالي)
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    total_sales_today = db.session.query(db.func.sum(Sale.net_amount)).filter(Sale.created_at >= today_start).scalar() or 0

    # ٢. رصيد الخزينة الحالي (بافتراض أن الحركات كلها مسجلة في CashDrawer)
    cash_balance = db.session.query(db.func.sum(CashDrawer.amount)).filter(
        CashDrawer.transaction_type == 'IN'
    ).scalar() or 0
    cash_out = db.session.query(db.func.sum(CashDrawer.amount)).filter(
        CashDrawer.transaction_type == 'OUT'
    ).scalar() or 0
    net_cash = cash_balance - cash_out

    # ٣. الأصناف التي أوشكت على النفاذ (الكمية <= الحد الأدنى)
    low_stock_items = Product.query.filter(Product.quantity <= Product.min_stock).all()
    
    # ٤. إجمالي المصروفات اليوم
    total_expenses_today = db.session.query(db.func.sum(Expense.amount)).filter(Expense.created_at >= today_start).scalar() or 0

    # ٥. آخر 5 مبيعات لعرضها في الجدول
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        total_sales=total_sales_today,
        cash_balance=net_cash,
        low_stock_items=low_stock_items,
        total_expenses=total_expenses_today,
        recent_sales=recent_sales
    )