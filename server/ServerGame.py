"""
Game.py - Server Version (No GUI/Client Dependencies)
Pure game logic for server-side processing
"""

import queue, threading, time, math, logging
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from Board import Board
from Command import Command
from State import State
from Piece import Piece
from move_log import MoveLog
from message_bus import publish
from enums.EventType import EventType

logger = logging.getLogger(__name__)

class InvalidBoard(Exception):
    pass

class ServerGame:
    """Server-side game logic without GUI dependencies"""
    
    def __init__(self, pieces: List[Piece], board: Board, game_id: str = "Unknown"):
        self.pieces = pieces
        self.board = board
        self.game_id = game_id  # שמירת ה-game_id
        self.curr_board = None
        self.user_input_queue = queue.Queue()
        self.piece_by_id = {p.id: p for p in pieces}
        self.pos: Dict[Tuple[int, int], List[Piece]] = defaultdict(list)
        self.START_NS = time.time_ns()
        self._time_factor = 1  
        self.move_log = MoveLog()
        
        # Server doesn't need GUI components
        # No cv2.namedWindow, no scoreboard, no voice, no screen_overlay
        logger.info("Server game initialized without GUI components")
    
    def game_time_ms(self) -> int:
        """Return the game elapsed time in milliseconds."""
        return self._time_factor * (time.monotonic_ns() - self.START_NS) // 1_000_000

    def clone_board(self) -> Board:
        """Return a clone of the current board."""
        return self.board.clone()

    def _update_cell2piece_map(self):
        """Update dictionary mapping board cells to the pieces in them."""
        self.pos.clear()
        for p in self.pieces:
            self.pos[p.current_cell()].append(p)

    def process_move_command(self, piece_id: str, target_cell: Tuple[int, int]) -> bool:
        """Process a single move command (server-side)"""
        logger.info(f"Processing move command: {piece_id} to {target_cell}")
        
        piece = self.piece_by_id.get(piece_id)
        if not piece:
            logger.warning(f"Unknown piece id {piece_id}")
            return False
            
        # Create command
        cmd = Command(
            timestamp=self.game_time_ms(),
            piece_id=piece_id,
            type="move",
            params=["move", target_cell]
        )
        
        # Process the command
        try:
            piece.on_command(cmd, self.pos)
            logger.info(f"Processed command: {cmd} for piece {piece_id}")
            publish(EventType.PIECE_MOVED, {"piece_id": piece_id, "target_cell": target_cell})
            
            return True
        except Exception as e:
            logger.error(f"Error processing command for {piece_id}: {e}")
            return False

    def _process_input(self, cmd: Command) -> bool:
        """Process a single input command - compatibility method for server calls"""
        if not cmd.params or len(cmd.params) < 2:
            logger.warning(f"Invalid command parameters: {cmd.params}")
            return False
            
        target_cell = cmd.params[1]
        return self.process_move_command(cmd.piece_id, target_cell)

    def update_game_state(self) -> bool:
        """Update game state (physics, collisions) - server version"""
        try:
            now = self.game_time_ms()
            
            # Update all pieces
            for p in self.pieces:
                p.update(now)
            
            # Update position map
            self._update_cell2piece_map()
            
            # Resolve collisions
            self._resolve_collisions()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating game state: {e}")
            return False

    def _resolve_collisions(self):
        """Resolve collisions on board cells where more than one piece is present."""
        self._update_cell2piece_map()
        for cell, pieces_at_cell in self.pos.items():
            if len(pieces_at_cell) < 2:
                continue
            logger.debug("Collision detected at %s: %s", cell, [p.id for p in pieces_at_cell])
            winner = self._determine_collision_winner(pieces_at_cell)
            for p in pieces_at_cell:
                if p is winner:
                    continue
                if winner.id[1] == p.id[1]:
                    logger.debug("Skipping capture: %s and %s are the same color", winner.id, p.id)
                    continue
                if p.state.can_be_captured():
                    logger.info("CAPTURE: %s captures %s at %s", winner.id, p.id, cell)
                    publish(EventType.PIECE_CAPTURED, {"victim": p, "winner": winner})
                    self.pieces.remove(p)
                else:
                    logger.debug("Piece %s cannot be captured (state: %s)", p.id, p.state.name)

    def _determine_collision_winner(self, pieces_at_cell: List[Piece]) -> Piece:
        """Determine the winning piece in a collision based on movement and start time."""
        moving = [p for p in pieces_at_cell if p.state.name != 'idle']
        if moving:
            winner = max(moving, key=lambda p: p.state.physics.get_start_ms())
            logger.debug("Winner (moving): %s (state: %s)", winner.id, winner.state.name)
        else:
            winner = max(pieces_at_cell, key=lambda p: p.state.physics.get_start_ms())
            logger.debug("Winner (idle): %s (state: %s)", winner.id, winner.state.name)
        return winner

    def _validate_board(self, pieces: List[Piece]) -> bool:
        """Check that there is exactly one king of each color and no duplicate same-color occupancy."""
        has_white_king = has_black_king = False
        seen_cells: Dict[Tuple[int, int], str] = {}
        for p in pieces:
            cell = p.current_cell()
            if cell in seen_cells:
                if seen_cells[cell] == p.id[1]:
                    return False
            else:
                seen_cells[cell] = p.id[1]
            if p.id.startswith("KW"):
                has_white_king = True
            elif p.id.startswith("KB"):
                has_black_king = True
        return has_white_king and has_black_king

    def is_game_over(self) -> bool:
        """Determine if the game is over (less than two kings remain)."""
        kings = [p for p in self.pieces if p.id.startswith(('KW', 'KB'))]
        return len(kings) < 2

    def get_winner(self) -> Optional[str]:
        """Get the winner of the game"""
        if not self.is_game_over():
            return None
        
        white_king_alive = any(p for p in self.pieces if p.id.startswith('KW'))
        return "white" if white_king_alive else "black"

    def get_game_state_dict(self) -> dict:
        """Get current game state as dictionary for API"""
        pieces_state = {}
        for piece in self.pieces:
            row, col = piece.current_cell()
            pieces_state[piece.id] = {
                "id": piece.id,
                "type": self._get_piece_type(piece.id),
                "color": "white" if piece.id[1] == "W" else "black",
                "position": {"row": row, "col": col},
                "is_alive": True
            }
        
        return {
            "pieces": pieces_state,
            "board_size": [self.board.H_cells, self.board.W_cells],
            "game_over": self.is_game_over(),
            "winner": self.get_winner()
        }
    
    def _get_piece_type(self, piece_id: str) -> str:
        """Get piece type from piece ID"""
        type_map = {
            "P": "pawn",
            "R": "rook", 
            "N": "knight",
            "B": "bishop",
            "Q": "queen",
            "K": "king"
        }
        return type_map.get(piece_id[0], "unknown")

# Keep original Game class for backward compatibility but mark as deprecated
class Game(ServerGame):
    """Deprecated: Use ServerGame for server-side logic"""
    
    def __init__(self, pieces: List[Piece], board: Board):
        super().__init__(pieces, board)
        logger.warning("Using deprecated Game class. Use ServerGame for server-side logic.")
