from datetime import datetime
from app.extensions import db


class Enrollment(db.Mode):
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable = False)
    status = db.Column(db.String(20), default = 'active')
    is_active = db.Column(db.Boolean, default = False)
    progress_percentage = db.Column(db.Integer, default = 0)
    rating = db.Column(db.Integer)
    review = db.Column(db.Text)
    
    # Timestamps
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    last_accessed_at = db.Column(db.DateTime)

    #constraints to prevent duplicate enrollments
    __table_args__ = (db.UniqueConstraint('user_id', 'course_id', name='unique_user_course_enrollment'))

    def __repr__(self):
        return f'<Enrollment {self.id}: User {self.user_id}, Course {self.course_id}>'
    
    def update_progress(self):
        total_lessons = self.course.lessons.filter_by(is_published=True).count()
        if total_lessons == 0:
            self.progress_percentage = 100
            return
        
        completed_lessons = 0
        self.progress_percentage = (completed_lessons / total_lessons) * 100

        if self.progress_percentage >= 100 and self.status == 'active':
            self.status = 'completed'
            self.completed_at = datetime.utcnow()

    def is_completed(self):
        return self.status == 'completed'
    
    def get_time_enrolled_days(self):
        return (datetime.utcnow() - self.enrolled_at).days
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'status': self.status,
            'is_active': self.is_active,
            'progress_percentage': self.progress_percentage,
            'rating': self.rating,
            'review': self.review,
            'enrolled_at': self.enrolled_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            'time_enrolled_days': self.get_time_enrolled_days(),
        }