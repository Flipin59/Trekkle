from flask import Blueprint, redirect, url_for, render_template, request, flash
from flask_login import login_required, current_user
from models import db, User, Treks, StaffAssignment, Booking
from functools import wraps
from datetime import date, datetime, timezone


admin_bp = Blueprint('admin_bp', __name__)


# ---- RBAC decorator (Admin only) ----
def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if current_user.role != 'Admin':
            from flask import abort
            abort(403)
        return f(*args, **kwargs)
    return wrapped


### -----------------------Admin Dashboard-------------------------
@admin_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # --- Search / filter logic for treks ---
    search_id   = request.args.get('search_id', '').strip()
    search_name = request.args.get('search_name', '').strip()
    
    query = Treks.query
    if search_id:
        query = query.filter(Treks.id == int(search_id))
    elif search_name:
        query = query.filter(Treks.name.ilike(f'%{search_name}%'))

    treks = query.order_by(Treks.id).all()

    # Build a dict mapping trek_id -> staff username (one staff per trek)
    staff_map = {}
    assignments = db.session.query(StaffAssignment, User).join(
        User, StaffAssignment.staff_assigned == User.id
    ).all()
    for assignment, staff_user in assignments:
        staff_map[assignment.trek_id] = staff_user.username

    # Get list of active staff for the "assign staff" dropdown in forms
    staff_list = User.query.filter_by(role='Staff', status='active').all()

    # --- User Control Logic ---
    
    pending_staff = User.query.filter_by(role='Staff', status='pending').order_by(User.id).all()

    
    user_search = request.args.get('user_search', '').strip()
    u_query = User.query.filter(User.id != current_user.id) #exclude current admin from the list
    
    # If user_search is not specified display all users else display user_searched users
    if user_search:
        u_query = u_query.filter(User.username.ilike(f'%{user_search}%'))
    all_users = u_query.order_by(User.username).all()

    # --- Booking Control Logic ---
    search_booking_id = request.args.get('search_booking_id', '').strip()
    search_username   = request.args.get('search_username', '').strip()
    search_trek_name  = request.args.get('search_trek_name', '').strip()

    b_query = db.session.query(Booking, User, Treks).join(
        User, Booking.user_id == User.id
    ).join(
        Treks, Booking.trek_id == Treks.id
    )

    if search_booking_id:
        b_query = b_query.filter(Booking.id == int(search_booking_id))
    elif search_username:
        b_query = b_query.filter(User.username.ilike(f'%{search_username}%'))
    elif search_trek_name:
        b_query = b_query.filter(Treks.name.ilike(f'%{search_trek_name}%'))

    bookings_data = b_query.order_by(Booking.id).all()

    # List of trekkers and treks for dropdowns
    trekker_list = User.query.filter_by(role='Trekker').all()
    trek_list = Treks.query.all()

    return render_template(
        'admin.html',
        user=current_user,
        treks=treks,
        staff_map=staff_map,
        staff_list=staff_list,
        search_id=search_id,
        search_name=search_name,
        pending_staff=pending_staff,
        all_users=all_users,
        user_search=user_search,
        bookings_data=bookings_data,
        trekker_list=trekker_list,
        trek_list=trek_list,
        search_booking_id=search_booking_id,
        search_username=search_username,
        search_trek_name=search_trek_name
    )


### -----------------------Admin: Update User Status-------------------------
@admin_bp.route('/admin/user/status/<int:user_id>/<string:new_status>', methods=['POST'])
@login_required
@admin_required
def update_user_status(user_id, new_status):
    if new_status not in ['active', 'blacklisted']:
        flash('Invalid status action!')
        return redirect(url_for('admin_bp.admin_dashboard'))

    user_to_mod = User.query.get_or_404(user_id)
    if user_to_mod.id == current_user.id:
        flash('Cannot modify your own admin status!')
        return redirect(url_for('admin_bp.admin_dashboard'))

    user_to_mod.status = new_status
    db.session.commit()
    flash(f'User "{user_to_mod.username}" status updated to "{new_status}" successfully!')
    return redirect(url_for('admin_bp.admin_dashboard'))


