"""SQLite 数据库升级脚本 v2

针对已存在的老 SQLite 数据库执行：
- post 表增加 view_count 列
- notice 表增加 publish_at / created_by 列
- 新建 keyword_subscription 表

新库可直接通过末尾的 db.create_all() 兜底建全。
"""
import sqlite3
import os
import sys


def try_connect(db_path):
    """尝试连接 SQLite 数据库，不存在则返回 None"""
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error:
        return None


def column_exists(conn, table_name, column_name):
    """检查表中是否存在指定列"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def table_exists(conn, table_name):
    """检查数据库中是否存在指定表"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def upgrade_post_table(conn):
    """升级 post 表：增加 view_count 列"""
    changes = []
    if not table_exists(conn, 'post'):
        changes.append("post 表不存在，跳过")
        return changes

    if not column_exists(conn, 'post', 'view_count'):
        cursor = conn.cursor()
        cursor.execute(
            "ALTER TABLE post ADD COLUMN view_count INTEGER DEFAULT 0"
        )
        cursor.execute(
            "UPDATE post SET view_count = 0 WHERE view_count IS NULL"
        )
        conn.commit()
        changes.append("post 表新增 view_count 列并初始化值为 0")
    else:
        changes.append("post 表 view_count 列已存在，跳过")

    return changes


def upgrade_notice_table(conn):
    """升级 notice 表：增加 publish_at / created_by 列"""
    changes = []
    if not table_exists(conn, 'notice'):
        changes.append("notice 表不存在，跳过")
        return changes

    if not column_exists(conn, 'notice', 'publish_at'):
        cursor = conn.cursor()
        cursor.execute(
            "ALTER TABLE notice ADD COLUMN publish_at DATETIME NULL"
        )
        conn.commit()
        changes.append("notice 表新增 publish_at 列")
    else:
        changes.append("notice 表 publish_at 列已存在，跳过")

    if not column_exists(conn, 'notice', 'created_by'):
        cursor = conn.cursor()
        cursor.execute(
            "ALTER TABLE notice ADD COLUMN created_by INTEGER NULL"
        )
        conn.commit()
        changes.append("notice 表新增 created_by 列")
    else:
        changes.append("notice 表 created_by 列已存在，跳过")

    changes.append(
        "notice 表 updated_at 列的 onupdate 约束无法在 SQLite 中通过 ALTER 修改，"
        "保持不动，由业务层写入"
    )

    return changes


def upgrade_keyword_subscription_table(conn):
    """升级：新建 keyword_subscription 表"""
    changes = []
    if table_exists(conn, 'keyword_subscription'):
        changes.append("keyword_subscription 表已存在，跳过")
        return changes

    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE keyword_subscription (
            id INTEGER NOT NULL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            keyword VARCHAR(50) NOT NULL,
            created_at DATETIME,
            CONSTRAINT uq_user_keyword UNIQUE (user_id, keyword),
            FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
        )
    """)
    cursor.execute(
        "CREATE INDEX ix_keyword_subscription_user_id "
        "ON keyword_subscription (user_id)"
    )
    conn.commit()
    changes.append("新建 keyword_subscription 表及唯一约束、索引")
    return changes


def upgrade_database(db_path):
    """升级单个数据库文件"""
    print(f"\n=== 尝试升级数据库: {db_path} ===")
    conn = try_connect(db_path)
    if conn is None:
        print(f"  [跳过] 文件不存在或无法连接: {db_path}")
        return False

    print(f"  [OK] 连接成功: {db_path}")
    all_changes = []

    all_changes.extend(upgrade_post_table(conn))
    all_changes.extend(upgrade_notice_table(conn))
    all_changes.extend(upgrade_keyword_subscription_table(conn))

    conn.close()

    for change in all_changes:
        print(f"  - {change}")
    print(f"  [完成] {db_path} 升级完成")
    return True


def create_all_safety_net():
    """db.create_all() 安全兜底：新库一次性建全所有表"""
    print("\n=== 执行 db.create_all() 安全兜底（新库建表/老库无影响） ===")
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, project_root)
        from app import app
        from models import db
        with app.app_context():
            db.create_all()
        print("  [OK] db.create_all() 执行成功")
        return True
    except Exception as e:
        print(f"  [警告] db.create_all() 执行失败（不影响老库升级）: {e}")
        return False


def migrate_all():
    """主迁移入口：尝试两个可能的数据库位置，再执行兜底建表"""
    print("====== 校园失物招领系统数据库迁移 v2 开始 ======")

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate_paths = [
        os.path.join(project_root, 'instance', 'lost_found.db'),
        os.path.join(project_root, 'lost_found.db'),
    ]

    upgraded_count = 0
    for db_path in candidate_paths:
        result = upgrade_database(db_path)
        if result:
            upgraded_count += 1

    if upgraded_count == 0:
        print("\n[提示] 两个候选位置均未找到现有数据库文件，"
              "将通过 db.create_all() 为新库建表")

    create_all_safety_net()

    print("\n====== 校园失物招领系统数据库迁移 v2 全部完成 ======")


if __name__ == '__main__':
    migrate_all()
