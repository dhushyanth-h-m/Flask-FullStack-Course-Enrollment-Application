from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db 


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(80), unique = True, nullable = False, index = True)
    email = db.Column(db.String(120), unique = True, nullable = False, index = True) 
    password_hash = db.Column(db.String(256), nullable = False) 
    first_name = db.Column(db.String(50), nullable = False)
    last_name = db.Column(db.String(50), nullable = False)
    role = db.Column(db.String(20), nullable = False, default = 'student')
    is_active = db.Column(db.Boolean, default = True)
    is_verified = db.Column(db.Boolean, default = False)
    created_at = db.Column(db.DateTime, default = datetime.utcnow) 
    updated_at = db.Column(db.DateTime, default = datetime.utcnow, onupdate = datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Profile Info
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(200))
    timezone = db.Column(db.String(50), default = 'UTC') 
    language = db.Column(db.String(10), default = 'en')

    # Relationships
    enrollments = db.relationship('Enrollment', backref = 'user', lazy = 'dynamic', cascade = 'all, delete-orphan')
    quiz_attempts = db.relationship('QuizAttempt', backref = 'user', lazy = 'dynamic', cascade = 'all, delete-orphan')
    created_courses = db.relationship('Course', backref = 'instructor', lazy = 'dynamic')

    def __repr__(self):
        return f'<User {self.username}'

    def set_password(self, password): 
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def is_student(self):
        return self.role == 'student'

    def is_teacher(self):
        return self.role == 'teacher'

    def is_admin(self):
        return self.role == 'admin'
    
    def get_enrolled_courses(self):
        return [enrollment.course for enrollment in self.enrollments if enrollment.is_active]
    
    def get_progress_summary(self):
        total_courses = self.enrollments.filter_by(is_active = True).count()
        completed_courses = self.enrollments.filter_by(is_active = True, status = 'completed').count()
        total_quizzes = self.quiz_attempts.count()

        return {
            'total_courses': total_courses,
            'completed_courses': completed_courses,
            'completion_rate': (completed_courses / total_courses * 100) if total_courses > 0 else 0,
            'total_quizzes': total_quizzes
        }
    
    def to_dict(self, include_email = False):
        data = {
            'id': self.id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'avatar_url': self.avatar_url,
            'bio': self.bio,
        }

        if include_email:
            data['email'] = self.email 

        return data 