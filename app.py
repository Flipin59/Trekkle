from flask import Flask, redirect, url_for, render_template, request, session, flash, abort
from flask_login import LoginManager, login_user, login_required,logout_user,current_user
from models import db,User,Treks, StaffAssignment,Booking
from datetime import timedelta
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
# from flask_sqlalchemy import SQLAlchemy

# ---- Admin Credentials (plain text) ----
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'
ADMIN_EMAIL    = 'admin@trekking.com'
ADMIN_FULLNAME = 'Administrator'
ADMIN_PHONE    = '0000000000'


app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_secretKey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'

# Connecting our app to the db model We CREATED IN models.py
db.init_app(app)

# Register blueprints
from admin import admin_bp
app.register_blueprint(admin_bp)
from staff import staff_bp
app.register_blueprint(staff_bp)

# LOGIN MANAGER SETUP AND RBAC setup
login_manager = LoginManager()
login_manager.login_view='login'
login_manager.init_app(app)



# f is the decorated function. The ROLE_REQUIRES ACTS LIKE A GATEKEEPER
# FUNCTION TO CHECK ROLE BEFORE ALLOWING THE CONTROLLER TO CALL THE 
# ACTUAL INTENDED FUNCTION

def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args,**kwargs):
            if current_user.role !=role:
                abort(403) #FORBIDDEN
            return f(*args, **kwargs)
        return wrapped
    return decorator

@login_manager.user_loader
def load_user(user_id):
    return(User.query.get(int(user_id)))




@app.route("/")
def home():
    return render_template("index.html",user = current_user)

### -----------------------Signup Page-------------------------
@app.route("/signup", methods=['GET', 'POST'])
def register():

    if current_user.is_authenticated:
        flash('You are already Logged in!!')
        return redirect(url_for('dashboard',user=current_user))


    if request.method  =='POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        email = request.form['email']
        full_name = request.form['full_name']
        phone = request.form['phone']
        status = 'pending'
        # Guardrail against admin registration through curl requests
        if(role == 'Admin'):
            flash('Admin role cannot be selected')
            return redirect(url_for("register"))
        elif(role == 'Trekker'):
            status = 'active'
        elif(role == 'Staff'):
            status = 'pending'
        else:
            flash("Invalid Role Request!!")
            return(redirect(url_for("register",user=current_user)))
        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()

        if existing_user:
            flash('Username already taken, please try another username')
            return redirect(url_for('register',user=current_user))
        if existing_email:
            flash('Email id already in system please login with your existing credentials!!')
            return redirect(url_for('login',user=current_user))
        
        user = User(username=username,email=email,password_hash=password,full_name=full_name,phone=phone,role=role,status=status)

        db.session.add(user)
        db.session.commit()
        flash("Registered Sucesfully. Please login!!")
        return redirect(url_for('login',user=current_user))
    
    return render_template('signup.html',user = current_user)

### -----------------------Login Page-------------------------
@app.route('/login', methods = ['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard',user=current_user))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            if user.status == 'pending':
                flash("Account activation pending, try again in a while!!")
                return redirect(url_for('login'))
            elif user.status == 'blacklisted':
                flash("Account blacklisted you cannot login")
                return redirect(url_for('login'))
            
            login_user(user)
            return redirect(url_for('dashboard', user = current_user))
        else:
            flash("Invalid Login credentials. Please try again")
            return redirect(url_for('login', user=current_user))
    
    return render_template('login.html',user=current_user)

### -----------------------Dashboard-------------------------
@app.route('/dashboard')
@login_required
def dashboard():

    if current_user.role == 'Admin':
        return redirect(url_for('admin_bp.admin_dashboard'))
    
    elif current_user.role == 'Staff':
        if current_user.status == 'active':
            
            return redirect(url_for('staff_bp.staff_dashboard'))
        elif current_user.status == 'pending':
            flash("Account activation pending try again in a while!!")
            return redirect(url_for('login', user = current_user))
        else:
            flash("Account blacklisted you cannot login")
            return redirect(url_for('login', user = current_user))
    elif current_user.role == 'Trekker':
        flash("Login Successful")
        return render_template('trekker.html',user = current_user)

### -----------------------Logout-------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!!')
    return redirect(url_for('home',user=current_user))

### -----------------------Profile-------------------------
@app.route('/Profile')
@login_required
def profile():
    return "THIS IS THE PROFILE PAGE"




def create_admin():
    """Seed the default admin user if it doesn't already exist."""
    existing = User.query.filter_by(username=ADMIN_USERNAME).first()
    if not existing:
        admin = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password_hash=generate_password_hash(ADMIN_PASSWORD),
            full_name=ADMIN_FULLNAME,
            phone=ADMIN_PHONE,
            role='Admin',
            status='active'
        )
        db.session.add(admin)
        db.session.commit()
        print(f'[+] Admin user "{ADMIN_USERNAME}" created.')
    else:
        print('[*] Admin user already exists, skipping seed.')


if __name__=="__main__":
    with app.app_context():
        db.create_all()
        create_admin()
    app.run(debug=True)