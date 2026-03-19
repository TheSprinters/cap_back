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

                is_production = os.environ.get('IS_PRODUCTION', 'false').lower() == 'true'
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

                cookie_name = "jwt_sheriff"
                if is_production:
                    resp.set_cookie(cookie_name, token, max_age=43200,
                                    secure=True, httponly=True, path='/',
                                    samesite='None', domain='.opencodingsociety.com')
                else:
                    resp.set_cookie(cookie_name, token, max_age=43200,
                                    secure=False, httponly=False, path='/',
                                    samesite='Lax')
                return resp

            except Exception as e:
                return {'message': 'Something went wrong', 'error': str(e)}, 500

        def delete(self):
            """Logout - expire the sheriff cookie."""
            try:
                resp = Response("Sheriff token invalidated")
                is_production = os.environ.get('IS_PRODUCTION', 'false').lower() == 'true'
                cookie_name = "jwt_sheriff"
                if is_production:
                    resp.set_cookie(cookie_name, '', max_age=0,
                                    secure=True, httponly=True, path='/',
                                    samesite='None', domain='.opencodingsociety.com')
                else:
                    resp.set_cookie(cookie_name, '', max_age=0,
                                    secure=False, httponly=False, path='/',
                                    samesite='Lax')
                return resp
            except Exception as e:
                return {'message': 'Failed to invalidate token', 'error': str(e)}, 500

    class _ID(Resource):
        """Get current sheriff from token."""
        def get(self):
            token = request.cookies.get("jwt_sheriff")
            if not token:
                return {'message': 'Not authenticated'}, 401
            try:
                data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
                sheriff = Sheriff.query.filter_by(_uid=data["_uid"]).first()
                if not sheriff:
                    return {'message': 'Sheriff not found'}, 404
                return jsonify(sheriff.read())
            except jwt.ExpiredSignatureError:
                return {'message': 'Token expired'}, 401
            except jwt.InvalidTokenError:
                return {'message': 'Invalid token'}, 401

    class _CRUD(Resource):
        """Sheriff user CRUD operations."""

        def post(self):
            """Create a new sheriff user (signup)."""
            body = request.get_json()
            if not body:
                return {'message': 'No data provided'}, 400

            name = body.get('name')
            if not name or len(name) < 2:
                return {'message': 'Name is missing or too short'}, 400

            uid = body.get('uid')
            if not uid or len(uid) < 2:
                return {'message': 'Username is missing or too short'}, 400

            sheriff_id = body.get('sheriff_id')
            if not sheriff_id:
                return {'message': 'Sheriff ID / Badge Number is required'}, 400

            password = body.get('password', 'sheriff123')
            if len(password) < 8:
                return {'message': 'Password must be at least 8 characters'}, 400

            sheriff = Sheriff(
                name=name,
                uid=uid,
                sheriff_id=sheriff_id,
                password=password,
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
            token = request.cookies.get("jwt_sheriff")
            if not token:
                return {'message': 'Not authenticated'}, 401
            try:
                data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
                current_sheriff = Sheriff.query.filter_by(_uid=data["_uid"]).first()
                if not current_sheriff:
                    return {'message': 'Sheriff not found'}, 404
                if not current_sheriff.is_admin():
                    return {'message': 'Admin access required'}, 403

                sheriffs = Sheriff.query.all()
                return jsonify([s.read() for s in sheriffs])
            except jwt.ExpiredSignatureError:
                return {'message': 'Token expired'}, 401
            except jwt.InvalidTokenError:
                return {'message': 'Invalid token'}, 401

        def put(self):
            """Update sheriff user."""
            token = request.cookies.get("jwt_sheriff")
            if not token:
                return {'message': 'Not authenticated'}, 401
            try:
                data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
                current_sheriff = Sheriff.query.filter_by(_uid=data["_uid"]).first()
                if not current_sheriff:
                    return {'message': 'Sheriff not found'}, 404

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
            except jwt.ExpiredSignatureError:
                return {'message': 'Token expired'}, 401
            except jwt.InvalidTokenError:
                return {'message': 'Invalid token'}, 401

        def delete(self):
            """Delete sheriff user (admin only)."""
            token = request.cookies.get("jwt_sheriff")
            if not token:
                return {'message': 'Not authenticated'}, 401
            try:
                data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
                current_sheriff = Sheriff.query.filter_by(_uid=data["_uid"]).first()
                if not current_sheriff or not current_sheriff.is_admin():
                    return {'message': 'Admin access required'}, 403

                body = request.get_json()
                uid = body.get('uid')
                target = Sheriff.query.filter_by(_uid=uid).first()
                if not target:
                    return {'message': f'Sheriff {uid} not found'}, 404

                target_data = target.read()
                target.delete()
                return jsonify({'message': f'Deleted sheriff: {target_data["name"]}'}), 200
            except jwt.ExpiredSignatureError:
                return {'message': 'Token expired'}, 401
            except jwt.InvalidTokenError:
                return {'message': 'Invalid token'}, 401

    # Register endpoints
    api.add_resource(_Authenticate, '/sheriff/authenticate')
    api.add_resource(_ID, '/sheriff/id')
    api.add_resource(_CRUD, '/sheriff/user')
