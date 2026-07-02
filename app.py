from flask import Flask, redirect, url_for, render_template, request, session, flash, abort
from flask_login import LoginManager, login_user, login_required,logout_user,current_user
from models import db,User,Treks, StaffAssignment,Booking
from datetime import timedelta
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from dotenv import load_dotenv

load_dotenv()
# from flask_sqlalchemy import SQLAlchemy

# admin credentials (loaded from .env)
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
ADMIN_EMAIL    = os.getenv('ADMIN_EMAIL')
ADMIN_FULLNAME = os.getenv('ADMIN_FULLNAME')
ADMIN_PHONE    = os.getenv('ADMIN_PHONE')


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'

# connecting our app to the db model we created in models.py
db.init_app(app)

# register blueprints
from admin import admin_bp
app.register_blueprint(admin_bp)
from staff import staff_bp
app.register_blueprint(staff_bp)
from trekker import trekker_bp
app.register_blueprint(trekker_bp)


# login manager setup and rbac
login_manager = LoginManager()
login_manager.login_view='login'
login_manager.init_app(app)



# role_required acts like a gatekeeper, checks role before
# letting the controller call the actual function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args,**kwargs):
            if current_user.role !=role:
                abort(403) # forbidden
            return f(*args, **kwargs)
        return wrapped
    return decorator

@login_manager.user_loader
def load_user(user_id):
    return(User.query.get(int(user_id)))




@app.route("/")
def home():
    return render_template("index.html",user = current_user)

### signup page
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
        # guardrail against admin registration through curl requests
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

### login page
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

### dashboard
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
       if current_user.status == 'active':
            
            return redirect(url_for('trekker_bp.trekker_dashboard'))
       elif current_user.status == 'pending':
           flash("Account activation pending try again in a while!!")
           return redirect(url_for('login', user = current_user))
       else:
           flash("Account blacklisted you cannot login")
           return redirect(url_for('login', user = current_user))

### logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!!')
    return redirect(url_for('home',user=current_user))

### profile
@app.route('/Profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        email = request.form['email'].strip()
        full_name = request.form['full_name'].strip()
        phone = request.form['phone'].strip()
        password = request.form.get('password', '').strip()

        # check if email is already taken by another user
        existing_email = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_email:
            flash('Email already registered by another account.')
            return redirect(url_for('profile'))

        current_user.email = email
        current_user.full_name = full_name
        current_user.phone = phone

        if password:
            current_user.password_hash = generate_password_hash(password)

        db.session.commit()
        flash('Profile updated successfully.')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=current_user)




def create_admin():
    """seed the default admin user if it doesn't already exist."""
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