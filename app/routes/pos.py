from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Product, Sale, SaleItem, CashDrawer, Branch, StockMovement, Customer
from datetime import datetime
import traceback
import logging
import os
import sys

pos_bp = Blueprint('pos', __name__)
logger = logging.getLogger(__name__)

# ============================================================
# تحديد المسار الجذر (لخدمة الصور)
# ============================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads', 'products')


# ============================================================
# 1. عرض صفحة نقاط البيع - 🔥 معدل لعرض منتجات الرئيسي + فرع المستخدم
# ============================================================
@pos_bp.route('/')
@login_required
def index():
    if 'cart' not in session:
        session['cart'] = []
    
    # 🔥 الحصول على الفرع الرئيسي
    main_branch = Branch.query.filter_by(is_main=True).first()
    
    # 🔥 جلب المنتجات من الفرع الرئيسي + فرع المستخدم (إذا كان مختلفاً)
    products_list = []
    
    # 1. منتجات الفرع الرئيسي (دائماً)
    if main_branch:
        main_products = Product.query.filter_by(branch_id=main_branch.id).all()
        products_list.extend(main_products)
    
    # 2. منتجات فرع المستخدم (إذا كان مختلفاً عن الرئيسي)
    if current_user.branch_id and (not main_branch or current_user.branch_id != main_branch.id):
        user_branch_products = Product.query.filter_by(branch_id=current_user.branch_id).all()
        # إضافة منتجات فرع المستخدم دون تكرار (باستخدام الـ id)
        existing_ids = {p.id for p in products_list}
        for p in user_branch_products:
            if p.id not in existing_ids:
                products_list.append(p)
                existing_ids.add(p.id)
    
    # 3. إذا لم يكن هناك فرع رئيسي ولا فرع للمستخدم، اعرض كل المنتجات
    if not products_list:
        products_list = Product.query.all()
    
    # إزالة التكرارات (في حالة وجود منتجات مكررة بين الفروع)
    seen_ids = set()
    unique_products = []
    for p in products_list:
        if p.id not in seen_ids:
            seen_ids.add(p.id)
            unique_products.append(p)
    
    products = unique_products
    customers = Customer.query.order_by(Customer.name).all()
    
    # طباعة عدد المنتجات لمساعدة التصحيح
    print(f"📦 عدد المنتجات المعروضة في POS: {len(products)}")
    if main_branch:
        print(f"🏢 الفرع الرئيسي: {main_branch.name}")
    if current_user.branch_id:
        print(f"👤 فرع المستخدم: {current_user.branch_id}")
    
    return render_template('pos.html', products=products, customers=customers)


# ============================================================
# 2. جلب محتويات السلة
# ============================================================
@pos_bp.route('/get-cart', methods=['GET'])
@login_required
def get_cart():
    cart = session.get('cart', [])
    total_items = sum(item.get('quantity', 0) for item in cart)
    return jsonify({'cart': cart, 'total_items': total_items})


# ============================================================
# 3. البحث عن العملاء
# ============================================================
@pos_bp.route('/search-customers', methods=['GET'])
@login_required
def search_customers():
    query = request.args.get('q', '')
    if len(query) < 1:
        return jsonify([])
    customers = Customer.query.filter(
        (Customer.name.contains(query)) | (Customer.phone.contains(query))
    ).limit(10).all()
    results = [{'phone': c.phone, 'name': c.name, 'balance': c.balance} for c in customers]
    return jsonify(results)


# ============================================================
# 4. البحث عن المنتجات (من الرئيسي وفرع المستخدم)
# ============================================================
@pos_bp.route('/search', methods=['GET'])
@login_required
def search_product():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    main_branch = Branch.query.filter_by(is_main=True).first()
    branch_ids = []
    
    # إضافة الفرع الرئيسي
    if main_branch:
        branch_ids.append(main_branch.id)
    
    # إضافة فرع المستخدم
    if current_user.branch_id and (not main_branch or current_user.branch_id != main_branch.id):
        branch_ids.append(current_user.branch_id)
    
    # إذا لم توجد فروع، ابحث في كل المنتجات
    if not branch_ids:
        products = Product.query.filter(Product.name.contains(query)).limit(10).all()
    else:
        products = Product.query.filter(
            Product.branch_id.in_(branch_ids),
            Product.name.contains(query)
        ).limit(10).all()
    
    results = [{
        'id': p.id,
        'name': p.name,
        'selling_price': p.selling_price,
        'wholesale_price': p.wholesale_price,
        'quantity': p.quantity
    } for p in products]
    return jsonify(results)


