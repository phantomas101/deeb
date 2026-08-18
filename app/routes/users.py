from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db, bcrypt
from app.models import User, Branch

users_bp = Blueprint('users', __name__)

# ===== عرض صفحة المستخدمين =====
@users_bp.route('/')
@login_required
def index():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه الصفحة.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    users = User.query.order_by(User.id).all()
    branches = Branch.query.all()
    return render_template('users.html', users=users, branches=branches)

# ===== صفحة إضافة مستخدم جديد (GET) =====
@users_bp.route('/add', methods=['GET'])
@login_required
def add_user_page():
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('users.index'))
    branches = Branch.query.all()
    return render_template('users_add.html', branches=branches)

# ===== إضافة مستخدم جديد (POST) =====
@users_bp.route('/add', methods=['POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('users.index'))
    
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    branch_id = request.form.get('branch_id')
    
    if not username or not password:
        flash('اسم المستخدم وكلمة المرور مطلوبان.', 'warning')
        branches = Branch.query.all()
        return render_template('users_add.html', branches=branches)
    
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash('اسم المستخدم موجود بالفعل.', 'danger')
        branches = Branch.query.all()
        return render_template('users_add.html', branches=branches)
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(
        username=username,
        password=hashed_password,
        role=role or 'cashier',
        branch_id=int(branch_id) if branch_id else None
    )
    db.session.add(new_user)
    db.session.commit()
    
    flash('تم إضافة المستخدم بنجاح!', 'success')
    return redirect(url_for('users.index'))

# ===== صفحة تعديل مستخدم (GET) =====
@users_bp.route('/edit/<int:user_id>', methods=['GET'])
@login_required
def edit_user_page(user_id):
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('users.index'))
    
    user = User.query.get_or_404(user_id)
    branches = Branch.query.all()
    return render_template('users_edit.html', user=user, branches=branches)

# ===== تعديل مستخدم (POST) =====
@users_bp.route('/edit/<int:user_id>', methods=['POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        flash('غير مسموح.', 'danger')
        return redirect(url_for('users.index'))
    
    user = User.query.get_or_404(user_id)
    
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    branch_id = request.form.get('branch_id')
    
    if not username:
        flash('اسم المستخدم مطلوب.', 'warning')
        branches = Branch.query.all()
        return render_template('users_edit.html', user=user, branches=branches)
    
    # منع تغيير صلاحية الأدمن الوحيد
    admin_count = User.query.filter_by(role='admin').count()
    if user.role == 'admin' and admin_count <= 1 and role != 'admin':
        flash('لا يمكن تغيير صلاحية الأدمن الوحيد.', 'danger')
        branches = Branch.query.all()
        return render_template('users_edit.html', user=user, branches=branches)
    
    try:
        user.username = username
        user.role = role or 'cashier'
        user.branch_id = int(branch_id) if branch_id else None
        
        if password and len(password) >= 4:
            user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        elif password:
            flash('كلمة المرور يجب أن تكون 4 أحرف على الأقل.', 'warning')
            branches = Branch.query.all()
            return render_template('users_edit.html', user=user, branches=branches)
        
        db.session.commit()
        flash('تم تحديث بيانات المستخدم بنجاح!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ: {str(e)}', 'danger')
    
    return redirect(url_for('users.index'))

# ===== حذف مستخدم =====
@users_bp.route('/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'status': 'error', 'message': 'لا يمكنك حذف حسابك الخاص'}), 400
    
    admin_count = User.query.filter_by(role='admin').count()
    if user.role == 'admin' and admin_count <= 1:
        return jsonify({'status': 'error', 'message': 'لا يمكن حذف الأدمن الوحيد'}), 400
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'تم حذف المستخدم بنجاح'})