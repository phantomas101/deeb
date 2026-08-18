from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Product, Branch
import os
import sys
from werkzeug.utils import secure_filename
from datetime import datetime

inventory_bp = Blueprint('inventory', __name__)

# ============================================================
# تحديد المسار الجذر
# ============================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads', 'products')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# دالة التحقق من الكود
# ============================================================
def is_code_unique(code, exclude_product_id=None):
    if not code:
        return True
    query = Product.query.filter(Product.code == code)
    if exclude_product_id:
        query = query.filter(Product.id != exclude_product_id)
    return query.first() is None


# ============================================================
# عرض صفحة المخزون
# ============================================================
@inventory_bp.route('/')
@login_required
def index():
    products = Product.query.order_by(Product.id.desc()).all()
    show_cost = (current_user.role == 'admin')
    return render_template('inventory.html', products=products, show_cost=show_cost)


# ============================================================
# صفحة إضافة منتج جديد (GET)
# ============================================================
@inventory_bp.route('/add', methods=['GET'])
@login_required
def add_product_page():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه العملية.', 'danger')
        return redirect(url_for('inventory.index'))
    return render_template('inventory_add.html')


# ============================================================
# إضافة منتج جديد (POST)
# ============================================================
@inventory_bp.route('/add', methods=['POST'])
@login_required
def add_product():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه العملية.', 'danger')
        return redirect(url_for('inventory.index'))
    
    name = request.form.get('name')
    code = request.form.get('code')
    category = request.form.get('category')
    cost_price = request.form.get('cost_price')
    selling_price = request.form.get('selling_price')
    wholesale_price = request.form.get('wholesale_price')
    quantity = request.form.get('quantity')
    min_stock = request.form.get('min_stock')

    if not name or not selling_price:
        flash('اسم المنتج وسعر البيع إلزاميان.', 'warning')
        return render_template('inventory_add.html')

    if code and not is_code_unique(code):
        flash('⚠️ كود المنتج موجود بالفعل. يرجى اختيار كود مختلف.', 'danger')
        return render_template('inventory_add.html')

    image_filename = None
    if 'image' in request.files:
        image = request.files['image']
        if image and allowed_file(image.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{image.filename}")
            image.save(os.path.join(UPLOAD_FOLDER, filename))
            image_filename = filename

    try:
        main_branch = Branch.query.filter_by(is_main=True).first()
        if not main_branch:
            flash('الفرع الرئيسي غير موجود.', 'danger')
            return redirect(url_for('inventory.index'))

        new_product = Product(
            name=name,
            code=code or None,
            category=category or 'Laptops',
            cost_price=float(cost_price) if cost_price else 0.0,
            selling_price=float(selling_price),
            wholesale_price=float(wholesale_price) if wholesale_price else 0.0,
            quantity=int(quantity) if quantity else 0,
            min_stock=int(min_stock) if min_stock else 5,
            image_filename=image_filename,
            branch_id=main_branch.id
        )
        db.session.add(new_product)
        db.session.commit()
        flash('تم إضافة المنتج بنجاح!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء الإضافة: {str(e)}', 'danger')
    
    return redirect(url_for('inventory.index'))


# ============================================================
# تعديل منتج
# ============================================================
@inventory_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه العملية.', 'danger')
        return redirect(url_for('inventory.index'))

    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        category = request.form.get('category')
        cost_price = request.form.get('cost_price')
        selling_price = request.form.get('selling_price')
        wholesale_price = request.form.get('wholesale_price')
        quantity = request.form.get('quantity')
        min_stock = request.form.get('min_stock')

        if not name or not selling_price:
            flash('اسم المنتج وسعر البيع إلزاميان.', 'warning')
            return render_template('inventory_edit.html', product=product)

        if code and not is_code_unique(code, exclude_product_id=product.id):
            flash('⚠️ كود المنتج موجود بالفعل لدى منتج آخر. يرجى اختيار كود مختلف.', 'danger')
            return render_template('inventory_edit.html', product=product)

        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                if product.image_filename:
                    old_path = os.path.join(UPLOAD_FOLDER, product.image_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{image.filename}")
                image.save(os.path.join(UPLOAD_FOLDER, filename))
                product.image_filename = filename

        try:
            product.name = name
            product.code = code or None
            product.category = category or 'Laptops'
            product.cost_price = float(cost_price) if cost_price else 0.0
            product.selling_price = float(selling_price)
            product.wholesale_price = float(wholesale_price) if wholesale_price else 0.0
            product.quantity = int(quantity) if quantity else 0
            product.min_stock = int(min_stock) if min_stock else 5
            db.session.commit()
            flash('تم تحديث المنتج بنجاح!', 'success')
            return redirect(url_for('inventory.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء التعديل: {str(e)}', 'danger')
    
    return render_template('inventory_edit.html', product=product)


# ============================================================
# حذف منتج
# ============================================================
@inventory_bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403
    
    product = Product.query.get_or_404(product_id)
    try:
        if product.image_filename:
            image_path = os.path.join(UPLOAD_FOLDER, product.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        db.session.delete(product)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'تم الحذف بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================================
# خدمة الصور
# ============================================================
@inventory_bp.route('/product-image/<filename>')
@login_required
def product_image(filename):
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/jpeg')
    else:
        return '', 404