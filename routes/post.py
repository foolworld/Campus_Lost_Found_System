"""帖子路由

处理失物招领信息的发布、查看、编辑、删除等请求。
"""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Post, Comment
from services import find_similar_posts

post_bp = Blueprint('post', __name__)


@post_bp.route('/publish', methods=['GET', 'POST'])
@login_required
def publish():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        pickup_time = request.form['pickup_time']
        location = request.form['location']
        place_location = request.form['place_location']
        post_type = request.form.get('post_type', 'found')
        
        image = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(post_bp.app.config['UPLOAD_FOLDER'], filename))
                image = filename
        
        new_post = Post(
            title=title,
            description=description,
            pickup_time=pickup_time,
            location=location,
            place_location=place_location,
            image=image,
            author_id=current_user.id,
            post_type=post_type
        )
        db.session.add(new_post)
        db.session.commit()
        flash('发布成功，等待审核', 'success')
        return redirect(url_for('main.index'))
    return render_template('publish.html')


@post_bp.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    similar_posts = find_similar_posts(post)

    comments = []
    guest_token = request.cookies.get('guest_token')
    
    if current_user.is_authenticated:
        if current_user.id == post.author_id or current_user.role == 'admin':
            comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.desc()).all()
        else:
            comments = Comment.query.filter(
                Comment.post_id == post_id,
                (Comment.author_id == current_user.id) | (Comment.author_id == post.author_id)
            ).order_by(Comment.created_at.desc()).all()
    else:
        if guest_token:
            comments = Comment.query.filter(
                Comment.post_id == post_id,
                (Comment.guest_token == guest_token) | (Comment.author_id == post.author_id)
            ).order_by(Comment.created_at.desc()).all()
        else:
            comments = Comment.query.filter_by(post_id=post_id, author_id=post.author_id).order_by(Comment.created_at.desc()).all()
    
    return render_template('post_detail.html', post=post, similar_posts=similar_posts, comments=comments)


@post_bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author_id != current_user.id:
        flash('无权编辑此信息', 'danger')
        return redirect(url_for('post.post_detail', post_id=post_id))
    
    if request.method == 'POST':
        post.title = request.form['title']
        post.description = request.form['description']
        post.pickup_time = request.form['pickup_time']
        post.location = request.form['location']
        post.place_location = request.form['place_location']
        
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(post_bp.app.config['UPLOAD_FOLDER'], filename))
                post.image = filename
        
        post.status = 'pending'
        db.session.commit()
        flash('修改成功，等待审核', 'success')
        return redirect(url_for('post.post_detail', post_id=post_id))
    
    return render_template('edit_post.html', post=post)


@post_bp.route('/post/<int:post_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author_id != current_user.id and current_user.role != 'admin':
        flash('无权删除此信息', 'danger')
        return redirect(url_for('post.post_detail', post_id=post_id))
    
    db.session.delete(post)
    db.session.commit()
    flash('删除成功', 'success')
    return redirect(url_for('main.index'))


@post_bp.route('/my-posts')
@login_required
def my_posts():
    posts = Post.query.filter_by(author_id=current_user.id).order_by(Post.created_at.desc()).all()
    return render_template('my_posts.html', posts=posts)
