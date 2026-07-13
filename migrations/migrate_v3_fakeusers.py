"""迁移脚本 v3 —— 清理硬编码假用户 + 给空图示例帖补真实配图

背景：
- 旧版 services.create_sample_data() 每次启动时会往 user 表里塞 3 个硬编码假账号：
  zhangsan / lisi / wangwu，并用这些假用户发布 10 篇示例帖，且 image 字段为空。
- 用户要求：示例必须从数据库存、不再硬编码；假用户除 admin / test 外都要删；
  所有示例帖必须配上真实物品 AI 图。

作用（幂等，可重复执行）：
1) 找出 username ∈ {zhangsan, lisi, wangwu} 的用户，把其所有关联数据迁到 admin：
   - post.author_id        → admin.id
   - post.created_by        → admin.id  (公告创建者)
   - comment.author_id      → admin.id
   - report.reporter_id     → admin.id
   - report.handled_by      → admin.id (若被这些假用户处理过)
   - notification.user_id   → admin.id
   - keyword_subscription.user_id 若与 admin 关键词重复则删除，否则迁到 admin
2) 删除这 3 个假用户（如果存在）
3) 对所有 Post（包含非示例）只要 image 是 NULL 或空字符串的，
   按 title 关键字匹配生成 text_to_image 图片 URL 并回填；
   匹配不上的走默认的失物招领通用图。

用法（手动执行一次即可，新库不需要跑）：
    cd c:\\Users\\xs\\Desktop\\校园失物招领
    python -m migrations.migrate_v3_fakeusers
    或
    python migrations/migrate_v3_fakeusers.py
"""
from urllib.parse import quote
from sqlalchemy import text


# ---------- 标题关键词 -> 配图 prompt（与 services.create_sample_data 保持同风格） ----------
TITLE_KEYWORDS_IMAGES = [
    (['校园卡', '学生卡', 'id card', '学生证', '学生证件'],
     'blue Chinese university student id card on library reading desk, school logo visible, closeup realistic photo'),
    (['钱包', 'wallet', '皮夹'],
     'black leather wallet closed on cafeteria table, card slots visible, realistic photo'),
    (['手机', 'iphone', 'android', '智能手机'],
     'black smartphone on classroom wooden desk, slight screen scratch, top view, realistic photo'),
    (['雨伞', '伞', 'umbrella'],
     'blue folding umbrella with cartoon pattern, silver handle, at gym entrance doorway, realistic photo'),
    (['笔记本', 'laptop', 'thinkpad', '电脑'],
     'silver Lenovo ThinkPad X1 Carbon laptop open on lab bench, realistic photo'),
    (['耳机', 'airpods', '蓝牙', 'earphone', 'earbuds'],
     'white Apple AirPods earbuds with round charging case on library reading table, realistic photo'),
    (['保温杯', '水杯', '杯子', 'thermos'],
     'golden 500ml stainless steel thermos cup standing in school corridor, realistic photo'),
    (['篮球', 'basketball', '足球', 'volleyball', '球'],
     'orange Nike basketball on outdoor court, pebbled surface, realistic photo'),
    (['眼镜', '镜', 'eyeglasses', 'glasses'],
     'black frame myopia eyeglasses on cafeteria tray, clear lens, closeup realistic photo'),
    (['钥匙', 'key', '钥匙扣'],
     'set of metal keys with plastic keychain on school hallway floor, closeup realistic photo'),
    (['校园卡', '卡'],
     'blue Chinese university student id card on library reading desk, school logo visible, closeup realistic photo'),
]
DEFAULT_IMAGE_PROMPT = 'lost and found items box with stationery and personal belongings on blue table, realistic photo'


def _img(prompt: str, size: str = 'square_hd') -> str:
    base = 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image'
    return f"{base}?prompt={quote(prompt)}&image_size={size}"


def image_for_title(title: str) -> str:
    """根据帖子标题匹配对应 AI 图 URL；匹配不到返回通用失物图。"""
    low = (title or '').lower()
    for keywords, prompt in TITLE_KEYWORDS_IMAGES:
        for kw in keywords:
            if kw.lower() in low:
                return _img(prompt)
    return _img(DEFAULT_IMAGE_PROMPT)


FAKE_USERNAMES = ['zhangsan', 'lisi', 'wangwu', 'test2']


