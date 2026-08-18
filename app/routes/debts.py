from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Customer, Supplier, CashDrawer, Branch
from datetime import datetime

debts_bp = Blueprint('debts', __name__)

# ===== عرض صفحة المديونية =====
@debts_bp.route('/')
@login_required
def index():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه الصفحة.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    customers = Customer.query.filter(Customer.balance > 0).order_by(Customer.balance.desc()).all()
    suppliers = Supplier.query.filter(Supplier.balance > 0).order_by(Supplier.balance.desc()).all()
    
    return render_template('debts.html', customers=customers, suppliers=suppliers)

# ===== عرض صفحة تسديد دين عميل (GET) =====
@debts_bp.route('/pay-customer/<string:phone>', methods=['GET'])
@login_required
def pay_customer_page(phone):
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('debts.index'))
    
    customer = Customer.query.get_or_404(phone)
    return render_template('debt_pay.html', entity=customer, debt_type='customer')

# ===== تسديد دين عميل (POST) =====
@debts_bp.route('/pay-customer/<string:phone>', methods=['POST'])
@login_required
def pay_customer(phone):
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('debts.index'))
    
    customer = Customer.query.get_or_404(phone)
    amount = float(request.form.get('amount', 0))
    
    if amount <= 0:
        flash('المبلغ يجب أن يكون أكبر من صفر.', 'warning')
        return redirect(url_for('debts.pay_customer_page', phone=phone))
    
    if amount > customer.balance:
        flash(f'المبلغ يتجاوز الرصيد المستحق ({customer.balance} ج.م).', 'danger')
        return redirect(url_for('debts.pay_customer_page', phone=phone))
    
    try:
        customer.balance -= amount
        
        main_branch = Branch.query.filter_by(is_main=True).first()
        if main_branch:
            cash_in = CashDrawer(
                branch_id=main_branch.id,
                transaction_type='IN',
                amount=amount,
                reason=f'سداد دين من العميل {customer.name} - {customer.phone}',
                created_at=datetime.now()
            )
            db.session.add(cash_in)
        
        db.session.commit()
        flash(f'✅ تم تسجيل سداد مبلغ {amount} ج.م من العميل {customer.name}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ حدث خطأ: {str(e)}', 'danger')
    
    return redirect(url_for('debts.index'))

# ===== عرض صفحة سداد مستحقات مورد (GET) =====
@debts_bp.route('/pay-supplier/<string:phone>', methods=['GET'])
@login_required
def pay_supplier_page(phone):
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('debts.index'))
    
    supplier = Supplier.query.get_or_404(phone)
    return render_template('debt_pay.html', entity=supplier, debt_type='supplier')

# ===== سداد مستحقات مورد (POST) =====
@debts_bp.route('/pay-supplier/<string:phone>', methods=['POST'])
@login_required
def pay_supplier(phone):
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('debts.index'))
    
    supplier = Supplier.query.get_or_404(phone)
    amount = float(request.form.get('amount', 0))
    
    if amount <= 0:
        flash('المبلغ يجب أن يكون أكبر من صفر.', 'warning')
        return redirect(url_for('debts.pay_supplier_page', phone=phone))
    
    if amount > supplier.balance:
        flash(f'المبلغ يتجاوز الرصيد المستحق للمورد ({supplier.balance} ج.م).', 'danger')
        return redirect(url_for('debts.pay_supplier_page', phone=phone))
    
    try:
        supplier.balance -= amount
        
        main_branch = Branch.query.filter_by(is_main=True).first()
        if main_branch:
            cash_out = CashDrawer(
                branch_id=main_branch.id,
                transaction_type='OUT',
                amount=amount,
                reason=f'سداد مستحقات للمورد {supplier.name} - {supplier.phone}',
                created_at=datetime.now()
            )
            db.session.add(cash_out)
        
        db.session.commit()
        flash(f'✅ تم تسجيل صرف مبلغ {amount} ج.م للمورد {supplier.name}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ حدث خطأ: {str(e)}', 'danger')
    
    return redirect(url_for('debts.index'))