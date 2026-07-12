"""应用配置与初始化

配置 Flask 应用的基础参数（密钥、数据库、文件上传等），
并初始化 SQLAlchemy 和 Flask-Login 扩展。
"""
import os
from flask import Flask
from flask_login import LoginManager
from models import db, User


def create_app():
    """创建并配置 Flask 应用实例"""
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'campus-lost-found-secret-key-2026'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lost_found.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'static/images'
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    
    return app


def init_login_manager(app):
    """初始化 Flask-Login 管理器"""
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return login_manager
