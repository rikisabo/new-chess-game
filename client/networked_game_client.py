"""
Chess Game Client - Using Original Graphics
Client that uses original game graphics and communicates with server via API
"""

import asyncio
import json
import logging
import time
import threading
import queue
from typing import Dict, List, Optional, Tuple
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

import requests
import websockets
import cv2
import numpy as np

# Import original client components
from Graphics import Graphics
from GraphicsFactory import ImgFactory
from img import Img
from KeyboardInput import KeyboardProcessor, KeyboardProducer
from scoreboard import ScoreBoard
from SoundManager import VoiceSFX
from ScreenOverlay import ScreenOverlay
from enums.EventType import EventType

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Client Configuration
SERVER_HOST = "localhost"
SERVER_PORT = 8000
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
WS_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}"

class NetworkedChessClient:
    def __init__(self):
        self.player_id = f"player_{int(time.time())}"
        self.player_name = f"Player_{self.player_id[-4:]}"
        self.game_id = None
        self.my_color = None
        
        # Game state from server
        self.game_state = None
        self.pieces_state = {}
        self.selected_piece_id = None
        
        # Original game components
        self.graphics = None
        self.board_img = None
        self.scoreboard = ScoreBoard()
        self.voice = VoiceSFX()
        self.screen_overlay = ScreenOverlay()
        
        # UI state
        self.cursor_pos = (0, 0)
        self.running = True
        self.board_rows = 8
        self.board_cols = 8
        
        # Networking
        self.websocket = None
        self.ws_task = None
        
        # Initialize graphics
        self._init_graphics()
        
        # Initialize keyboard input
        self.user_input_queue = queue.Queue()
        self.keyboard_processor = None
        self.keyboard_producer = None
        
    def _init_graphics(self):
        """Initialize graphics system"""
        try:
            img_factory = ImgFactory()
            self.graphics = Graphics(img_factory)
            
            # Create board image
            board_width = self.board_cols * 80  # 80 pixels per cell
            board_height = self.board_rows * 80
            
            self.board_img = Img(board_width, board_height, img_factory)
            
            # Initialize OpenCV window
            cv2.namedWindow("Chess Game", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Chess Game", 1200, 900)
            
            logger.info("Graphics initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize graphics: {e}")
            # Fallback to simple graphics
            self._init_simple_graphics()
    
    def _init_simple_graphics(self):
        """Fallback simple graphics"""
        cv2.namedWindow("Chess Game", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Chess Game", 800, 600)
        logger.info("Using simple graphics fallback")
    
    def _init_keyboard_input(self):
        """Initialize keyboard input"""
        try:
            keymap = {
                "up": "up", "down": "down", "left": "left", "right": "right",
                "enter": "select", "space": "select", "w": "up", "s": "down",
                "a": "left", "d": "right", "f": "select"
            }
            
            self.keyboard_processor = KeyboardProcessor(
                self.board_rows, self.board_cols, 
                keymap=keymap, 
                initial_pos=(7, 0) if self.my_color == "white" else (0, 0)
            )
            
            self.keyboard_producer = KeyboardProducer(
                self, self.user_input_queue, self.keyboard_processor, player=1
            )
            self.keyboard_producer.start()
            
            logger.info("Keyboard input initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize keyboard input: {e}")
    
    def create_game(self) -> bool:
        """Create a new game"""
        try:
            response = requests.post(f"{SERVER_URL}/game/create", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.game_id = data["game_id"]
                logger.info(f"Created game: {self.game_id}")
                return True
        except Exception as e:
            logger.error(f"Error creating game: {e}")
        return False
    
    def join_game(self, game_id: str = None) -> bool:
        """Join a game"""
        try:
            target_game_id = game_id or self.game_id
            if not target_game_id:
                return False
                
            join_data = {
                "player_id": self.player_id,
                "player_name": self.player_name
            }
            
            response = requests.post(f"{SERVER_URL}/game/{target_game_id}/join", json=join_data, timeout=5)
            
            if response.status_code == 200:
                self.game_id = target_game_id
                logger.info(f"Joined game: {self.game_id}")
                return True
            else:
                logger.warning(f"Failed to join game: {response.text}")
                
        except Exception as e:
            logger.error(f"Error joining game: {e}")
        return False
    
    def make_move(self, piece_id: str, to_row: int, to_col: int) -> bool:
        """Make a move via API call"""
        try:
            move_data = {
                "player_id": self.player_id,
                "piece_id": piece_id,
                "to_row": to_row,
                "to_col": to_col
            }
            
            response = requests.post(f"{SERVER_URL}/game/move", json=move_data, timeout=5)
            
            if response.status_code == 200:
                logger.info(f"Move successful: {piece_id} to ({to_row}, {to_col})")
                # Play move sound
                if hasattr(self.voice, 'play_move'):
                    self.voice.play_move()
                return True
            else:
                logger.warning(f"Move failed: {response.text}")
                
        except Exception as e:
            logger.error(f"Error making move: {e}")
        return False
    
    def get_game_state(self) -> bool:
        """Get current game state"""
        try:
            if not self.game_id:
                return False
                
            response = requests.get(f"{SERVER_URL}/game/{self.game_id}/state", timeout=5)
            
            if response.status_code == 200:
                self.game_state = response.json()
                self._update_local_state()
                return True
            else:
                logger.warning(f"Failed to get game state: {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting game state: {e}")
        return False
    
    def _update_local_state(self):
        """Update local state from server response"""
        if not self.game_state:
            return
            
        # Update pieces state
        self.pieces_state = self.game_state.get("pieces", {})
        
        # Update my color
        players = self.game_state.get("players", {})
        for player_id, player_data in players.items():
            if player_id == self.player_id:
                self.my_color = player_data["color"]
                break
        
        # Initialize keyboard input if not done yet
        if not self.keyboard_processor and self.my_color:
            self._init_keyboard_input()
    
    async def _websocket_handler(self):
        """Handle WebSocket connection for real-time updates"""
        try:
            uri = f"{WS_URL}/ws/{self.player_id}"
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                logger.info("WebSocket connected")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "game_update":
                            self.game_state = data.get("data")
                            self._update_local_state()
                        elif data.get("type") == "ping":
                            await websocket.send(json.dumps({"type": "pong"}))
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")
                        
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.websocket = None
    
    def start_websocket(self):
        """Start WebSocket connection in background"""
        def run_websocket():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._websocket_handler())
            
        self.ws_task = threading.Thread(target=run_websocket, daemon=True)
        self.ws_task.start()
    
    def _handle_keyboard_input(self):
        """Handle keyboard input for piece selection and movement"""
        if not self.keyboard_processor:
            return
            
        processed_count = 0
        while not self.user_input_queue.empty():
            try:
                cmd = self.user_input_queue.get_nowait()
                self._process_keyboard_command(cmd)
                processed_count += 1
            except queue.Empty:
                break
        
        if processed_count > 0:
            logger.debug(f"Processed {processed_count} keyboard commands")
    
    def _process_keyboard_command(self, cmd):
        """Process a keyboard command"""
        if cmd.command == "select":
            self._handle_select_command()
        elif cmd.command == "move":
            target_cell = cmd.params[1] if len(cmd.params) > 1 else None
            if target_cell:
                self._handle_move_command(target_cell)
    
    def _handle_select_command(self):
        """Handle select command at current cursor position"""
        if not self.keyboard_processor:
            return
            
        cursor_row, cursor_col = self.keyboard_processor.get_cursor()
        self.cursor_pos = (cursor_row, cursor_col)
        
        # Find piece at cursor position
        piece_at_cursor = None
        for piece_id, piece_data in self.pieces_state.items():
            pos = piece_data["position"]
            if pos["row"] == cursor_row and pos["col"] == cursor_col:
                piece_at_cursor = piece_data
                break
        
        if self.selected_piece_id is None:
            # Select piece if it belongs to current player
            if piece_at_cursor and piece_at_cursor["color"] == self.my_color:
                self.selected_piece_id = piece_at_cursor["id"]
                logger.info(f"Selected piece {self.selected_piece_id}")
        else:
            # Try to move selected piece or select new piece
            if piece_at_cursor and piece_at_cursor["color"] == self.my_color:
                # Select different piece
                self.selected_piece_id = piece_at_cursor["id"]
                logger.info(f"Selected piece {self.selected_piece_id}")
            else:
                # Move to cursor position
                self.make_move(self.selected_piece_id, cursor_row, cursor_col)
                self.selected_piece_id = None
    
    def _handle_move_command(self, target_cell):
        """Handle move command to target cell"""
        if self.selected_piece_id:
            target_row, target_col = target_cell
            self.make_move(self.selected_piece_id, target_row, target_col)
            self.selected_piece_id = None
    
    def _draw_board(self, image: np.ndarray):
        """Draw the chess board"""
        board_size = 640
        cell_size = board_size // 8
        offset_x = (image.shape[1] - board_size) // 2
        offset_y = (image.shape[0] - board_size) // 2
        
        # Draw checkerboard pattern
        for row in range(8):
            for col in range(8):
                x = offset_x + col * cell_size
                y = offset_y + row * cell_size
                
                color = (240, 217, 181) if (row + col) % 2 == 0 else (181, 136, 99)
                cv2.rectangle(image, (x, y), (x + cell_size, y + cell_size), color, -1)
                cv2.rectangle(image, (x, y), (x + cell_size, y + cell_size), (0, 0, 0), 1)
        
        return offset_x, offset_y, cell_size
    
    def _draw_pieces(self, image: np.ndarray, offset_x: int, offset_y: int, cell_size: int):
        """Draw chess pieces on the board"""
        piece_symbols = {
            "pawn": "♟", "rook": "♜", "knight": "♞", 
            "bishop": "♝", "queen": "♛", "king": "♚"
        }
        
        for piece_id, piece_data in self.pieces_state.items():
            if not piece_data.get("is_alive", True):
                continue
                
            pos = piece_data["position"]
            row, col = pos["row"], pos["col"]
            
            x = offset_x + col * cell_size + cell_size // 2
            y = offset_y + row * cell_size + cell_size // 2
            
            # Get piece symbol and color
            symbol = piece_symbols.get(piece_data["type"], "?")
            color = (255, 255, 255) if piece_data["color"] == "white" else (0, 0, 0)
            
            # Draw piece
            cv2.putText(image, symbol, (x - 20, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 2)
            
            # Highlight selected piece
            if piece_id == self.selected_piece_id:
                x1 = offset_x + col * cell_size
                y1 = offset_y + row * cell_size
                cv2.rectangle(image, (x1, y1), (x1 + cell_size, y1 + cell_size), (0, 255, 255), 3)
    
    def _draw_cursor(self, image: np.ndarray, offset_x: int, offset_y: int, cell_size: int):
        """Draw cursor position"""
        if self.keyboard_processor:
            cursor_row, cursor_col = self.keyboard_processor.get_cursor()
            x1 = offset_x + cursor_col * cell_size
            y1 = offset_y + cursor_row * cell_size
            cursor_color = (0, 255, 0) if self.my_color == "white" else (255, 0, 0)
            cv2.rectangle(image, (x1, y1), (x1 + cell_size, y1 + cell_size), cursor_color, 2)
    
    def _draw_ui(self, image: np.ndarray):
        """Draw UI information"""
        y_offset = 30
        
        # Game info
        if self.game_id:
            cv2.putText(image, f"Game: {self.game_id}", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y_offset += 30
        
        if self.my_color:
            cv2.putText(image, f"You: {self.my_color.upper()}", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y_offset += 30
        
        # Game status
        if self.game_state:
            status = self.game_state.get("status", "unknown")
            cv2.putText(image, f"Status: {status.upper()}", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y_offset += 30
            
            if status == "finished":
                winner = self.game_state.get("winner")
                if winner:
                    cv2.putText(image, f"Winner: {winner.upper()}", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Controls
        controls = [
            "Arrow keys: Move cursor",
            "Enter/Space: Select/Move",
            "R: Refresh game",
            "ESC: Quit"
        ]
        
        for i, control in enumerate(controls):
            cv2.putText(image, control, (20, image.shape[0] - 120 + i * 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def render(self):
        """Render the game"""
        # Create base image
        image = np.zeros((800, 1000, 3), dtype=np.uint8)
        
        # Draw board
        offset_x, offset_y, cell_size = self._draw_board(image)
        
        # Draw pieces
        self._draw_pieces(image, offset_x, offset_y, cell_size)
        
        # Draw cursor
        self._draw_cursor(image, offset_x, offset_y, cell_size)
        
        # Draw UI
        self._draw_ui(image)
        
        # Show image
        cv2.imshow("Chess Game", image)
    
    def run(self):
        """Main game loop"""
        logger.info(f"Starting Chess Client - Player: {self.player_name}")
        
        # Create and join game
        if not self.create_game():
            logger.error("Failed to create game")
            return
        
        if not self.join_game():
            logger.error("Failed to join game")
            return
        
        # Start WebSocket connection
        self.start_websocket()
        
        # Get initial state
        self.get_game_state()
        
        # Main loop
        while self.running:
            # Handle keyboard input
            self._handle_keyboard_input()
            
            # Render
            self.render()
            
            # Handle OpenCV events
            key = cv2.waitKey(30) & 0xFF
            
            if key == 27:  # ESC
                self.running = False
            elif key == ord('r'):  # R - refresh
                self.get_game_state()
            elif key == ord(' '):  # Space - deselect
                self.selected_piece_id = None
        
        # Cleanup
        if self.keyboard_producer:
            self.keyboard_producer.stop()
        
        cv2.destroyAllWindows()
        logger.info("Chess Client stopped")

def main():
    """Main entry point"""
    client = NetworkedChessClient()
    try:
        client.run()
    except KeyboardInterrupt:
        logger.info("Client interrupted by user")
    except Exception as e:
        logger.error(f"Client error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
