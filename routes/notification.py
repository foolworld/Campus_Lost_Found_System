"""通知路由

处理用户通知的查看和管理相关请求。
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Notification

notification_bp = Blueprint('notification', __name__)


@notification_bp.route('/api/notifications/unread-count')
@login_required
def unread_notification_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return {'count': count}


@notification_bp.route('/notifications')
@login_required
def notifications_page():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifications)


@notification_bp.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return {'status': 'ok'}


@notification_bp.route('/api/notifications/read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return {'status': 'error', 'message': '无权操作'}, 403
    notification.is_read = True
    db.session.commit()
    return {'status': 'ok'}


@notification_bp.route('/api/notifications/delete/<int:notification_id>', methods=['POST'])
@login_required
def delete_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id and current_user.role != 'admin':
        return {'status': 'error', 'message': '无权操作'}, 403
    db.session.delete(notification)
    db.session.commit()
    return {'status': 'ok'}
