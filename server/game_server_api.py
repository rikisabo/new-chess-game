"""
Chess Game Server - Using Original Game Logic
Server that uses the original game engine with REST API + WebSocket interface
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Set
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import original game logic (server version)
from ServerGame import ServerGame
from GameFactory import create_game
from GraphicsFactory import MockImgFactory
from Board import Board
from Piece import Piece
from Command import Command
from protocol import (
    ProtocolMessage, MessageType, 
    create_game_state_message, create_error_message,
    PlayerJoinMessage, PlayerMoveMessage, PieceState,
    DEFAULT_SERVER_PORT, DEFAULT_SERVER_HOST, ErrorCodes
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChessGameServer:
    def __init__(self):
        self.games: Dict[str, ServerGame] = {}
        self.websocket_connections: Dict[WebSocket, str] = {}  # websocket -> player_id
        self.player_games: Dict[str, str] = {}  # player_id -> game_id
        self.player_colors: Dict[str, str] = {}  # player_id -> "white"/"black"
        self.game_players: Dict[str, List[str]] = {}  # game_id -> [player_id1, player_id2]
        
    def create_new_game(self) -> str:
        """Create a new game and return game_id"""
        game_id = f"game_{int(time.time())}"
        
        # Create game using original game factory
        import pathlib
        pieces_root = pathlib.Path(__file__).parent.parent / "pieces"
        from GameFactory import create_game as create_game_instance
        game = create_game_instance(pieces_root, MockImgFactory())
        
        # Store game
        self.games[game_id] = game
        self.game_players[game_id] = []
        
        logger.info(f"Created new game: {game_id}")
        return game_id
    
    def add_player_to_game(self, game_id: str, player_id: str, player_name: str) -> bool:
        """Add player to game"""
        if game_id not in self.games:
            return False
            
        if len(self.game_players[game_id]) >= 2:
            return False
            
        # Assign color
        color = "white" if len(self.game_players[game_id]) == 0 else "black"
        
        # Store player info
        self.player_games[player_id] = game_id
        self.player_colors[player_id] = color
        self.game_players[game_id].append(player_id)
        
        logger.info(f"Player {player_name} ({player_id}) joined game {game_id} as {color}")
        return True
    
    def make_move(self, player_id: str, piece_id: str, target_row: int, target_col: int) -> bool:
        """Make a move in the game"""
        if player_id not in self.player_games:
            logger.warning(f"Player {player_id} not in any game")
            return False
            
        game_id = self.player_games[player_id]
        game = self.games[game_id]
        player_color = self.player_colors[player_id]
        
        # Validate piece ownership
        piece = game.piece_by_id.get(piece_id)
        if not piece:
            logger.warning(f"Piece {piece_id} not found")
            return False
            
        # Check if piece belongs to player (based on color)
        piece_color = "white" if piece.id[1] == "W" else "black"
        if piece_color != player_color:
            logger.warning(f"Player {player_id} ({player_color}) trying to move {piece_id} ({piece_color})")
            return False
        
        # Create command and process move
        success = game.process_move_command(piece_id, (target_row, target_col))
        
        if success:
            # Update game state
            game.update_game_state()
        
        logger.info(f"Move processed: {success} - {player_id} moves {piece_id} to ({target_row}, {target_col})")
        return success
    
    def get_game_state(self, game_id: str) -> Optional[dict]:
        """Get current game state"""
        if game_id not in self.games:
            return None
            
        game = self.games[game_id]
        
        # Get game state from server game
        game_state_data = game.get_game_state_dict()
        
        # Get players info
        players_info = {}
        for player_id in self.game_players.get(game_id, []):
            players_info[player_id] = {
                "id": player_id,
                "color": self.player_colors.get(player_id, "unknown"),
                "is_connected": True
            }
        
        # Build complete game state
        return {
            "game_id": game_id,
            "status": "finished" if game_state_data["game_over"] else ("active" if len(self.game_players.get(game_id, [])) == 2 else "waiting"),
            "players": players_info,
            "pieces": game_state_data["pieces"],
            "winner": game_state_data["winner"],
            "board_size": game_state_data["board_size"]
        }
    
    async def broadcast_game_update(self, game_id: str):
        """Broadcast game state update to all players in the game"""
        game_state = self.get_game_state(game_id)
        if not game_state:
            return
            
        message = {
            "type": "game_state",
            "data": game_state
        }
        
        # Send to all connected players in this game
        disconnected = []
        for websocket, player_id in self.websocket_connections.items():
            if player_id in self.player_games and self.player_games[player_id] == game_id:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            if ws in self.websocket_connections:
                del self.websocket_connections[ws]
    
    async def broadcast_move(self, game_id: str, player_id: str, piece_id: str, from_cell: tuple, to_cell: tuple):
        """Broadcast a move to all players in the game"""
        player_color = self.player_colors.get(player_id, "unknown")
        
        message = {
            "type": "move_made",
            "data": {
                "piece_id": piece_id,
                "from": from_cell,
                "to": to_cell,
                "color": player_color,
                "player_id": player_id
            }
        }
        
        # Send to all connected players in this game
        disconnected = []
        for websocket, ws_player_id in self.websocket_connections.items():
            if ws_player_id in self.player_games and self.player_games[ws_player_id] == game_id:
                try:
                    await websocket.send_text(json.dumps(message))
                    logger.info(f"Sent move to player {ws_player_id}: {piece_id} {from_cell} -> {to_cell}")
                except:
                    disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            if ws in self.websocket_connections:
                del self.websocket_connections[ws]

# Global server instance
game_server = ChessGameServer()

# FastAPI app
app = FastAPI(title="Chess Game Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Chess Game Server is running", 
        "games": len(game_server.games),
        "active_connections": len(game_server.websocket_connections)
    }

@app.post("/game/create")
async def create_game():
    """Create a new game"""
    game_id = game_server.create_new_game()
    return {"game_id": game_id, "status": "created"}

@app.post("/game/{game_id}/join")
async def join_game(game_id: str, player_data: dict):
    """Join a game"""
    player_id = player_data.get("player_id")
    player_name = player_data.get("player_name", f"Player_{player_id}")
    
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id is required")
    
    success = game_server.add_player_to_game(game_id, player_id, player_name)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot join game")
    
    # Broadcast update
    await game_server.broadcast_game_update(game_id)
    
    return {"status": "joined", "game_id": game_id, "player_id": player_id}

@app.post("/game/move")
async def make_move(move_data: dict):
    """Make a move"""
    player_id = move_data.get("player_id")
    piece_id = move_data.get("piece_id")
    to_row = move_data.get("to_row")
    to_col = move_data.get("to_col")
    
    if not all([player_id, piece_id, to_row is not None, to_col is not None]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    success = game_server.make_move(player_id, piece_id, to_row, to_col)
    
    if not success:
        raise HTTPException(status_code=400, detail="Invalid move")
    
    # Broadcast update
    if player_id in game_server.player_games:
        game_id = game_server.player_games[player_id]
        await game_server.broadcast_game_update(game_id)
    
    return {"status": "move_made"}

@app.get("/game/{game_id}/state")
async def get_game_state(game_id: str):
    """Get game state"""
    game_state = game_server.get_game_state(game_id)
    
    if not game_state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return game_state

@app.get("/player/{player_id}/game")
async def get_player_game(player_id: str):
    """Get player's current game state"""
    if player_id not in game_server.player_games:
        raise HTTPException(status_code=404, detail="Player not in any game")
        
    game_id = game_server.player_games[player_id]
    game_state = game_server.get_game_state(game_id)
    
    if not game_state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return game_state

