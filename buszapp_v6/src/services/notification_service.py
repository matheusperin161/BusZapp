"""Service layer for notifications."""
from src.models import db
from src.models.user import Notification


def create_notification(user_id: int, title: str, message: str) -> Notification:
    """Create and persist a notification for a user."""
    notification = Notification(user_id=user_id, title=title, message=message)
    db.session.add(notification)
    db.session.commit()
    return notification
