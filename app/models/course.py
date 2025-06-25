from datetime import datetime
from app.extensions import db 


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(200), nullable = False)
    description = db.Column(db.Text)
    short_description = db.Column(db.String(500))
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    category = db.Column(db.String(100))
    difficulty_level = db.Column(db.String(20), default = 'beginner')
    duration_hours = db.Column(db.Integer)
    price = db.Column(db.Numeric(10, 2), default = 0.00)
    is_published = db.Column(db.Boolean, default = False)
    is_featured = db.Column(db.Boolean, default = False)
    thumbnail_url = db.Column(db.String(300))
    video_preview_url = db.Column(db.String(300))
    
    # timestamps 
    created_at = db.Column(db.DateTime, default = datetime.utcnow)
    updated_at = db.Column(db.DateTime, default = datetime.utcnow, onupdate = datetime.utcnow)
    published_at = db.Column(db.DateTime)

    # Course metadata
    tags = db.Column(db.Text)
    learning_objectives = db.Column(db.Text)
    prerequisites = db.Column(db.Text)

    # Relationships
    lessons = db.relationship('Lesson', backref = 'course', lazy = 'dynamic', cascade = 'all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref = 'course', lazy = 'dynamic', cascade = 'all, delete-orphan')
    quizzes = db.relationship('Quiz', backref = 'course', lazy = 'dynamic', cascade = 'all, delete-orphan')

    def __repr__(self):
        return f'<Course {self.title}'
    
    def get_enrollment_count(self):
        return self.enrollments.filter_by(is_active = True).count() 
    
    def get_average_rating(self):
        ratings = [e.rating for e in self.enrollments if e.rating is not None]
        return sum(ratings) / len(ratings) if ratings else 0
    
    def get_completion_rate(self):
        total_enrollments = self.enrollments.filter_by(is_active = True).count()
        completed_enrollments = self.enrollments.filter_by(is_active = True, status = 'completed').count()
        return (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
    
    def get_lessons_count(self):
        return self.lessons.filter_by(is_pubished = True).count()
    
    def get_total_duration(self):
        return sum([lesson.duration_minutes or 0 for lesson in self.lessons])
    
    def is_enrolled_by_user(self, user):
        return self.enrollments.filter_by(user_id = user.id, is_active = True).first() is not None
    
    def can_be_accessed_by_user(self, user):
        if user.is_teacher() or user.is_admin():
            return True
        return self.is_enrolled_by_user(user)
    
    def to_dict(self, include_lessons = False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'short_description': self.short_description,
            'instructor': self.instructor.get_full_name() if self.istructor else None,
            'category': self.category,
            'difficulty_level': self.difficulty_level,
            'duration_hours': self.duration_hours,
            'price': float(self.price) if self.price else 0.0,
            'is_published': self.is_published,
            'is_featured': self.is_featured,
            'thumbnail_url': self.thumbnail_url,
            'created_at': self.created_at.isoformat(),
            'enrollment_count': self.get_enrollment_count(),
            'average_rating': self.get_average_rating(),
            'completion_rate': self.get_completion_rate(),
            'lessons_count': self.get_lessons_count(),
            'total_duration': self.get_total_duration(),
        }

        if include_lessons:
            data['lessons'] = [lesson.to_dict() for lesson in self.lessons.filter_by(is_published = True)]

        return data 
    
class Lesson(db.Model):
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(200), nullable = False)
    content = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    order_index = db.Column(db.Integer, nullable = False)
    lesson_type = db.Column(db.String(20), default = 'text')
    duration_minutes = db.Column(db.Integer)
    video_url = db.Column(db.String(300))
    materials_url = db.Column(db.String(300))
    is_published = db.Column(db.Boolean, defaut = True)
    is_preview = db.Column(db.Boolean, defaut = False)

    # Timestamps
    created_at = db.Column(db.DateTime, defaut = datetime.utcnow)
    updated_at = db.Column(db.DateTime, defaut = datetime.utcnow, onupdate = datetime.utcnow)

    def __repr__(self):
        return f'<Lesson {self.title}'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'course_id': self.course_id,
            'order_index': self.order_index,
            'lesson_type': self.lesson_type,
            'duration_minutes': self.duration_minutes,
            'video_url': self.video_url,
            'materials_url': self.materials_url,
            'is_published': self.is_published,
            'is_preview': self.is_preview,
            'created_at': self.created_at.isoformat()
        }