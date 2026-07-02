from flask import Blueprint, redirect, url_for, render_template, request, flash
from flask_login import login_required, current_user
from models import db, User, Treks, StaffAssignment, Booking
from functools import wraps
from datetime import date, datetime, timezone


staff_bp = Blueprint('staff_bp', __name__)



# creating a custom decorator args and kwargs are passed to the function 
# f provided it passes the validation check
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
    # get trek ids assigned to this staff member
    assigned_trek_ids = db.session.query(StaffAssignment.trek_id).filter(
        StaffAssignment.staff_assigned == current_user.id
    ).subquery()

    query = Treks.query.filter(
        Treks.id.in_(assigned_trek_ids),
        Treks.start_date >= date.today()
    ) # only show upcoming treks

    # apply search filters
    if search_id:
        try:
            query = query.filter(Treks.id == int(search_id))
        except ValueError:
            flash('Invalid Trek ID format.', 'error')
    elif search_name:
        query = query.filter(Treks.name.ilike(f'%{search_name}%'))

    treks = query.order_by(Treks.id).all()

    # fetch bookings for a given trek (called from template)
    def fetch_bookings(trek_id):
        return db.session.query(Booking, User, Treks).join(
            User, Booking.user_id == User.id
        ).join(
            Treks, Booking.trek_id == Treks.id
        ).filter(
            Booking.trek_id == trek_id,
            Booking.status=='Booked'
        ).order_by(Booking.id).all()

    # count of active bookings for a trek
    def booking_count(trek_id):
        return Booking.query.filter(
            Booking.trek_id == trek_id,
            Booking.status != 'Cancelled'
        ).count()

    return render_template(
        'staff.html',
        user=current_user,
        treks=treks,
        search_id=search_id,
        search_name=search_name,
        fetch_bookings=fetch_bookings,
        booking_count=booking_count,
    )

### staff: edit trek
### only allow necessary edits, keeping admin template structure
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

    # verify this trek is assigned to the current staff
    assignment = StaffAssignment.query.filter_by(
        trek_id=trek_id,
        staff_assigned=current_user.id
    ).first()
    if not assignment:
        flash('You are not authorised to modify this trek.')
        return redirect(url_for('staff_bp.staff_dashboard'))

    trek = Treks.query.get_or_404(trek_id)

    # total_slots is disabled in the form so it won't be submitted, use db value
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

    # if trek is cancelled or completed, update all active bookings accordingly
    if trek.status in ('Cancelled', 'Completed'):
        active_bookings = Booking.query.filter(
            Booking.trek_id == trek_id,
            Booking.status == 'Booked'
        ).all()
        for b in active_bookings:
            b.status = trek.status

    # staff can't reassign themselves
    # update staff assignment: clear old, insert new
    # StaffAssignment.query.filter_by(trek_id=trek_id).delete()
    # db.session.add(StaffAssignment(trek_id=trek_id, staff_assigned=int(staff_id)))

    db.session.commit()
    flash(f'Trek "{trek.name}" updated successfully!')
    return redirect(url_for('staff_bp.staff_dashboard'))


### staff: cancel booking
@staff_bp.route('/staff/booking/cancel/<int:booking_id>', methods=['POST'])
@login_required
@staff_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    # make sure this booking belongs to a trek assigned to the current staff
    assignment = StaffAssignment.query.filter_by(
        trek_id=booking.trek_id,
        staff_assigned=current_user.id
    ).first()
    if not assignment:
        flash('You are not authorised to manage this booking.')
        return redirect(url_for('staff_bp.staff_dashboard'))

    if booking.status == 'Cancelled':
        flash('Booking is already cancelled.')
        return redirect(url_for('staff_bp.staff_dashboard'))

    trek = Treks.query.get(booking.trek_id)
    if trek:
        if trek.status == 'Completed':
            flash('Trek has already completed!')
            return redirect(url_for('staff_bp.staff_dashboard'))
        elif trek.status == 'Cancelled':
            flash('Trek has already cancelled!')
            return redirect(url_for('staff_bp.staff_dashboard'))
        elif trek.start_date < date.today():
            flash('Trek has already started!')
            return redirect(url_for('staff_bp.staff_dashboard'))
    else:
        flash('Trek not found!')
        return redirect(url_for('staff_bp.staff_dashboard'))

    booking.status = 'Cancelled'
    
    # free up the slot
    if trek and trek.available_slots < trek.total_slots:
        trek.available_slots += 1

    db.session.commit()
    flash(f'Booking #{booking.id} cancelled successfully.')
    return redirect(url_for('staff_bp.staff_dashboard'))