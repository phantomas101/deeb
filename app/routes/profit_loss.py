from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Sale, Purchase, Expense, CashDrawer, Customer, Supplier, Branch
from datetime import datetime, timedelta

profit_loss_bp = Blueprint('profit_loss', __name__)


@profit_loss_bp.route('/')
@login_required
def index():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه الصفحة.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # ===== الحصول على الفترة (افتراضي: اليوم) =====
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if date_from and date_to:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
        except:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
    else:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    
    # ===== 1. إجمالي المبيعات =====
    total_sales = db.session.query(db.func.sum(Sale.net_amount)).filter(
        Sale.created_at >= start_date,
        Sale.created_at < end_date
    ).scalar() or 0
    
    # تفصيل المبيعات حسب النوع
    retail_sales = db.session.query(db.func.sum(Sale.net_amount)).filter(
        Sale.created_at >= start_date,
        Sale.created_at < end_date,
        Sale.sale_type == 'retail'
    ).scalar() or 0
    
    wholesale_sales = db.session.query(db.func.sum(Sale.net_amount)).filter(
        Sale.created_at >= start_date,
        Sale.created_at < end_date,
        Sale.sale_type == 'wholesale'
    ).scalar() or 0
    
    # تفصيل المبيعات حسب نوع الدفع
    cash_sales = db.session.query(db.func.sum(Sale.net_amount)).filter(
        Sale.created_at >= start_date,
        Sale.created_at < end_date,
        Sale.payment_type == 'cash'
    ).scalar() or 0
    
    credit_sales = db.session.query(db.func.sum(Sale.net_amount)).filter(
        Sale.created_at >= start_date,
        Sale.created_at < end_date,
        Sale.payment_type == 'credit'
    ).scalar() or 0
    
    # ===== 2. تكلفة البضاعة المباعة =====
    # نحسبها من جدول SaleItem (لكل منتج، نضرب الكمية في سعر التكلفة الحالي)
    cost_of_goods_sold = 0
    from app.models import SaleItem, Product
    
    sale_items = SaleItem.query.join(Sale).filter(
        Sale.created_at >= start_date,
        Sale.created_at < end_date
    ).all()
    
    for item in sale_items:
        product = Product.query.get(item.product_id)
        if product:
            cost_of_goods_sold += item.quantity * product.cost_price
    
    # ===== 3. إجمالي المشتريات =====
    total_purchases = db.session.query(db.func.sum(Purchase.total_cost)).filter(
        Purchase.created_at >= start_date,
        Purchase.created_at < end_date
    ).scalar() or 0
    
    # ===== 4. إجمالي المصروفات =====
    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.created_at >= start_date,
        Expense.created_at < end_date
    ).scalar() or 0
    
    # ===== 5. صافي الديون (الزيادة في رصيد العملاء والموردين) =====
    # عملاء: زيادة المديونية خلال الفترة
    customers_balance_start = 0
    customers_balance_end = db.session.query(db.func.sum(Customer.balance)).scalar() or 0
    
    # موردين: زيادة المستحقات خلال الفترة
    suppliers_balance_start = 0
    suppliers_balance_end = db.session.query(db.func.sum(Supplier.balance)).scalar() or 0
    
    # ===== 6. الحسابات النهائية =====
    gross_profit = total_sales - cost_of_goods_sold
    net_profit = gross_profit - total_expenses
    net_profit_after_debts = net_profit - (customers_balance_end + suppliers_balance_end)
    
    return render_template(
        'profit_loss.html',
        start_date=start_date,
        end_date=end_date,
        total_sales=total_sales,
        retail_sales=retail_sales,
        wholesale_sales=wholesale_sales,
        cash_sales=cash_sales,
        credit_sales=credit_sales,
        cost_of_goods_sold=cost_of_goods_sold,
        total_purchases=total_purchases,
        total_expenses=total_expenses,
        gross_profit=gross_profit,
        net_profit=net_profit,
        customers_balance=customers_balance_end,
        suppliers_balance=suppliers_balance_end,
        net_profit_after_debts=net_profit_after_debts
    )