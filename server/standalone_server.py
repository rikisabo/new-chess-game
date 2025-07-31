"""
Standalone Chess Game Server - REST API Server for Chess Game
Completely independent server with no external dependencies from KFC_Py
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
from collections import defaultdict
import time
from dataclasses import dataclass, asdict
from enum import Enum
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Game State Enums
class PieceType(Enum):
    PAWN = "pawn"
    ROOK = "rook"
    KNIGHT = "knight"
    BISHOP = "bishop"
    QUEEN = "queen"
    KING = "king"

class Color(Enum):
    WHITE = "white"
    BLACK = "black"

class GameStatus(Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"

# Data Classes
@dataclass
class Position:
    row: int
    col: int
    
    def to_dict(self):
        return {"row": self.row, "col": self.col}

@dataclass
class Piece:
    id: str
    piece_type: PieceType
    color: Color
    position: Position
    is_alive: bool = True
    
    def to_dict(self):
        return {
            "id": self.id,
            "type": self.piece_type.value,
            "color": self.color.value,
            "position": self.position.to_dict(),
            "is_alive": self.is_alive
        }

@dataclass
class Move:
    piece_id: str
    from_pos: Position
    to_pos: Position
    timestamp: float
    player_id: str
    
    def to_dict(self):
        return {
            "piece_id": self.piece_id,
            "from_pos": self.from_pos.to_dict(),
            "to_pos": self.to_pos.to_dict(),
            "timestamp": self.timestamp,
            "player_id": self.player_id
        }

@dataclass
class Player:
    id: str
    name: str
    color: Color
    is_connected: bool = True
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color.value,
            "is_connected": self.is_connected
        }

class GameState:
    def __init__(self):
        self.game_id = f"game_{int(time.time())}"
        self.status = GameStatus.WAITING
        self.players: Dict[str, Player] = {}
        self.pieces: Dict[str, Piece] = {}
        self.moves: List[Move] = []
        self.board_size = (8, 8)
        self.created_at = datetime.now()
        self.last_move_time = time.time()
        self._init_pieces()
        
    def _init_pieces(self):
        """Initialize chess pieces in starting positions"""
        # White pieces
        self.pieces["RW1"] = Piece("RW1", PieceType.ROOK, Color.WHITE, Position(7, 0))
        self.pieces["NW1"] = Piece("NW1", PieceType.KNIGHT, Color.WHITE, Position(7, 1))
        self.pieces["BW1"] = Piece("BW1", PieceType.BISHOP, Color.WHITE, Position(7, 2))
        self.pieces["QW1"] = Piece("QW1", PieceType.QUEEN, Color.WHITE, Position(7, 3))
        self.pieces["KW1"] = Piece("KW1", PieceType.KING, Color.WHITE, Position(7, 4))
        self.pieces["BW2"] = Piece("BW2", PieceType.BISHOP, Color.WHITE, Position(7, 5))
        self.pieces["NW2"] = Piece("NW2", PieceType.KNIGHT, Color.WHITE, Position(7, 6))
        self.pieces["RW2"] = Piece("RW2", PieceType.ROOK, Color.WHITE, Position(7, 7))
        
        # White pawns
        for i in range(8):
            self.pieces[f"PW{i+1}"] = Piece(f"PW{i+1}", PieceType.PAWN, Color.WHITE, Position(6, i))
            
        # Black pieces
        self.pieces["RB1"] = Piece("RB1", PieceType.ROOK, Color.BLACK, Position(0, 0))
        self.pieces["NB1"] = Piece("NB1", PieceType.KNIGHT, Color.BLACK, Position(0, 1))
        self.pieces["BB1"] = Piece("BB1", PieceType.BISHOP, Color.BLACK, Position(0, 2))
        self.pieces["QB1"] = Piece("QB1", PieceType.QUEEN, Color.BLACK, Position(0, 3))
        self.pieces["KB1"] = Piece("KB1", PieceType.KING, Color.BLACK, Position(0, 4))
        self.pieces["BB2"] = Piece("BB2", PieceType.BISHOP, Color.BLACK, Position(0, 5))
        self.pieces["NB2"] = Piece("NB2", PieceType.KNIGHT, Color.BLACK, Position(0, 6))
        self.pieces["RB2"] = Piece("RB2", PieceType.ROOK, Color.BLACK, Position(0, 7))
        
        # Black pawns
        for i in range(8):
            self.pieces[f"PB{i+1}"] = Piece(f"PB{i+1}", PieceType.PAWN, Color.BLACK, Position(1, i))
    
    def add_player(self, player_id: str, player_name: str) -> bool:
        """Add a player to the game"""
        if len(self.players) >= 2:
            return False
            
        color = Color.WHITE if len(self.players) == 0 else Color.BLACK
        player = Player(player_id, player_name, color)
        self.players[player_id] = player
        
        if len(self.players) == 2:
            self.status = GameStatus.ACTIVE
            
        logger.info(f"Player {player_name} joined as {color.value}")
        return True
    
    def remove_player(self, player_id: str):
        """Remove a player from the game"""
        if player_id in self.players:
            self.players[player_id].is_connected = False
            logger.info(f"Player {player_id} disconnected")
    
    def make_move(self, player_id: str, piece_id: str, to_row: int, to_col: int) -> bool:
        """Make a move for a player"""
        if self.status != GameStatus.ACTIVE:
            logger.warning("Game is not active")
            return False
            
        if player_id not in self.players:
            logger.warning(f"Player {player_id} not in game")
            return False
            
        if piece_id not in self.pieces:
            logger.warning(f"Piece {piece_id} not found")
            return False
            
        piece = self.pieces[piece_id]
        player = self.players[player_id]
        
        # Check if player owns the piece
        if piece.color != player.color:
            logger.warning(f"Player {player_id} doesn't own piece {piece_id}")
            return False
            
        # Check if piece is alive
        if not piece.is_alive:
            logger.warning(f"Piece {piece_id} is not alive")
            return False
        
        # Validate move bounds
        if not (0 <= to_row < 8 and 0 <= to_col < 8):
            logger.warning(f"Move out of bounds: ({to_row}, {to_col})")
            return False
        
        # Store the move
        from_pos = piece.position
        to_pos = Position(to_row, to_col)
        move = Move(piece_id, from_pos, to_pos, time.time(), player_id)
        self.moves.append(move)
        
        # Check for capture
        captured_piece = self._get_piece_at_position(to_pos)
        if captured_piece and captured_piece.color != piece.color:
            captured_piece.is_alive = False
            logger.info(f"Piece {captured_piece.id} captured by {piece_id}")
        
        # Update piece position
        piece.position = to_pos
        self.last_move_time = time.time()
        
        # Check for game end
        if self._is_game_over():
            self.status = GameStatus.FINISHED
            
        logger.info(f"Move made: {piece_id} from {from_pos.to_dict()} to {to_pos.to_dict()}")
        return True
    
    def _get_piece_at_position(self, position: Position) -> Optional[Piece]:
        """Get piece at given position"""
        for piece in self.pieces.values():
            if piece.is_alive and piece.position.row == position.row and piece.position.col == position.col:
                return piece
        return None
    
    def _is_game_over(self) -> bool:
        """Check if game is over (king captured)"""
        white_king_alive = any(p.is_alive and p.piece_type == PieceType.KING and p.color == Color.WHITE 
                              for p in self.pieces.values())
        black_king_alive = any(p.is_alive and p.piece_type == PieceType.KING and p.color == Color.BLACK 
                              for p in self.pieces.values())
        return not (white_king_alive and black_king_alive)
    
    def get_winner(self) -> Optional[str]:
        """Get the winner of the game"""
        if self.status != GameStatus.FINISHED:
            return None
            
        white_king_alive = any(p.is_alive and p.piece_type == PieceType.KING and p.color == Color.WHITE 
                              for p in self.pieces.values())
        
        if white_king_alive:
            return "white"
        else:
            return "black"
    
    def to_dict(self):
        """Convert game state to dictionary"""
        return {
            "game_id": self.game_id,
            "status": self.status.value,
            "players": {pid: player.to_dict() for pid, player in self.players.items()},
            "pieces": {pid: piece.to_dict() for pid, piece in self.pieces.items() if piece.is_alive},
            "moves": [move.to_dict() for move in self.moves[-10:]],  # Last 10 moves
            "board_size": self.board_size,
            "winner": self.get_winner(),
            "last_move_time": self.last_move_time
        }

# Server Implementation
class ChessGameServer:
    def __init__(self):
        self.games: Dict[str, GameState] = {}
        self.websocket_connections: Dict[WebSocket, str] = {}  # websocket -> player_id
        self.player_games: Dict[str, str] = {}  # player_id -> game_id
        
    def create_game(self) -> GameState:
        """Create a new game"""
        game = GameState()
        self.games[game.game_id] = game
        logger.info(f"Created new game: {game.game_id}")
        return game
    
    def join_game(self, game_id: str, player_id: str, player_name: str) -> bool:
        """Join a game"""
        if game_id not in self.games:
            return False
            
        game = self.games[game_id]
        success = game.add_player(player_id, player_name)
        
        if success:
            self.player_games[player_id] = game_id
            
        return success
    
    def make_move(self, player_id: str, piece_id: str, to_row: int, to_col: int) -> bool:
        """Make a move"""
        if player_id not in self.player_games:
            return False
            
        game_id = self.player_games[player_id]
        game = self.games[game_id]
        
        return game.make_move(player_id, piece_id, to_row, to_col)
    
    def get_game_state(self, game_id: str) -> Optional[dict]:
        """Get game state"""
        if game_id not in self.games:
            return None
        return self.games[game_id].to_dict()
    
    def get_player_game_state(self, player_id: str) -> Optional[dict]:
        """Get game state for a player"""
        if player_id not in self.player_games:
            return None
        game_id = self.player_games[player_id]
        return self.get_game_state(game_id)
    
    async def broadcast_game_update(self, game_id: str):
        """Broadcast game update to all connected players"""
        if game_id not in self.games:
            return
            
        game_state = self.games[game_id].to_dict()
        message = {
            "type": "game_update",
            "data": game_state
        }
        
        # Send to all websocket connections for this game
        disconnected = []
        for websocket, player_id in self.websocket_connections.items():
            if player_id in self.player_games and self.player_games[player_id] == game_id:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            del self.websocket_connections[ws]

# Global server instance
game_server = ChessGameServer()

# FastAPI App
app = FastAPI(title="Chess Game Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API Endpoints
@app.get("/")
async def root():
    return {"message": "Chess Game Server is running", "games": len(game_server.games)}

@app.post("/game/create")
async def create_game():
    """Create a new game"""
    game = game_server.create_game()
    return {"game_id": game.game_id, "status": "created"}

@app.post("/game/{game_id}/join")
async def join_game(game_id: str, player_data: dict):
    """Join a game"""
    player_id = player_data.get("player_id")
    player_name = player_data.get("player_name", f"Player_{player_id}")
    
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id is required")
    
    success = game_server.join_game(game_id, player_id, player_name)
    
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
    game_state = game_server.get_player_game_state(player_id)
    
    if not game_state:
        raise HTTPException(status_code=404, detail="Player not in any game")
    
    return game_state

@app.get("/games")
async def list_games():
    """List all games"""
    games_info = []
    for game_id, game in game_server.games.items():
        games_info.append({
            "game_id": game_id,
            "status": game.status.value,
            "players": len(game.players),
            "created_at": game.created_at.isoformat()
        })
    return {"games": games_info}

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    await websocket.accept()
    game_server.websocket_connections[websocket] = player_id
    logger.info(f"WebSocket connected for player {player_id}")
    
    try:
        # Send current game state if player is in a game
        game_state = game_server.get_player_game_state(player_id)
        if game_state:
            await websocket.send_text(json.dumps({
                "type": "game_state",
                "data": game_state
            }))
        
        # Keep connection alive
        while True:
            try:
                # Wait for client messages (ping/pong, etc.)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
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
    uvicorn.run("standalone_server:app", host="0.0.0.0", port=8000, reload=True)
