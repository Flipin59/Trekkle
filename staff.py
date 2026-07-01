from flask import Blueprint, redirect, url_for, render_template, request, flash
from flask_login import login_required, current_user
from models import db, User, Treks, StaffAssignment, Booking
from functools import wraps
from datetime import date, datetime, timezone


staff_bp = Blueprint('staff_bp', __name__)

def staff_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if current_user.role != 'Staff' or current_user.status != 'active':
            from flask import abort
            abort(403)
        return f(*args, **kwargs)
    return wrapped



@staff_bp.route('/staff/dashboard')
@login_required
@staff_required
def staff_dashboard():
    search_id   = request.args.get('search_id', '').strip()
    search_name = request.args.get('search_name', '').strip()

    squery = StaffAssignment.query.filter(StaffAssignment.staff_assigned == current_user.id)
    # Get trek IDs assigned to current staff, then query Treks
    assigned_trek_ids = db.session.query(StaffAssignment.trek_id).filter(
        StaffAssignment.staff_assigned == current_user.id
    ).subquery()

    query = Treks.query.filter(
        Treks.id.in_(assigned_trek_ids),
        Treks.start_date >= date.today()
    )

    # Apply search filters
    if search_id:
        query = query.filter(Treks.id == int(search_id))
    elif search_name:
        query = query.filter(Treks.name.ilike(f'%{search_name}%'))

    treks = query.order_by(Treks.id).all()

    # Callable passed to the template so it can fetch bookings per trek
    def fetch_bookings(trek_id):
        return db.session.query(Booking, User, Treks).join(
            User, Booking.user_id == User.id
        ).join(
            Treks, Booking.trek_id == Treks.id
        ).filter(
            Booking.trek_id == trek_id
        ).order_by(Booking.id).all()

    return render_template(
        'staff.html',
        user=current_user,
        treks=treks,
        search_id=search_id,
        search_name=search_name,
        fetch_bookings=fetch_bookings,
    )

### -----------------------Staff: Edit Trek-------------------------
### -----------------------Only allow necessary edits keeping admin template -------------------------
@staff_bp.route('/staff/trek/edit/<int:trek_id>', methods=['POST'])
@login_required
@staff_required
def edit_trek(trek_id):
    # start_date = date.fromisoformat(request.form['start_date'])
    # end_date   = date.fromisoformat(request.form['end_date'])
    # staff_id   = request.form.get('staff_id')

    # --- Integrity checks ---
    # if end_date < start_date:
    #     flash('End date cannot be before the start date!')
    #     return redirect(url_for('admin_bp.admin_dashboard'))

    # if not staff_id:
    #     flash('A staff member must be assigned to the trek!')
    #     return redirect(url_for('admin_bp.admin_dashboard'))

    trek = Treks.query.get_or_404(trek_id)

    # total_slots is disabled in the staff form (not submitted), so use existing DB value
    total_slots     = trek.total_slots
    available_slots = int(request.form['available_slots'])
    if available_slots > total_slots:
        flash('Available slots cannot be greater than total slots!')
        return redirect(url_for('staff_bp.staff_dashboard'))

    # duration_days = (end_date - start_date).days + 1

    # trek.name            = request.form['name']
    # trek.location        = request.form['location']
    trek.description     = request.form.get('description', '')
    # trek.difficulty      = request.form['difficulty']
    # trek.duration_days   = duration_days
    trek.available_slots = available_slots
    # trek.start_date      = start_date
    # trek.end_date        = end_date
    trek.status          = request.form.get('status', 'Open')
    trek.trek_updates    = request.form.get('trek_updates', 'As Scheduled')

    # No need for staff to do this 
    # Update staff assignment: clear old, insert new
    # StaffAssignment.query.filter_by(trek_id=trek_id).delete()
    # db.session.add(StaffAssignment(trek_id=trek_id, staff_assigned=int(staff_id)))

    db.session.commit()
    flash(f'Trek "{trek.name}" updated successfully!')
    return redirect(url_for('staff_bp.staff_dashboard'))