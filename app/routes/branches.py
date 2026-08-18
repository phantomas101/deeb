from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Branch

branches_bp = Blueprint('branches', __name__)

# ===== عرض صفحة الفروع =====
@branches_bp.route('/')
@login_required
def index():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه الصفحة.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    branches = Branch.query.order_by(Branch.is_main.desc(), Branch.id).all()
    return render_template('branches.html', branches=branches)

# ===== صفحة إضافة فرع جديد (GET) =====
@branches_bp.route('/add', methods=['GET'])
@login_required
def add_branch_page():
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('branches.index'))
    return render_template('branches_add.html')

# ===== إضافة فرع جديد (POST) =====
@branches_bp.route('/add', methods=['POST'])
@login_required
def add_branch():
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('branches.index'))
    
    name = request.form.get('name')
    is_main = request.form.get('is_main') == 'on'
    
    if not name:
        flash('اسم الفرع مطلوب.', 'warning')
        return render_template('branches_add.html')
    
    if is_main:
        Branch.query.update({Branch.is_main: False})
    
    new_branch = Branch(name=name, is_main=is_main)
    db.session.add(new_branch)
    db.session.commit()
    
    flash('تم إضافة الفرع بنجاح!', 'success')
    return redirect(url_for('branches.index'))

# ===== حذف فرع =====
@branches_bp.route('/delete/<int:branch_id>', methods=['POST'])
@login_required
def delete_branch(branch_id):
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403
    
    branch = Branch.query.get_or_404(branch_id)
    if branch.is_main:
        return jsonify({'status': 'error', 'message': 'لا يمكن حذف الفرع الرئيسي'}), 400
    if branch.products and len(branch.products) > 0:
        return jsonify({'status': 'error', 'message': 'لا يمكن حذف فرع يحتوي على منتجات.'}), 400
    
    db.session.delete(branch)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'تم الحذف'})

# ===== تعيين فرع كرئيسي =====
@branches_bp.route('/set-main/<int:branch_id>', methods=['POST'])
@login_required
def set_main_branch(branch_id):
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403
    
    Branch.query.update({Branch.is_main: False})
    branch = Branch.query.get_or_404(branch_id)
    branch.is_main = True
    db.session.commit()
    return jsonify({'status': 'success', 'message': f'تم تعيين {branch.name} كفرع رئيسي'})