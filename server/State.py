from __future__ import annotations
from ast import List, Tuple
from Command import Command
from enums.EventType import EventType
from message_bus import publish  
from Moves import Moves
# from Graphics import Graphics  # Not needed for server
from Physics import BasePhysics
from typing import Dict, Callable, Optional, TYPE_CHECKING
import time, logging

if TYPE_CHECKING:
    from Piece import Piece

logger = logging.getLogger(__name__)

class State:
    def __init__(self, moves: Optional[Moves], graphics: Optional[object], physics: BasePhysics):
        self.moves: Optional[Moves] = moves
        self.graphics, self.physics = graphics, physics
        self.transitions: Dict[str, State] = {}
        self.name = None

    def __repr__(self):
        return f"State({self.name})"

    def set_transition(self, event: str, target: "State"):
        self.transitions[event] = target

    def reset(self, cmd: Command):
        self.graphics.reset(cmd)
        self.physics.reset(cmd)

    def on_command(self, cmd: Command, cell2piece: Dict[Tuple[int, int], List[Piece]], my_color: str = "X"):
        """Process a command and potentially transition to a new state."""
        logger.debug(f"State.on_command: {cmd.type} for {self.name}")
        
        nxt = self.transitions.get(cmd.type)

        if not nxt:
            logger.debug(f"No transition for command type: {cmd.type}")
            return self

        if cmd.type == "move":
            if self.moves is None or len(cmd.params) < 2:
                logger.debug(f"Invalid move command: params={cmd.params} moves={self.moves}")
                return self

            src_cell = cmd.params[0]
            dst_cell = cmd.params[1]
            
            # Use the current cell position instead of the provided src_cell
            current_cell = self.physics.get_curr_cell()
            logger.debug(f"Move command: from {current_cell} to {dst_cell}")
            
            # Check if move is valid from current position
            if not self.moves.is_valid(current_cell, dst_cell, cell2piece, self.physics.is_need_clear_path(), my_color):
                logger.debug(f"Invalid move: {current_cell} → {dst_cell}")
                logger.debug(f"Move validation failed for piece color: {my_color}")
                publish(EventType.INVALID_MOVE, {
                    "from": current_cell,
                    "to": dst_cell,
                    "color": my_color,
                })
                return self
        elif cmd.type == "jump":
            # For jump, we just transition to the next state without validation here
            pass

        logger.debug("[TRANSITION] %s: %s → %s", cmd.type, self, nxt)

        nxt.reset(cmd)
        return nxt

    def update(self, now_ms: int) -> State:
        internal = self.physics.update(now_ms)
        if internal:
            logger.debug(f"[DBG] internal: {internal.type}")
            return self.on_command(internal, None)
        self.graphics.update(now_ms)
        return self

    def can_be_captured(self) -> bool:
        return self.physics.can_be_captured()

    def can_capture(self) -> bool:
        return self.physics.can_capture()
