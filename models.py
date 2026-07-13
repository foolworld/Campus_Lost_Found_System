"""数据库模型定义

定义所有数据库表对应的 ORM 模型类：
- User: 用户模型
- Post: 失物招领信息模型
- Report: 举报模型
- Comment: 评论模型
- Notification: 通知模型
- Notice: 公告模型
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Post(db.Model):
    """失物招领信息模型"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    pickup_time = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    place_location = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(200))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    post_type = db.Column(db.String(10), default='found')
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.now)

    author = db.relationship('User', backref=db.backref('posts', lazy=True))


class Report(db.Model):
    """举报模型"""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    result = db.Column(db.String(20))
    handled_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    handled_at = db.Column(db.DateTime)

    post = db.relationship('Post', backref=db.backref('reports', lazy=True))
    reporter = db.relationship('User', foreign_keys=[reporter_id], backref=db.backref('reported_posts', lazy=True))
    handler = db.relationship('User', foreign_keys=[handled_by], backref=db.backref('handled_reports', lazy=True))


class Comment(db.Model):
    """评论模型"""
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    guest_name = db.Column(db.String(50))
    guest_token = db.Column(db.String(36))
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete='CASCADE'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    post = db.relationship('Post', backref=db.backref('comments', lazy=True))
    author = db.relationship('User', backref=db.backref('comments', lazy=True))
    parent = db.relationship('Comment', remote_side=[id], backref='replies')


class Notification(db.Model):
    """通知模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    content = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))


class Notice(db.Model):
    """公告模型"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime)