### -----------------------Admin: Add Trek-------------------------
@admin_bp.route('/admin/trek/add', methods=['POST'])
@login_required
@admin_required
def add_trek():
    start_date = date.fromisoformat(request.form['start_date'])
    end_date   = date.fromisoformat(request.form['end_date'])
    staff_id   = request.form.get('staff_id')

    # --- Integrity checks ---
    if end_date < start_date:
        flash('End date cannot be before the start date!')
        return redirect(url_for('admin_bp.admin_dashboard'))

    if not staff_id:
        flash('A staff member must be assigned to the trek!')
        return redirect(url_for('admin_bp.admin_dashboard'))

    total_slots     = int(request.form['total_slots'])
    available_slots = int(request.form['available_slots'])
    if available_slots > total_slots:
        flash('Available slots cannot be greater than total slots!')
        return redirect(url_for('admin_bp.admin_dashboard'))

    duration_days = (end_date - start_date).days + 1  # inclusive of both days

    trek = Treks(
        name            = request.form['name'],
        location        = request.form['location'],
        description     = request.form.get('description', ''),
        difficulty      = request.form['difficulty'],
        duration_days   = duration_days,
        total_slots     = total_slots,
        available_slots = available_slots,
        start_date      = start_date,
        end_date        = end_date,
        status          = request.form.get('status', 'Open'),
        trek_updates    = request.form.get('trek_updates', 'As Scheduled'),
    )
    db.session.add(trek)
    db.session.flush()  # get trek.id before commit

    # Assign staff
    db.session.add(StaffAssignment(trek_id=trek.id, staff_assigned=int(staff_id)))

    db.session.commit()
    flash(f'Trek "{trek.name}" added successfully! (Duration: {duration_days} days)')
    return redirect(url_for('admin_bp.admin_dashboard'))


### -----------------------Admin: Edit Trek-------------------------
@admin_bp.route('/admin/trek/edit/<int:trek_id>', methods=['POST'])
@login_required
@admin_required
def edit_trek(trek_id):
    start_date = date.fromisoformat(request.form['start_date'])
    end_date   = date.fromisoformat(request.form['end_date'])
    staff_id   = request.form.get('staff_id')

    # --- Integrity checks ---
    if end_date < start_date:
        flash('End date cannot be before the start date!')
        return redirect(url_for('admin_bp.admin_dashboard'))

    if not staff_id:
        flash('A staff member must be assigned to the trek!')
        return redirect(url_for('admin_bp.admin_dashboard'))

    total_slots     = int(request.form['total_slots'])
    available_slots = int(request.form['available_slots'])
    if available_slots > total_slots:
        flash('Available slots cannot be greater than total slots!')
        return redirect(url_for('admin_bp.admin_dashboard'))

    duration_days = (end_date - start_date).days + 1

    trek = Treks.query.get_or_404(trek_id)
    trek.name            = request.form['name']
    trek.location        = request.form['location']
    trek.description     = request.form.get('description', '')
    trek.difficulty      = request.form['difficulty']
    trek.duration_days   = duration_days
    trek.total_slots     = total_slots
    trek.available_slots = available_slots
    trek.start_date      = start_date
    trek.end_date        = end_date
    trek.status          = request.form.get('status', 'Open')
    trek.trek_updates    = request.form.get('trek_updates', 'As Scheduled')

    # Update staff assignment: clear old, insert new
    StaffAssignment.query.filter_by(trek_id=trek_id).delete()
    db.session.flush()
    db.session.add(StaffAssignment(trek_id=trek_id, staff_assigned=int(staff_id)))

    db.session.commit()
    flash(f'Trek "{trek.name}" updated successfully!')
    return redirect(url_for('admin_bp.admin_dashboard'))


### -----------------------Admin: Delete Trek-------------------------
@admin_bp.route('/admin/trek/delete/<int:trek_id>', methods=['POST'])
@login_required
@admin_required
def delete_trek(trek_id):
    trek = Treks.query.get_or_404(trek_id)
    db.session.delete(trek)
    db.session.commit()
    flash(f'Trek "{trek.name}" deleted successfully!')
    return redirect(url_for('admin_bp.admin_dashboard'))


### -----------------------Admin: Cancel Booking-------------------------
@admin_bp.route('/admin/booking/cancel/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.status == 'Cancelled':
        flash('Booking is already cancelled!')
        return redirect(url_for('admin_bp.admin_dashboard'))
        
    booking.status = 'Cancelled'
    
    # Slot management: increment slots of the associated trek
    trek = Treks.query.get(booking.trek_id)
    if trek:
        trek.available_slots += 1
        
    db.session.commit()
    flash(f'Booking #{booking.id} cancelled successfully!')
    return redirect(url_for('admin_bp.admin_dashboard'))


### -----------------------Admin: Uncancel Booking-------------------------
@admin_bp.route('/admin/booking/uncancel/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def uncancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.status == 'Booked':
        flash('Booking is already active!')
        return redirect(url_for('admin_bp.admin_dashboard'))
        
    trek = Treks.query.get(booking.trek_id)
    if not trek:
        flash('Associated trek not found!')
        return redirect(url_for('admin_bp.admin_dashboard'))
        
    if trek.available_slots <= 0:
        flash(f'Cannot uncancel: No slots available on the trek "{trek.name}"!')
        return redirect(url_for('admin_bp.admin_dashboard'))
        
    booking.status = 'Booked'
    trek.available_slots -= 1
    
    db.session.commit()
    flash(f'Booking #{booking.id} restored successfully!')
    return redirect(url_for('admin_bp.admin_dashboard'))
