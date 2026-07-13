"""评论路由

处理评论的添加、编辑、删除等请求。
"""
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Comment, Post
from services import create_notification

comment_bp = Blueprint('comment', __name__)


@comment_bp.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id')
    
    if not content:
        flash('请填写留言内容', 'danger')
        return redirect(url_for('post.post_detail', post_id=post_id))
    
    if current_user.is_authenticated:
        comment = Comment(
            post_id=post_id,
            author_id=current_user.id,
            content=content,
            parent_id=int(parent_id) if parent_id else None
        )
        db.session.add(comment)
        db.session.commit()
        
        if post.author_id != current_user.id:
            create_notification(
                post.author_id,
                'new_comment',
                f'{current_user.username} 在您的帖子「{post.title}」下留言了',
                url_for('post.post_detail', post_id=post_id)
            )
        if parent_id:
            parent_comment = Comment.query.get(int(parent_id))
            if parent_comment and parent_comment.author_id and parent_comment.author_id != current_user.id:
                create_notification(
                    parent_comment.author_id,
                    'new_reply',
                    f'{current_user.username} 回复了您在帖子「{post.title}」下的留言',
                    url_for('post.post_detail', post_id=post_id)
                )
        db.session.commit()
        flash('留言成功', 'success')
    else:
        guest_name = request.form.get('guest_name', '游客').strip()
        guest_token = request.cookies.get('guest_token')
        if not guest_token:
            guest_token = str(uuid.uuid4())
        
        comment = Comment(
            post_id=post_id,
            guest_name=guest_name,
            guest_token=guest_token,
            content=content
        )
        db.session.add(comment)
        db.session.commit()
        
        resp = redirect(url_for('post.post_detail', post_id=post_id))
        resp.set_cookie('guest_token', guest_token, max_age=30*24*60*60)
        flash('留言成功', 'success')
        return resp
    
    return redirect(url_for('post.post_detail', post_id=post_id))


@comment_bp.route('/comment/<int:comment_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if current_user.role != 'admin':
        flash('无权删除此留言', 'danger')
        return redirect(url_for('post.post_detail', post_id=comment.post_id))
    
    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    flash('留言已删除', 'success')
    
    post = Post.query.get(post_id)
    if post:
        return redirect(url_for('post.post_detail', post_id=post_id))
    else:
        return redirect(url_for('main.index'))


@comment_bp.route('/comment/<int:comment_id>/reply', methods=['GET', 'POST'])
def reply_comment(comment_id):
    parent_comment = Comment.query.get_or_404(comment_id)
    post_id = parent_comment.post_id
    post = Post.query.get_or_404(post_id)
    
    if not current_user.is_authenticated:
        flash('请先登录后再回复', 'danger')
        return redirect(url_for('auth.login', next=url_for('comment.reply_comment', comment_id=comment_id)))
    
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            flash('回复内容不能为空', 'danger')
            return redirect(url_for('comment.reply_comment', comment_id=comment_id))
        
        reply = Comment(
            post_id=post_id,
            author_id=current_user.id,
            content=content,
            parent_id=comment_id
        )
        db.session.add(reply)
        db.session.commit()
        
        if parent_comment.author_id and parent_comment.author_id != current_user.id:
            create_notification(
                parent_comment.author_id,
                'new_reply',
                f'{current_user.username} 回复了您在帖子「{post.title}」下的留言',
                url_for('post.post_detail', post_id=post_id)
            )
            db.session.commit()
        
        flash('回复成功', 'success')
        return redirect(url_for('post.post_detail', post_id=post_id))
    
    return render_template('reply_comment.html', parent_comment=parent_comment)


@comment_bp.route('/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id
    
    if current_user.is_authenticated:
        if comment.author_id != current_user.id and current_user.role != 'admin':
            flash('无权编辑此留言', 'danger')
            return redirect(url_for('post.post_detail', post_id=post_id))
    else:
        guest_token = request.cookies.get('guest_token')
        if not guest_token or not comment.guest_token or comment.guest_token != guest_token:
            flash('无权编辑此留言', 'danger')
            return redirect(url_for('post.post_detail', post_id=post_id))
    
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            flash('留言内容不能为空', 'danger')
            return redirect(url_for('comment.edit_comment', comment_id=comment_id))
        
        comment.content = content
        db.session.commit()
        flash('留言已修改', 'success')
        return redirect(url_for('post.post_detail', post_id=post_id))
    
    return render_template('edit_comment.html', comment=comment)