# ============================================================
# 5. إضافة منتج للسلة
# ============================================================
@pos_bp.route('/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    sale_type = request.form.get('sale_type', 'retail')
    
    if not product_id:
        return jsonify({'status': 'error', 'message': 'المنتج غير موجود'}), 400
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'status': 'error', 'message': 'المنتج غير موجود'}), 404
    
    if product.quantity < quantity:
        return jsonify({'status': 'error', 'message': f'الكمية المتاحة {product.quantity} فقط'}), 400
    
    if product.quantity <= 0:
        return jsonify({'status': 'error', 'message': 'هذا المنتج غير متوفر حالياً'}), 400
    
    unit_price = product.wholesale_price if sale_type == 'wholesale' else product.selling_price
    
    cart = session.get('cart', [])
    
    found = False
    for item in cart:
        if item.get('product_id') == product_id and item.get('sale_type') == sale_type:
            new_qty = item.get('quantity', 0) + quantity
            if new_qty > product.quantity:
                return jsonify({'status': 'error', 'message': f'الكمية الإجمالية تتجاوز المخزون ({product.quantity})'}), 400
            item['quantity'] = new_qty
            item['unit_price'] = unit_price
            found = True
            break
    
    if not found:
        cart.append({
            'product_id': product.id,
            'name': product.name,
            'sale_type': sale_type,
            'unit_price': unit_price,
            'quantity': quantity,
            'max_quantity': product.quantity
        })
    
    session['cart'] = cart
    session.modified = True
    
    total_items = sum(item.get('quantity', 0) for item in cart)
    return jsonify({
        'status': 'success',
        'message': 'تم إضافة المنتج',
        'cart': cart,
        'total_items': total_items
    })


