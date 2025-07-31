import threading, logging
import keyboard  # pip install keyboard
from Command import Command

logger = logging.getLogger(__name__)


class KeyboardProcessor:
    """
    Maintains a cursor on an R×C grid and maps raw key names
    into logical actions via a user‑supplied keymap.
    """

    def __init__(self, rows: int, cols: int, keymap: dict[str, str], initial_pos: tuple[int, int] = (0, 0)):
        self.rows = rows
        self.cols = cols
        self.keymap = keymap
        self._cursor = list(initial_pos)  # Start at specified position
        self._lock = threading.Lock()

    def process_key(self, event):
        # Only care about key‑down events
        if event.event_type != "down":
            return None

        key = event.name
        
        # Translate Hebrew keys to English
        hebrew_to_english = {
            'ש': 'a',
            'ד': 's',
            'ג': 'd',
            '\'': 'w',
            'כ': 'f',
            'ע': 'g',
        }
        
        # Convert Hebrew key to English
        if key in hebrew_to_english:
            key = hebrew_to_english[key]
        
        action = self.keymap.get(key)
        logger.debug("Key '%s' → action '%s'", key, action)

        if action in ("up", "down", "left", "right"):
            with self._lock:
                r, c = self._cursor
                if action == "up":
                    r = max(0, r - 1)
                elif action == "down":
                    r = min(self.rows - 1, r + 1)
                elif action == "left":
                    c = max(0, c - 1)
                elif action == "right":
                    c = min(self.cols - 1, c + 1)
                self._cursor = [r, c]
                logger.debug("Cursor moved to (%s,%s)", r, c)

        return action

    def get_cursor(self) -> tuple[int, int]:
        with self._lock:
            return tuple(self._cursor)


class KeyboardProducer(threading.Thread):

    def __init__(self, game, queue, processor: KeyboardProcessor, player: int):
        super().__init__(daemon=True)
        self.game = game
        self.queue = queue
        self.proc = processor
        self.player = player
        self.selected_id = None
        self.selected_cell = None
        self.is_active = True  # Player activity flag
        # Define which color each player controls
        self.my_color = "W" if player == 1 else "B"

    def run(self):
        # Install our hook; it stays active until we call keyboard.unhook_all()
        keyboard.hook(self._on_event)
        keyboard.wait()

    def _find_piece_at(self, cell):
        for p in self.game.pieces:
            if p.current_cell() == cell:
                return p
        return None

    def _on_event(self, event):
        action = self.proc.process_key(event)
        # only interpret select/jump
        if action not in ("select", "jump"):
            return

        # General check if player is disabled (in networked game)
        if self.my_color == "DISABLED" or not self.is_active:
            print(f"🚫 Player{self.player} is DISABLED - ignoring input")
            return  # No response to input at all
            
        # Check if it's the player's turn (only in networked game) - temporarily disabled
        # if hasattr(self.game, 'networked_client'):
        #     if not self.game.networked_client.is_my_turn:
        #         print(f"[INFO] Not your turn, waiting for opponent...")
        #         return

        cell = self.proc.get_cursor()
        
        if action == "select":
            if self.selected_id is None:
                # first press = pick up the piece under the cursor
                piece = self._find_piece_at(cell)
                if not piece:
                    print(f"[WARN] No piece at {cell}")
                    return

                # Check if the piece belongs to this player's color
                piece_color = piece.id[1]  # W or B
                if piece_color != self.my_color:
                    print(f"🚫 Player{self.player} ({self.my_color}) cannot select {piece.id} (color {piece_color})")
                    return

                self.selected_id = piece.id
                self.selected_cell = cell
                
                # Update selected_id_X in Game
                if self.player == 1:
                    self.game.selected_id_1 = self.selected_id
                else:
                    self.game.selected_id_2 = self.selected_id
                    
                print(f"[KEY] Player{self.player} selected {piece.id} at {cell}")
                return

            elif cell == self.selected_cell:  # selected same place
                self.selected_id = None
                # Update in Game
                if self.player == 1:
                    self.game.selected_id_1 = None
                else:
                    self.game.selected_id_2 = None
                return

            else:
                cmd = Command(
                    self.game.game_time_ms(),
                    self.selected_id,
                    "move",
                    [self.selected_cell, cell]
                )
                # the command enter to the game queue
                self.queue.put(cmd)
                logger.info(f"Player{self.player} queued {cmd}")
                self.selected_id = None
                self.selected_cell = None
                
                # Update in Game
                if self.player == 1:
                    self.game.selected_id_1 = None
                else:
                    self.game.selected_id_2 = None

        elif action == "jump":
            if self.selected_id is None:
                print(f"[WARN] Player{self.player} tried to jump but no piece selected")
                return
            
            cmd = Command(
                self.game.game_time_ms(),
                self.selected_id,
                "jump",
                [self.selected_cell]  # Pass current cell to the command
            )
            self.queue.put(cmd)
            logger.info(f"Player{self.player} queued {cmd}")
            # We don't deselect the piece after a jump


    def stop(self):
        self.is_active = False
        print(f"[INFO] Player{self.player} keyboard input stopped")
