# ============================================================
# مصنع التطبيق (Application Factory)
# ============================================================
import os
from flask import Flask, request, redirect, url_for
from app.extensions import db, bcrypt, login_manager
from app.config import config_by_name
from app.utils.helpers import (
    generate_csrf_token,
    get_settings,
    create_default_admin,
    create_default_branch,
    create_default_settings,
    upgrade_database
)


def create_app(config_name=None):
    """إنشاء وتكوين تطبيق Flask"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    
    # تحميل الإعدادات
    app.config.from_object(config_by_name[config_name])
    
    # تهيئة الملحقات
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    # ===== تعريف user_loader (هام لـ Flask-Login) =====
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # ===== سياق القوالب (متاح لجميع القوالب) =====
    @app.context_processor
    def inject_globals():
        return {
            'settings': get_settings(),
            'csrf_token': generate_csrf_token()
        }
    
    # ===== سياسة أمان المحتوى (CSP) مع دعم unsafe-eval =====
    @app.after_request
    def set_csp(response):
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers['Content-Security-Policy'] = csp
        return response
    
    # ===== التحقق من الترخيص قبل كل طلب =====
    @app.before_request
    def check_license_global():
        from app.routes.auth import verify_license
        if request.endpoint in ['auth.license_page', 'auth.login', 'auth.logout', 'static']:
            return None
        is_valid, _ = verify_license()
        if not is_valid:
            return redirect(url_for('auth.license_page'))
        return None
    
    # ===== تسجيل Blueprints =====
    register_blueprints(app)
    
    # ===== تهيئة قاعدة البيانات والبيانات الافتراضية =====
    with app.app_context():
        os.makedirs(app.instance_path, exist_ok=True)
        db.create_all()
        create_default_admin()
        create_default_branch()
        create_default_settings()
        upgrade_database()
    
    return app


def register_blueprints(app):
    """تسجيل جميع Blueprints"""
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.inventory import inventory_bp
    from app.routes.pos import pos_bp
    from app.routes.sales import sales_bp
    from app.routes.purchases import purchases_bp
    from app.routes.transfers import transfers_bp
    from app.routes.branches import branches_bp
    from app.routes.cash_expenses import cash_bp
    from app.routes.users import users_bp
    from app.routes.settings import settings_bp
    from app.routes.customers import customers_bp
    from app.routes.suppliers import suppliers_bp
    from app.routes.debts import debts_bp
    from app.routes.profit_loss import profit_loss_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(pos_bp, url_prefix='/pos')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(purchases_bp, url_prefix='/purchases')
    app.register_blueprint(transfers_bp, url_prefix='/transfers')
    app.register_blueprint(branches_bp, url_prefix='/branches')
    app.register_blueprint(cash_bp, url_prefix='/cash')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(suppliers_bp, url_prefix='/suppliers')
    app.register_blueprint(debts_bp, url_prefix='/debts')
    app.register_blueprint(profit_loss_bp, url_prefix='/profit-loss')