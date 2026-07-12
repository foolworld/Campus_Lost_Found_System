"""路由模块初始化

统一注册所有路由蓝图到 Flask 应用。
"""


def register_routes(app):
    """注册所有路由蓝图"""
    from .auth import auth_bp
    from .main import main_bp
    from .post import post_bp
    from .comment import comment_bp
    from .admin import admin_bp
    from .notification import notification_bp
    from .notice import notice_bp
    from .report import report_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(post_bp)
    app.register_blueprint(comment_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(notice_bp)
    app.register_blueprint(report_bp)
