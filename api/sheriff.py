"""Sheriff API endpoints for the Deputy Sheriffs' Association portal."""
import jwt
from flask import Blueprint, request, jsonify, current_app, Response, g
from flask_restful import Api, Resource
from datetime import datetime
from __init__ import app, db
from api.authorize import token_required
from model.sheriff import Sheriff
import os

sheriff_api = Blueprint('sheriff_api', __name__, url_prefix='/api')
api = Api(sheriff_api)


def decode_sheriff_token():
    """Read jwt_sheriff cookie, decode it, and return the Sheriff object.

    Returns the Sheriff object or raises an appropriate error tuple.
    """
    token = request.cookies.get("jwt_sheriff")
    if not token:
        raise AuthError({'message': 'Not authenticated'}, 401)
    try:
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError({'message': 'Token expired'}, 401)
    except jwt.InvalidTokenError:
        raise AuthError({'message': 'Invalid token'}, 401)
    sheriff = Sheriff.query.filter_by(_uid=data["_uid"]).first()
    if not sheriff:
        raise AuthError({'message': 'Sheriff not found'}, 404)
    return sheriff


def require_admin():
    """Decode token and verify the sheriff is an admin.

    Returns the Sheriff object or raises 403 if not admin.
    """
    sheriff = decode_sheriff_token()
    if not sheriff.is_admin():
        raise AuthError({'message': 'Admin access required'}, 403)
    return sheriff


def set_sheriff_cookie(response, token, max_age):
    """Set the jwt_sheriff cookie with production or dev settings."""
    is_production = os.environ.get('IS_PRODUCTION', 'false').lower() == 'true'
    cookie_name = "jwt_sheriff"
    if is_production:
        response.set_cookie(cookie_name, token, max_age=max_age,
                            secure=True, httponly=True, path='/',
                            samesite='None', domain='.opencodingsociety.com')
    else:
        response.set_cookie(cookie_name, token, max_age=max_age,
                            secure=False, httponly=False, path='/',
                            samesite='Lax')
    return response


def validate_signup_data(body):
    """Validate name, uid, sheriff_id, password from the request body.

    Returns a validated dict or raises an error tuple.
    """
    if not body:
        raise AuthError({'message': 'No data provided'}, 400)

    name = body.get('name')
    if not name or len(name) < 2:
        raise AuthError({'message': 'Name is missing or too short'}, 400)

    uid = body.get('uid')
    if not uid or len(uid) < 2:
        raise AuthError({'message': 'Username is missing or too short'}, 400)

    sheriff_id = body.get('sheriff_id')
    if not sheriff_id:
        raise AuthError({'message': 'Sheriff ID / Badge Number is required'}, 400)

    password = body.get('password', 'sheriff123')
    if len(password) < 8:
        raise AuthError({'message': 'Password must be at least 8 characters'}, 400)

    return {
        'name': name,
        'uid': uid,
        'sheriff_id': sheriff_id,
        'password': password,
    }


class AuthError(Exception):
    """Simple exception to carry an error response tuple out of helpers."""
    def __init__(self, body, status_code):
        self.body = body
        self.status_code = status_code


class SheriffAPI:

    class _Authenticate(Resource):
        """Sheriff login endpoint."""
        def post(self):
            try:
                body = request.get_json()
                if not body:
                    return {'message': 'Please provide credentials'}, 400

                uid = body.get('uid')
                if not uid:
                    return {'message': 'Username is missing'}, 401
                password = body.get('password')
                if not password:
                    return {'message': 'Password is missing'}, 401

                sheriff = Sheriff.query.filter_by(_uid=uid).first()
                if sheriff is None or not sheriff.is_password(password):
                    return {'message': 'Invalid username or password'}, 401

                token = jwt.encode(
                    {"_uid": sheriff._uid, "_type": "sheriff"},
                    current_app.config["SECRET_KEY"],
                    algorithm="HS256"
                )

                response_data = {
                    "message": f"Authentication for {sheriff._uid} successful",
                    "user": {
                        "uid": sheriff._uid,
                        "name": sheriff.name,
                        "sheriff_id": sheriff.sheriff_id,
                        "rank": sheriff.rank,
                        "station": sheriff.station,
                        "role": sheriff.role,
                        "status": sheriff.status,
                    }
                }
                resp = jsonify(response_data)
                set_sheriff_cookie(resp, token, 43200)
                return resp

            except Exception as e:
                return {'message': 'Something went wrong', 'error': str(e)}, 500

        def delete(self):
            """Logout - expire the sheriff cookie."""
            try:
                resp = Response("Sheriff token invalidated")
                set_sheriff_cookie(resp, '', 0)
                return resp
            except Exception as e:
                return {'message': 'Failed to invalidate token', 'error': str(e)}, 500

    class _ID(Resource):
        """Get current sheriff from token."""
        def get(self):
            try:
                sheriff = decode_sheriff_token()
                return jsonify(sheriff.read())
            except AuthError as e:
                return e.body, e.status_code

    class _CRUD(Resource):
        """Sheriff user CRUD operations."""

        def post(self):
            """Create a new sheriff user (signup)."""
            try:
                body = request.get_json()
                validated = validate_signup_data(body)
            except AuthError as e:
                return e.body, e.status_code

            sheriff = Sheriff(
                name=validated['name'],
                uid=validated['uid'],
                sheriff_id=validated['sheriff_id'],
                password=validated['password'],
                email=body.get('email', ''),
                rank=body.get('rank', 'Deputy'),
                station=body.get('station', 'San Diego Central'),
                phone=body.get('phone', ''),
            )

            try:
                created = sheriff.create()
                if not created:
                    return {'message': f'Sheriff ID or username already exists'}, 400
                return jsonify(created.read())
            except Exception as e:
                return {'message': f'Error creating sheriff: {str(e)}'}, 500

        def get(self):
            """Get all sheriff users (admin only)."""
            try:
                require_admin()
                sheriffs = Sheriff.query.all()
                return jsonify([s.read() for s in sheriffs])
            except AuthError as e:
                return e.body, e.status_code

        def put(self):
            """Update sheriff user."""
            try:
                current_sheriff = decode_sheriff_token()
            except AuthError as e:
                return e.body, e.status_code

            body = request.get_json()
            # Admin can update anyone, members can only update themselves
            if current_sheriff.is_admin() and body.get('uid'):
                target = Sheriff.query.filter_by(_uid=body['uid']).first()
                if not target:
                    return {'message': 'Target sheriff not found'}, 404
            else:
                target = current_sheriff

            target.update(body)
            return jsonify(target.read())

        def delete(self):
            """Delete sheriff user (admin only)."""
            try:
                current_sheriff = decode_sheriff_token()
                if not current_sheriff or not current_sheriff.is_admin():
                    return {'message': 'Admin access required'}, 403
            except AuthError as e:
                return e.body, e.status_code

            body = request.get_json()
            uid = body.get('uid')
            target = Sheriff.query.filter_by(_uid=uid).first()
            if not target:
                return {'message': f'Sheriff {uid} not found'}, 404

            target_data = target.read()
            target.delete()
            return jsonify({'message': f'Deleted sheriff: {target_data["name"]}'}), 200

    # Register endpoints
    api.add_resource(_Authenticate, '/sheriff/authenticate')
    api.add_resource(_ID, '/sheriff/id')
    api.add_resource(_CRUD, '/sheriff/user')