@app.get("/games")
async def list_games():
    """List all games"""
    games_info = []
    for game_id in game_server.games.keys():
        game_state = game_server.get_game_state(game_id)
        if game_state:
            games_info.append({
                "game_id": game_id,
                "status": game_state["status"],
                "players": len(game_state["players"]),
                "created_at": game_id.split('_')[1]
            })
    return {"games": games_info}

@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    await websocket.accept()
    game_server.websocket_connections[websocket] = player_id
    logger.info(f"WebSocket connected for player {player_id}")
    
    try:
        # Send current game state if player is in a game
        if player_id in game_server.player_games:
            game_id = game_server.player_games[player_id]
            game_state = game_server.get_game_state(game_id)
            if game_state:
                await websocket.send_text(json.dumps({
                    "type": "game_state",
                    "data": game_state
                }))
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message_type == "player_move":
                    # Handle move from client
                    move_data = message.get("data", {})
                    piece_id = move_data.get("piece_id")
                    target_cell = move_data.get("to_cell")
                    
                    if piece_id and target_cell:
                        target_row, target_col = target_cell
                        success = game_server.make_move(player_id, piece_id, target_row, target_col)
                        
                        if success and player_id in game_server.player_games:
                            # Broadcast the move to all players in the game
                            game_id = game_server.player_games[player_id]
                            await game_server.broadcast_move(game_id, player_id, piece_id, move_data.get("from_cell"), target_cell)
                            # Also broadcast updated game state
                            await game_server.broadcast_game_update(game_id)
                        
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for player {player_id}")
    except Exception as e:
        logger.error(f"WebSocket error for player {player_id}: {e}")
    finally:
        if websocket in game_server.websocket_connections:
            del game_server.websocket_connections[websocket]

if __name__ == "__main__":
    logger.info("Starting Chess Game Server...")
    uvicorn.run("game_server_api:app", host="0.0.0.0", port=8000, reload=True)
