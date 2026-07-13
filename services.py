"""业务服务

提供核心业务逻辑：
- 搜索服务：基于 TF-IDF 和余弦相似度的搜索
- 通知服务：创建用户通知
- 数据服务：生成示例数据
"""
from datetime import datetime, timedelta
from models import db, User, Post, Notification, KeywordSubscription
from utils import tokenize, compute_idf, compute_tfidf, cosine_similarity


def search_with_similarity(keyword, top_n=10):
    """基于 TF-IDF 和余弦相似度的搜索功能"""
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


def create_notification(user_id, notif_type, content, link):
    """创建用户通知"""
    notification = Notification(
        user_id=user_id,
        type=notif_type,
        content=content,
        link=link
    )
    db.session.add(notification)


def find_similar_posts(post, max_count=3):
    """查找相似帖子"""
    similar_posts = []
    try:
        if post.status == 'approved':
            all_approved = Post.query.filter(Post.status == 'approved', Post.id != post.id).all()
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
                similar_posts = [p for p, _ in results[:max_count]]
    except Exception as e:
        print(f"Error computing similar posts: {e}")
    return similar_posts


def _img(prompt: str, size: str = 'square_hd') -> str:
    """根据物品描述生成 text_to_image 接口 URL（示例配图，存储进 Post.image 字段）
    说明：示例数据真正从 create_sample_data() 插入进数据库，不再是前端硬编码渲染。
    """
    from urllib.parse import quote
    base = 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image'
    return f"{base}?prompt={quote(prompt)}&image_size={size}"


