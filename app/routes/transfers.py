from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Branch, Product, StockMovement
from datetime import datetime

transfers_bp = Blueprint('transfers', __name__)

# ===== عرض صفحة التحويلات =====
@transfers_bp.route('/')
@login_required
def index():
    transfers = StockMovement.query.filter_by(movement_type='TRANSFER').order_by(StockMovement.created_at.desc()).all()
    branches = Branch.query.all()
    return render_template('transfers.html', transfers=transfers, branches=branches)

# ===== عرض صفحة إضافة تحويل جديد (صادر) =====
@transfers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_transfer():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه العملية.', 'danger')
        return redirect(url_for('transfers.index'))

    main_branch = Branch.query.filter_by(is_main=True).first()
    if not main_branch:
        flash('الفرع الرئيسي غير موجود!', 'danger')
        return redirect(url_for('transfers.index'))
    
    products = Product.query.filter_by(branch_id=main_branch.id).filter(Product.quantity > 0).all()
    other_branches = Branch.query.filter(Branch.id != main_branch.id).all()

    if request.method == 'POST':
        to_branch_id = request.form.get('to_branch_id')
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')

        if not to_branch_id:
            flash('يرجى اختيار الفرع الوجهة.', 'warning')
            return render_template('transfer_add.html', products=products, branches=other_branches)

        if not product_ids or len(product_ids) == 0:
            flash('يرجى إضافة منتج واحد على الأقل.', 'warning')
            return render_template('transfer_add.html', products=products, branches=other_branches)

        try:
            to_branch = Branch.query.get(to_branch_id)
            if not to_branch:
                flash('الفرع الوجهة غير موجود.', 'danger')
                return render_template('transfer_add.html', products=products, branches=other_branches)

            for i in range(len(product_ids)):
                product_id = int(product_ids[i])
                quantity = int(quantities[i])

                if quantity <= 0:
                    continue

                product = Product.query.get(product_id)
                if not product:
                    flash(f'المنتج {product_id} غير موجود.', 'danger')
                    db.session.rollback()
                    return redirect(url_for('transfers.add_transfer'))

                if product.quantity < quantity:
                    flash(f'المنتج {product.name} غير متوفر بالكمية المطلوبة في الفرع الرئيسي (المتاح: {product.quantity})', 'danger')
                    db.session.rollback()
                    return redirect(url_for('transfers.add_transfer'))

                product.quantity -= quantity

                target_product = Product.query.filter_by(name=product.name, branch_id=to_branch.id).first()
                if target_product:
                    target_product.quantity += quantity
                else:
                    new_product = Product(
                        name=product.name,
                        category=product.category,
                        cost_price=product.cost_price,
                        selling_price=product.selling_price,
                        quantity=quantity,
                        min_stock=product.min_stock,
                        branch_id=to_branch.id
                    )
                    db.session.add(new_product)
                    db.session.flush()

                # حركة التحويل للفرع المصدر (سالب)
                stock_move = StockMovement(
                    product_id=product.id,
                    from_branch_id=main_branch.id,
                    to_branch_id=to_branch.id,
                    quantity_change=-quantity,
                    movement_type='TRANSFER',
                    notes=f'نقل من {main_branch.name} إلى {to_branch.name}',
                    created_at=datetime.now(),
                    is_received=False
                )
                db.session.add(stock_move)

                # حركة إضافية للفرع الوجهة (موجب) - للتوثيق
                stock_move_to = StockMovement(
                    product_id=product.id,
                    from_branch_id=main_branch.id,
                    to_branch_id=to_branch.id,
                    quantity_change=quantity,
                    movement_type='TRANSFER',
                    notes=f'استلام من {main_branch.name} إلى {to_branch.name}',
                    created_at=datetime.now(),
                    is_received=False
                )
                db.session.add(stock_move_to)

            db.session.commit()
            flash('تم إجراء التحويل المخزني بنجاح!', 'success')
            return redirect(url_for('transfers.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء حفظ التحويل: {str(e)}', 'danger')
            return render_template('transfer_add.html', products=products, branches=other_branches)

    return render_template('transfer_add.html', products=products, branches=other_branches)


# ============================================================
# 🔥 استلام تحويل وارد (من فرع آخر)
# ============================================================
@transfers_bp.route('/receive-incoming', methods=['GET', 'POST'])
@login_required
def receive_incoming_transfer():
    if current_user.role not in ['admin']:
        flash('غير مسموح لك بهذه العملية.', 'danger')
        return redirect(url_for('transfers.index'))
    
    branches = Branch.query.filter(Branch.id != current_user.branch_id).all()
    
    if request.method == 'POST':
        product_name = request.form.get('product_name', '').strip()
        quantity = request.form.get('quantity', 0, type=int)
        from_branch_id = request.form.get('from_branch_id', type=int)
        notes = request.form.get('notes', '').strip()
        
        if not product_name:
            flash('يرجى إدخال اسم المنتج.', 'warning')
            return render_template('receive_transfer.html', branches=branches)
        if quantity <= 0:
            flash('يرجى إدخال كمية صحيحة (أكبر من صفر).', 'warning')
            return render_template('receive_transfer.html', branches=branches)
        if not from_branch_id:
            flash('يرجى اختيار الفرع المرسل.', 'warning')
            return render_template('receive_transfer.html', branches=branches)
        
        from_branch = Branch.query.get(from_branch_id)
        if not from_branch:
            flash('الفرع المرسل غير موجود.', 'danger')
            return render_template('receive_transfer.html', branches=branches)
        
        try:
            product = Product.query.filter_by(name=product_name, branch_id=current_user.branch_id).first()
            if product:
                product.quantity += quantity
            else:
                product = Product(
                    name=product_name,
                    category='غير مصنف',
                    cost_price=0,
                    selling_price=0,
                    wholesale_price=0,
                    quantity=quantity,
                    min_stock=5,
                    branch_id=current_user.branch_id
                )
                db.session.add(product)
                db.session.flush()
            
            # 🔥 هنا التعديل المهم: ننشئ الكائن ثم نضبط is_received بعده
            stock_move = StockMovement(
                product_id=product.id,
                from_branch_id=from_branch.id,
                to_branch_id=current_user.branch_id,
                quantity_change=quantity,
                movement_type='TRANSFER_IN',
                notes=f'استلام وارد من {from_branch.name} - {notes or "بدون ملاحظات"}',
                created_at=datetime.now()
            )
            # تعيين is_received بعد الإنشاء
            stock_move.is_received = True
            db.session.add(stock_move)
            
            db.session.commit()
            flash(f'✅ تم استلام {quantity} من "{product_name}" من {from_branch.name} بنجاح!', 'success')
            return redirect(url_for('inventory.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء استلام التحويل: {str(e)}', 'danger')
            return render_template('receive_transfer.html', branches=branches)
    
    return render_template('receive_transfer.html', branches=branches)


# ============================================================
# تأكيد استلام تحويل صادر
# ============================================================
@transfers_bp.route('/receive/<int:transfer_id>', methods=['POST'])
@login_required
def receive_transfer(transfer_id):
    if current_user.role not in ['admin']:
        flash('غير مسموح لك بهذه العملية.', 'danger')
        return redirect(url_for('transfers.index'))
    
    transfer = StockMovement.query.get_or_404(transfer_id)
    if transfer.movement_type != 'TRANSFER':
        flash('هذه ليست حركة تحويل.', 'danger')
        return redirect(url_for('transfers.index'))
    
    if transfer.to_branch_id != current_user.branch_id and current_user.role != 'admin':
        flash('لا يمكنك استلام تحويل ليس لفرعك.', 'danger')
        return redirect(url_for('transfers.index'))
    
    if transfer.is_received:
        flash('هذا التحويل تم استلامه بالفعل.', 'warning')
        return redirect(url_for('transfers.index'))
    
    try:
        transfer.is_received = True
        transfer.notes = (transfer.notes or '') + f' - تم الاستلام بواسطة {current_user.username} في {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        db.session.commit()
        flash('✅ تم استلام التحويل بنجاح!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ حدث خطأ أثناء الاستلام: {str(e)}', 'danger')
    
    return redirect(url_for('transfers.index'))


# ===== API للبحث عن المنتجات =====
@transfers_bp.route('/search-products', methods=['GET'])
@login_required
def search_products():
    main_branch = Branch.query.filter_by(is_main=True).first()
    if not main_branch:
        return jsonify([])
    
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    products = Product.query.filter(
        Product.branch_id == main_branch.id,
        Product.name.contains(query),
        Product.quantity > 0
    ).limit(10).all()
    
    results = [{'id': p.id, 'name': p.name, 'quantity': p.quantity} for p in products]
    return jsonify(results)