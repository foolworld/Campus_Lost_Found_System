"""举报路由

处理帖子举报和举报管理相关请求。
"""
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Post, Report

report_bp = Blueprint('report', __name__)


@report_bp.route('/post/<int:post_id>/report', methods=['POST'])
@login_required
def report_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if post.author_id == current_user.id:
        flash('不能举报自己的帖子', 'danger')
        return redirect(url_for('post.post_detail', post_id=post_id))
    
    existing_report = Report.query.filter_by(post_id=post_id, reporter_id=current_user.id).first()
    if existing_report:
        flash('您已举报过此帖子', 'warning')
        return redirect(url_for('post.post_detail', post_id=post_id))
    
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('请填写举报原因', 'danger')
        return redirect(url_for('post.post_detail', post_id=post_id))
    
    report = Report(
        post_id=post_id,
        reporter_id=current_user.id,
        reason=reason
    )
    db.session.add(report)
    db.session.commit()
    
    flash('举报成功，管理员将尽快处理', 'success')
    return redirect(url_for('post.post_detail', post_id=post_id))


@report_bp.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.role != 'admin':
        flash('无权访问举报管理', 'danger')
        return redirect(url_for('main.index'))
    
    reports = Report.query.order_by(Report.created_at.desc()).all()
    pending_count = Report.query.filter_by(status='pending').count()
    
    return render_template('admin_dashboard.html', 
                           reports=reports, 
                           posts=[], users=[],
                           tab='reports',
                           pending_count=pending_count,
                           approved_count=Post.query.filter_by(status='approved').count(),
                           rejected_count=Post.query.filter_by(status='rejected').count(),
                           total_users=db.session.query(db.func.count(User.id)).scalar())


@report_bp.route('/admin/report/<int:report_id>/handle', methods=['POST'])
@login_required
def handle_report(report_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    report = Report.query.get_or_404(report_id)
    result = request.form.get('result', '')
    
    if result not in ['violation', 'rejected']:
        flash('无效的处理结果', 'danger')
        return redirect(url_for('report.admin_reports'))
    
    report.status = 'handled'
    report.result = result
    report.handled_by = current_user.id
    report.handled_at = datetime.datetime.now()
    
    if result == 'violation':
        post = Post.query.get(report.post_id)
        if post:
            post.status = 'rejected'
    
    db.session.commit()
    
    if result == 'violation':
        flash('已确认违规，帖子已被拒绝', 'success')
    else:
        flash('已驳回举报', 'success')
    
    return redirect(url_for('report.admin_reports'))
