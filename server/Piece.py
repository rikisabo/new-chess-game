from __future__ import annotations

from Board import Board
from Command import Command
from enums.EventType import EventType
from State import State
from message_bus import publish
from typing import Callable, Dict, List, Tuple


class Piece:
    def __init__(self, piece_id: str, init_state: State):
        self.id = piece_id
        self.state = init_state
        self._last_cell = self.current_cell()  # Store the last cell

    def on_command(self, cmd: Command, cell2piece: Dict[Tuple[int, int], List[Piece]]):
        """Process a command and potentially transition to a new state.
           After executing the command, if the piece actually moved - publish a movement event.
        """
        my_color = self.id[1]
        prev_cell = self.current_cell()
        self.state = self.state.on_command(cmd, cell2piece, my_color)
        new_cell = self.current_cell()
        if prev_cell != new_cell:
           ####
            self._last_cell = new_cell

    def reset(self, start_ms: int):
        self.state.reset(Command(start_ms, self.id, "idle", [self.current_cell()]))

    def update(self, now_ms: int):
        prev_cell = self.current_cell()
        self.state = self.state.update(now_ms)
        new_cell = self.current_cell()
        # if the piece move we publish an event
        if prev_cell != new_cell:
            publish(EventType.PIECE_MOVED, {
                "piece": self,
                "piece_id": self.id,  
                "from": prev_cell,
                "to": new_cell,
            })
        self._last_cell = new_cell

    def is_movement_blocker(self) -> bool:
        return self.state.physics.is_movement_blocker()

    def draw_on_board(self, board, now_ms: int):
        x, y = self.state.physics.get_pos_pix()
        sprite = self.state.graphics.get_img()
        sprite.draw_on(board.img, x, y)  # <-- paste the piece

    # ────────────────────────────────────────────────────────────────────
    # Abstraction helper – SINGLE public accessor so other modules don't have
    # to reach deep into `state → physics` implementation details.
    # Does **not** mutate internal state, so thread-safe without extra locks.
    def current_cell(self) -> tuple[int, int]:
        """Return the piece's board cell as (row, col)."""
        return self.state.physics.get_curr_cell()
