from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.extensions import bcrypt
from app.models import User, License
import hashlib
import uuid
import subprocess
import platform
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# ============================================================
# دوال استخراج بصمة الجهاز وتوليد الكود
# ============================================================

def get_machine_id():
    """استخراج معرف فريد للجهاز (MAC Address + CPU ID)"""
    try:
        mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
        cpu_id = "UNKNOWN"
        if platform.system() == "Windows":
            try:
                output = subprocess.check_output("wmic cpu get ProcessorId", shell=True).decode()
                lines = output.strip().split('\n')
                if len(lines) > 1:
                    cpu_id = lines[1].strip()
            except:
                pass
        machine_id = f"{mac}-{cpu_id}".replace(" ", "")
        return machine_id[:50]
    except:
        return "UNKNOWN-DEVICE"

def generate_license_key(machine_id, secret_key="POS_SYSTEM_2025"):
    """توليد كود تفعيل فريد بناءً على بصمة الجهاز"""
    raw = f"{machine_id}{secret_key}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24].upper()

def verify_license():
    """التحقق من صحة التفعيل"""
    machine_id = get_machine_id()
    license_record = License.query.filter_by(machine_id=machine_id, is_active=True).first()
    
    if not license_record:
        return False, None
    
    if license_record.license_type == 'permanent':
        return True, license_record
    
    if license_record.license_type == 'trial':
        if license_record.expires_at and license_record.expires_at < datetime.utcnow():
            license_record.is_active = False
            db.session.commit()
            return False, license_record
        return True, license_record
    
    return False, None

# ============================================================
# التحقق من التفعيل قبل أي طلب
# ============================================================

@auth_bp.before_request
def check_license():
    if request.endpoint in ['auth.license_page', 'auth.login', 'auth.logout', 'static']:
        return None
    
    if not current_user.is_authenticated:
        is_valid, _ = verify_license()
        if not is_valid:
            return redirect(url_for('auth.license_page'))
    
    if current_user.is_authenticated:
        is_valid, _ = verify_license()
        if not is_valid:
            logout_user()
            flash('انتهت صلاحية التفعيل. يرجى تجديد الترخيص.', 'warning')
            return redirect(url_for('auth.license_page'))
    
    return None

# ============================================================
# دوال المصادقة
# ============================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    is_valid, _ = verify_license()
    if not is_valid:
        return redirect(url_for('auth.license_page'))
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# ============================================================
# صفحة التفعيل
# ============================================================

@auth_bp.route('/license', methods=['GET', 'POST'])
def license_page():
    is_valid, _ = verify_license()
    if is_valid:
        return redirect(url_for('auth.login'))
    
    machine_id = get_machine_id()
    
    if request.method == 'POST':
        license_key_input = request.form.get('license_key', '').strip().upper()
        
        if not license_key_input:
            flash('يرجى إدخال كود التفعيل.', 'danger')
            return render_template('license.html', machine_id=machine_id)
        
        expected_key = generate_license_key(machine_id)
        
        if license_key_input == expected_key:
            license_record = License.query.filter_by(machine_id=machine_id).first()
            if license_record:
                license_record.license_key = license_key_input
                license_record.is_active = True
                license_record.activated_at = datetime.utcnow()
                license_record.license_type = 'permanent'
                license_record.expires_at = None
            else:
                new_license = License(
                    machine_id=machine_id,
                    license_key=license_key_input,
                    is_active=True,
                    activated_at=datetime.utcnow(),
                    license_type='permanent',
                    expires_at=None
                )
                db.session.add(new_license)
            db.session.commit()
            flash('✅ تم تفعيل البرنامج بنجاح!', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('❌ كود التفعيل غير صحيح لهذا الجهاز.', 'danger')
            return render_template('license.html', machine_id=machine_id)
    
    return render_template('license.html', machine_id=machine_id)