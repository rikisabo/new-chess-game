"""
Standalone Chess Game Client - Independent client with REST API calls
Completely independent client with no external dependencies from KFC_Py
"""

import asyncio
import json
import logging
import time
import threading
import queue
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import requests
import websockets
import cv2
import numpy as np
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Client Configuration
SERVER_HOST = "localhost"
SERVER_PORT = 8000
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
WS_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}"

# Game Constants
BOARD_SIZE = 8
CELL_SIZE = 80
BOARD_WIDTH = BOARD_SIZE * CELL_SIZE
BOARD_HEIGHT = BOARD_SIZE * CELL_SIZE
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_BROWN = (240, 217, 181)
DARK_BROWN = (181, 136, 99)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

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

@dataclass
class Position:
    row: int
    col: int

@dataclass
class Piece:
    id: str
    piece_type: str
    color: str
    position: Position
    is_alive: bool = True
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data["id"],
            piece_type=data["type"],
            color=data["color"],
            position=Position(data["position"]["row"], data["position"]["col"]),
            is_alive=data.get("is_alive", True)
        )

@dataclass
class Player:
    id: str
    name: str
    color: str
    is_connected: bool = True
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data["id"],
            name=data["name"],
            color=data["color"],
            is_connected=data.get("is_connected", True)
        )