def run():
    # 延迟 import，避免循环引用
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import create_app
    from models import db, User, Post, Comment, Report, Notification, KeywordSubscription, Notice

    app = create_app()
    with app.app_context():
        print("\n=== migrate_v3 开始 ===")

        # 1. 找到 admin / 假用户
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("  [ERR] admin 用户不存在，无法迁移外键，请先运行一次 app.py 生成 admin/test。")
            return

        fake_users = User.query.filter(User.username.in_(FAKE_USERNAMES)).all()
        fake_map = {u.id: u.username for u in fake_users}
        print(f"  找到假用户 {len(fake_map)} 个：{list(fake_map.values()) or '(none)'}")

        fake_ids = list(fake_map.keys())

        if fake_ids:
            # 2. 迁外键（先迁，后删用户，避免 FK cascade 删帖）
            # --- Post.author_id ---
            moved_posts = Post.query.filter(Post.author_id.in_(fake_ids)).update(
                {Post.author_id: admin.id}, synchronize_session=False
            )
            print(f"  Post.author_id 迁移到 admin: {moved_posts} 条")

            # --- Notice.created_by ---
            moved_notice = Notice.query.filter(Notice.created_by.in_(fake_ids)).update(
                {Notice.created_by: admin.id}, synchronize_session=False
            )
            print(f"  Notice.created_by 迁移到 admin: {moved_notice} 条")

            # --- Comment.author_id ---
            moved_cmt = Comment.query.filter(Comment.author_id.in_(fake_ids)).update(
                {Comment.author_id: admin.id}, synchronize_session=False
            )
            print(f"  Comment.author_id 迁移到 admin: {moved_cmt} 条")

            # --- Report.reporter_id / handled_by ---
            moved_r1 = Report.query.filter(Report.reporter_id.in_(fake_ids)).update(
                {Report.reporter_id: admin.id}, synchronize_session=False
            )
            moved_r2 = Report.query.filter(Report.handled_by.in_(fake_ids)).update(
                {Report.handled_by: admin.id}, synchronize_session=False
            )
            print(f"  Report.reporter_id 迁移: {moved_r1}，handled_by 迁移: {moved_r2}")

            # --- Notification.user_id ---
            moved_notif = Notification.query.filter(Notification.user_id.in_(fake_ids)).update(
                {Notification.user_id: admin.id}, synchronize_session=False
            )
            print(f"  Notification.user_id 迁移到 admin: {moved_notif} 条")

            # --- KeywordSubscription.user_id（注意 uq_user_keyword 唯一约束） ---
            subs = KeywordSubscription.query.filter(KeywordSubscription.user_id.in_(fake_ids)).all()
            moved_sub = 0
            removed_sub = 0
            for s in subs:
                exists = KeywordSubscription.query.filter_by(
                    user_id=admin.id, keyword=s.keyword
                ).first()
                if exists:
                    db.session.delete(s)
                    removed_sub += 1
                else:
                    s.user_id = admin.id
                    moved_sub += 1
            print(f"  KeywordSubscription 迁移: {moved_sub} 条，冲突删除: {removed_sub} 条")

            db.session.commit()

            # 3. 删假用户
            User.query.filter(User.id.in_(fake_ids)).delete(synchronize_session=False)
            db.session.commit()
            print(f"  删除假用户 {len(fake_ids)} 个：{list(fake_map.values())} 完成 ✓")
        else:
            print("  假用户已清理过，跳过。")

        # 4. 回填所有 Post.image 空字段
        empty_posts = Post.query.filter((Post.image.is_(None)) | (Post.image == '')).all()
        print(f"  需要补图片的帖子数: {len(empty_posts)}")
        fixed = 0
        for p in empty_posts:
            p.image = image_for_title(p.title)
            fixed += 1
        if fixed:
            db.session.commit()
            print(f"  为 {fixed} 条空图帖子补了 AI 配图。")
        else:
            print("  空图帖子为 0，跳过。")

        # 5. 最终用户列表
        remain = [u.username for u in User.query.order_by(User.id.asc()).all()]
        print(f"\n  当前用户表（共 {len(remain)} 个）：{remain}")
        empty_left = Post.query.filter((Post.image.is_(None)) | (Post.image == '')).count()
        print(f"  当前空 image 帖子数：{empty_left}")
        print("=== migrate_v3 完成 ===\n")


if __name__ == '__main__':
    run()
