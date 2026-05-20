"""Web Push notification service using VAPID + pywebpush."""
import json
import os
import logging

logger = logging.getLogger(__name__)

try:
    from pywebpush import webpush, WebPushException
    WEBPUSH_AVAILABLE = True
except ImportError:
    logger.warning('pywebpush not installed — Web Push disabled. Run: pip install pywebpush')
    WEBPUSH_AVAILABLE = False
    WebPushException = Exception

VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC_KEY  = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_CLAIMS      = {'sub': os.environ.get('VAPID_CLAIMS_EMAIL', 'mailto:admin@buszapp.com')}


def send_push(subscription, title: str, body: str, url: str = '/dashboard.html', icon: str = '/static/img/icon-192x192.png') -> bool:
    """Send a single Web Push notification. Returns True on success."""
    if not WEBPUSH_AVAILABLE:
        return False
    if not VAPID_PRIVATE_KEY:
        logger.warning('VAPID_PRIVATE_KEY not configured — push skipped')
        return False

    payload = json.dumps({
        'title': title,
        'body': body,
        'icon': icon,
        'url': url,
    })

    try:
        webpush(
            subscription_info={
                'endpoint': subscription['endpoint'],
                'keys': {
                    'p256dh': subscription['p256dh'],
                    'auth':   subscription['auth'],
                },
            },
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
        )
        return True
    except WebPushException as e:
        status = e.response.status_code if e.response is not None else None
        if status in (404, 410):
            # Subscription expired or unregistered — caller should delete it
            raise
        logger.error('WebPush error %s: %s', status, e)
        return False
    except Exception as e:
        logger.error('Unexpected push error: %s', e)
        return False


def send_push_to_user(user_id: int, title: str, body: str, url: str = '/dashboard.html') -> int:
    """Send push to all active subscriptions of a user. Returns count of successful sends."""
    from src.models.user import PushSubscription
    from src.models import db
    from pywebpush import WebPushException

    subs = PushSubscription.query.filter_by(user_id=user_id).all()
    sent = 0
    to_delete = []

    for sub in subs:
        sub_dict = {'endpoint': sub.endpoint, 'p256dh': sub.p256dh, 'auth': sub.auth}
        try:
            if send_push(sub_dict, title, body, url):
                sent += 1
        except WebPushException:
            to_delete.append(sub.id)

    if to_delete:
        PushSubscription.query.filter(PushSubscription.id.in_(to_delete)).delete(synchronize_session=False)
        db.session.commit()

    return sent


def send_push_to_all(title: str, body: str, url: str = '/dashboard.html') -> int:
    """Broadcast push to every subscribed user. Returns count of successful sends."""
    from src.models.user import PushSubscription
    from src.models import db
    from pywebpush import WebPushException

    subs = PushSubscription.query.all()
    sent = 0
    to_delete = []

    for sub in subs:
        sub_dict = {'endpoint': sub.endpoint, 'p256dh': sub.p256dh, 'auth': sub.auth}
        try:
            if send_push(sub_dict, title, body, url):
                sent += 1
        except WebPushException:
            to_delete.append(sub.id)

    if to_delete:
        PushSubscription.query.filter(PushSubscription.id.in_(to_delete)).delete(synchronize_session=False)
        db.session.commit()

    return sent
