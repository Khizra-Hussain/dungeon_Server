# In-memory store for all active games
# key = game_id, value = game state dict
active_games = {}

# In-memory store for world data
# key = game_id, value = world dict (tiles, entities, spawn_points)
active_worlds = {}


def validate_action(action, game_state, world):
    
    # player must be in this game
    player = next(
        (p for p in game_state.get("players", [])
         if p["username"] == action["username"]), None
    )
    if not player:
        return False, "Player not found"

    # move
    if action["action_type"] == "move":
        direction = action["payload"].get("direction")
        if direction not in ["north", "south", "east", "west"]:
            return False, "Invalid direction"

        x, y = player["x"], player["y"]
        if direction == "north": y -= 1
        if direction == "south": y += 1
        if direction == "east":  x += 1
        if direction == "west":  x -= 1

        if player.get("has_moved", False):
            if x == player.get("spawn_x", 0) and y == player.get("spawn_y", 0):
                return False, "Cannot return to spawn point"
        # checking boundries
        if y < 0 or y >= len(world["tiles"]):
            return False, "Out of bounds"
        if x < 0 or x >= len(world["tiles"][y]):
            return False, "Out of bounds"

        tile = next(
            (t for t in world["tiles"]
            if t["x"] == x and t["y"] == y), None
        )
        target_tile = tile["type"] if tile else "grass"

        if target_tile == "water" :
            return False, "Cannot move into water " 
        # wall, tree, statue entity check cannot move into these
        obstacle = next(
            (e for e in game_state.get("entities", [])
            if e.get("x") == x and e.get("y") == y
            and e.get("type") in ["wall", "tree", "statue"]), None
        )
        if obstacle:
            return False, f"Cannot move into {obstacle.get('type')}"

    

    # pickup
    elif action["action_type"] == "pickup":
        target_id = action["payload"].get("target_id")
        if not target_id:
            return False, "No target_id in payload"

        entity = next(
            (e for e in game_state.get("entities", [])
             if e.get("id") == target_id), None
        )
        if not entity:
            return False, "Item not found"

        
        if entity.get("x") != player["x"] or entity.get("y") != player["y"]:
            return False, "Item is not on your tile"

    # door open
    elif action["action_type"] == "open_door":
        if not player.get("has_key", False):
            return False, "Player does not have the key"

    
    elif action["action_type"] == "idle":
        pass 

    # chat action
    elif action["action_type"] == "chat":
        message = action["payload"].get("msg")
        if not message:
            return False, "Message is empty"
        if len(message) > 200:
            return False, "Message too long"

    else:
        return False, f"Unknown action type: {action['action_type']}"

    return True, "Action valid"


def apply_action(action, game_state):

    player = next(
        (p for p in game_state.get("players", [])
         if p["username"] == action["username"]), None
    )
    if not player:
        return game_state

    # move
    if action["action_type"] == "move":
        direction = action["payload"].get("direction")
        if direction == "north": player["y"] -= 1
        if direction == "south": player["y"] += 1
        if direction == "east":  player["x"] += 1
        if direction == "west":  player["x"] -= 1
        player["has_moved"] = True

    
    #pickup
    elif action["action_type"] == "pickup":
        target_id = action["payload"].get("target_id")
        entity = next(
            (e for e in game_state.get("entities", [])
             if e.get("id") == target_id), None
        )
        if entity:
            if entity["type"] == "treat":
                player["hp"] = player.get("hp", 0) + 1
                player["score"] = player.get("score", 0) + 5
            elif entity["type"] == "key":
                player["has_key"] = True
            game_state["entities"].remove(entity)

    #door open
    elif action["action_type"] == "open_door":
        game_state["status"] = "finished"
        game_state["winner_username"] = action["username"]

    elif action["action_type"] == "chat":
        message = action["payload"].get("msg")
        username = action.get("username", "unknown")
        game_state["chat"].append({
            "player": username,
            "msg": message,
            "at": action.get("timestamp")
        })

    return game_state
