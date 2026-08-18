from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Customer

customers_bp = Blueprint('customers', __name__)

# ===== عرض صفحة العملاء =====
@customers_bp.route('/')
@login_required
def index():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه الصفحة.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    customers = Customer.query.order_by(Customer.name).all()
    return render_template('customers.html', customers=customers)

# ===== صفحة إضافة عميل جديد (GET) =====
@customers_bp.route('/add', methods=['GET'])
@login_required
def add_customer_page():
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('customers.index'))
    return render_template('customers_add.html', customer=None)

# ===== إضافة عميل جديد (POST) =====
@customers_bp.route('/add', methods=['POST'])
@login_required
def add_customer():
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('customers.index'))
    
    phone = request.form.get('phone')
    name = request.form.get('name')
    address = request.form.get('address')
    balance = request.form.get('balance')
    notes = request.form.get('notes')
    
    if not phone or not name:
        flash('رقم الهاتف والاسم مطلوبان.', 'warning')
        return render_template('customers_add.html', customer=None)
    
    existing = Customer.query.get(phone)
    if existing:
        flash('هذا الرقم مسجل بالفعل.', 'danger')
        return render_template('customers_add.html', customer=None)
    
    try:
        new_customer = Customer(
            phone=phone,
            name=name,
            address=address or '',
            balance=float(balance) if balance else 0.0,
            notes=notes or ''
        )
        db.session.add(new_customer)
        db.session.commit()
        flash('تم إضافة العميل بنجاح!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ: {str(e)}', 'danger')
    
    return redirect(url_for('customers.index'))

# ===== صفحة تعديل عميل (GET) =====
@customers_bp.route('/edit/<string:phone>', methods=['GET'])
@login_required
def edit_customer_page(phone):
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('customers.index'))
    
    customer = Customer.query.get_or_404(phone)
    return render_template('customers_add.html', customer=customer)

# ===== تعديل عميل (POST) =====
@customers_bp.route('/edit/<string:phone>', methods=['POST'])
@login_required
def edit_customer(phone):
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('customers.index'))
    
    customer = Customer.query.get_or_404(phone)
    
    name = request.form.get('name')
    address = request.form.get('address')
    balance = request.form.get('balance')
    notes = request.form.get('notes')
    
    if not name:
        flash('الاسم مطلوب.', 'warning')
        return render_template('customers_add.html', customer=customer)
    
    try:
        customer.name = name
        customer.address = address or ''
        customer.balance = float(balance) if balance else 0.0
        customer.notes = notes or ''
        db.session.commit()
        flash('تم تحديث العميل بنجاح!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ: {str(e)}', 'danger')
    
    return redirect(url_for('customers.index'))

# ===== حذف عميل =====
@customers_bp.route('/delete/<string:phone>', methods=['POST'])
@login_required
def delete_customer(phone):
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403
    
    customer = Customer.query.get_or_404(phone)
    
    # التحقق من وجود فواتير مرتبطة
    if customer.sales and len(customer.sales) > 0:
        return jsonify({'status': 'error', 'message': 'لا يمكن حذف عميل لديه فواتير مسجلة.'}), 400
    
    try:
        db.session.delete(customer)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500