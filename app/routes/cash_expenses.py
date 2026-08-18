from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import CashDrawer, Expense, Sale, Branch
from datetime import datetime, timedelta

cash_bp = Blueprint('cash', __name__)

# ===== عرض صفحة الخزينة والمصروفات =====
@cash_bp.route('/')
@login_required
def index():
    # جلب الفرع الرئيسي
    main_branch = Branch.query.filter_by(is_main=True).first()
    if not main_branch:
        flash('الفرع الرئيسي غير موجود!', 'danger')
        return render_template('cash_expenses.html', balance=0, transactions=[], expenses=[], now=datetime.now())

    # ١. حساب رصيد الخزينة الحالي
    total_in = db.session.query(db.func.sum(CashDrawer.amount)).filter(
        CashDrawer.branch_id == main_branch.id,
        CashDrawer.transaction_type == 'IN'
    ).scalar() or 0

    total_out = db.session.query(db.func.sum(CashDrawer.amount)).filter(
        CashDrawer.branch_id == main_branch.id,
        CashDrawer.transaction_type == 'OUT'
    ).scalar() or 0

    balance = total_in - total_out

    # ٢. جلب آخر ٢٠ حركة خزينة
    transactions = CashDrawer.query.filter_by(branch_id=main_branch.id).order_by(CashDrawer.created_at.desc()).limit(20).all()

    # ٣. جلب آخر ٢٠ مصروف
    expenses = Expense.query.filter_by(branch_id=main_branch.id).order_by(Expense.created_at.desc()).limit(20).all()

    return render_template(
        'cash_expenses.html',
        balance=balance,
        transactions=transactions,
        expenses=expenses,
        now=datetime.now()  # <-- التعديل المطلوب
    )

# ===== إضافة مصروف جديد =====
@cash_bp.route('/add-expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه العملية.', 'danger')
        return redirect(url_for('cash.index'))

    main_branch = Branch.query.filter_by(is_main=True).first()
    if not main_branch:
        flash('الفرع الرئيسي غير موجود!', 'danger')
        return redirect(url_for('cash.index'))

    if request.method == 'POST':
        category = request.form.get('category')
        amount = request.form.get('amount')
        notes = request.form.get('notes', '')

        if not category or not amount:
            flash('يرجى إدخال الفئة والمبلغ.', 'warning')
            return render_template('expense_add.html')

        try:
            amount = float(amount)
            if amount <= 0:
                flash('المبلغ يجب أن يكون أكبر من صفر.', 'warning')
                return render_template('expense_add.html')

            # ١. إضافة المصروف
            expense = Expense(
                branch_id=main_branch.id,
                category=category,
                amount=amount,
                notes=notes,
                created_at=datetime.now()
            )
            db.session.add(expense)

            # ٢. تسجيل حركة خزينة (صرف)
            cash_transaction = CashDrawer(
                branch_id=main_branch.id,
                transaction_type='OUT',
                amount=amount,
                reason=f'مصروف: {category}',
                created_at=datetime.now()
            )
            db.session.add(cash_transaction)

            db.session.commit()
            flash('تم إضافة المصروف وتسجيله في الخزينة بنجاح!', 'success')
            return redirect(url_for('cash.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return render_template('expense_add.html')

    return render_template('expense_add.html')

# ===== تقفيل اليومية (تقرير اليوم) =====
@cash_bp.route('/daily-close')
@login_required
def daily_close():
    if current_user.role != 'admin':
        flash('غير مسموح لك.', 'danger')
        return redirect(url_for('cash.index'))

    main_branch = Branch.query.filter_by(is_main=True).first()
    if not main_branch:
        flash('الفرع الرئيسي غير موجود!', 'danger')
        return redirect(url_for('cash.index'))

    # تحديد تاريخ اليوم (من منتصف الليل)
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    # ١. إجمالي مبيعات اليوم (من جدول المبيعات)
    total_sales_today = db.session.query(db.func.sum(Sale.net_amount)).filter(
        Sale.branch_id == main_branch.id,
        Sale.created_at >= today_start,
        Sale.created_at < tomorrow_start
    ).scalar() or 0

    # ٢. إجمالي المصروفات اليوم
    total_expenses_today = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.branch_id == main_branch.id,
        Expense.created_at >= today_start,
        Expense.created_at < tomorrow_start
    ).scalar() or 0

    # ٣. حركات الخزينة اليوم (للتحقق)
    cash_in_today = db.session.query(db.func.sum(CashDrawer.amount)).filter(
        CashDrawer.branch_id == main_branch.id,
        CashDrawer.transaction_type == 'IN',
        CashDrawer.created_at >= today_start,
        CashDrawer.created_at < tomorrow_start
    ).scalar() or 0

    cash_out_today = db.session.query(db.func.sum(CashDrawer.amount)).filter(
        CashDrawer.branch_id == main_branch.id,
        CashDrawer.transaction_type == 'OUT',
        CashDrawer.created_at >= today_start,
        CashDrawer.created_at < tomorrow_start
    ).scalar() or 0

    # ٤. صافي الخزينة اليوم
    net_cash_today = cash_in_today - cash_out_today

    # ٥. حساب الربح المتوقع (إجمالي المبيعات - تكلفة البضاعة المباعة)
    cost_of_goods_sold = 0
    sales_today = Sale.query.filter(
        Sale.branch_id == main_branch.id,
        Sale.created_at >= today_start,
        Sale.created_at < tomorrow_start
    ).all()
    
    for sale in sales_today:
        for item in sale.items:
            if item.product:
                cost_of_goods_sold += item.quantity * item.product.cost_price

    gross_profit = total_sales_today - cost_of_goods_sold
    net_profit = gross_profit - total_expenses_today

    return render_template(
        'daily_close.html',
        today_start=today_start,
        total_sales=total_sales_today,
        total_expenses=total_expenses_today,
        cash_in=cash_in_today,
        cash_out=cash_out_today,
        net_cash=net_cash_today,
        cost_of_goods_sold=cost_of_goods_sold,
        gross_profit=gross_profit,
        net_profit=net_profit
    )