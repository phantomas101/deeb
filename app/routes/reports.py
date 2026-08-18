from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.services.report_service import get_sales_report

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/sales')
@login_required
def sales_report():
    if current_user.role != 'admin':
        flash('غير مسموح', 'danger')
        return redirect(url_for('dashboard.index'))
    
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    customer_phone = request.args.get('customer_phone')
    payment_type = request.args.get('payment_type')
    
    data = get_sales_report(date_from, date_to, customer_phone, payment_type)
    
    # تأكد من وجود القيم
    data['total_sales'] = data.get('total_sales', 0)
    data['count'] = data.get('count', 0)
    data['total_items'] = data.get('total_items', 0)
    
    return render_template('reports/sales.html', **data)