"""关键词订阅路由

处理关键词订阅的查看、添加、删除等请求。
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from models import db, KeywordSubscription

subscription_bp = Blueprint('subscription', __name__)


@subscription_bp.route('/subscriptions')
@login_required
def subscription_list():
    subscriptions = (
        KeywordSubscription.query
        .filter_by(user_id=current_user.id)
        .order_by(KeywordSubscription.created_at.desc())
        .all()
    )
    return render_template('subscriptions.html', subscriptions=subscriptions)


@subscription_bp.route('/subscriptions/add', methods=['POST'])
@login_required
def add_subscription():
    keyword = request.form.get('keyword', '').strip()

    if not keyword:
        flash('关键词不能为空', 'danger')
        return redirect(url_for('subscription.subscription_list'))

    if len(keyword) < 1 or len(keyword) > 20:
        flash('关键词长度需在 1-20 字之间', 'danger')
        return redirect(url_for('subscription.subscription_list'))

    current_count = KeywordSubscription.query.filter_by(user_id=current_user.id).count()
    if current_count >= 10:
        flash('最多只能订阅 10 个关键词', 'warning')
        return redirect(url_for('subscription.subscription_list'))

    try:
        sub = KeywordSubscription(user_id=current_user.id, keyword=keyword)
        db.session.add(sub)
        db.session.commit()
        flash(f'已订阅关键词「{keyword}」', 'success')
    except IntegrityError:
        db.session.rollback()
        flash(f'您已订阅过关键词「{keyword}」', 'warning')
    except Exception:
        db.session.rollback()
        flash('订阅失败，请稍后重试', 'danger')

    return redirect(url_for('subscription.subscription_list'))


@subscription_bp.route('/subscriptions/<int:sub_id>/delete', methods=['POST'])
@login_required
def delete_subscription(sub_id):
    sub = KeywordSubscription.query.get_or_404(sub_id)

    if sub.user_id != current_user.id:
        flash('无权取消此订阅', 'danger')
        return redirect(url_for('subscription.subscription_list'))

    keyword_name = sub.keyword
    try:
        db.session.delete(sub)
        db.session.commit()
        flash(f'已取消订阅「{keyword_name}」', 'success')
    except Exception:
        db.session.rollback()
        flash('取消订阅失败，请稍后重试', 'danger')

    return redirect(url_for('subscription.subscription_list'))
