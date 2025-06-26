# REST API endpoints for course management 

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc 

from app.extensions import db
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.utils.decorators import role_required

bp = Blueprint('courses_api', __name__)


@bp.route('/courses', methods=['GET'])
def get_courses():
    # Get paginated list of courses
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        category = request.args.get('category', '')
        difficulty = request.args.get('difficulty', '')
        search = request.args.get('search', '')
        featured_only = request.args.get('featured', False, type=bool)

        # Build query 
        query = Course.query.filter_by(is_published = True)

        if category: 
            query = query.filter_by(category = category)

        if difficulty: 
            query = query.filter_by(difficulty_level = difficulty)

        if featured_only:
            query = query.filter_by(is_featured = True)

        if search: 
            search_term = f'%{search}%'
            query = query.filter(
                Course.title.ilike(search_term) | 
                Course.description.ilike(search_term)
            )

        # Get paginated results 
        courses_pagination = query.order_by(desc(Course.created_at)).paginate(
            page = page,
            per_page = per_page,
            error_out = False
        )

        return jsonify({
            'success': True,
            'courses': [course.to_dict() for course in courses_pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': courses_pagination.total,
                'pages': courses_pagination.pages,
                'has_prev': courses_pagination.has_prev,
                'has_next': courses_pagination.has_next
            }
        })
    except Exception as e:
        current_app.logger.error(f'Error fetching courses: {str(e)}')
        return jsonify({'success': False, 'message': 'Failed to fetch '
        'courses'}), 500
    

@bp.route('/courses/<int:course_id>', methods = ['GET'])
def get_course(course_id):
    try:
        course = Course.query.get_or_404(course_id)

        if not course.is_published and not (
            current_user.is_authenticated and (
                current_user.is_admin() or 
                current_user.id == course.instructor_id
            )
        ):
            return jsonify({'success': False, 'message': 'Course not found'}), 400
        
        # check if the user is enrolled
        enrollment = None
        if current_user.is_authenticate:
            enrollment = Enrollment.query.filter_by(
                user_id = current_user.id,
                course_id = course_id,
                is_active = True
            ).first()

        course_data = course.to_dict(include_lessons = True)
        course_data['is_enrolled'] = enrollment is not None 
        course_data['enrollment_progress'] = enrollment.progress_percentage if enrollment else 0

        return jsonify({
            'success': True,
            'course': course_data
        })
    
    except Exception as e:
        current_app.logger.error(f'Error fetching course {course_id}: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Failed to fetch course'
        }), 500
    

@bp.route('/courses', methods = ['POST'])
@login_required
@role_required('teacher', 'admin')
def create_course():
    # create a new course
    try:
        data = request.get_json()

        if not data or 'title' not in data:
            return jsonify({'success': False, 'message': 'Course title is requried'}), 400
        
        course = Course(
            title=data['title'],
            description=data.get('description', ''),
            short_description=data.get('short_description', ''),
            instructor_id=current_user.id,
            category=data.get('category', ''),
            difficulty_level=data.get('difficulty_level', 'beginner'),
            duration_hours=data.get('duration_hours', 0),
            price=data.get('price', 0.00),
            is_published=data.get('is_published', False)
        )

        db.session.add(course)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Course created successfully',
            'course': course.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating course: {str(e)}')
        return jsonify({'success': False, 'message': 'Failed to create course'}), 500
    

@bp.route('/courses/<int:course_id>', methods = ['PUT'])
@login_required
@role_required('teacher', 'admin')
def update_course(course_id):
    try:
        course = Course.query.get_or_404(course_id)

        if not current_user.is_admin() and course.instructor_id != current_user.id:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
         # Update course fields
        if 'title' in data:
            course.title = data['title']
        if 'description' in data:
            course.description = data['description']
        if 'short_description' in data:
            course.short_description = data['short_description']
        if 'category' in data:
            course.category = data['category']
        if 'difficulty_level' in data:
            course.difficulty_level = data['difficulty_level']
        if 'duration_hours' in data:
            course.duration_hours = data['duration_hours']
        if 'price' in data:
            course.price = data['price']
        if 'is_published' in data:
            course.is_published = data['is_published']
        if 'is_featured' in data and current_user.is_admin():
            course.is_featured = data['is_featured']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Course updated successfully',
            'course': course.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error updating course {course_id}: {str(e)}')
        return jsonify({'success': False, 'message': 'Failed to update course'}), 500
    

@bp.route('/courses/<int:course_id>', methods = ['DELETE'])
@login_required
@role_required('teacher', 'admin')
def delete_course(course_id):
    # Delete a course
    try:
        course = Course.query.get_or_404(course_id)
        if not current_user.is_admin() and course.instructor_id != current_user.id:
            return jsonify({'success': False, 'message': 'Access Denied'}), 403
        
        active_enrollments = course.enrollments.filter_by(is_active=True).count()
        if active_enrollments > 0:
            return jsonify({
                'success': False,
                'message': 'Cannot delete course with active enrollments'
            }), 400
        
        db.session.delete(course)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Course delete successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting course {course_id}: {str(e)}')
        return jsonify({'success': False, 'message': 'Failed to delete course'}), 500
    

@bp.route('/courses/<int:course_id>/enroll', methods=['POST'])
@login_required
def enroll_in_course(course_id):
    """Enroll user in a course."""
    try:
        course = Course.query.get_or_404(course_id)
        
        if not course.is_published:
            return jsonify({'success': False, 'message': 'Course is not available for enrollment'}), 400
        
        # Check if already enrolled
        existing_enrollment = Enrollment.query.filter_by(
            user_id=current_user.id,
            course_id=course_id
        ).first()
        
        if existing_enrollment:
            if existing_enrollment.is_active:
                return jsonify({'success': False, 'message': 'Already enrolled in this course'}), 400
            else:
                # Reactivate enrollment
                existing_enrollment.is_active = True
                existing_enrollment.status = 'active'
                existing_enrollment.enrolled_at = datetime.utcnow()
                message = 'Successfully re-enrolled in the course'
        else:
            # Create new enrollment
            enrollment = Enrollment(
                user_id=current_user.id,
                course_id=course_id
            )
            db.session.add(enrollment)
            message = 'Successfully enrolled in the course'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error enrolling in course {course_id}: {str(e)}')
        return jsonify({'success': False, 'message': 'Failed to enroll in course'}), 500
    


@bp.route('/courses/<int:course_id>/lessons', methods=['GET'])
@login_required
def get_course_lessons(course_id):
    """Get lessons for a course."""
    try:
        course = Course.query.get_or_404(course_id)
        
        # Check access permissions
        if not course.can_be_accessed_by_user(current_user):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get lessons based on access level
        if (current_user.is_admin() or 
            current_user.id == course.instructor_id or 
            course.is_enrolled_by_user(current_user)):
            lessons = course.lessons.filter_by(is_published=True).order_by(Lesson.order_index).all()
        else:
            lessons = course.lessons.filter_by(
                is_published=True, 
                is_preview=True
            ).order_by(Lesson.order_index).all()
        
        return jsonify({
            'success': True,
            'lessons': [lesson.to_dict() for lesson in lessons]
        })
        
    except Exception as e:
        current_app.logger.error(f'Error fetching lessons for course {course_id}: {str(e)}')
        return jsonify({'success': False, 'message': 'Failed to fetch lessons'}), 500
