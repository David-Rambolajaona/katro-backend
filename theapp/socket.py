from flask_socketio import SocketIO, emit, send, join_room, leave_room
from flask import request

import gevent
import eventlet

from .bp.game.func import *

import json

socketio = SocketIO(cors_allowed_origins="*")

active_rooms = {}
active_games = {}

def s() :
    print("active_rooms", active_rooms)
    print("active_games", active_games)
    print("\n")

def get_available_rooms():
    global active_rooms
    # print(socketio.server.rooms(request.sid))
    return list(active_rooms.keys())

def delete_room(sid, emit_leave_room = True):
    global active_rooms
    for client_room in socketio.server.rooms(sid) :
        if client_room in get_available_rooms() :
            if emit_leave_room :
                res = {
                    "type": "leave_room",
                    "sid": sid
                }
                emit('message', json.dumps(res), room=client_room)
            if sid in active_rooms[client_room]["sid"] :
                active_rooms[client_room]["sid"].remove(sid)
                if active_rooms[client_room]["host_sid"] == sid :
                    for client_sid in active_rooms[client_room]["sid"] :
                        active_rooms[client_room]["sid"].remove(client_sid)
            leave_room(client_room)
            if len(active_rooms[client_room]["sid"]) == 0 :
                del active_rooms[client_room]

@socketio.on('connect')
def on_connect() :
    res = {
        "type": "on_connect",
        "sid": request.sid
    }
    emit('message', json.dumps(res), broadcast=False)

@socketio.on('disconnect')
def on_disconnect() :
    global active_games
    delete_room(request.sid)

    # Setting the connection of this user to False in a game
    rooms_to_delete = []
    for game_room, users in active_games.items() :
        has_disconnected = False
        other_user_sid = None
        for sid, sid_data in users.items() :
            if sid_data.get("sids", [None])[-1] == request.sid :
                active_games[game_room][sid]["connected"] = False
                has_disconnected = True
            else :
                other_user_sid = sid_data.get("sids", [None])[-1]
        
        # Inform the other user about the disconnection
        if has_disconnected and other_user_sid :
            res = {
                "type": "opp_disconnected"
            }
            emit('message', json.dumps(res), room=other_user_sid)
        
        # Checking if all users in the room are disconnected
        # If so, delete the room in the variable
        all_disconnected = True
        for sid, sid_data in users.items() :
            if sid_data.get("connected") :
                all_disconnected = False
        if all_disconnected :
            rooms_to_delete.append(game_room)

        
        if has_disconnected and other_user_sid :
            add_notification_to_game(game_room, "disco", "host", "", None, request.sid)

    for room in rooms_to_delete :
        if room in active_games.keys() :
            del active_games[room]

@socketio.on('join')
def on_join(data) :
    global active_rooms
    data = json.loads(data)
    game_code = data.get("game_code")
    if data.get("create") :
        if game_code :
            join_room(game_code)
            if active_rooms.get(game_code) :
                active_rooms[game_code]["sid"].append(request.sid)
            else :
                active_rooms[game_code] = {
                    "sid": [request.sid],
                    "host_sid": request.sid,
                    "host_username": data.get("username", "Joueur")
                } 
            res = {
                "type": "response_create_game",
                "success": True,
                "sid": request.sid
            }
            emit('message', json.dumps(res), room=game_code)
        else :
            res = {
                "type": "response_create_game",
                "success": False
            }
            emit('message', json.dumps(res), broadcast=False)
    else :
        if game_code in get_available_rooms() :
            join_room(game_code)
            if active_rooms.get(game_code) :
                active_rooms[game_code]["sid"].append(request.sid)
            res = {
                "type": "response_join_game",
                "msg": "room_exists",
                "sid": request.sid,
                "username": data.get("username", "Joueur"),
                "host_sid": active_rooms[game_code]["host_sid"] if active_rooms.get(game_code) else None,
                "host_username": active_rooms[game_code]["host_username"] if active_rooms.get(game_code) else "Joueur",
                "token": data.get("token")
            }
            emit('message', json.dumps(res), room=game_code)
        else :
            res = {
                "type": "response_join_game",
                "msg": "no_room",
            }
            emit('message', json.dumps(res), broadcast=False)

