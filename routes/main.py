"""主页面路由

处理首页、搜索页面等公共页面请求。
"""
from flask import Blueprint, render_template, request
from flask_login import current_user
from models import Post, User, Notice
from services import search_with_similarity

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'time', type=str)
    
    if sort == 'hot':
        posts = Post.query.filter_by(status='approved').order_by(Post.created_at.desc()).paginate(page=page, per_page=6)
    else:
        posts = Post.query.filter_by(status='approved').order_by(Post.created_at.desc()).paginate(page=page, per_page=6)
    
    total_posts = Post.query.filter_by(status='approved').count()
    total_users = User.query.count()
    
    is_admin = False
    if current_user.is_authenticated and current_user.role == 'admin':
        is_admin = True
    
    latest_notice = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).first()
    
    return render_template('index.html', posts=posts.items, page=page, total_pages=posts.pages, 
                           total_posts=total_posts, total_users=total_users, sort=sort, is_admin=is_admin,
                           latest_notice=latest_notice)


@main_bp.route('/search')
def search():
    keyword = request.args.get('keyword', '')
    post_type = request.args.get('post_type', 'all')
    posts = []
    if keyword:
        posts = search_with_similarity(keyword, top_n=20)
        if post_type != 'all':
            posts = [p for p in posts if p.post_type == post_type]
    else:
        query = Post.query.filter_by(status='approved')
        if post_type != 'all':
            query = query.filter_by(post_type=post_type)
        posts = query.order_by(Post.created_at.desc()).all()
    return render_template('search.html', posts=posts, keyword=keyword, post_type=post_type)
