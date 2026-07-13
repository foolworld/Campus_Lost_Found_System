"""公告路由

处理公告的管理和查看相关请求。
"""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from models import db, User, Post, Notice

notice_bp = Blueprint('notice', __name__)


@notice_bp.route('/admin/notices')
@login_required
def admin_notices():
    if current_user.role != 'admin':
        flash('无权访问公告管理', 'danger')
        return redirect(url_for('main.index'))
    
    now = datetime.now()
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return render_template('admin_dashboard.html', 
                           notices=notices, 
                           posts=[], users=[], reports=[],
                           tab='notices',
                           now=now,
                           pending_count=Post.query.filter_by(status='pending').count(),
                           approved_count=Post.query.filter_by(status='approved').count(),
                           rejected_count=Post.query.filter_by(status='rejected').count(),
                           total_users=User.query.count())


@notice_bp.route('/admin/notice/add', methods=['POST'])
@login_required
def add_notice():
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    publish_at_str = request.form.get('publish_at', '').strip()
    is_active = request.form.get('is_active') is not None
    
    publish_at = None
    if publish_at_str:
        try:
            publish_at = datetime.fromisoformat(publish_at_str)
        except ValueError:
            publish_at = None
    
    if not title or not content:
        flash('请填写公告标题和内容', 'danger')
        return redirect(url_for('notice.admin_notices'))
    
    notice = Notice(
        title=title,
        content=content,
        is_active=is_active,
        publish_at=publish_at,
        created_by=current_user.id
    )
    db.session.add(notice)
    db.session.commit()
    
    flash('公告发布成功', 'success')
    return redirect(url_for('notice.admin_notices'))


@notice_bp.route('/admin/notice/<int:notice_id>/json')
@login_required
def get_notice_json(notice_id):
    if current_user.role != 'admin':
        abort(403)
    
    notice = Notice.query.get_or_404(notice_id)
    return jsonify({
        'id': notice.id,
        'title': notice.title,
        'content': notice.content,
        'is_active': notice.is_active,
        'publish_at': notice.publish_at.strftime('%Y-%m-%dT%H:%M') if notice.publish_at else ''
    })


@notice_bp.route('/admin/notice/<int:notice_id>/edit', methods=['POST'])
@login_required
def edit_notice(notice_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    notice = Notice.query.get_or_404(notice_id)
    
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    publish_at_str = request.form.get('publish_at', '').strip()
    is_active = request.form.get('is_active') is not None
    
    if not title or not content:
        flash('请填写公告标题和内容', 'danger')
        return redirect(url_for('notice.admin_notices'))
    
    publish_at = None
    if publish_at_str:
        try:
            publish_at = datetime.fromisoformat(publish_at_str)
        except ValueError:
            publish_at = None
    
    notice.title = title
    notice.content = content
    notice.is_active = is_active
    notice.publish_at = publish_at
    if notice.created_by is None:
        notice.created_by = current_user.id
    notice.updated_at = datetime.now()
    
    db.session.commit()
    
    flash('公告更新成功', 'success')
    return redirect(url_for('notice.admin_notices'))


@notice_bp.route('/admin/notice/<int:notice_id>/toggle')
@login_required
def toggle_notice(notice_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    notice = Notice.query.get_or_404(notice_id)
    notice.is_active = not notice.is_active
    db.session.commit()
    
    flash(f'公告已{"启用" if notice.is_active else "禁用"}', 'success')
    return redirect(url_for('notice.admin_notices'))


@notice_bp.route('/admin/notice/<int:notice_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_notice(notice_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    notice = Notice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()
    
    flash('公告已删除', 'success')
    return redirect(url_for('notice.admin_notices'))


@notice_bp.route('/api/notices')
def get_notices():
    now = datetime.now()
    notices = Notice.query.filter(
        Notice.is_active == True,
        db.or_(Notice.publish_at.is_(None), Notice.publish_at <= now)
    ).order_by(Notice.created_at.desc()).all()
    return {'notices': [{
        'id': notice.id,
        'title': notice.title,
        'content': notice.content,
        'created_at': notice.created_at.strftime('%Y-%m-%d %H:%M'),
        'publish_at': notice.publish_at.strftime('%Y-%m-%d %H:%M') if notice.publish_at else None
    } for notice in notices]}


@notice_bp.route('/notices')
def notices_page():
    now = datetime.now()
    notices = Notice.query.filter(
        Notice.is_active == True,
        db.or_(Notice.publish_at.is_(None), Notice.publish_at <= now)
    ).order_by(Notice.created_at.desc()).all()
    return render_template('notices.html', notices=notices)
