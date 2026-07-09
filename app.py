from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import datetime
import jieba
import math
from collections import defaultdict

app = Flask(__name__)
app.config['SECRET_KEY'] = 'campus-lost-found-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lost_found.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
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
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)

    author = db.relationship('User', backref=db.backref('posts', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def tokenize(text):
    return [word for word in jieba.lcut(text) if word.strip()]

def compute_tf(tokens):
    tf = defaultdict(int)
    total = len(tokens)
    for token in tokens:
        tf[token] += 1
    for token in tf:
        tf[token] /= total
    return tf

def compute_idf(documents):
    idf = {}
    total_docs = len(documents)
    all_tokens = set()
    for doc in documents:
        all_tokens.update(tokenize(doc))
    
    for token in all_tokens:
        doc_count = sum(1 for doc in documents if token in tokenize(doc))
        idf[token] = math.log((total_docs + 1) / (doc_count + 1)) + 1
    return idf

def compute_tfidf(tokens, idf):
    tf = compute_tf(tokens)
    tfidf = {}
    for token in tf:
        if token in idf:
            tfidf[token] = tf[token] * idf[token]
    return tfidf

def cosine_similarity(vec1, vec2):
    all_tokens = set(vec1.keys()) | set(vec2.keys())
    dot_product = sum(vec1.get(token, 0) * vec2.get(token, 0) for token in all_tokens)
    norm1 = math.sqrt(sum(v**2 for v in vec1.values()))
    norm2 = math.sqrt(sum(v**2 for v in vec2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def search_with_similarity(keyword, top_n=10):
    approved_posts = Post.query.filter_by(status='approved').all()
    if not approved_posts:
        return []
    
    documents = [f"{post.title} {post.description} {post.location}" for post in approved_posts]
    idf = compute_idf(documents)
    
    query_tokens = tokenize(keyword)
    query_tfidf = compute_tfidf(query_tokens, idf)
    
    results = []
    for i, post in enumerate(approved_posts):
        doc_text = f"{post.title} {post.description} {post.location}"
        doc_tokens = tokenize(doc_text)
        doc_tfidf = compute_tfidf(doc_tokens, idf)
        similarity = cosine_similarity(query_tfidf, doc_tfidf)
        
        for qt in query_tokens:
            for dt in doc_tokens:
                if qt in dt or dt in qt:
                    similarity += 0.1
        
        if similarity > 0.01:
            results.append((post, similarity))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return [post for post, _ in results[:top_n]]

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'time', type=str)
    
    if sort == 'hot':
        posts = Post.query.filter_by(status='approved').order_by(Post.created_at.desc()).paginate(page=page, per_page=6)
    else:
        posts = Post.query.filter_by(status='approved').order_by(Post.created_at.desc()).paginate(page=page, per_page=6)
    
    total_posts = Post.query.filter_by(status='approved').count()
    total_users = User.query.count()
    return render_template('index.html', posts=posts.items, page=page, total_pages=posts.pages, total_posts=total_posts, total_users=total_users, sort=sort)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if len(username) < 3:
            flash('用户名至少需要3个字符', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('密码至少需要6个字符', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'danger')
            return render_template('register.html')
        
        new_user = User(username=username, role='user')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        flash('用户名或密码错误', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))

@app.route('/search')
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

@app.route('/publish', methods=['GET', 'POST'])
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
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
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
        return redirect(url_for('index'))
    return render_template('publish.html')

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    similar_posts = []
    if post.status == 'approved':
        all_approved = Post.query.filter(Post.status == 'approved', Post.id != post_id).all()
        if all_approved:
            documents = [f"{p.title} {p.description} {p.location}" for p in all_approved]
            idf = compute_idf(documents)
            query_tokens = tokenize(f"{post.title} {post.description}")
            query_tfidf = compute_tfidf(query_tokens, idf)
            
            results = []
            for p in all_approved:
                doc_tokens = tokenize(f"{p.title} {p.description}")
                doc_tfidf = compute_tfidf(doc_tokens, idf)
                similarity = cosine_similarity(query_tfidf, doc_tfidf)
                if similarity > 0.1:
                    results.append((p, similarity))
            
            results.sort(key=lambda x: x[1], reverse=True)
            similar_posts = [p for p, _ in results[:3]]
    
    return render_template('post_detail.html', post=post, similar_posts=similar_posts)

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author_id != current_user.id:
        flash('无权编辑此信息', 'danger')
        return redirect(url_for('post_detail', post_id=post_id))
    
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
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                post.image = filename
        
        post.status = 'pending'
        db.session.commit()
        flash('修改成功，等待审核', 'success')
        return redirect(url_for('post_detail', post_id=post_id))
    
    return render_template('edit_post.html', post=post)

@app.route('/post/<int:post_id>/delete')
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author_id != current_user.id and current_user.role != 'admin':
        flash('无权删除此信息', 'danger')
        return redirect(url_for('post_detail', post_id=post_id))
    
    db.session.delete(post)
    db.session.commit()
    flash('删除成功', 'success')
    return redirect(url_for('index'))

@app.route('/my-posts')
@login_required
def my_posts():
    posts = Post.query.filter_by(author_id=current_user.id).order_by(Post.created_at.desc()).all()
    return render_template('my_posts.html', posts=posts)

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('无权访问管理后台', 'danger')
        return redirect(url_for('index'))
    
    tab = request.args.get('tab', 'pending')
    
    if tab == 'approved':
        posts = Post.query.filter_by(status='approved').order_by(Post.created_at.desc()).all()
    elif tab == 'rejected':
        posts = Post.query.filter_by(status='rejected').order_by(Post.created_at.desc()).all()
    else:
        posts = Post.query.filter_by(status='pending').order_by(Post.created_at.desc()).all()
    
    users = User.query.all()
    pending_count = Post.query.filter_by(status='pending').count()
    approved_count = Post.query.filter_by(status='approved').count()
    rejected_count = Post.query.filter_by(status='rejected').count()
    total_users = User.query.count()
    
    return render_template('admin_dashboard.html', 
                           posts=posts, users=users, tab=tab,
                           pending_count=pending_count,
                           approved_count=approved_count,
                           rejected_count=rejected_count,
                           total_users=total_users)

@app.route('/admin/post/<int:post_id>/approve')
@login_required
def approve_post(post_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('index'))
    
    post = Post.query.get_or_404(post_id)
    post.status = 'approved'
    db.session.commit()
    flash('已通过审核', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/post/<int:post_id>/reject')
@login_required
def reject_post(post_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('index'))
    
    post = Post.query.get_or_404(post_id)
    post.status = 'rejected'
    db.session.commit()
    flash('已拒绝审核', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/delete')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('不能删除管理员', 'danger')
        return redirect(url_for('admin_dashboard', tab='users'))
    
    Post.query.filter_by(author_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    flash('删除用户成功，其发布的帖子已一并删除', 'success')
    return redirect(url_for('admin_dashboard', tab='users'))

@app.route('/admin/user/<int:user_id>/promote')
@login_required
def promote_user(user_id):
    if current_user.role != 'admin':
        flash('无权执行此操作', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    user.role = 'admin'
    db.session.commit()
    flash(f'{user.username} 已提升为管理员', 'success')
    return redirect(url_for('admin_dashboard', tab='users'))

def create_sample_data():
    sample_users = [
        {'username': 'zhangsan', 'password': '123456', 'role': 'user'},
        {'username': 'lisi', 'password': '123456', 'role': 'user'},
        {'username': 'wangwu', 'password': '123456', 'role': 'user'},
    ]
    
    for u in sample_users:
        if not User.query.filter_by(username=u['username']).first():
            user = User(username=u['username'], role=u['role'])
            user.set_password(u['password'])
            db.session.add(user)
    
    db.session.commit()
    
    sample_posts = [
        {
            'title': '校园卡一张',
            'description': '在图书馆三楼阅览室捡到一张校园卡，卡号开头是2023，姓名看不清。卡面是蓝色的，带有学校logo。',
            'pickup_time': '2026-07-05 14:30',
            'location': '图书馆三楼阅览室',
            'place_location': '图书馆一楼服务台',
            'author_username': 'zhangsan',
            'status': 'approved'
        },
        {
            'title': '黑色钱包一个',
            'description': '在食堂二楼捡到一个黑色皮质钱包，里面有身份证、银行卡和一些现金。钱包品牌是七匹狼。',
            'pickup_time': '2026-07-05 12:15',
            'location': '食堂二楼',
            'place_location': '食堂一楼失物招领处',
            'author_username': 'lisi',
            'status': 'approved'
        },
        {
            'title': 'iPhone手机一部',
            'description': '在教学楼A栋302教室捡到一部iPhone手机，黑色外壳，屏幕有轻微划痕。已关机等待失主联系。',
            'pickup_time': '2026-07-04 18:45',
            'location': '教学楼A栋302教室',
            'place_location': '教学楼A栋值班室',
            'author_username': 'wangwu',
            'status': 'approved'
        },
        {
            'title': '蓝色雨伞一把',
            'description': '在体育馆门口捡到一把蓝色雨伞，伞柄是银色的，伞面有卡通图案。看起来比较新。',
            'pickup_time': '2026-07-04 17:00',
            'location': '体育馆门口',
            'place_location': '体育馆服务台',
            'author_username': 'zhangsan',
            'status': 'approved'
        },
        {
            'title': '笔记本电脑一台',
            'description': '在实验室B栋捡到一台银色笔记本电脑，品牌是联想ThinkPad，型号看起来是X1 Carbon。',
            'pickup_time': '2026-07-03 16:30',
            'location': '实验室B栋205',
            'place_location': '实验室B栋管理员办公室',
            'author_username': 'lisi',
            'status': 'approved'
        },
        {
            'title': '学生证一个',
            'description': '在操场跑道边捡到一个学生证，姓名是李明，学号20220101，计算机学院。',
            'pickup_time': '2026-07-03 20:00',
            'location': '操场跑道',
            'place_location': '学生事务中心',
            'author_username': 'wangwu',
            'status': 'approved'
        },
        {
            'title': '白色耳机一副',
            'description': '在图书馆自习室捡到一副白色蓝牙耳机，充电盒是圆形的，品牌像是AirPods。',
            'pickup_time': '2026-07-02 10:20',
            'location': '图书馆自习室',
            'place_location': '图书馆服务台',
            'author_username': 'zhangsan',
            'status': 'approved'
        },
        {
            'title': '保温杯一个',
            'description': '在教学楼C栋走廊捡到一个不锈钢保温杯，颜色是金色的，容量大约500ml。',
            'pickup_time': '2026-07-02 09:30',
            'location': '教学楼C栋走廊',
            'place_location': '教学楼C栋值班室',
            'author_username': 'lisi',
            'status': 'pending'
        },
        {
            'title': '篮球一个',
            'description': '在篮球场捡到一个橙色篮球，上面有Nike标志，看起来还比较新。',
            'pickup_time': '2026-07-01 15:00',
            'location': '篮球场',
            'place_location': '体育馆器材室',
            'author_username': 'wangwu',
            'status': 'pending'
        },
        {
            'title': '眼镜一副',
            'description': '在食堂三楼捡到一副近视眼镜，黑色镜框，镜片有度数。',
            'pickup_time': '2026-07-01 11:45',
            'location': '食堂三楼',
            'place_location': '食堂失物招领处',
            'author_username': 'zhangsan',
            'status': 'approved'
        }
    ]
    
    for p in sample_posts:
        if not Post.query.filter_by(title=p['title']).first():
            author = User.query.filter_by(username=p['author_username']).first()
            if author:
                post = Post(
                    title=p['title'],
                    description=p['description'],
                    pickup_time=p['pickup_time'],
                    location=p['location'],
                    place_location=p['place_location'],
                    author_id=author.id,
                    post_type=p.get('post_type', 'found'),
                    status=p['status']
                )
                db.session.add(post)
    
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
        if not User.query.filter_by(username='test').first():
            test = User(username='test', role='user')
            test.set_password('test123')
            db.session.add(test)
            db.session.commit()
        create_sample_data()
    app.run(debug=True)