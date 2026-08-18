# ============================================================
# استيراد جميع النماذج
# ============================================================

from app.models.user import User
from app.models.branch import Branch
from app.models.product import Product, StockMovement
from app.models.supplier import Supplier
from app.models.customer import Customer
from app.models.sale import Sale, SaleItem
from app.models.purchase import Purchase, PurchaseItem
from app.models.cash import CashDrawer, Expense
from app.models.setting import Setting
from app.models.license import License
# جميع النماذج مستوردة
__all__ = [
    "User",
    "Branch",
    "Product",
    "StockMovement",
    "Supplier",
    "Customer",
    "Sale",
    "SaleItem",
    "Purchase",
    "PurchaseItem",
    "CashDrawer",
    "Expense",
    "Setting",
    "License"
]