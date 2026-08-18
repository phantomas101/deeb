from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Supplier

suppliers_bp = Blueprint('suppliers', __name__)

# ===== عرض صفحة الموردين =====
@suppliers_bp.route('/')
@login_required
def index():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه الصفحة.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('suppliers.html', suppliers=suppliers)

# ===== صفحة إضافة مورد جديد (GET) =====
@suppliers_bp.route('/add', methods=['GET'])
@login_required
def add_supplier_page():
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('suppliers.index'))
    return render_template('suppliers_add.html', supplier=None)

# ===== إضافة مورد جديد (POST) =====
@suppliers_bp.route('/add', methods=['POST'])
@login_required
def add_supplier():
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('suppliers.index'))
    
    phone = request.form.get('phone')
    name = request.form.get('name')
    address = request.form.get('address')
    balance = request.form.get('balance')
    notes = request.form.get('notes')
    
    if not phone or not name:
        flash('رقم الهاتف والاسم مطلوبان.', 'warning')
        return render_template('suppliers_add.html', supplier=None)
    
    existing = Supplier.query.get(phone)
    if existing:
        flash('هذا الرقم مسجل بالفعل.', 'danger')
        return render_template('suppliers_add.html', supplier=None)
    
    try:
        new_supplier = Supplier(
            phone=phone,
            name=name,
            address=address or '',
            balance=float(balance) if balance else 0.0,
            notes=notes or ''
        )
        db.session.add(new_supplier)
        db.session.commit()
        flash('تم إضافة المورد بنجاح!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ: {str(e)}', 'danger')
    
    return redirect(url_for('suppliers.index'))

# ===== صفحة تعديل مورد (GET) =====
@suppliers_bp.route('/edit/<string:phone>', methods=['GET'])
@login_required
def edit_supplier_page(phone):
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('suppliers.index'))
    
    supplier = Supplier.query.get_or_404(phone)
    return render_template('suppliers_add.html', supplier=supplier)

# ===== تعديل مورد (POST) =====
@suppliers_bp.route('/edit/<string:phone>', methods=['POST'])
@login_required
def edit_supplier(phone):
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('suppliers.index'))
    
    supplier = Supplier.query.get_or_404(phone)
    
    name = request.form.get('name')
    address = request.form.get('address')
    balance = request.form.get('balance')
    notes = request.form.get('notes')
    
    if not name:
        flash('الاسم مطلوب.', 'warning')
        return render_template('suppliers_add.html', supplier=supplier)
    
    try:
        supplier.name = name
        supplier.address = address or ''
        supplier.balance = float(balance) if balance else 0.0
        supplier.notes = notes or ''
        db.session.commit()
        flash('تم تحديث المورد بنجاح!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ: {str(e)}', 'danger')
    
    return redirect(url_for('suppliers.index'))

# ===== حذف مورد =====
@suppliers_bp.route('/delete/<string:phone>', methods=['POST'])
@login_required
def delete_supplier(phone):
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403
    
    supplier = Supplier.query.get_or_404(phone)
    
    if supplier.purchases and len(supplier.purchases) > 0:
        return jsonify({'status': 'error', 'message': 'لا يمكن حذف مورد لديه فواتير مشتريات مسجلة.'}), 400
    
    try:
        db.session.delete(supplier)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500