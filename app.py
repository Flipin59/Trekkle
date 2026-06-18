from flask import Flask, redirect, url_for, render_template, request, session, flash, abort
from flask_login import LoginManager, login_user, login_required,logout_user,current_user
from models import db,User,Treks, StaffAssignment,Booking
from datetime import timedelta
import os
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
# from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_secretKey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'

# Connecting our app to the db model We CREATED IN models.py
db.init_app(app)


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

    # Tester:
    return "THIS IS THE DASHBOARD PAGE"
    # return render_template('dashboard.html', user= current_user) 


# @app.route('/admin')
# @login_required
# @role_required('Admin')
# def admin_page():
#     return "Welcome Admin!!"

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

if __name__=="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)