class GameClient:
    def __init__(self):
        self.player_id = f"player_{int(time.time())}"
        self.player_name = f"Player_{self.player_id[-4:]}"
        self.game_id = None
        self.my_color = None
        self.game_state = None
        self.pieces: Dict[str, Piece] = {}
        self.players: Dict[str, Player] = {}
        
        # UI State
        self.selected_piece = None
        self.cursor_pos = (0, 0)
        self.board_image = None
        self.running = True
        
        # Networking
        self.websocket = None
        self.ws_task = None
        self.message_queue = queue.Queue()
        
        # Initialize OpenCV
        cv2.namedWindow("Chess Game", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Chess Game", WINDOW_WIDTH, WINDOW_HEIGHT)
        cv2.setMouseCallback("Chess Game", self._mouse_callback)
        
        self._init_board_image()
        
    def _init_board_image(self):
        """Initialize the chess board image"""
        self.board_image = np.zeros((WINDOW_HEIGHT, WINDOW_WIDTH, 3), dtype=np.uint8)
        
        # Draw chessboard
        board_offset_x = (WINDOW_WIDTH - BOARD_WIDTH) // 2
        board_offset_y = (WINDOW_HEIGHT - BOARD_HEIGHT) // 2
        
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x = board_offset_x + col * CELL_SIZE
                y = board_offset_y + row * CELL_SIZE
                
                color = LIGHT_BROWN if (row + col) % 2 == 0 else DARK_BROWN
                cv2.rectangle(self.board_image, (x, y), (x + CELL_SIZE, y + CELL_SIZE), color, -1)
                cv2.rectangle(self.board_image, (x, y), (x + CELL_SIZE, y + CELL_SIZE), BLACK, 2)
    
    def _mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # Convert screen coordinates to board coordinates
            board_offset_x = (WINDOW_WIDTH - BOARD_WIDTH) // 2
            board_offset_y = (WINDOW_HEIGHT - BOARD_HEIGHT) // 2
            
            if (board_offset_x <= x < board_offset_x + BOARD_WIDTH and
                board_offset_y <= y < board_offset_y + BOARD_HEIGHT):
                
                col = (x - board_offset_x) // CELL_SIZE
                row = (y - board_offset_y) // CELL_SIZE
                
                self.cursor_pos = (row, col)
                self._handle_cell_click(row, col)
    
    def _handle_cell_click(self, row: int, col: int):
        """Handle clicking on a board cell"""
        # Find piece at clicked position
        clicked_piece = None
        for piece in self.pieces.values():
            if piece.position.row == row and piece.position.col == col and piece.is_alive:
                clicked_piece = piece
                break
        
        if self.selected_piece is None:
            # Select piece if it belongs to current player
            if clicked_piece and clicked_piece.color == self.my_color:
                self.selected_piece = clicked_piece
                logger.info(f"Selected piece {clicked_piece.id} at ({row}, {col})")
        else:
            # Move selected piece or select new piece
            if clicked_piece and clicked_piece.color == self.my_color:
                # Select new piece
                self.selected_piece = clicked_piece
                logger.info(f"Selected piece {clicked_piece.id} at ({row}, {col})")
            else:
                # Try to move to clicked position
                self._make_move(self.selected_piece.id, row, col)
                self.selected_piece = None
    
    def _make_move(self, piece_id: str, to_row: int, to_col: int):
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
            else:
                logger.warning(f"Move failed: {response.text}")
                
        except Exception as e:
            logger.error(f"Error making move: {e}")
    
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
            
        # Update pieces
        self.pieces.clear()
        for piece_id, piece_data in self.game_state.get("pieces", {}).items():
            self.pieces[piece_id] = Piece.from_dict(piece_data)
        
        # Update players
        self.players.clear()
        for player_id, player_data in self.game_state.get("players", {}).items():
            player = Player.from_dict(player_data)
            self.players[player_id] = player
            
            # Set my color
            if player_id == self.player_id:
                self.my_color = player.color
    
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
    
    def _draw_pieces(self, image: np.ndarray):
        """Draw pieces on the board"""
        board_offset_x = (WINDOW_WIDTH - BOARD_WIDTH) // 2
        board_offset_y = (WINDOW_HEIGHT - BOARD_HEIGHT) // 2
        
        for piece in self.pieces.values():
            if not piece.is_alive:
                continue
                
            row, col = piece.position.row, piece.position.col
            x = board_offset_x + col * CELL_SIZE + CELL_SIZE // 2
            y = board_offset_y + row * CELL_SIZE + CELL_SIZE // 2
            
            # Choose color based on piece color
            piece_color = WHITE if piece.color == "white" else BLACK
            
            # Draw piece symbol
            symbol = self._get_piece_symbol(piece.piece_type)
            cv2.putText(image, symbol, (x - 20, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 1, piece_color, 2)
            
            # Highlight selected piece
            if self.selected_piece and self.selected_piece.id == piece.id:
                cv2.rectangle(image, 
                            (board_offset_x + col * CELL_SIZE, board_offset_y + row * CELL_SIZE),
                            (board_offset_x + (col + 1) * CELL_SIZE, board_offset_y + (row + 1) * CELL_SIZE),
                            YELLOW, 3)
    
    def _get_piece_symbol(self, piece_type: str) -> str:
        """Get symbol for piece type"""
        symbols = {
            "pawn": "P",
            "rook": "R",
            "knight": "N",
            "bishop": "B",
            "queen": "Q",
            "king": "K"
        }
        return symbols.get(piece_type, "?")
    
    def _draw_ui(self, image: np.ndarray):
        """Draw UI elements"""
        # Draw game info
        y_offset = 30
        
        if self.game_id:
            cv2.putText(image, f"Game: {self.game_id}", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2)
            y_offset += 30
        
        if self.my_color:
            cv2.putText(image, f"You are: {self.my_color.upper()}", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2)
            y_offset += 30
        
        # Draw players info
        for i, (player_id, player) in enumerate(self.players.items()):
            status = "Connected" if player.is_connected else "Disconnected"
            text = f"{player.name} ({player.color}) - {status}"
            color = GREEN if player.is_connected else RED
            cv2.putText(image, text, (20, y_offset + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Draw game status
        if self.game_state:
            status = self.game_state.get("status", "unknown")
            cv2.putText(image, f"Status: {status.upper()}", (20, WINDOW_HEIGHT - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2)
            
            if status == "finished":
                winner = self.game_state.get("winner")
                if winner:
                    cv2.putText(image, f"Winner: {winner.upper()}", (20, WINDOW_HEIGHT - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, GREEN, 2)
        
        # Draw instructions
        instructions = [
            "Click to select/move pieces",
            "ESC to quit",
            "SPACE to refresh state"
        ]
        
        for i, instruction in enumerate(instructions):
            cv2.putText(image, instruction, (WINDOW_WIDTH - 300, 30 + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)
    
    def render(self):
        """Render the game"""
        # Start with base board
        image = self.board_image.copy()
        
        # Draw pieces
        self._draw_pieces(image)
        
        # Draw UI
        self._draw_ui(image)
        
        # Show image
        cv2.imshow("Chess Game", image)
    
    def run(self):
        """Main game loop"""
        logger.info(f"Starting Chess Client - Player: {self.player_name}")
        
        # Try to create and join a game
        if not self.create_game():
            logger.error("Failed to create game")
            return
        
        if not self.join_game():
            logger.error("Failed to join game")
            return
        
        # Start WebSocket connection
        self.start_websocket()
        
        # Initial state fetch
        self.get_game_state()
        
        # Main loop
        while self.running:
            # Render
            self.render()
            
            # Handle keyboard input
            key = cv2.waitKey(30) & 0xFF
            
            if key == 27:  # ESC
                self.running = False
            elif key == ord(' '):  # Space - refresh state
                self.get_game_state()
            elif key == ord('r'):  # R - reset selection
                self.selected_piece = None
        
        cv2.destroyAllWindows()
        logger.info("Chess Client stopped")

def main():
    """Main entry point"""
    client = GameClient()
    try:
        client.run()
    except KeyboardInterrupt:
        logger.info("Client interrupted by user")
    except Exception as e:
        logger.error(f"Client error: {e}")

if __name__ == "__main__":
    main()
