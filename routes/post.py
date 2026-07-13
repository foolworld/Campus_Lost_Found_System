"""帖子路由

处理失物招领信息的发布、查看、编辑、删除等请求。
"""
import os
import time
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
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
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
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
        if post_type == 'found':
            flash('发布成功，感谢您的付出！', 'success')
            return redirect(url_for('post.post_detail', post_id=new_post.id, thanks=1))
        else:
            flash('发布成功，等待审核', 'success')
            return redirect(url_for('post.post_detail', post_id=new_post.id))
    return render_template('publish.html')


@post_bp.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)

    viewed_posts = session.get('viewed_posts', {})
    now = time.time()
    expired = [pid for pid, ts in viewed_posts.items() if now - ts > 300]
    for pid in expired:
        del viewed_posts[pid]

    if str(post_id) not in viewed_posts:
        try:
            if post.view_count is None:
                post.view_count = 0
            post.view_count += 1
            db.session.commit()
        except Exception:
            db.session.rollback()
        viewed_posts[str(post_id)] = now
        session['viewed_posts'] = viewed_posts

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
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
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

    # 优先按来源跳回原界面，保证"我的发布删完仍在我的发布"；兜底再回首页
    # 1) next 参数（同源安全校验，防止开放重定向）
    next_url = request.args.get('next') or request.form.get('next')
    if next_url:
        from urllib.parse import urlparse
        parsed = urlparse(next_url)
        # 允许相对路径 /xxx 或 同 host/空 netloc 的完整 URL
        if not parsed.netloc or parsed.netloc == request.host.split(':')[0]:
            return redirect(next_url)

    # 2) 同源 referrer（包含 my-posts 则一定跳回我的发布）
    referer = request.headers.get('Referer', '')
    if referer:
        from urllib.parse import urlparse as _up
        rp = _up(referer)
        same_host = (not rp.netloc) or (rp.netloc == request.host) or (rp.netloc.split(':')[0] == request.host.split(':')[0])
        if same_host:
            # 在我的发布页删除 → 保持我的发布界面
            return redirect(referer)

    # 3) 兜底回首页
    return redirect(url_for('main.index'))


@post_bp.route('/my-posts')
@login_required
def my_posts():
    posts = Post.query.filter_by(author_id=current_user.id).order_by(Post.created_at.desc()).all()
    return render_template('my_posts.html', posts=posts)
