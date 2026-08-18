from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Purchase, PurchaseItem, Product, Supplier, StockMovement, CashDrawer, Branch
from datetime import datetime, timezone

purchases_bp = Blueprint('purchases', __name__)

# ============================================================
# 1. عرض صفحة المشتريات (قائمة الفواتير)
# ============================================================
@purchases_bp.route('/')
@login_required
def index():
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    for purchase in purchases:
        purchase.supplier = Supplier.query.get(purchase.supplier_phone) if purchase.supplier_phone else None
    return render_template('purchases.html', purchases=purchases)


# ============================================================
# 2. عرض تفاصيل فاتورة شراء
# ============================================================
@purchases_bp.route('/details/<int:purchase_id>')
@login_required
def details(purchase_id):
    purchase = Purchase.query.get_or_404(purchase_id)
    items = PurchaseItem.query.filter_by(purchase_id=purchase_id).all()
    for item in items:
        item.product = Product.query.get(item.product_id) if item.product_id else None
    supplier = Supplier.query.get(purchase.supplier_phone) if purchase.supplier_phone else None
    return render_template('purchase_details.html', purchase=purchase, items=items, supplier=supplier)


# ============================================================
# 3. عرض صفحة إضافة فاتورة شراء جديدة (GET)
# ============================================================
@purchases_bp.route('/add', methods=['GET'])
@login_required
def add_purchase_page():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه العملية.', 'danger')
        return redirect(url_for('purchases.index'))
    
    suppliers = Supplier.query.all()
    products = Product.query.all()
    now = datetime.now(timezone.utc)
    return render_template('purchase_add.html', suppliers=suppliers, products=products, now=now)


# ============================================================
# 4. البحث عن الموردين (للاكتمال التلقائي)
# ============================================================
@purchases_bp.route('/suppliers-search', methods=['GET'])
@login_required
def suppliers_search():
    query = request.args.get('q', '')
    if len(query) < 1:
        return jsonify([])
    
    suppliers = Supplier.query.filter(
        (Supplier.name.contains(query)) | (Supplier.phone.contains(query))
    ).limit(10).all()
    
    results = [{'phone': s.phone, 'name': s.name} for s in suppliers]
    return jsonify(results)


# ============================================================
# 5. API للبحث عن المنتجات
# ============================================================
@purchases_bp.route('/search-products', methods=['GET'])
@login_required
def search_products():
    query = request.args.get('q', '')
    if len(query) < 1:
        return jsonify([])
    
    products = Product.query.filter(Product.name.contains(query)).limit(10).all()
    results = [{'id': p.id, 'name': p.name, 'cost_price': p.cost_price} for p in products]
    return jsonify(results)


# ============================================================
# 6. إضافة منتج جديد بسرعة (من داخل فاتورة الشراء)
# ============================================================
@purchases_bp.route('/quick-add-product', methods=['POST'])
@login_required
def quick_add_product():
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403
    
    try:
        name = request.form.get('name')
        category = request.form.get('category')
        cost_price = request.form.get('cost_price')
        selling_price = request.form.get('selling_price')
        min_stock = request.form.get('min_stock')
        
        if not name:
            return jsonify({'status': 'error', 'message': 'اسم المنتج مطلوب'}), 400
        
        existing = Product.query.filter_by(name=name).first()
        if existing:
            return jsonify({
                'status': 'error',
                'message': 'هذا المنتج موجود بالفعل',
                'product': {
                    'id': existing.id,
                    'name': existing.name,
                    'cost_price': existing.cost_price
                }
            }), 400
        
        main_branch = Branch.query.filter_by(is_main=True).first()
        if not main_branch:
            return jsonify({'status': 'error', 'message': 'الفرع الرئيسي غير موجود'}), 400
        
        new_product = Product(
            name=name,
            category=category or 'Laptops',
            cost_price=float(cost_price) if cost_price else 0.0,
            selling_price=float(selling_price) if selling_price else 0.0,
            wholesale_price=0.0,
            quantity=0,
            min_stock=int(min_stock) if min_stock else 5,
            branch_id=main_branch.id
        )
        db.session.add(new_product)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'تم إضافة المنتج',
            'product': {
                'id': new_product.id,
                'name': new_product.name,
                'cost_price': new_product.cost_price
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'خطأ في السيرفر: {str(e)}'}), 500