def create_sample_data():
    """创建示例数据（帖子）。

    - 不再硬编码插入假用户：用户账号（admin、test）由 app.py 负责建；
    - 删除了 zhangsan / lisi / wangwu 三个假用户的初始化逻辑；
    - 示例帖子作者统一使用 admin / test（账号已在 app.py 保证存在）；
    - 每篇示例帖子都存入了真实物品配图（text_to_image URL），image 字段不再是空字符串。
    """
    admin = User.query.filter_by(username='admin').first()
    test  = User.query.filter_by(username='test').first()
    if not admin or not test:
        # 账号尚未就绪（例如首次启动 app.py 会先创建 admin/test，再调本函数），跳过
        return

    sample_posts = [
        # ---------- 拾物（found），已审核通过 ----------
        {
            'title': '校园卡一张',
            'description': '在图书馆三楼阅览室捡到一张校园卡，卡号开头是2023，姓名看不清。卡面是蓝色的，带有学校logo。',
            'pickup_time': '2026-07-05 14:30',
            'location': '图书馆三楼阅览室',
            'place_location': '图书馆一楼服务台',
            'post_type': 'found',
            'status': 'approved',
            'author_id': admin.id,
            'image': _img('blue Chinese university student id card on library reading desk, school logo visible, closeup realistic photo'),
        },
        {
            'title': '黑色钱包一个',
            'description': '在食堂二楼捡到一个黑色皮质钱包，里面有身份证、银行卡和一些现金。钱包品牌是七匹狼。',
            'pickup_time': '2026-07-05 12:15',
            'location': '食堂二楼',
            'place_location': '食堂一楼失物招领处',
            'post_type': 'found',
            'status': 'approved',
            'author_id': test.id,
            'image': _img('black leather wallet closed on cafeteria table, card slots visible, realistic photo'),
        },
        {
            'title': 'iPhone手机一部',
            'description': '在教学楼A栋302教室捡到一部iPhone手机，黑色外壳，屏幕有轻微划痕。已关机等待失主联系。',
            'pickup_time': '2026-07-04 18:45',
            'location': '教学楼A栋302教室',
            'place_location': '教学楼A栋值班室',
            'post_type': 'found',
            'status': 'approved',
            'author_id': admin.id,
            'image': _img('black iPhone smartphone on classroom wooden desk, slight screen scratch, top view, realistic photo'),
        },
        {
            'title': '蓝色雨伞一把',
            'description': '在体育馆门口捡到一把蓝色雨伞，伞柄是银色的，伞面有卡通图案。看起来比较新。',
            'pickup_time': '2026-07-04 17:00',
            'location': '体育馆门口',
            'place_location': '体育馆服务台',
            'post_type': 'found',
            'status': 'approved',
            'author_id': test.id,
            'image': _img('blue folding umbrella with cartoon pattern, silver handle, at gym entrance doorway, realistic photo'),
        },
        {
            'title': '笔记本电脑一台',
            'description': '在实验室B栋捡到一台银色笔记本电脑，品牌是联想ThinkPad，型号看起来是X1 Carbon。',
            'pickup_time': '2026-07-03 16:30',
            'location': '实验室B栋205',
            'place_location': '实验室B栋管理员办公室',
            'post_type': 'found',
            'status': 'approved',
            'author_id': admin.id,
            'image': _img('silver Lenovo ThinkPad X1 Carbon laptop open on lab bench, realistic photo'),
        },
        {
            'title': '学生证一个',
            'description': '在操场跑道边捡到一个学生证，姓名是李明，学号20220101，计算机学院。',
            'pickup_time': '2026-07-03 20:00',
            'location': '操场跑道',
            'place_location': '学生事务中心',
            'post_type': 'found',
            'status': 'approved',
            'author_id': test.id,
            'image': _img('Chinese student ID card with small photo, on outdoor running track by grass, closeup photo'),
        },
        {
            'title': '白色耳机一副',
            'description': '在图书馆自习室捡到一副白色蓝牙耳机，充电盒是圆形的，品牌像是AirPods。',
            'pickup_time': '2026-07-02 10:20',
            'location': '图书馆自习室',
            'place_location': '图书馆服务台',
            'post_type': 'found',
            'status': 'approved',
            'author_id': admin.id,
            'image': _img('white Apple AirPods earbuds with round charging case on library reading table, realistic photo'),
        },
        {
            'title': '眼镜一副',
            'description': '在食堂三楼捡到一副近视眼镜，黑色镜框，镜片有度数。',
            'pickup_time': '2026-07-01 11:45',
            'location': '食堂三楼',
            'place_location': '食堂失物招领处',
            'post_type': 'found',
            'status': 'approved',
            'author_id': test.id,
            'image': _img('black frame myopia eyeglasses on cafeteria tray, clear lens, closeup realistic photo'),
        },
        # ---------- 拾物（found），仍待管理员审核 ----------
        {
            'title': '保温杯一个',
            'description': '在教学楼C栋走廊捡到一个不锈钢保温杯，颜色是金色的，容量大约500ml。',
            'pickup_time': '2026-07-02 09:30',
            'location': '教学楼C栋走廊',
            'place_location': '教学楼C栋值班室',
            'post_type': 'found',
            'status': 'pending',
            'author_id': test.id,
            'image': _img('golden 500ml stainless steel thermos cup standing in school corridor, realistic photo'),
        },
        {
            'title': '篮球一个',
            'description': '在篮球场捡到一个橙色篮球，上面有Nike标志，看起来还比较新。',
            'pickup_time': '2026-07-01 15:00',
            'location': '篮球场',
            'place_location': '体育馆器材室',
            'post_type': 'found',
            'status': 'pending',
            'author_id': admin.id,
            'image': _img('orange Nike basketball on outdoor court, pebbled surface, realistic photo'),
        },
    ]

    for p in sample_posts:
        if not Post.query.filter_by(title=p['title']).first():
            post = Post(
                title=p['title'],
                description=p['description'],
                pickup_time=p['pickup_time'],
                location=p['location'],
                place_location=p['place_location'],
                author_id=p['author_id'],
                post_type=p.get('post_type', 'found'),
                status=p['status'],
                image=p.get('image') or None,
                view_count=0,
            )
            db.session.add(post)

    db.session.commit()


def match_and_notify_subscribers(post):
    try:
        subscriptions = KeywordSubscription.query.all()
        if not subscriptions:
            return

        post_text = (post.title + ' ' + post.description).lower()
        cutoff = datetime.now() - timedelta(hours=24)
        post_link = f'/post/{post.id}'
        notified_users = set()

        for sub in subscriptions:
            if sub.user_id == post.author_id:
                continue

            if sub.keyword.lower() not in post_text:
                continue

            dedup_key = (sub.user_id, post_link)
            if dedup_key in notified_users:
                continue

            existing = Notification.query.filter(
                Notification.user_id == sub.user_id,
                Notification.type == 'new_post_match',
                Notification.link == post_link,
                Notification.created_at >= cutoff
            ).first()
            if existing:
                continue

            create_notification(
                sub.user_id,
                'new_post_match',
                f'您订阅的关键词「{sub.keyword}」有新匹配：《{post.title}》',
                post_link
            )
            notified_users.add(dedup_key)

        db.session.commit()
    except Exception:
        db.session.rollback()
