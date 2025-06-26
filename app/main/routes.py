# main application routes for dashboard, courses, and general pages

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from datetime import datetime

from app.extensions import db
from app.models.user import User
from app.models.course import Course, Lesson
from app.models.quiz import Quiz, QuizAttempt, Question
from app.models.enrollment import Enrollment

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # home page
    # Get featured courses for homepage
    featured_courses = Course.query.filter_by(
        is_published=True,
        is_featured=True
    ).limit(6).all()

    # Get stats for homepage
    stats = {
        'total_courses': Course.query.filter_by(is_published=True).count(),
        'total_students': User.query.filter_by(role='student', is_active=True).count(),
        'total_teachers': User.query.filter_by(role='teacher', is_active=True).count(),
        'total_enrollment': Enrollment.query.filter_by(is_active=True).count()
    }

    return render_template('main/index.html',
                           featured_courses=featured_courses,
                           stats=stats)


@bp.route('/dashboard')
@login_required
def dashboard():
    # User dashboard
    if current_user.is_student():
        return student_dashboard()
    elif current_user.is_teacher():
        return teacher_dashboard()
    elif current_user.is_admin():
        return admin_dashboard
    else:
        flash('Access Denied', 'error')
        return redirect(url_for('main.index'))
    

def student_dashboard():
    # Student-specific dashboard
    enrollments = Enrollment.query.filter_by(
        user_id = current_user.id,
        is_active = True
    ).order_by(desc(Enrollment.last_accessed_at)).all()

    # Get recent quiz attempts
    recent_quiz_attempts = QuizAttempt.query.filter_by(
        user_id = current_user.user_id
    ).order_by(desc(QuizAttempt.completed_at)).limit(5).all()

    # Calculate progress statistics
    total_courses = len(enrollments)
    completed_courses = len([e for e in enrollments if e.is_completed()])
    average_progress = sum([e.progress_percentage for e in enrollments]) / total_courses if total_courses > 0 else 0

    # Get recommened courses (simple algo - courses in same category as enrolled course)
    enrolled_categories = list(set([e.course_category for e in enrollments if e.category]))
    recommended_courses = []

    if enrolled_categories:
        recommended_courses = Course.query.filter(
            Course.category.in_(enrolled_categories),
            Course.is_published == True,
            ~Course.id.in_([e.course_id for e in enrollments])
        ).limit(4).all()

    dashboard_data = {
        'enrollments': enrollments,
        'recent_quiz_attempts': recent_quiz_attempts,
        'stats': {
            'total_courses': total_courses,
            'completed_courses': completed_courses,
            'completion_rate': (completed_courses / total_courses) * 100 if total_courses > 0 else 0,
            'average_progress': average_progress,
        },
        'recommened_courses': recommended_courses
    }

    return render_template('main/dashboard_student.html', **dashboard_data)


def teacher_dashboard():
    # Teacher specific dashboard
    teacher_courses = Course.query.filter_by(
        instructor_id = current_user.id
    ).all()

    # Calc stats 
    total_students = db.session.query(func.count(Enrollment.id)).filter(
        Enrollment.course_id.in_([c.id for c in teacher_courses]),
        Enrollment.is_active == True
    ).scalar() or 0

    total_quizzes = db.session.query(func.count(Quiz.id)).filter(
        Quiz.course_id.in_([c.id for c in teacher_courses])
    ).scalar() or 0 

    # Get recent enrollments for teacher's courses
    recent_enrollments = db.session.query(Enrollment).join(Course).filter_by(
        Course.instructor_id == current_user.id,
        Enrollment.is_active == True
    ).order_by(desc(Enrollment.enrolled_at)).limit(10).all()

    # Get quiz stats 
    quiz_attempts_count = db.session.query(func.count(QuizAttempt.id)).join(Quiz).join(Course).filter(
        Course.instructor_id == current_user.id
    ).scalar() or 0

    dashboard_data = {
        'teacher_courses': teacher_courses,
        'recent_enrollments': recent_enrollments,
        'stats': {
            'total_courses': len(teacher_courses),
            'published_courses': len([c for c in teacher_courses if c.is_published]),
            'total_students': len(total_students),
            'total_quizzes': total_quizzes,
            'quiz_attempts': quiz_attempts_count
        }
    }

    return render_template('main/dashboard_teacher.html', **dashboard_data)


