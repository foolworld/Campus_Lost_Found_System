"""管理员路由

处理管理员后台相关操作：审核帖子、管理用户、批量操作等。
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Post, User, Report, Notice
from services import create_notification, match_and_notify_subscribers

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('无权访问管理后台', 'danger')
        return redirect(url_for('main.index'))
    
    tab = request.args.get('tab', 'pending')
    
    if tab == 'approved':
        posts = Post.query.filter_by(status='approved').order_by(Post.created_at.desc()).all()
    elif tab == 'rejected':
        posts = Post.query.filter_by(status='rejected').order_by(Post.created_at.desc()).all()
    elif tab == 'users':
        posts = []
    elif tab == 'reports':
        posts = []
    else:
        posts = Post.query.filter_by(status='pending').order_by(Post.created_at.desc()).all()
    
    users = User.query.all()
    reports = Report.query.order_by(Report.created_at.desc()).all() if tab == 'reports' else []
    pending_count = Post.query.filter_by(status='pending').count()
    approved_count = Post.query.filter_by(status='approved').count()
    rejected_count = Post.query.filter_by(status='rejected').count()
    total_users = User.query.count()
    
    return render_template('admin_dashboard.html', 
                           posts=posts, users=users, reports=reports, tab=tab,
                           notices=[],
                           pending_count=pending_count,
                           approved_count=approved_count,
                           rejected_count=rejected_count,
                           total_users=total_users)


@admin_bp.route('/admin/post/<int:post_id>/approve')
@login_required
def approve_post(post_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    post = Post.query.get_or_404(post_id)
    post.status = 'approved'
    db.session.commit()

    match_and_notify_subscribers(post)
    
    create_notification(
        post.author_id,
        'post_approved',
        f'您的帖子「{post.title}」已通过审核',
        url_for('post.post_detail', post_id=post_id)
    )
    db.session.commit()
    
    flash('已通过审核', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/admin/post/<int:post_id>/reject')
@login_required
def reject_post(post_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    post = Post.query.get_or_404(post_id)
    post.status = 'rejected'
    db.session.commit()
    
    create_notification(
        post.author_id,
        'post_rejected',
        f'您的帖子「{post.title}」已被拒绝',
        url_for('post.post_detail', post_id=post_id)
    )
    db.session.commit()
    
    flash('已拒绝审核', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/admin/user/<int:user_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('不能删除管理员', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='users'))
    
    Post.query.filter_by(author_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    flash('删除用户成功，其发布的帖子已一并删除', 'success')
    return redirect(url_for('admin.admin_dashboard', tab='users'))


@admin_bp.route('/admin/user/<int:user_id>/promote')
@login_required
def promote_user(user_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    user = User.query.get_or_404(user_id)
    user.role = 'admin'
    db.session.commit()
    flash(f'{user.username} 已提升为管理员', 'success')
    return redirect(url_for('admin.admin_dashboard', tab='users'))


@admin_bp.route('/admin/users/batch-delete', methods=['POST'])
@login_required
def batch_delete_users():
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    user_ids = request.form.get('user_ids', '')
    if not user_ids:
        flash('请选择要删除的用户', 'warning')
        return redirect(url_for('admin.admin_dashboard', tab='users'))
    
    user_id_list = [int(id.strip()) for id in user_ids.split(',') if id.strip().isdigit()]
    deleted_count = 0
    skipped_admins = []
    
    for user_id in user_id_list:
        user = User.query.get(user_id)
        if not user:
            continue
        if user.role == 'admin':
            skipped_admins.append(user.username)
            continue
        
        Post.query.filter_by(author_id=user_id).delete()
        db.session.delete(user)
        deleted_count += 1
    
    if deleted_count > 0:
        db.session.commit()
        flash(f'成功删除 {deleted_count} 个用户', 'success')
    
    if skipped_admins:
        flash(f'以下管理员用户无法删除：{", ".join(skipped_admins)}', 'warning')
    
    if deleted_count == 0 and not skipped_admins:
        flash('未删除任何用户', 'warning')
    
    return redirect(url_for('admin.admin_dashboard', tab='users'))


@admin_bp.route('/admin/posts/batch-review', methods=['POST'])
@login_required
def batch_review_posts():
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    post_ids = request.form.get('post_ids', '')
    action = request.form.get('action', '')
    
    if not post_ids:
        flash('请选择要审核的信息', 'warning')
        return redirect(url_for('admin.admin_dashboard', tab='pending'))
    
    if action not in ['approve', 'reject']:
        flash('无效的操作类型', 'danger')
        return redirect(url_for('admin.admin_dashboard', tab='pending'))
    
    post_id_list = [int(id.strip()) for id in post_ids.split(',') if id.strip().isdigit()]
    reviewed_count = 0
    skipped_count = 0
    approved_posts = []
    
    for post_id in post_id_list:
        post = Post.query.get(post_id)
        if not post:
            continue
        if post.status != 'pending':
            skipped_count += 1
            continue
        
        post.status = 'approved' if action == 'approve' else 'rejected'
        if action == 'approve':
            approved_posts.append(post)
        reviewed_count += 1
    
    if reviewed_count > 0:
        db.session.commit()

        if action == 'approve':
            for post in approved_posts:
                match_and_notify_subscribers(post)

        action_text = '通过' if action == 'approve' else '拒绝'
        notif_type = 'post_approved' if action == 'approve' else 'post_rejected'
        for post_id in post_id_list:
            post = Post.query.get(post_id)
            if post:
                create_notification(
                    post.author_id,
                    notif_type,
                    f'您的帖子「{post.title}」已{action_text}审核',
                    url_for('post.post_detail', post_id=post_id)
                )
        db.session.commit()
        flash(f'成功{action_text} {reviewed_count} 条信息', 'success')
    
    if skipped_count > 0:
        flash(f'{skipped_count} 条信息非待审核状态，已跳过', 'warning')
    
    if reviewed_count == 0 and skipped_count == 0:
        flash('未审核任何信息', 'warning')
    
    return redirect(url_for('admin.admin_dashboard', tab='pending'))


@admin_bp.route('/admin/posts/batch-delete', methods=['POST'])
@login_required
def batch_delete_posts():
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('main.index'))
    
    post_ids = request.form.get('post_ids', '')
    tab = request.form.get('tab', 'approved')
    
    if not post_ids:
        flash('请选择要删除的信息', 'warning')
        return redirect(url_for('admin.admin_dashboard', tab=tab))
    
    post_id_list = [int(id.strip()) for id in post_ids.split(',') if id.strip().isdigit()]
    deleted_count = 0
    
    for post_id in post_id_list:
        post = Post.query.get(post_id)
        if not post:
            continue
        
        db.session.delete(post)
        deleted_count += 1
    
    if deleted_count > 0:
        db.session.commit()
        flash(f'成功删除 {deleted_count} 条信息', 'success')
    else:
        flash('未删除任何信息', 'warning')
    
    return redirect(url_for('admin.admin_dashboard', tab=tab))
