from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text

from datetime import datetime

db = SQLAlchemy()

class Visitor(db.Model) :
    __tablename__ = "visitor"
    id = db.Column(db.Integer, primary_key=True)
    user_agent = db.Column(db.Text)
    ip_address = db.Column(db.Text)
    date_creation = db.Column(db.DateTime, default = datetime.utcnow)

class Visit(db.Model) :
    __tablename__ = "visit"
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.Integer)
    date_creation = db.Column(db.DateTime, default = datetime.utcnow)
    fullpath = db.Column(db.Text)
    name = db.Column(db.Text)
    other_data = db.Column(db.Text)

class GameOnline(db.Model) :
    __tablename__ = "game_online"
    id = db.Column(db.Integer, primary_key=True)
    host_name = db.Column(db.Text)
    client_name = db.Column(db.Text)
    code = db.Column(db.Text)
    nb_game = db.Column(db.Integer)
    winner = db.Column(db.Text)
    host_visitor_id = db.Column(db.Integer)
    client_visitor_id = db.Column(db.Integer)
    host_sids = db.Column(db.Text)
    client_sids = db.Column(db.Text)
    config = db.Column(db.Text)
    pebbles_move = db.Column(db.Text)
    chat = db.Column(db.Text)
    date_creation = db.Column(db.DateTime)
    date_update = db.Column(db.DateTime)

def convert_table_character() :
    sql = text("ALTER TABLE game_online CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
    db.session.execute(sql)
    db.session.commit()

def init_db():
    #db.drop_all()
    db.create_all()
    #db.session.add(Content("THIS IS SPARTAAAAAAA!!!", Gender['male']))
    #db.session.add(Content("What's your favorite scary movie?", Gender['female']))
    #db.session.commit()