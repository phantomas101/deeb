from app import db
from app.models import Sale, SaleItem, Purchase, PurchaseItem, Product, Customer, Supplier, CashDrawer, Expense
from datetime import datetime, timedelta
from sqlalchemy import func

# ============================================================
# دوال تقرير المبيعات
# ============================================================
def get_sales_report(date_from=None, date_to=None, customer_phone=None, payment_type=None, created_by=None):
    """تقرير المبيعات مع إمكانية التصفية"""
    query = Sale.query
    
    if date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Sale.created_at >= start_date)
        except:
            pass
    if date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Sale.created_at < end_date)
        except:
            pass
    if customer_phone:
        query = query.filter(Sale.customer_phone == customer_phone)
    if payment_type:
        query = query.filter(Sale.payment_type == payment_type)
    if created_by:
        query = query.filter(Sale.created_by == created_by)
    
    sales = query.order_by(Sale.created_at.desc()).all()
    
    total_sales = sum(sale.net_amount for sale in sales) if sales else 0
    total_items = sum(len(sale.items) for sale in sales) if sales else 0
    total_discount = sum(sale.discount for sale in sales) if sales else 0
    
    # تفصيل حسب نوع الدفع
    cash_sales = sum(sale.net_amount for sale in sales if sale.payment_type == 'cash') if sales else 0
    credit_sales = sum(sale.net_amount for sale in sales if sale.payment_type == 'credit') if sales else 0
    
    # تفصيل حسب نوع البيع
    retail_sales = sum(sale.net_amount for sale in sales if sale.sale_type == 'retail') if sales else 0
    wholesale_sales = sum(sale.net_amount for sale in sales if sale.sale_type == 'wholesale') if sales else 0
    
    return {
        'sales': sales,
        'total_sales': total_sales,
        'total_items': total_items,
        'total_discount': total_discount,
        'count': len(sales),
        'cash_sales': cash_sales,
        'credit_sales': credit_sales,
        'retail_sales': retail_sales,
        'wholesale_sales': wholesale_sales
    }


# ============================================================
# دوال تقرير المشتريات
# ============================================================
def get_purchases_report(date_from=None, date_to=None, supplier_phone=None, payment_type=None):
    """تقرير المشتريات مع إمكانية التصفية"""
    query = Purchase.query
    
    if date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Purchase.created_at >= start_date)
        except:
            pass
    if date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Purchase.created_at < end_date)
        except:
            pass
    if supplier_phone:
        query = query.filter(Purchase.supplier_phone == supplier_phone)
    if payment_type:
        query = query.filter(Purchase.payment_type == payment_type)
    
    purchases = query.order_by(Purchase.created_at.desc()).all()
    
    total_cost = sum(purchase.total_cost for purchase in purchases) if purchases else 0
    total_items = sum(len(purchase.items) for purchase in purchases) if purchases else 0
    
    # تفصيل حسب نوع الدفع
    cash_purchases = sum(purchase.total_cost for purchase in purchases if purchase.payment_type == 'cash') if purchases else 0
    credit_purchases = sum(purchase.total_cost for purchase in purchases if purchase.payment_type == 'credit') if purchases else 0
    
    return {
        'purchases': purchases,
        'total_cost': total_cost,
        'total_items': total_items,
        'count': len(purchases),
        'cash_purchases': cash_purchases,
        'credit_purchases': credit_purchases
    }


# ============================================================
# دوال تقرير المخزون
# ============================================================
def get_inventory_report(category=None, min_stock=None, branch_id=None):
    """تقرير المخزون الحالي"""
    query = Product.query
    
    if category:
        query = query.filter(Product.category == category)
    if min_stock:
        query = query.filter(Product.quantity <= Product.min_stock)
    if branch_id:
        query = query.filter(Product.branch_id == branch_id)
    
    products = query.order_by(Product.name).all()
    
    total_products = len(products)
    total_quantity = sum(p.quantity for p in products) if products else 0
    total_value = sum(p.quantity * p.cost_price for p in products) if products else 0
    
    # الأصناف منخفضة المخزون
    low_stock = [p for p in products if p.quantity <= p.min_stock]
    
    # الأصناف غير المتوفرة
    out_of_stock = [p for p in products if p.quantity <= 0]
    
    return {
        'products': products,
        'total_products': total_products,
        'total_quantity': total_quantity,
        'total_value': total_value,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock
    }


