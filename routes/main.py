"""主页面路由

处理首页、搜索页面等公共页面请求。
"""
from datetime import datetime, timedelta
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
        posts = Post.query.filter_by(status='approved').order_by(Post.view_count.desc().nullslast(), Post.created_at.desc()).paginate(page=page, per_page=6)
    else:
        posts = Post.query.filter_by(status='approved').order_by(Post.created_at.desc()).paginate(page=page, per_page=6)
    
    total_posts = Post.query.filter_by(status='approved').count()
    total_users = User.query.count()
    
    is_admin = False
    if current_user.is_authenticated and current_user.role == 'admin':
        is_admin = True
    
    latest_notice = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).first()
    
    thanks_title = None
    if request.args.get('thanks') == '1':
        tid = request.args.get('tid', type=int)
        if tid and current_user.is_authenticated:
            post = Post.query.get(tid)
            if post and post.author_id == current_user.id:
                thanks_title = post.title
    
    return render_template('index.html', posts=posts.items, page=page, total_pages=posts.pages, 
                           total_posts=total_posts, total_users=total_users, sort=sort, is_admin=is_admin,
                           latest_notice=latest_notice, thanks_title=thanks_title)


@main_bp.route('/search')
def search():
    keyword = request.args.get('keyword', '')
    post_type = request.args.get('post_type', 'all')
    time_range = request.args.get('time', 'all')

    valid_ranges = ['all', '7d', '30d', '90d']
    if time_range not in valid_ranges:
        time_range = 'all'

    cutoff = None
    if time_range == '7d':
        cutoff = datetime.now() - timedelta(days=7)
    elif time_range == '30d':
        cutoff = datetime.now() - timedelta(days=30)
    elif time_range == '90d':
        cutoff = datetime.now() - timedelta(days=90)

    posts = []
    if keyword:
        posts = search_with_similarity(keyword, top_n=20)
        if post_type != 'all':
            posts = [p for p in posts if p.post_type == post_type]
        if cutoff is not None:
            posts = [p for p in posts if p.created_at >= cutoff]
    else:
        # 无 keyword 时不默认显示全部（避免首次进入空状态引导不出现），用户想看全部去首页
        # 仅当用户选了非默认筛选（类型/时间）时才按筛选拉结果
        if post_type != 'all' or cutoff is not None:
            query = Post.query.filter_by(status='approved')
            if post_type != 'all':
                query = query.filter_by(post_type=post_type)
            if cutoff is not None:
                query = query.filter(Post.created_at >= cutoff)
            posts = query.order_by(Post.created_at.desc()).all()

    suggestions = ['学生证', '钥匙', '耳机', '校园卡', '钱包']

    hot_posts = Post.query.filter_by(status='approved').order_by(Post.created_at.desc()).limit(6).all()

    type_filter = post_type

    return render_template('search.html', posts=posts, keyword=keyword, post_type=post_type,
                           time_range=time_range, suggestions=suggestions, hot_posts=hot_posts,
                           type_filter=type_filter)
