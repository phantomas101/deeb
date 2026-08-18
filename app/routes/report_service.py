from app import db
from app.models import Sale, SaleItem, Product, Customer
from datetime import datetime

def get_sales_report(date_from=None, date_to=None, customer_phone=None, payment_type=None):
    query = Sale.query
    
    if date_from:
        query = query.filter(Sale.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Sale.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    if customer_phone:
        query = query.filter(Sale.customer_phone == customer_phone)
    if payment_type:
        query = query.filter(Sale.payment_type == payment_type)
    
    sales = query.order_by(Sale.created_at.desc()).all()
    
    total_sales = sum(sale.net_amount for sale in sales)
    total_items = sum(len(sale.items) for sale in sales)
    
    return {
        'sales': sales,
        'total_sales': total_sales,
        'total_items': total_items,
        'count': len(sales)
    }