# ============================================================
# دوال تقرير الأرباح والخسائر
# ============================================================
def get_profit_loss_report(date_from=None, date_to=None):
    """تقرير الأرباح والخسائر"""
    if not date_from:
        start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
        except:
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    if not date_to:
        end_date = datetime.now().replace(hour=23, minute=59, second=59)
    else:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
        except:
            end_date = datetime.now().replace(hour=23, minute=59, second=59)
    
    # المبيعات
    sales = Sale.query.filter(Sale.created_at >= start_date, Sale.created_at < end_date).all()
    total_sales = sum(sale.net_amount for sale in sales) if sales else 0
    
    # تكلفة البضاعة المباعة
    cost_of_goods_sold = 0
    for sale in sales:
        for item in sale.items:
            if item.product:
                cost_of_goods_sold += item.quantity * item.product.cost_price
    
    # المشتريات
    purchases = Purchase.query.filter(Purchase.created_at >= start_date, Purchase.created_at < end_date).all()
    total_purchases = sum(purchase.total_cost for purchase in purchases) if purchases else 0
    
    # المصروفات
    expenses = Expense.query.filter(Expense.created_at >= start_date, Expense.created_at < end_date).all()
    total_expenses = sum(expense.amount for expense in expenses) if expenses else 0
    
    # الربح الإجمالي
    gross_profit = total_sales - cost_of_goods_sold
    
    # صافي الربح
    net_profit = gross_profit - total_expenses
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'total_sales': total_sales,
        'total_purchases': total_purchases,
        'total_expenses': total_expenses,
        'cost_of_goods_sold': cost_of_goods_sold,
        'gross_profit': gross_profit,
        'net_profit': net_profit
    }


# ============================================================
# دوال تقرير العملاء
# ============================================================
def get_customers_report(phone=None, min_balance=None):
    """تقرير العملاء مع أرصدتهم"""
    query = Customer.query
    
    if phone:
        query = query.filter(Customer.phone == phone)
    if min_balance:
        query = query.filter(Customer.balance >= min_balance)
    
    customers = query.order_by(Customer.name).all()
    
    total_customers = len(customers)
    total_balance = sum(c.balance for c in customers) if customers else 0
    total_debtors = sum(c.balance for c in customers if c.balance > 0) if customers else 0
    
    return {
        'customers': customers,
        'total_customers': total_customers,
        'total_balance': total_balance,
        'total_debtors': total_debtors
    }


# ============================================================
# دوال تقرير الموردين
# ============================================================
def get_suppliers_report(phone=None, min_balance=None):
    """تقرير الموردين مع أرصدتهم"""
    query = Supplier.query
    
    if phone:
        query = query.filter(Supplier.phone == phone)
    if min_balance:
        query = query.filter(Supplier.balance >= min_balance)
    
    suppliers = query.order_by(Supplier.name).all()
    
    total_suppliers = len(suppliers)
    total_balance = sum(s.balance for s in suppliers) if suppliers else 0
    total_creditors = sum(s.balance for s in suppliers if s.balance > 0) if suppliers else 0
    
    return {
        'suppliers': suppliers,
        'total_suppliers': total_suppliers,
        'total_balance': total_balance,
        'total_creditors': total_creditors
    }


# ============================================================
# دوال تقرير المدفوعات
# ============================================================
def get_payments_report(date_from=None, date_to=None):
    """تقرير حركات الخزينة (المدفوعات والإيداعات)"""
    query = CashDrawer.query
    
    if date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(CashDrawer.created_at >= start_date)
        except:
            pass
    if date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(CashDrawer.created_at < end_date)
        except:
            pass
    
    transactions = query.order_by(CashDrawer.created_at.desc()).all()
    
    total_in = sum(t.amount for t in transactions if t.transaction_type == 'IN') if transactions else 0
    total_out = sum(t.amount for t in transactions if t.transaction_type == 'OUT') if transactions else 0
    net_balance = total_in - total_out
    
    return {
        'transactions': transactions,
        'total_in': total_in,
        'total_out': total_out,
        'net_balance': net_balance,
        'count': len(transactions)
    }


# ============================================================
# دوال مساعدة لتنسيق التقارير
# ============================================================
def format_currency(amount):
    """تنسيق المبلغ مع فصل الآلاف"""
    try:
        return f"{amount:,.2f}"
    except:
        return "0.00"

def format_date(date):
    """تنسيق التاريخ بصيغة عربية"""
    if not date:
        return ''
    months = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
              'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
    return f"{date.day} {months[date.month-1]} {date.year}"