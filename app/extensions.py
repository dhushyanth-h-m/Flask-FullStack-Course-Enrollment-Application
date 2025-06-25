from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager 
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail 

# Init extensions
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()
csrf = CSRFProtect()
mail = Mail()


@login_manager.user_loader 
def load_user(user_id):
    from app.models.user import User 
    return User.query.get(int(user_id))