"""
Protocol definition for Chess Game Client-Server communication
"""

from enum import Enum
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import json

# Default server configuration
DEFAULT_SERVER_HOST = "localhost"
DEFAULT_SERVER_PORT = 8000

class MessageType(Enum):
    PLAYER_JOIN = "player_join"
    PLAYER_MOVE = "player_move" 
    PLAYER_JUMP = "player_jump"
    PLAYER_SELECT = "player_select"
    
    GAME_STATE = "game_state"
    GAME_UPDATE = "game_update"
    MOVE_RESULT = "move_result"
    MOVE_MADE = "move_made"
    PLAYER_CONNECTED = "player_connected"
    GAME_START = "game_start"
    GAME_END = "game_end"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"

class ErrorCodes:
    PLAYER_NOT_FOUND = "PLAYER_NOT_FOUND"
    GAME_NOT_FOUND = "GAME_NOT_FOUND"
    INVALID_MOVE = "INVALID_MOVE"
    GAME_FULL = "GAME_FULL"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    SERVER_ERROR = "SERVER_ERROR"          # הוספתי את זה
    INVALID_MESSAGE = "INVALID_MESSAGE"    # הוספתי את זה

@dataclass
class PlayerJoinMessage:
    """Player join message"""
    player_name: str
    preferred_color: Optional[str] = None

@dataclass 
class PlayerMoveMessage:
    """Move message from client"""
    piece_id: str
    from_cell: Tuple[int, int]
    to_cell: Tuple[int, int]
    timestamp: int

@dataclass
class PlayerJumpMessage:
    """Jump message"""
    piece_id: str
    target_cell: Tuple[int, int]
    timestamp: int

@dataclass
class PlayerSelectMessage:
    """Piece selection message"""
    piece_id: str
    timestamp: int

@dataclass
class PieceState:
    """Piece state in game"""
    id: str
    position: Tuple[int, int]
    piece_type: str
    color: str
    state_name: str
    can_be_captured: bool
    is_selected: bool = False

@dataclass
class GameStateMessage:
    """Complete game state message"""
    pieces: List[PieceState]
    current_player: str
    move_log: List[Dict[str, Any]]
    game_status: str
    winner: Optional[str] = None
    selected_pieces: Dict[str, str] = None

@dataclass
class MoveResultMessage:
    """Move result message"""
    success: bool
    piece_id: str
    from_cell: Tuple[int, int]
    to_cell: Tuple[int, int]
    error_message: Optional[str] = None

@dataclass
class ErrorMessage:
    """Error message"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None

@dataclass
class ProtocolMessage:
    """Generic protocol message"""
    type: MessageType
    data: Dict[str, Any]
    
    def to_json(self) -> str:
        """Convert to JSON string for transmission"""
        return json.dumps({
            "type": self.type.value,
            "data": self.data
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProtocolMessage':
        """Create from received JSON"""
        data = json.loads(json_str)
        message_type = MessageType(data["type"])
        message_data = data.get("data", {})
        return cls(message_type, message_data)

def create_player_join_message(player_name: str, preferred_color: str = None) -> ProtocolMessage:
    return ProtocolMessage(
        MessageType.PLAYER_JOIN,
        {
            "player_name": player_name,
            "preferred_color": preferred_color
        }
    )

def create_player_move_message(piece_id: str, from_cell: Tuple[int, int], 
                              to_cell: Tuple[int, int], timestamp: int) -> ProtocolMessage:
    return ProtocolMessage(
        MessageType.PLAYER_MOVE,
        {
            "piece_id": piece_id,
            "from_cell": from_cell,
            "to_cell": to_cell,
            "timestamp": timestamp
        }
    )

def create_error_message(error_code: str, message: str, details: Dict[str, Any] = None) -> ProtocolMessage:
    return ProtocolMessage(
        MessageType.ERROR,
        {
            "error_code": error_code,
            "message": message,
            "details": details or {}
        }
    )

def create_player_select_message(piece_id: str, timestamp: int) -> ProtocolMessage:
    return ProtocolMessage(
        MessageType.PLAYER_SELECT,
        {
            "piece_id": piece_id,
            "timestamp": timestamp
        }
    )

def create_game_start_message(game_id: str, players: List[Dict[str, Any]]) -> ProtocolMessage:
    return ProtocolMessage(
        MessageType.GAME_START,
        {
            "game_id": game_id,
            "players": players
        }
    )

def create_game_state_message(pieces: List[PieceState], current_player: str, 
                             move_log: List[Dict[str, Any]], game_status: str,
                             winner: str = None, selected_pieces: Dict[str, str] = None) -> ProtocolMessage:
    return ProtocolMessage(
        MessageType.GAME_STATE,
        {
            "pieces": [piece.__dict__ for piece in pieces],
            "current_player": current_player,
            "move_log": move_log,
            "game_status": game_status,
            "winner": winner,
            "selected_pieces": selected_pieces or {}
        }
    )

def create_move_made_message(piece_id: str, from_cell: Tuple[int, int], 
                            to_cell: Tuple[int, int], timestamp: int) -> ProtocolMessage:
    return ProtocolMessage(
        MessageType.MOVE_MADE,
        {
            "piece_id": piece_id,
            "from_cell": from_cell,
            "to_cell": to_cell,
            "timestamp": timestamp
        }
    )
