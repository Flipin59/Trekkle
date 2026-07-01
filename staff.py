from flask import Blueprint, redirect, url_for, render_template, request, flash
from flask_login import login_required, current_user
from models import db, User, Treks, StaffAssignment, Booking
from functools import wraps
from datetime import date, datetime, timezone


staff_bp = Blueprint('staff_bp', __name__)

def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if current_user.role != 'Admin':
            from flask import abort
            abort(403)
        return f(*args, **kwargs)
    return wrapped
