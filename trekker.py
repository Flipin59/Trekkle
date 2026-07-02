from flask import Blueprint, redirect, url_for, render_template, request, flash
from flask_login import login_required, current_user
from models import db, User, Treks, StaffAssignment, Booking
from functools import wraps
from datetime import date, datetime, timezone


trekker_bp = Blueprint('trekker_bp', __name__)


# creating a custom decorator args and kwargs are passed to the function 
# f provided it passes the validation check
def trekker_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if current_user.role != 'Trekker' or current_user.status != 'active':
            from flask import abort
            abort(403)
        return f(*args, **kwargs)
    return wrapped

@trekker_bp.route('/trekker/dashboard')
@login_required
@trekker_required
def trekker_dashboard():

    search_id   = request.args.get('search_id', '').strip()
    search_name = request.args.get('search_name', '').strip()
    search_location = request.args.get('search_location', '').strip()
    search_difficulty = request.args.get('search_difficulty', '').strip()

    # get all bookings made by this user
    my_bookings = db.session.query(Booking, Treks).join(
        Treks, Booking.trek_id == Treks.id
    ).filter(
        Booking.user_id == current_user.id
    ).order_by(Booking.id.desc()).all()

    # collect all booked trek ids to exclude from available treks
    booked_trek_ids = {
        booking.trek_id for booking, trek in my_bookings
    }

    # show open treks which aren't already booked by this user and those which are after today
    query = Treks.query.filter(
        ~Treks.id.in_(booked_trek_ids) if booked_trek_ids else True,
        Treks.start_date >= date.today(),
        Treks.status == 'Open'
    )

    all_treks = Treks.query.all()

    if search_id:
        try:
            query = query.filter(Treks.id == int(search_id))
        except ValueError:
            flash('Invalid Trek ID format.', 'error')
    if search_name:
        query = query.filter(Treks.name.ilike(f'%{search_name}%'))
    if search_location:
        query = query.filter(Treks.location.ilike(f'%{search_location}%'))
    if search_difficulty:
        query = query.filter(Treks.difficulty.ilike(f'%{search_difficulty}%'))

    treks = query.order_by(Treks.id).all()



    def find_trek(trek_id):
        return Treks.query.get(trek_id)

    return render_template(
        'trekker.html',
        user=current_user,
        my_bookings=my_bookings,
        search_id=search_id,
        search_name=search_name,
        search_location=search_location,
        search_difficulty=search_difficulty,
        treks=treks,
        all_treks=all_treks,
        find_trek=find_trek,
        date=date
        )



@trekker_bp.route('/trekker/booking/add/<int:trek_id>', methods=['POST'])
@login_required
@trekker_required
def book_trek(trek_id):
    trek = Treks.query.filter(
        Treks.id == trek_id,
        Treks.start_date >= date.today(),
        Treks.status == 'Open'
    ).first()

    if not trek:
        flash("Invalid Trek ID/ Trek Completed", "error")
        return redirect(url_for('trekker_bp.trekker_dashboard'))

    # check if already booked
    existing = Booking.query.filter_by(
        user_id=current_user.id, trek_id=trek_id
    ).filter(Booking.status == 'Booked').first()
    if existing:
        flash('You have already booked this trek!', 'error')
        return redirect(url_for('trekker_bp.trekker_dashboard'))

    if trek.available_slots > 0:
        booking = Booking(
            user_id=current_user.id,
            trek_id=trek_id,
            booking_date=datetime.now(),
            status='Booked'
        )
        db.session.add(booking)
        trek.available_slots -= 1
        db.session.commit()
        flash('Booking successful!', 'success')
    else:
        flash('No slots available!', 'error')
    return redirect(url_for('trekker_bp.trekker_dashboard'))


@trekker_bp.route('/trekker/booking/cancel/<int:booking_id>', methods=['POST'])
@login_required
@trekker_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)


    # Not needed for trekker
    # # Verify this booking belongs to a trek assigned to the current staff
    # assignment = StaffAssignment.query.filter_by(
    #     trek_id=booking.trek_id,
    #     staff_assigned=current_user.id
    # ).first()
    # if not assignment:
    #     flash('You are not authorised to manage this booking.')
    #     return redirect(url_for('staff_bp.staff_dashboard'))

    # verify this booking belongs to the current user
    if booking.user_id != current_user.id:
        flash('You are not authorised to cancel this booking.')
        return redirect(url_for('trekker_bp.trekker_dashboard'))

    if booking.status == 'Cancelled':
        flash('Booking is already cancelled.')
        return redirect(url_for('trekker_bp.trekker_dashboard'))

    trek = Treks.query.get(booking.trek_id)
    
    if trek:
        if trek.status == 'Completed':
            flash('Trek has already completed!')
            return redirect(url_for('trekker_bp.trekker_dashboard'))
        elif trek.status == 'Cancelled':
            # Should never reach here cos we cancel the bookings when the trek gets cancelled 
            # Hopefully intention and actuality are the same
            flash('Trek has already cancelled!')
            return redirect(url_for('trekker_bp.trekker_dashboard'))
        elif trek.start_date < date.today():
            flash('Trek has already started!')
            return redirect(url_for('trekker_bp.trekker_dashboard'))
    else:
        flash('Trek not found!')
        return redirect(url_for('trekker_bp.trekker_dashboard'))



    booking.status = 'Cancelled'

    # free up the slot
    if trek.available_slots < trek.total_slots:
        trek.available_slots += 1

    db.session.commit()
    flash(f'Booking #{booking.id} cancelled successfully.')
    return redirect(url_for('trekker_bp.trekker_dashboard'))


@trekker_bp.route('/trekker/booking/uncancel/<int:booking_id>', methods=['POST'])
@login_required
@trekker_required
def uncancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    # verify this booking belongs to the current user
    if booking.user_id != current_user.id:
        flash('You are not authorised to uncancel this booking.')
        return redirect(url_for('trekker_bp.trekker_dashboard'))

    # if booking.status != 'Cancelled':
    #     flash('Booking is already active.')
    #     return redirect(url_for('trekker_bp.trekker_dashboard'))

    if booking.status == 'Completed':
        flash('Cannot uncancel: Booking has already been completed.')
        return redirect(url_for('trekker_bp.trekker_dashboard'))
    elif booking.status == 'Booked':
        flash('Cannot uncancel: Booking is already active.')
        return redirect(url_for('trekker_bp.trekker_dashboard'))

    trek = Treks.query.get(booking.trek_id)
    if trek:
        if trek.status == 'Completed':
            flash('Trek has already completed!')
            return redirect(url_for('trekker_bp.trekker_dashboard'))
        elif trek.status == 'Cancelled':
            flash('Trek has already cancelled!')
            return redirect(url_for('trekker_bp.trekker_dashboard'))
        elif trek.start_date < date.today():
            flash('Trek has already started!')
            return redirect(url_for('trekker_bp.trekker_dashboard'))
        elif trek.available_slots <= 0:
            flash('Cannot uncancel: No available slots on the trek.')
            return redirect(url_for('trekker_bp.trekker_dashboard'))
    else:
        flash('Trek not found!')
        return redirect(url_for('trekker_bp.trekker_dashboard'))


    booking.status = 'Booked'
    trek.available_slots -= 1

    db.session.commit()
    flash(f'Booking #{booking.id} uncancelled successfully.')
    return redirect(url_for('trekker_bp.trekker_dashboard'))