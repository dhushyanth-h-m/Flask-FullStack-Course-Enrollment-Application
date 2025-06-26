from datetime import datetime 
from app.extensions import db 
import json


class Quiz(db.Model):
    __tablename__ = 'quizzes'

    id = db.Column(db.Intger, primary_key = True)
    title = db.Column(db.String(200), nullable = False)
    description = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable = False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable = False)
    duration_minutes = db.Column(db.Integer, default = 30)
    max_attemtps = db.Column(db.Integer, default = 3)
    passing_score = db.Column(db.Integer, default = 70)
    is_published = db.Column(db.Boolean, default = False)
    is_randomized = db.Column(db.Boolean, default = True)
    show_results_immediately = db.Column(db.Boolean, default = True)

    # Timestamps
    created_at = db.Column(db.DateTime, default =datetime.utcnow)
    updated_at = db.Column(db.DateTime, default =datetime.utcnow, onupdate = datetime.utcnow)

    #Relationships
    questions = db.realtionship('Question', backref = 'quiz', lazy = 'dynamic', cascade = 'all, delete-orphan')
    attempts = db.realtionship('QuizAttempt', backref = 'quiz', lazy = 'dynamic', cascade = 'all, delete-orphan')

    def __repr__(self):
        return f'<Quiz {self.title}>'
    
    def get_questions_count(self):
        return self.questions.count() 
    
    def get_total_points(self):
        return sum([q.points for q in self.questions])
    
    def get_average_score(self):
        completed_attemtps = self.attempts.filter_by(status = 'completed')
        scores = [attempt.score for attempt in completed_attemtps if attempt.score is not None]
        return sum(scores) / len(scores) if scores else 0
    
    def get_completion_rate(self):
        total_attempts = self.attempts.count()
        completed_attempts = self.attempts.filter_by(status = 'completed').count()
        return (completed_attempts / total_attempts * 100) if total_attempts > 0 else 0
    
    def can_user_attempt(self, user):
        user_attempts = self.attempts.filter_by(user_id = user.id).count()
        return user_attempts < self.max_attemtps
    
    def get_user_best_score(self, user):
        user_attempts = self.attempts.filter_by(user_id = user.id, status='completed')
        scores = [attempts.score for attempts in user_attempts if attempts.score is not None]
        return max(scores) if scores else None

    def to_dict(self, include_questions = False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'course_id': self.course_id,
            'lesson_id': self.lesson_id,
            'duration_minutes': self.duration_minutes,
            'max_attempts': self.max_attemtps,
            'passing_score': self.passing_score,
            'is_published': self.is_published,
            'is_randomized': self.is_randomized,
            'show_results_immediately': self.show_results_immediately,
            'questions_count': self.get_questions_count(),
            'total_points': self.get_total_points(),
            'average_score': self.get_average_score(),
            'completion_rate': self.get_completion_rate(),
            'create_at': self.created_at.isoformat(),
        }

        if include_questions:
            data['questions'] = [q.to_dict() for q in self.questions.order_by(Question.order_index)]

        return data
    

class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key = True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable = False)
    question_text = db.Column(db.Text, nullable = False)
    question_type = db.Column(db.String(20), default='multiple_choice')
    options = db.Column(db.Text)
    correct_answer = db.Column(db.Text, nullable = False)
    explanation = db.Column(db.Text)
    points = db.Column(db.Integer, default = 1)
    order_index = db.Column(db.Integer, nullable = False)
    difficulty = db.Column(db.Integer, default = 'medium')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default =datetime.utcnow)
    updated_at = db.Column(db.DateTime, default =datetime.utcnow, onupdate = datetime.utcnow)


    def __repr__(self):
        return f'<Question {self.id}: {self.question_text[:50]}...>'
    
    def get_options_list(self):
        if self.options:
            try:
                return json.loads(self.options)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_options_list(self, options_list):
        self.options = json.dumps(options_list)

    def check_answer(self, user_answer):
        if self.question_type == 'multiple_choice':
            return str(user_answer).strip().lower() == str(self.correct_answer).strip().lower()
        elif self.question_type == 'true_false':
            return str(user_answer).strip().lower() == str(self.correct_answer).strip().lower()
        elif self.question_type == 'short_answer':
            return str(user_answer).strip().lower() == str(self.correct_answer).strip().lower()
        elif self.question_type == 'short_answer':
            return str(user_answer).strip().lower() == str(self.correct_answer).strip().lower()
        return False
    
    def to_dict(self, include_correct_answer = False):
        data = {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'options': self.get_options_list(),
            'explanation': self.explanation,
            'points': self.points,
            'order_index': self.order_index,
            'difficulty': self.difficulty,
        }

        if include_correct_answer:
            data['correct_answer'] = self.correct_answer

        return data
    

class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable = False)
    status = db.Column(db.String(20), default = 'in_progress')
    score = db.Column(db.Integer)
    total_points = db.Column(db.Integer)
    earned_points = db.Column(db.Integer)
    time_spent_minutes = db.Column(db.Integer)
    answers = db.Column(db.Text)
    
    #Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<QuizzAttempt {self.id}: User {self.user_id}, Quiz {self.quiz_id}>'
    
    def get_answers_dict(self):
        if self.answers:
            try:
                return json.loads(self.answer)
            except json.JSONDecodeError:
                return {}
            
        return {}
    
    def set_answers_dict(self, answers_dict):
        self.answers = json.dump(answers_dict)

    def calculate_score(self):
        if self.status != 'completed':
            return 
        
        answers_dict = self.get_answers_dict()
        total_points = 0
        earned_points = 0

        for question in self.quiz.questions:
            total_points += question.points
            user_answer = answers_dict.get(str(question.id))

            if user_answer is not None and question.check_answer(user_answer):
                earned_points += question.points

        self.total_points = total_points
        self.earned_points = earned_points
        self.score = (earned_points / total_points * 100) if total_points > 0 else 0


    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'quiz_id': self.quiz_id,
            'status': self.status,
            'total_points': self.total_points,
            'earned_points': self.earned_points,
            'time_spent_minutes': self.time_spent_minutes,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }