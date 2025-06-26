# Auth routes for user login, registration, and management

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from datetime import datetime

from app.extensions import db
from app.models.user import User
from app.utils.decorators import anonymous_required

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
@anonymous_required
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember = data.get('remember', False)

        if not email or not password:
            error_msg = 'Email and password are required'
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email = email).first()

        if user is None or not user.check_password(password):
            error_msg = 'Invalid email or password'
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 401
            flash(error_msg, 'error')
            return render_template('auth/login.html')
        
        if not user.is_active:
            error_msg = 'Your account has been deactivated. Please contact support'

            if request.is_json:
                return jsonify({'success': False, 'message':error_msg}), 401
            flash(error_msg, 'error')
            return render_template('auth/login.html')
        

    user.last_login = datetime.utcnow()
    db.session.commit()

    # Log user in
    login_user(user, remember=remember)

    if request.is_json:
        return jsonify({
            'success': True,
            'message': 'Login successful!',
            'user': user.to_dict(),
            'redirect_url': url_for('main.dashboard')
        })
    

    # Handle redirect for form submission
    next_page = request.args.get('next')
    if not next_page or url_parse(next_page).nextloc != '':
        next_page = url_for('main.dashboard')

    flash('Login successful! Welcome back.', 'success')
    return redirect(next_page)


@bp.route('/register', methods=['GET', 'POST'])
@anonymous_required
def register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form 

        # Extract from data
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        role = data.get('role', 'student').strip()

        # Validation
        errors = []

        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long.')

        if not email or '@' not in email:
            errors.append('Please provide a valid email address.')

        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters long.')

        if not first_name:
            errors.append('First name is required.')
        
        if not last_name:
            errors.append('Last name is required.')

        if role not in ['student', 'teacher']:
            role = 'student'

        if User.query.filter_by(username = username).first():
            errors.append('Username already exists. Please choose a different one.')

        if User.query.filter_by(email = email).first():
            errors.append('Email already registered. Please use a different email.')
        
        if errors:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'errors': errors
                }), 400
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        user = User(
            username = username,
            email = email, 
            first_name = first_name, 
            last_name = last_name,
            role = role
        )

        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()

            if request.is_json():
                return jsonify({
                    'success': True,
                    'message': 'Registration successful! Please log in.',
                    'redirect_url': url_for('auth_login')
                })
            
            flash('Registration successful! Please log in with your cred.', 'success')

        except Exception as e:
            db.session.rollback()
            error_msg = 'An error occured during registration. Please try again'

            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 500
            
            flash(error_msg, 'error')

    return render_template('auth/register.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('main.index'))


@bp.route('/profile')
@login_required 
def profile():
    return render_template('auth/profile.html', user = current_user)


@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form

    
        current_user.first_name = data.get('first_name', current_user.first_name).strip()
        current_user.last_name = data.get('last_name', current_user.last_name).strip()
        current_user.bio = data.get('bio', current_user.bio)
        current_user.timezone = data.get('timezone', current_user.timezone)
        current_user.language = data.get('language', current_user.language)

        # handle username change with validation
        new_username = data.get('username', '').strip()
        if new_username and new_username != current_user.username:
            if User.query.filter_by(username = new_username).first():
                error_msg = 'Username already exists. Please choose a different one.'

                if request.is_json:
                    return jsonify({'success': False, 'message':error_msg}), 400
                
                flash(error_msg, 'error')
                return render_template('auth/edit_profile.html')
            current_user.user = new_username

        try:
            db.session.commit()

            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Profile updated successfully',
                    'user': current_user.to_dict()
                })

            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
        
        except Exception as e:
            db.session.rollback()
            error_msg= 'An error occured while updating your profile'

            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 500
            
            flash(error_msg, 'error')

    return render_template('auth/edit_profile.html') 


@bp.route('/change-password', methods = ['POST'])
@login_required
def change_password():
    data = request.get_json() if request.is_json else request.form

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    #validation
    if not current_password or not new_password or not confirm_password:
        error_msg = 'All password fields are required.'

        if request.is_json:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        flash(error_msg, 'error')
        return redirect(url_for('auth.profile'))
    
    if not current_user.check_password(current_password):
        error_msg = 'Current password is incorrect.'
        if request.is_json:
            return jsonify({'success': False, 'message': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.profile'))
    
    if new_password != confirm_password:
        error_msg = 'New passwords do not match'
        if request.is_json:
            return jsonify({'success': False, 'message': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.profile'))
    
    if len(new_password) < 6:
        error_msg = 'New password must be at least 6 chars long'
        if request.is_json:
            return jsonify({'success': False, 'message': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('auth.profile'))
    
    current_user.set_password(new_password)

    try:
        db.session.commit()

        if request.is_json:
            return jsonify({'success': True, 'message': 'Password changed successfully'})
        flash('Password changed successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    except Exception as e:
        db.session.rollback()
        error_msg = 'An error occurred while changing your password'

        if request.is_json:
            return jsonify({'success': False, 'message': error_msg}), 500
        flash(error_msg, 'error')
        return redirect(url_for('auth.profile'))