from flask import current_app
import jwt

from theapp.models import db, GameOnline

import datetime
import json

def get_game_from_code(code) :
    game = db.session.query(GameOnline).filter(GameOnline.code == code).order_by(GameOnline.date_update.desc()).first()
    return game

def get_date_now() :
    date_now = datetime.datetime.utcnow()
    date_str = date_now.strftime("%d/%m/%Y, %H:%M:%S")
    return date_now, date_str

def create_game(host_name, client_name, code, host_token, client_token, host_sid, client_sid, config) :
    p_start = "host" if config.get("p_start") == "opp" else "client"
    config["p_start"] = p_start
    
    date_now, date_str = get_date_now()
    game = GameOnline()
    game.host_name = host_name
    game.client_name = client_name
    game.code = code
    game.nb_game = 1
    game.winner = json.dumps({
        "history": []
    })

    decoded_token = jwt.decode(host_token, current_app.secret_key, algorithms=['HS256'])
    visitor_id = decoded_token.get("visitor_id")
    game.host_visitor_id = visitor_id

    decoded_token = jwt.decode(client_token, current_app.secret_key, algorithms=['HS256'])
    visitor_id = decoded_token.get("visitor_id")
    game.client_visitor_id = visitor_id

    game.host_sids = json.dumps({
        "history": [{"sid": host_sid, "date": date_str}]
    })

    game.client_sids = json.dumps({
        "history": [{"sid": client_sid, "date": date_str}]
    })

    game.config = json.dumps({
        "history": [{
            "conf": config,
            "date": date_str,
            "game": 1
        }]
    })

    game.pebbles_move = json.dumps({
        "games": [
            {
                "history": []
            }
        ]
    })

    game.chat = json.dumps({
        "history": []
    })

    game.date_creation = date_now
    game.date_update = date_now

    db.session.add(game)
    db.session.commit()
    db.session.refresh(game)
    return game.id

def add_pebbles_move(game_code, num, speed, user_sid) :
    game = get_game_from_code(game_code)
    if game :
        date_now, date_str = get_date_now()

        who = "host" if user_sid in game.host_sids else "client"
        # Convert the client num to host viewpoint
        if who == "client" :
            num = 9 - num

        pebbles_move = json.loads(game.pebbles_move)
        pebbles_move["games"][-1]["history"].append({
            "num": num,
            "who": who,
            "speed": speed,
            "date": date_str
        })

        game.pebbles_move = json.dumps(pebbles_move)

        game.date_update = date_now
        db.session.commit()

def update_pubbles_move_for_pos(game_code, pos, score, winner = None) :
    game = get_game_from_code(game_code)
    if game :
        date_now, date_str = get_date_now()

        pebbles_move = json.loads(game.pebbles_move)
        pebbles_move["games"][-1]["history"][-1]["pos_score"] = {
            "pos": pos,
            "score": score,
            "date_end_turn": date_str
        }

        game.pebbles_move = json.dumps(pebbles_move)

        if winner :
            game_winner = json.loads(game.winner)
            game_winner["history"].append({
                "who": winner,
                "date": date_str,
                "game": game.nb_game
            })
            game.winner = json.dumps(game_winner)

        game.date_update = date_now
        db.session.commit()

def update_game_to_over(game_code, winner, pos, score) :
    update_pubbles_move_for_pos(game_code, pos, score, winner)

def update_game_for_restart(game_code, config) :
    game = get_game_from_code(game_code)
    if game :
        date_now, date_str = get_date_now()
        pebbles_move = json.loads(game.pebbles_move)
        game_config = json.loads(game.config)

        # Get last speed
        last_speed = None
        if len(pebbles_move["games"][-1]["history"]) > 0 :
            last_speed = pebbles_move["games"][-1]["history"][-1].get("speed")
        if not last_speed :
            last_speed = game_config.get("history", [{}])[-1].get("conf", {}).get("speed", 400)
        config["speed"] = last_speed

        game.nb_game += 1
        game_config["history"].append({
            "conf": config,
            "date": date_str,
            "game": game.nb_game
        })
        game.config = json.dumps(game_config)
        pebbles_move["games"].append({
            "history": []
        })
        game.pebbles_move = json.dumps(pebbles_move)
        game.date_update = date_now
        db.session.commit()

def add_notification_to_game(game_code, type_notif, who = 'host', value = '', timestamp = None, sid_disco = None) :
    game = get_game_from_code(game_code)
    if game :
        date_now, date_str = get_date_now()

        if sid_disco :
            who = "host" if sid_disco in game.host_sids else "client"

        chat = json.loads(game.chat)
        chat["history"].append({
            "type": type_notif,
            "who": who,
            "value": value,
            "timestamp": timestamp,
            "date": date_str
        })
        game.chat = json.dumps(chat)
        game.date_update = date_now
        db.session.commit()

def add_new_sid_for_user(game_code, who = 'host', sid = None) :
    game = get_game_from_code(game_code)
    if game :
        date_now, date_str = get_date_now()

        if who == "host" :
            sids = json.loads(game.host_sids)
        else :
            sids = json.loads(game.client_sids)
        
        sids["history"].append({
            "sid": sid,
            "date": date_str
        })

        if who == "host" :
            game.host_sids = json.dumps(sids)
        else :
            game.client_sids = json.dumps(sids)
        
        game.date_update = date_now
        db.session.commit()