# ============================================================
# 6. حذف منتج من السلة
# ============================================================
@pos_bp.route('/remove-from-cart/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    cart = session.get('cart', [])
    cart = [item for item in cart if item.get('product_id') != product_id]
    session['cart'] = cart
    session.modified = True
    total_items = sum(item.get('quantity', 0) for item in cart)
    return jsonify({'status': 'success', 'cart': cart, 'total_items': total_items})


# ============================================================
# 7. تحديث الكمية
# ============================================================
@pos_bp.route('/update-cart', methods=['POST'])
@login_required
def update_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    
    if quantity <= 0:
        return remove_from_cart(product_id)
    
    cart = session.get('cart', [])
    for item in cart:
        if item.get('product_id') == product_id:
            product = Product.query.get(product_id)
            if product and quantity > product.quantity:
                return jsonify({'status': 'error', 'message': f'الكمية المتاحة {product.quantity} فقط'}), 400
            item['quantity'] = quantity
            break
    
    session['cart'] = cart
    session.modified = True
    total_items = sum(item.get('quantity', 0) for item in cart)
    return jsonify({'status': 'success', 'cart': cart, 'total_items': total_items})


# ============================================================
# 8. تفريغ السلة
# ============================================================
@pos_bp.route('/clear-cart', methods=['POST'])
@login_required
def clear_cart():
    session.pop('cart', None)
    flash('تم تفريغ السلة.', 'info')
    return redirect(url_for('pos.index'))


# ============================================================
# 9. إنهاء الفاتورة
# ============================================================
@pos_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart = session.get('cart', [])
    
    if not cart:
        flash('السلة فارغة!', 'warning')
        return redirect(url_for('pos.index'))
    
    # تنظيف السلة
    cleaned_cart = []
    for item in cart:
        if 'product_id' not in item:
            continue
        if 'unit_price' not in item or item['unit_price'] == 0:
            product = Product.query.get(item.get('product_id'))
            if product:
                sale_type = item.get('sale_type', 'retail')
                item['unit_price'] = product.wholesale_price if sale_type == 'wholesale' else product.selling_price
            else:
                flash(f'تم تخطي المنتج {item.get("name", "غير معروف")} لأنه غير موجود', 'warning')
                continue
        if 'quantity' not in item or item['quantity'] <= 0:
            continue
        cleaned_cart.append(item)
    
    if not cleaned_cart:
        flash('لا توجد منتجات صالحة في السلة!', 'danger')
        return redirect(url_for('pos.index'))
    
    cart = cleaned_cart
    session['cart'] = cart
    session.modified = True
    
    customer_phone = request.form.get('customer_phone')
    sale_type = request.form.get('sale_type', 'retail')
    payment_type = request.form.get('payment_type', 'cash')
    discount = float(request.form.get('discount', 0))
    paid_amount = float(request.form.get('paid_amount', 0))
    discount_type = request.form.get('discount_type', 'fixed')
    
    subtotal = sum(item['unit_price'] * item['quantity'] for item in cart)
    
    if discount_type == 'percentage':
        discount_value = (discount / 100) * subtotal
    else:
        discount_value = discount
    
    net_amount = subtotal - discount_value
    
    change = paid_amount - net_amount
    if change < 0:
        flash('المبلغ المدفوع أقل من إجمالي الفاتورة!', 'danger')
        return redirect(url_for('pos.index'))
    
    try:
        if current_user.branch_id:
            branch = Branch.query.get(current_user.branch_id)
        else:
            branch = Branch.query.filter_by(is_main=True).first()
        
        if not branch:
            flash('الفرع غير موجود!', 'danger')
            return redirect(url_for('pos.index'))
        
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        sale = Sale(
            invoice_number=invoice_number,
            branch_id=branch.id,
            customer_phone=customer_phone if customer_phone else None,
            total_amount=subtotal,
            discount=discount_value,
            net_amount=net_amount,
            paid_amount=paid_amount,
            change_amount=change,
            payment_type=payment_type,
            sale_type=sale_type,
            created_by=current_user.id,
            created_at=datetime.now()
        )
        db.session.add(sale)
        db.session.flush()
        
        for item in cart:
            product = Product.query.get(item['product_id'])
            if not product:
                db.session.rollback()
                flash(f'المنتج {item["name"]} غير موجود!', 'danger')
                return redirect(url_for('pos.index'))
            
            if product.quantity < item['quantity']:
                db.session.rollback()
                flash(f'المنتج {product.name} غير متوفر بالكمية المطلوبة!', 'danger')
                return redirect(url_for('pos.index'))
            
            product.quantity -= item['quantity']
            
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                total=item['unit_price'] * item['quantity']
            )
            db.session.add(sale_item)
            
            stock_move = StockMovement(
                product_id=product.id,
                from_branch_id=branch.id,
                to_branch_id=None,
                quantity_change=-item['quantity'],
                movement_type='SALE',
                notes=f'بيع فاتورة {invoice_number}',
                sale_id=sale.id,
                created_at=datetime.now()
            )
            db.session.add(stock_move)
        
        if payment_type == 'credit' and customer_phone:
            customer = Customer.query.get(customer_phone)
            if customer:
                customer.balance += net_amount
        
        if payment_type == 'cash' and net_amount > 0:
            cash_transaction = CashDrawer(
                branch_id=branch.id,
                transaction_type='IN',
                amount=net_amount,
                reason=f'مبيعات فاتورة {invoice_number}',
                created_at=datetime.now()
            )
            db.session.add(cash_transaction)
        
        db.session.commit()
        session.pop('cart', None)
        
        return redirect(url_for('pos.invoice', sale_id=sale.id))
        
    except Exception as e:
        db.session.rollback()
        logger.error("=" * 60)
        logger.error("🔥 حدث خطأ في إنهاء الفاتورة:")
        logger.error(f"📌 رسالة الخطأ: {str(e)}")
        traceback.print_exc()
        logger.error("=" * 60)
        flash(f'حدث خطأ: {str(e)}', 'danger')
        return redirect(url_for('pos.index'))


# ============================================================
# 10. عرض صفحة طباعة الفاتورة
# ============================================================
@pos_bp.route('/invoice/<int:sale_id>')
@login_required
def invoice(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    items = SaleItem.query.filter_by(sale_id=sale.id).all()
    return render_template('invoice.html', sale=sale, items=items)


# ============================================================
# 11. خدمة الصور
# ============================================================
@pos_bp.route('/product-image/<filename>')
@login_required
def product_image(filename):
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/jpeg')
    else:
        return '', 404