def admin_dashboard():
    #Admin specific dashboard 
    stats = {
        'total_users': User.query.filter_by(is_active=True).count(),
        'total_students': User.query.filter_by(role='student', is_active=True).count(),
        'total_teachers': User.query.filter_by(role='teacher', is_active=True).count(),
        'total_courses': Course.query.count(),
        'published_courses': Course.query.filter_by(is_published=True).count(),
        'total_enrollments': Enrollment.query.filter_by(is_active=True).count(),
        'total_quizzes': Quiz.query.count(),
        'quiz_attempts': QuizAttempt .query.count(),
    }

    # Recent activity 
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    recent_courses = Course.query.order_by(desc(Course.created_at)).limit(5).all()
    recent_enrollments = Enrollment.query.order_by(desc(Enrollment.enrolled_at)).limit(10).all()


    dashboard_data = {
        'stats': stats,
        'recent_users': recent_users,
        'recent_courses': recent_courses,
        'recent_enrollments': recent_enrollments,
    }

    return render_template('main/dashboard_admin.html', **dashboard_data)


@bp.route('/courses')
def courses():
    # browse all courses 
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')
    search = request.args.get('search', '')

    query = Course.query.filter_by(is_published=True)
    if category:
        query = query.filter_by(category = category)
    if difficulty:
        query = query.filter_by(difficulty_level=difficulty)
    if search:
        query = query.filter(Course.title.contains(search) | Course.description.contains(search))

    # Get paginated results 
    courses_pagination = query.order_by(desc(Course.created_at)).paginate(
        page = page,
        per_page = current_app.config['COURSES_PER_PAGE'],
        error_out = False   
    )

    # Get available categories and difficulties for filters
    categories = db.session.query(Course.category).filter(
        Course.is_published == True,
        Course.category != None
    ).distinct().all()

    categories = [c[0] for c in categories if c[0]]

    difficulties = ['beginner', 'intermediate', 'advanced']

    return render_template('main/courses.html',
                           courses = courses_pagination.items,
                           paginatio = courses_pagination,
                           categories = categories,
                           difficulties = difficulties,
                           current_difficulty = difficulty,
                           current_user = search)

    
@bp.route('/course/<int:course_id>')
def course_details(course_id):
    # Course detials page 
    course = Course.query.get_or_404(course_id)

    if not course.is_published and not (current_user.is_authenticated and (
        current_user.is_admin() or current_user.id == course.instructor_id
    )):
        flash('This course is not yet published.', 'error')
        return redirect(url_for('main.courses'))
    
    # Check if the user accesing it is enrolled
    enrollment = None
    if current_user.is_authenticated: 
        enrollment = Enrollment.query.filter_by(
            user_id = current_user.id,
            course_id = course_id,
            is_active = True
        ).first()

    # Get course lessons (preview for non-enrolled, all for enrolled)
    if enrollment or (current_user.is_authenticated and 
                      (current_user.is_admin() or current_user.id ==
                       course.instructor_id)):
        lessons = course.lessons.filter_by(is_published = True).order_by(Lesson.order_index).all()
    else:
        lessons = course.lessons.filter_by(is_published = True,
                                           is_preview = True).order_by(Lesson.order_index).all()
        
    
    # Get course stats
    enrollment_count = course.get_enrollment_count()
    average_rating = course.get_average_rating()

    return render_template('main/course_detail.html',
                           course = course,
                           lessons = lessons,
                           enrollment = enrollment,
                           enrollment_count = enrollment_count,
                           average_rating = average_rating) 


@bp.route('/course/<int:course_id>/enroll', methods = ['POST'])
@login_required
def enroll_course(course_id):
    #Enroll in a course
    course = Course.query.get_or_404(course_id)

    if not course.is_published:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Course is not '
            'available for enrollment.'}), 400
        flash('Course is not available for enrollment.', 'error')
        return redirect(url_for('main.course_detial', course_id = course_id))
    

    # Check if already enrolled 
    existing_enrollment = Enrollment.query.filter_by(
        user_id = current_user.id,
        course_id = course_id
    ).first()

    if existing_enrollment:
        if existing_enrollment.is_active:
            message = 'You are already enrolled in this course.'
        else:
            # reactivate enrollment 
            existing_enrollment.is_active = True
            existing_enrollment.status = 'active'
            existing_enrollment.enrolled_at = datetime.utcnow()
            db.session.commit()
            message = "Successfully re-enrolled in the course"
    else:
        enrollment = Enrollment(
            user_id = current_user.id,
            course_id = course_id
        )

        db.session.add(enrollment)
        db.session.commit()
        message = 'Successfully enrolled in the course!'
    
    if request.is_json:
        return jsonify({
            'success': True, 
            'message': message
        })
    
    flash(message, 'success')
    return redirect(url_for('main.course_detial', course_id= course_id))