# ============================================================
# 7. إضافة فاتورة شراء جديدة (POST)
# ============================================================
@purchases_bp.route('/add', methods=['POST'])
@login_required
def add_purchase():
    if current_user.role != 'admin':
        flash('غير مسموح لك بهذه العملية.', 'danger')
        return redirect(url_for('purchases.index'))

    supplier_phone = request.form.get('supplier_phone', '').strip()
    payment_type = request.form.get('payment_type', 'cash')
    product_ids = request.form.getlist('product_id[]')
    quantities = request.form.getlist('quantity[]')
    cost_prices = request.form.getlist('cost_price[]')

    if payment_type == 'credit' and not supplier_phone:
        flash('الدفع الآجل يتطلب اختيار المورد.', 'warning')
        suppliers = Supplier.query.all()
        products = Product.query.all()
        now = datetime.now(timezone.utc)
        return render_template('purchase_add.html', suppliers=suppliers, products=products, now=now)

    if not product_ids or len(product_ids) == 0:
        flash('يرجى إضافة منتج واحد على الأقل.', 'warning')
        suppliers = Supplier.query.all()
        products = Product.query.all()
        now = datetime.now(timezone.utc)
        return render_template('purchase_add.html', suppliers=suppliers, products=products, now=now)

    try:
        purchase = Purchase(
            invoice_number=f"PO-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            supplier_phone=supplier_phone if supplier_phone else None,
            total_cost=0,
            payment_type=payment_type,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(purchase)
        db.session.flush()

        total_cost = 0
        main_branch = Branch.query.filter_by(is_main=True).first()
        if not main_branch:
            flash('الفرع الرئيسي غير موجود!', 'danger')
            db.session.rollback()
            return redirect(url_for('purchases.index'))

        for i in range(len(product_ids)):
            product_id = int(product_ids[i])
            quantity = int(quantities[i])
            cost_price = float(cost_prices[i])

            if quantity <= 0 or cost_price < 0:
                continue

            product = Product.query.get(product_id)
            if not product:
                flash(f'المنتج غير موجود.', 'danger')
                db.session.rollback()
                return redirect(url_for('purchases.add_purchase_page'))

            product.quantity += quantity

            item_total = cost_price * quantity
            purchase_item = PurchaseItem(
                purchase_id=purchase.id,
                product_id=product.id,
                quantity=quantity,
                cost_price=cost_price,
                total=item_total
            )
            db.session.add(purchase_item)
            total_cost += item_total

            stock_move = StockMovement(
                product_id=product.id,
                from_branch_id=None,
                to_branch_id=main_branch.id,
                quantity_change=quantity,
                movement_type='PURCHASE',
                notes=f'شراء عبر فاتورة {purchase.invoice_number}',
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(stock_move)

        purchase.total_cost = total_cost

        if payment_type == 'cash':
            cash_out = CashDrawer(
                branch_id=main_branch.id,
                transaction_type='OUT',
                amount=total_cost,
                reason=f'شراء بضاعة فاتورة {purchase.invoice_number}',
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(cash_out)
        else:
            supplier = Supplier.query.get(supplier_phone)
            if supplier:
                supplier.balance += total_cost

        db.session.commit()
        flash(f'تم إضافة فاتورة الشراء بنجاح! رقم: {purchase.invoice_number}', 'success')
        return redirect(url_for('purchases.index'))

    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حفظ الفاتورة: {str(e)}', 'danger')
        suppliers = Supplier.query.all()
        products = Product.query.all()
        now = datetime.now(timezone.utc)
        return render_template('purchase_add.html', suppliers=suppliers, products=products, now=now)


# ============================================================
# 8. حذف فاتورة شراء (مع التراجع المحاسبي الكامل)
# ============================================================
@purchases_bp.route('/delete/<int:purchase_id>', methods=['POST'])
@login_required
def delete_purchase(purchase_id):
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403
    
    purchase = Purchase.query.get_or_404(purchase_id)
    
    try:
        # 1. التراجع عن تأثير الأصناف على المخزون (نقص الكمية)
        items = PurchaseItem.query.filter_by(purchase_id=purchase_id).all()
        for item in items:
            product = Product.query.get(item.product_id)
            if product:
                product.quantity -= item.quantity
            db.session.delete(item)
        
        # 2. 🔥 حذف حركات المخزون (StockMovement) المرتبطة بهذه الفاتورة
        #    نبحث باستخدام movement_type='PURCHASE' و notes التي تحتوي على رقم الفاتورة
        stock_moves = StockMovement.query.filter(
            StockMovement.movement_type == 'PURCHASE',
            StockMovement.notes.contains(purchase.invoice_number)
        ).all()
        for sm in stock_moves:
            db.session.delete(sm)
        
        # 3. التراجع المالي حسب نوع الدفع
        if purchase.payment_type == 'cash':
            # حذف حركة الخزينة (الصرف)
            cash_transactions = CashDrawer.query.filter_by(
                reason=f'شراء بضاعة فاتورة {purchase.invoice_number}'
            ).all()
            for ct in cash_transactions:
                db.session.delete(ct)
        else:
            # آجل: ننقص رصيد المورد
            supplier = Supplier.query.get(purchase.supplier_phone)
            if supplier:
                supplier.balance -= purchase.total_cost
        
        # 4. حذف الفاتورة نفسها
        db.session.delete(purchase)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'تم حذف الفاتورة وجميع حركات المخزون المرتبطة بها بنجاح'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500