@socketio.on('leave')
def on_leave(data) :
    data = json.loads(data)
    game_code = data.get("game_code")
    if game_code :
        leave_room(game_code)
    delete_room(request.sid, emit_leave_room=data.get("emit_leave_room", True))

@socketio.on('accept_client')
def on_accept_client(data) :
    data = json.loads(data)
    game_code = data.get("game_code")
    if game_code :
        if game_code in active_rooms.keys() :
            del active_rooms[game_code]

        active_games[game_code] = {
            data.get("client_sid") : {
                "sids": [data.get("client_sid")],
                "connected": True
            },
            request.sid : {
                "sids": [request.sid],
                "connected": True
            } 
        }
        res = {
            "type": "accept_client",
            "sid": data.get("client_sid"),
            "host_sid": request.sid,
            "who_starts": data.get("who_starts"),
            "clock_start": data.get("clock_start"),
            "speed_timer": data.get("speed_timer")
        }
        emit('message', json.dumps(res), room=game_code)

        create_game(data.get("host_name"), data.get("client_name"), game_code, data.get("host_token"), data.get("client_token"), request.sid, data.get("client_sid"), {"p_start": data.get("who_starts"), "p_start_c": data.get("clock_start"), "speed": data.get("speed_timer")})

@socketio.on('move_pebbles')
def on_move_pebbles(data) :
    data = json.loads(data)
    game_room = data.get('game_code')
    if game_room in active_games.keys() and data.get('to') :
        to_room = active_games[data.get('game_code')][data.get('to')]["sids"][-1]

        # If the destination user is connected, move the pebbles for him
        # Otherwise, save the pebbles move for his future connection
        res = {
            "type": "move_pebbles",
            "from": request.sid,
            "num": data.get('num'),
            "speed": data.get("speed")
        }
        if active_games[game_room].get(data.get('to', '.'), {}).get("connected") :
            emit('message', json.dumps(res), room=to_room)
        else :
            active_games[game_room][data.get('to')]["unreceived_move"] = res
        
        add_pebbles_move(game_room, data.get('num'), data.get("speed"), request.sid)
    else :
        res = {
            "type": "move_pebbles_no_game"
        }
        emit('message', json.dumps(res), broadcast=False)

@socketio.on('restart')
def on_restart(data) :
    data = json.loads(data)
    if data.get('game_code') in active_games.keys() and data.get('to') :
        if active_games[data.get('game_code')].get(data.get('to', '.'), {}).get("connected") :
            to_room = active_games[data.get('game_code')][data.get('to')]["sids"][-1]
            res = {
                "type": "restart_request",
                "from": request.sid,
                "p_start": data.get("p_start", "me"),
                "p_start_c": data.get("p_start_c", "clock")
            }
            emit('message', json.dumps(res), room=to_room)

            update_game_for_restart(data.get('game_code'), {"p_start": "client" if data.get("p_start") == "me" else "host", "p_start_c": data.get("p_start_c")})
        else :
            res = {
                "type": "restart_no_game"
            }
            emit('message', json.dumps(res), broadcast=False)
    else :
        res = {
            "type": "restart_no_game"
        }
        emit('message', json.dumps(res), broadcast=False)

@socketio.on("restart_ok")
def on_restart_ok(data) :
    data = json.loads(data)
    if data.get('game_code') in active_games.keys() and data.get('to') :
        res = {
            "type": "restart_ok",
        }
        emit('message', json.dumps(res), broadcast=False)

        to_room = active_games[data.get('game_code')][data.get('to')]["sids"][-1]
        emit('message', json.dumps(res), room=to_room)
    else :
        res = {
            "type": "restart_no_game"
        }
        emit('message', json.dumps(res), broadcast=False)

