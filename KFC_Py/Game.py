import queue, threading, time, math, logging
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import cv2
import numpy as np
import pathlib

from Board import Board
from Command import Command
from State import State
from SoundManager import VoiceSFX
from scoreboard import ScoreBoard
from message_bus import publish
from Piece import Piece
from move_log import MoveLog
from KeyboardInput import KeyboardProcessor, KeyboardProducer
from ScreenOverlay import ScreenOverlay
from enums.EventType import EventType
logger = logging.getLogger(__name__)

class InvalidBoard(Exception):
    pass

class Game:
    def __init__(self, pieces: List[Piece], board: Board):
        self.pieces = pieces
        self.board = board
        self.curr_board = None
        self.user_input_queue = queue.Queue()
        self.piece_by_id = {p.id: p for p in pieces}
        self.pos: Dict[Tuple[int, int], List[Piece]] = defaultdict(list)
        self.START_NS = time.time_ns()
        self._time_factor = 1  
        self.kp1 = None
        self.kp2 = None
        self.kb_prod_1 = None
        self.kb_prod_2 = None
        self.selected_id_1: Optional[str] = None
        self.selected_id_2: Optional[str] = None  
        self.last_cursor1 = (0, 0)
        self.last_cursor2 = (0, 0)
        self.move_log = MoveLog()
        self.scoreboard = ScoreBoard()  
        self.voice = VoiceSFX()
        self.screen_overlay = ScreenOverlay()

        cv2.namedWindow("Game", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Game", 1920, 1080)
        
        bg_path = "../pieces/background.jpg"
        bg = cv2.imread(str(bg_path), cv2.IMREAD_COLOR)
        if bg is not None:
            self.background = cv2.resize(bg, (1920, 1080))
        else:
            logger.error(f"Background image not found at {bg_path}")
            self.background = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    def game_time_ms(self) -> int:
        """Return the game elapsed time in milliseconds."""
        return self._time_factor * (time.monotonic_ns() - self.START_NS) // 1_000_000

    def clone_board(self) -> Board:
        """Return a clone of the current board."""
        return self.board.clone()

    def start_user_input_thread(self):
        """Start separate threads to process player keyboard input."""
        p1_map = {
            "up": "up", "down": "down", "left": "left", "right": "right",
            "enter": "select", "space": "select", "+": "jump"
        }
        p2_map = {
            "w": "up", "s": "down", "a": "left", "d": "right",
            "f": "select", "space": "select", "g": "jump"
        }
        self.kp1 = KeyboardProcessor(self.board.H_cells, self.board.W_cells, keymap=p1_map, initial_pos=(7, 0))
        self.kp2 = KeyboardProcessor(self.board.H_cells, self.board.W_cells, keymap=p2_map, initial_pos=(0, 0))
        self.kb_prod_1 = KeyboardProducer(self, self.user_input_queue, self.kp1, player=1)
        self.kb_prod_2 = KeyboardProducer(self, self.user_input_queue, self.kp2, player=2)
        self.kb_prod_1.start()
        self.kb_prod_2.start()

    def _update_cell2piece_map(self):
        """Update dictionary mapping board cells to the pieces in them."""
        self.pos.clear()
        for p in self.pieces:
            self.pos[p.current_cell()].append(p)

    def _run_game_loop(self, num_iterations=None, is_with_graphics=True):
        iteration = 0
        while not self._is_win():
            now = self.game_time_ms()
            for p in self.pieces:
                p.update(now)
            self._update_cell2piece_map()
            self._process_all_inputs()
            if is_with_graphics:
                self._draw()
                self._show()
            self._resolve_collisions()
            if num_iterations is not None:
                iteration += 1
                if iteration >= num_iterations:
                    return

    def run(self, num_iterations=None, is_with_graphics=True):
        """Run the game, publishing start and end events."""
        publish(EventType.GAME_START, {})
        self.start_user_input_thread()
        start_ms = self.START_NS
        for p in self.pieces:
            p.reset(start_ms)
        self._run_game_loop(num_iterations, is_with_graphics)
        publish(EventType.GAME_END, {})
        self._announce_win()
        if self.kb_prod_1:
            self.kb_prod_1.stop()
            self.kb_prod_2.stop()

    def _draw(self):
        """Draw the current game board and overlays (key markers, move log)."""
        self.curr_board = self.clone_board()
        for p in self.pieces:
            p.draw_on_board(self.curr_board, now_ms=self.game_time_ms())
        if self.kp1 and self.kp2:
            for player, kp, last_attr in ((1, self.kp1, 'last_cursor1'), (2, self.kp2, 'last_cursor2')):
                r, c = kp.get_cursor()
                y1 = r * self.board.cell_H_pix
                x1 = c * self.board.cell_W_pix
                y2 = y1 + self.board.cell_H_pix - 1
                x2 = x1 + self.board.cell_W_pix - 1
                color = (0, 255, 0) if player == 1 else (255, 0, 0)
                self.curr_board.img.draw_rect(x1, y1, x2, y2, color)
                prev = getattr(self, last_attr)
                if prev != (r, c):
                    logger.debug("Marker P%s moved to (%s, %s)", player, r, c)
                    setattr(self, last_attr, (r, c))
            self.move_log.draw(self.curr_board.img.img)

    def _show(self):
        """Display the current board image on the game window."""
        win_w, win_h = 1920, 1080
        bg = self.background.copy()
        board_img = self.curr_board.img.img
        if board_img is not None and board_img.shape[2] == 4:
            board_img = cv2.cvtColor(board_img, cv2.COLOR_BGRA2BGR)
        board_h, board_w = board_img.shape[:2]
        x0 = (win_w - board_w) // 2
        y0 = (win_h - board_h) // 2
        bg[y0:y0+board_h, x0:x0+board_w] = board_img

        if hasattr(self, "scoreboard"):
            self.scoreboard.draw(bg, origin=(50, 30), player="WHITE")
            self.scoreboard.draw(bg, origin=(win_w - 300, 30), player="BLACK")
        self.move_log.draw(bg, origin=(50, 150), player="WHITE")
        self.move_log.draw(bg, origin=(win_w - 300, 150), player="BLACK")
        cv2.imshow("Game", bg)
        cv2.waitKey(1)

    def _process_all_inputs(self):
        """Process all commands from the input queue."""
        while not self.user_input_queue.empty():
            cmd: Command = self.user_input_queue.get()
            self._process_input(cmd)

    def _process_input(self, cmd: Command):
        """Process a single input command."""
        mover = self.piece_by_id.get(cmd.piece_id)
        if not mover:
            logger.debug("Unknown piece id %s", cmd.piece_id)
            return
        if len(cmd.params) < 2:
            logger.error("Invalid command parameters: %s", cmd.params)
            return
        target_cell = cmd.params[1]
        mover.on_command(cmd, self.pos)
        logger.info("Processed command: %s for piece %s", cmd, cmd.piece_id)
        publish(EventType.PIECE_MOVED, {"piece_id": cmd.piece_id, "target_cell": target_cell})

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

    def _is_win(self) -> bool:
        """Determine if the game is over (less than two kings remain)."""
        kings = [p for p in self.pieces if p.id.startswith(('KW', 'KB'))]
        return len(kings) < 2

    def _announce_win(self):
        """Announce the winning side."""
        win_text = 'Black wins!' if any(p.id.startswith('KB') for p in self.pieces) else 'White wins!'
        logger.info(win_text)
