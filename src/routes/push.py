"""Web Push subscription management routes."""
import os
from flask import Blueprint, request, jsonify, session

from src.models import db
from src.models.user import PushSubscription
from src.utils.auth import login_required

push_bp = Blueprint('push', __name__, url_prefix='/api/push')


@push_bp.route('/vapid-public-key', methods=['GET'])
def vapid_public_key():
    """Return the VAPID public key so the frontend can subscribe."""
    return jsonify({'publicKey': os.environ.get('VAPID_PUBLIC_KEY', '')})


@push_bp.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    """Save (or update) a push subscription for the current user."""
    data = request.get_json() or {}
    endpoint = data.get('endpoint')
    p256dh   = (data.get('keys') or {}).get('p256dh')
    auth     = (data.get('keys') or {}).get('auth')

    if not all([endpoint, p256dh, auth]):
        return jsonify({'error': 'endpoint, keys.p256dh e keys.auth são obrigatórios'}), 400

    user_id = session['user_id']

    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        existing.p256dh = p256dh
        existing.auth   = auth
        existing.user_id = user_id
    else:
        db.session.add(PushSubscription(user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth))

    db.session.commit()
    return jsonify({'ok': True}), 201


@push_bp.route('/unsubscribe', methods=['POST'])
@login_required
def unsubscribe():
    """Remove a push subscription."""
    data     = request.get_json() or {}
    endpoint = data.get('endpoint')
    if not endpoint:
        return jsonify({'error': 'endpoint obrigatório'}), 400

    PushSubscription.query.filter_by(endpoint=endpoint, user_id=session['user_id']).delete()
    db.session.commit()
    return jsonify({'ok': True})