@socketio.on("finish_turn")
def on_finish_turn(data) :
    data = json.loads(data)
    if data.get('game_code') in active_games.keys() and data.get('to') :
        res = {
            "type": "finish_turn"
        }
        to_room = active_games[data.get('game_code')][data.get('to')]["sids"][-1]
        emit('message', json.dumps(res), room=to_room)

        update_pubbles_move_for_pos(data.get('game_code'), data.get('pos', {}).get('pos'), data.get('pos', {}).get('score'))
    else :
        res = {
            "type": "finish_turn_no_game"
        }
        emit('message', json.dumps(res), broadcast=False)
    
@socketio.on("reconnect_game")
def on_reconnect_game(data) :
    global active_games
    data = json.loads(data)
    game_room = data.get("game_code")
    sid = None
    if game_room and game_room in active_games.keys() :
        sid = data.get("sid")
    # Notify the user that there is no game anymore
    else :
        res = {
            "type": "reconnect_no_game"
        }
        emit('message', json.dumps(res), broadcast=False)
    if sid and sid in active_games[game_room].keys() :
        active_games[game_room][sid]["sids"].append(request.sid)
        active_games[game_room][sid]["connected"] = True
        
        # Inform the other user about the reconnection
        for sid_2 in list(active_games[game_room].keys()) :
            if sid_2 != sid :
                res = {
                    "type": "opp_reconnected"
                }
                to_room = active_games[game_room][sid_2]["sids"][-1]
                emit('message', json.dumps(res), room=to_room)
        
        # Get unreceived messages if there is any
        unreceived_messages = active_games[game_room][sid].get("unreceived_messages", [])
        for msg in unreceived_messages :
            res = {
                "type": "receive_message",
                "message": msg.get("message")
            }
            emit('message', json.dumps(res), broadcast=False)
        active_games[game_room][sid]["unreceived_messages"] = []

        # Get unreceived move if there is any
        unreceived_move = active_games[game_room][sid].get("unreceived_move")
        if unreceived_move :
            emit('message', json.dumps(unreceived_move), broadcast=False)
            res = {
                "type": "finish_turn"
            }
            emit('message', json.dumps(res), broadcast=False)
            active_games[game_room][sid]["unreceived_move"] = None
        
        add_notification_to_game(game_room, "reco", "host" if data.get("is_host") else "client")
        add_new_sid_for_user(game_room, "host" if data.get("is_host") else "client", request.sid)
    else :
        res = {
            "type": "reconnect_game_no_sid"
        }
        emit('message', json.dumps(res), broadcast=False)

@socketio.on("send_message")
def on_send_message(data) :
    global active_games
    data = json.loads(data)
    game_room = data.get("game_code")
    if game_room and game_room in active_games.keys() :
        to_room = active_games[game_room].get(data.get('to', '.'), {}).get("sids", [None])[-1]
        if to_room and data.get('from') in active_games[game_room].keys() :
            res = {
                "type": "message_sent",
                "index": data.get("index", 0)
            }
            emit('message', json.dumps(res), broadcast=False)

            # If the destination user is connected, send the message to him
            # Otherwise, save the message for his future connection
            if active_games[game_room].get(data.get('to', '.'), {}).get("connected") :
                res = {
                    "type": "receive_message",
                    "message": data.get("message")
                }
                emit('message', json.dumps(res), room=to_room)
            else :
                if active_games[game_room].get(data.get('to', '.'), {}).get("unreceived_messages") is None :
                    active_games[game_room][data.get('to')]["unreceived_messages"] = []
                active_games[game_room][data.get('to')]["unreceived_messages"].append({
                    "message": data.get("message")
                })
            
            add_notification_to_game(game_room, "msg", "host" if data.get("is_host") else "client", data.get("message"), data.get("timestamp"))

@socketio.on("game_over")
def on_game_over(data) :
    data = json.loads(data)
    game_room = data.get("game_code")
    if game_room and game_room in active_games.keys() :
        update_game_to_over(game_room, data.get("winner"), data.get("pos", {}).get("pos"), data.get("pos", {}).get("score"))