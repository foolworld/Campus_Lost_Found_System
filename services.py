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


def create_sample_data():
    """创建示例数据（用户和帖子）"""
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
