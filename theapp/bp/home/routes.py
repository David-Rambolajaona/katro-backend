from flask import Blueprint, render_template, current_app, request, redirect, jsonify
import jwt

from theapp.models import db, Visitor, Visit

import datetime
import json
import time

home_bp = Blueprint('home_bp', __name__, template_folder='template', static_folder='static', static_url_path='/home-static')

@home_bp.route('/')
def home():    
    return render_template('home.html')

def create_visitor() :
    date_now = datetime.datetime.utcnow()
    visitor = Visitor()
    visitor.ip_address = request.remote_addr
    visitor.user_agent = request.headers.get('User-Agent')
    visitor.date_creation = date_now
    db.session.add(visitor)
    db.session.commit()
    db.session.refresh(visitor)
    return visitor.id

def create_visit(visitor_id) :
    other_data = {
        "params": request.args.get("params"),
        "query": request.args.get("query")
    }
    date_now = datetime.datetime.utcnow()
    visit = Visit()
    visit.date_creation = date_now
    visit.visitor_id = visitor_id
    visit.fullpath = request.args.get("fullpath")
    visit.name = request.args.get("name")
    visit.other_data = json.dumps(other_data)
    db.session.add(visit)
    db.session.commit()
    db.session.refresh(visit)
    return visit.id

@home_bp.route('/api/token')
def api_token():
    token_client = request.args.get("token")
    token = ""
    if token_client is None :
        return "error", 401
    elif token_client in ["loading", "error"] :
        visitor_id = create_visitor()
        token = jwt.encode({"visitor_id": visitor_id}, current_app.secret_key, algorithm="HS256")
    else :
        try:
            decoded_token = jwt.decode(token_client, current_app.secret_key, algorithms=['HS256'])
            visitor_id = decoded_token.get("visitor_id")
            token = token_client

            # Check if the visitor id exists
            # If not, create
            visitor = Visitor.query.get(visitor_id)
            if not visitor :
                visitor_id = create_visitor()
                token = jwt.encode({"visitor_id": visitor_id}, current_app.secret_key, algorithm="HS256")
        except jwt.InvalidTokenError :
            return "error_token", 401

    visit_id = create_visit(visitor_id = visitor_id)

    return jsonify({"token": token})