@bp.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    # Get the lesson details
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.course 

    # Check access permissions
    if not course.can_be_accessed_by_user(current_user) and not lesson.is_preview:
        flash('You must be enrolled in this course to access this lesson.')
        return redirect(url_for('main.course_detial', course_id = course.id))
    
    # Get all lessons for navigation
    all_lessons = course.lessons.filter_by(is_published = True).order_by(
        Lesson.order_index).all()
    
    # Find the current lesson index for navigation
    current_index = next((i for i, l in enumerate(all_lessons)
                          if l.id == lesson_id), 0)
    
    # Get previous and next lessons 
    prev_lesson = all_lessons[current_index - 1] if current_index > 0 else None
    next_lesson = all_lessons[current_index + 1] if current_index < len(all_lessons) - 1 else None

    # Update last accessed time for enrollment
    if current_user.is_authenticated:
        enrollment = Enrollment.query.filter_by(
            user_id = current_user.id,
            course_id = course.id,
            is_active = True
        ).first()
        if enrollment:
            enrollment.last_accessed_at = datetime.utcnow()
            db.session.commit()

    return render_template('main/lesson_detail.html',
                           lesson = lesson,
                           course = course,
                           all_lessons = all_lessons,
                           current_index = current_index,
                           prev_lesson = prev_lesson,
                           next_lesson = next_lesson)


@bp.route('/quiz/<int:quiz_id>')
@login_required
def quiz_detail(quiz_id):
    # Get the details of the quiz
    quiz = Quiz.query.get_or_404()
    course = quiz.course 

    # Check access permissions
    if not course.can_be_accessed_by_user(current_user):
        flash('You must be enrolled in this course to access this quiz.')
        return redirect(url_for('main.course_detail', course_id = course.id))
    
    # Get user's previous attempts
    user_attempts = QuizAttempt.query.filter_by(
        user_id = current_user.id,
        quiz_id = quiz_id
    ).order_by(desc(QuizAttempt.started_at)).all()

    # Check if the user can attempt the quiz
    can_attempt = quiz.can_user_attempt(current_user)
    best_score = quiz.get_user_best_score(current_user)


    return render_template('main/quiz_detail.html',
                           quiz = quiz,
                           course = course,
                           user_attempts = user_attempts,
                           can_attempt = can_attempt,
                           best_score = best_score)


@bp.route('/quiz/<int:quiz_id>/take')
@login_required
def take_quiz(quiz_id):
    # Take quiz page 
    quiz = Quiz.query.get_or_404(quiz_id)
    course = quiz.course 

    # Check access permissions
    if not course.can_be_accessed_by_user(current_user):
        flash('You must be enrolled in this course to access this quiz.')
        return redirect(url_for('main.course_detail', course_id = course.id))
    
    # Check if the user can attempt the quiz
    if not quiz.can_user_attempt(current_user):
        flash('You have reached the maximum number of attempts for this quiz.')
        return redirect(url_for('main.quiz_detail', quiz_id = quiz_id))
    

    # create a new quiz attempt 
    attempt = QuizAttempt(
        user_id = current_user.id,
        quiz_id = quiz_id
    )
    db.session.add(attempt)
    db.session.commit()

    # Get quiz questions 
    questions = quiz.questions.order_by(Question.order_index).all()
    if quiz.is_ramdomized:
        import random
        questions = random.sample(questions, len(questions))

    return render_template('main/take_quiz.html',
                           quiz = quiz,
                           questions = questions,
                           attempt = attempt)


# Error handlers
@bp.app_errorhandler(404)
def page_not_found(error):
    return render_template('errors/404.html'), 404


@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500