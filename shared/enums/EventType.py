from enum import Enum

class EventType(Enum):
    GAME_START = "game_start"
    GAME_END = "game_end"
    PIECE_MOVED = "piece_moved"
    PIECE_CAPTURED = "piece_captured"
    INVALID_MOVE = "invalid_move"
