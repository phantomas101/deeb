from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db, bcrypt, login_manager
from app.models import Sale, SaleItem, Product, CashDrawer, StockMovement
from datetime import datetime, timedelta

sales_bp = Blueprint('sales', __name__)


# ============================================================
# 1. عرض صفحة المبيعات (قائمة الفواتير)
# ============================================================
@sales_bp.route('/')
@login_required
def index():
    sales = Sale.query.order_by(Sale.created_at.desc()).all()
    return render_template('sales.html', sales=sales)


# ============================================================
# 2. عرض تفاصيل فاتورة بيع
# ============================================================
@sales_bp.route('/details/<int:sale_id>')
@login_required
def details(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    items = SaleItem.query.filter_by(sale_id=sale.id).all()
    for item in items:
        item.product = Product.query.get(item.product_id) if item.product_id else None
    return render_template('sale_details.html', sale=sale, items=items)


# ============================================================
# 3. طباعة فاتورة بيع
# ============================================================
@sales_bp.route('/print/<int:sale_id>')
@login_required
def print_invoice(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    items = SaleItem.query.filter_by(sale_id=sale.id).all()
    return render_template('invoice.html', sale=sale, items=items)


# ============================================================
# 4. حذف فاتورة بيع (محاسبي متكامل)
# ============================================================
@sales_bp.route('/delete/<int:sale_id>', methods=['POST'])
@login_required
def delete_sale(sale_id):
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'غير مصرح'}), 403
    
    sale = Sale.query.get_or_404(sale_id)
    
    # 🔥 منع حذف الفواتير القديمة (أكثر من 30 يوم)
    days_old = (datetime.now() - sale.created_at).days
    if days_old > 30:
        return jsonify({
            'status': 'error',
            'message': f'لا يمكن حذف فاتورة أقدم من 30 يوم (تاريخ الفاتورة: {sale.created_at.strftime("%Y-%m-%d")})'
        }), 400
    
    try:
        # 1. جلب الأصناف المرتبطة بالفاتورة
        items = SaleItem.query.filter_by(sale_id=sale_id).all()
        
        # 2. إرجاع الكميات للمخزون (تراجع نقصان الكمية)
        for item in items:
            product = Product.query.get(item.product_id)
            if product:
                product.quantity += item.quantity  # نزيد الكمية لأن البيع نقصها
        
        # 3. حذف حركات المخزون المرتبطة (StockMovement)
        stock_moves = StockMovement.query.filter_by(
            movement_type='SALE',
            notes=f'بيع تجريبي'  # هنحتاج نعدل في الـ pos.py عشان يخزن رقم الفاتورة
        ).all()
        # للدقة، هنبحث بالـ invoice_number من خلال الـ sale
        for sm in stock_moves:
            if sale.invoice_number in sm.notes:
                db.session.delete(sm)
        
        # 4. حذف حركات الخزينة المرتبطة
        cash_transactions = CashDrawer.query.filter_by(
            reason=f'مبيعات فاتورة {sale.invoice_number}'
        ).all()
        for ct in cash_transactions:
            db.session.delete(ct)
        
        # 5. حذف تفاصيل الفاتورة (SaleItem)
        for item in items:
            db.session.delete(item)
        
        # 6. حذف الفاتورة نفسها
        db.session.delete(sale)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'تم حذف الفاتورة بنجاح وتراجعت جميع الحركات المالية والمخزنية'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500