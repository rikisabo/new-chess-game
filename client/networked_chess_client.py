"""
Networked Chess Game Client
"""

import asyncio
import websockets
import json
import threading
import queue
import time
import logging
import sys
import os
from typing import Optional, Dict, Tuple

current_dir = os.path.dirname(__file__)
shared_dir = os.path.join(current_dir, '..', 'shared')
sys.path.insert(0, current_dir)
sys.path.insert(0, shared_dir)

from protocol import (
    ProtocolMessage, MessageType,
    create_player_join_message, create_player_move_message,
    DEFAULT_SERVER_PORT, DEFAULT_SERVER_HOST
)

from Game import Game
from GameFactory import create_game
from GraphicsFactory import ImgFactory
from Command import Command
from enums.EventType import EventType

logger = logging.getLogger(__name__)

class NetworkedChessClient:
    
    def __init__(self, player_name: str, preferred_color: str = None):
        self.player_name = player_name
        self.preferred_color = preferred_color
        self.player_id = None  # Will be set when connecting
        self.game_id = None  # ID של המשחק הנוכחי
        self.websocket = None
        self.connected = False
        
        self.game: Optional[Game] = None
        self.my_color = None
        self.opponent_color = None
        self.is_my_turn = False
        self.game_started = False
        self.processing_opponent_move = False
        
        self.server_message_queue = queue.Queue()
        self.move_queue = queue.Queue()
        
        self.game_thread = None
        self.running = False
        
    async def connect_to_server(self):
        try:
            # Generate a unique player ID
            import uuid
            self.player_id = str(uuid.uuid4())[:8]  # Short unique ID
            
            uri = f"ws://{DEFAULT_SERVER_HOST}:{DEFAULT_SERVER_PORT}/ws/{self.player_id}"
            logger.info(f"Connecting to {uri}...")
            
            self.websocket = await websockets.connect(uri)
            self.connected = True
            logger.info("Connected to server!")
            
            join_message = create_player_join_message(
                self.player_name, 
                self.preferred_color
            )
            await self.websocket.send(join_message.to_json())
            logger.info(f"Joined as {self.player_name} (preferred color: {self.preferred_color})")
            
            # No need for separate REST API calls - everything via WebSocket
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.connected = False
            
    async def listen_to_server(self):
        try:
            async for message in self.websocket:
                await self.handle_server_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection to server closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Error listening for messages: {e}")
            self.connected = False
            
    async def handle_server_message(self, message: str):
        try:
            logger.debug(f"Received raw message: {message}")
            protocol_msg = ProtocolMessage.from_json(message)
            logger.debug(f"Parsed protocol message: type={protocol_msg.type}, data={protocol_msg.data}")
            message_type = MessageType(protocol_msg.type)
            
            if message_type == MessageType.GAME_STATE:
                await self.handle_game_state(protocol_msg.data)
            elif message_type == MessageType.GAME_UPDATE:
                await self.handle_game_state(protocol_msg.data)  # Same handler as GAME_STATE
            elif message_type == MessageType.ERROR:
                await self.handle_error(protocol_msg.data)
            elif message_type == MessageType.PING:
                # Respond to ping with pong
                pong_msg = ProtocolMessage(MessageType.PONG, {})
                await self.websocket.send(pong_msg.to_json())
                logger.debug("Responded to ping with pong")
            elif message_type == MessageType.MOVE_MADE:
                self.handle_move_from_server(protocol_msg.data)
            elif protocol_msg.type == "MOVE_MADE":  # Keep for backward compatibility
                self.handle_move_from_server(protocol_msg.data)
            else:
                logger.info(f"Received message: {message_type.value}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            import traceback
            traceback.print_exc()
            
    async def handle_game_state(self, data: dict):
        game_status = data.get('status', 'unknown')  # Changed from 'game_status' to 'status'
        players = data.get('players', {})
        game_id = data.get('game_id', 'Unknown')  # קבל את ה-game_id
        
        # עדכן את ה-game_id הנוכחי
        if self.game_id != game_id:
            self.game_id = game_id
            print(f"\n🎯 משחק ID: {game_id}")
            print("=" * 30)
        
        logger.info(f"Game ID: {game_id}, Status: {game_status}, Players: {len(players)}, Game started: {self.game_started}")  # Debug log מפורט יותר
        
        # Show status to user
        if game_status == 'waiting':
            print(f"Waiting for another player... ({len(players)}/2 players)")
        elif game_status == 'active':
            print(f"Game is starting with {len(players)} players!")
        elif game_status == 'ready':
            print(f"Game is ready with {len(players)} players!")
        
        # Update player names in game if we have both players
        if self.game and len(players) >= 2:
            self.update_player_names(players)
        
        # Store player data for later use
        self.last_players_data = players
        
        if self.my_color is None:
            for player_id, player_info in players.items():
                if player_info.get('name') == self.player_name:
                    self.my_color = player_info.get('color')
                    self.opponent_color = 'black' if self.my_color == 'white' else 'white'
                    logger.info(f"My color: {self.my_color}")
                    print(f"You are playing as: {self.my_color}")
                    
                    if self.game:
                        self.update_player_colors()
                    break
        
        if (game_status == 'ongoing' or game_status == 'active') and not self.game_started and len(players) >= 2:
            logger.info(f"Starting game! Status: {game_status}, Players: {len(players)}, Game started: {self.game_started}")
            print(f"\n🎮 מתחיל משחק {self.game_id}")
            print("Starting chess game window...")
            self.game_started = True
            self.start_original_game()
        elif (game_status == 'ongoing' or game_status == 'active') and len(players) < 2:
            logger.warning(f"Game status is {game_status} but only {len(players)} players - not starting game")
            print(f"⚠️ Game status is {game_status} but only {len(players)} players connected")
            
        self.server_message_queue.put({
            'type': 'game_state',
            'data': data
        })
        
    def update_player_colors(self):
        if not self.my_color or not self.game:
            return
            
        logger.info(f"Updating player colors in original game. My color: {self.my_color}")
        
        if hasattr(self.game, 'kb_prod_1') and self.game.kb_prod_1:
            self.game.kb_prod_1.my_color = "W" if self.my_color == "white" else "B"
            print(f"Player 1 (local) color set to: {self.game.kb_prod_1.my_color}")
            logger.info(f"Player 1 (local) color set to: {self.game.kb_prod_1.my_color}")
        
        if hasattr(self.game, 'kb_prod_2') and self.game.kb_prod_2:
            self.game.kb_prod_2.my_color = "DISABLED"
            self.game.kb_prod_2.is_active = False
            print(f"Player 2 (remote) DISABLED for network play")
            logger.info(f"Player 2 (remote) disabled - each client controls only one color")

    def update_player_names(self, players: dict):
        """Update player names in the game interface"""
        if not self.game:
            return
            
        white_name = "Player 1"
        black_name = "Player 2"
        
        for player_id, player_info in players.items():
            player_name = player_info.get('name', 'Unknown')
            player_color = player_info.get('color', '').lower()
            
            if player_color == 'white':
                white_name = player_name
            elif player_color == 'black':
                black_name = player_name
        
        # Update the game with player names
        if hasattr(self.game, 'set_player_names'):
            self.game.set_player_names(white_name, black_name)
            logger.info(f"Updated player names: WHITE={white_name}, BLACK={black_name}")
            print(f"Players: {white_name} (White) vs {black_name} (Black)")
        
    def handle_move_from_server(self, move_data: dict):
        try:
            piece_id = move_data.get('piece_id')
            from_cell = move_data.get('from')
            to_cell = move_data.get('to')
            player_color = move_data.get('color')
            
            logger.info(f"Received move from server: {piece_id} {from_cell} -> {to_cell}")
            
            if player_color != self.my_color and self.game:
                logger.info(f"Applying opponent move: {piece_id}")
                
                if piece_id in self.game.piece_by_id:
                    piece = self.game.piece_by_id[piece_id]
                    
                    try:
                        self.processing_opponent_move = True
                        
                        from Command import Command
                        cmd = Command(
                            timestamp=int(time.time() * 1000),
                            piece_id=piece_id,
                            type="move",
                            params=[from_cell, to_cell]
                        )
                        
                        self.game._process_input(cmd)
                        
                    except Exception as e:
                        logger.error(f"Failed to apply opponent move locally: {e}")
                    finally:
                        self.processing_opponent_move = False
            
            from enums.EventType import EventType
            from message_bus import publish
            
            publish(EventType.PIECE_MOVED, {
                "piece_id": piece_id, 
                "target_cell": to_cell,
                "from_cell": from_cell,
                "player_color": player_color
            })
                
        except Exception as e:
            logger.error(f"Error handling move from server: {e}")
        
    async def handle_error(self, data: dict):
        error_code = data.get('error_code', 'UNKNOWN')
        message = data.get('message', 'Unknown error')
        logger.error(f"Server error [{error_code}]: {message}")
        
    async def send_move_to_server(self, piece_id: str, from_pos: tuple, to_pos: tuple):
        if not self.connected:
            logger.warning("Cannot send move: not connected")
            return
            
        move_message = create_player_move_message(
            piece_id, from_pos, to_pos, int(time.time() * 1000)
        )
        
        try:
            await self.websocket.send(move_message.to_json())
            logger.info(f"Sent move: {piece_id} from {from_pos} to {to_pos}")
        except Exception as e:
            logger.error(f"Failed to send move: {e}")
            
    def start_original_game(self):
        # בדיקה נוספת - לא להתחיל אם אין מספיק שחקנים
        if hasattr(self, 'last_players_data') and len(self.last_players_data) < 2:
            logger.warning(f"Not starting game - only {len(self.last_players_data)} players")
            print(f"⚠️ לא מתחיל משחק - יש רק {len(self.last_players_data)} שחקנים")
            return
            
        if self.game_thread is None:
            self.running = True
            self.game_thread = threading.Thread(target=self.run_original_game)
            self.game_thread.daemon = True
            self.game_thread.start()
            logger.info("Started original game thread")
            
    def run_original_game(self):
        # בדיקה נוספת בתחילת run_original_game
        if hasattr(self, 'last_players_data') and len(self.last_players_data) < 2:
            logger.warning(f"Aborting game creation - only {len(self.last_players_data)} players")
            return
            
        try:
            logger.info("Creating original game...")
            
            original_cwd = os.getcwd()
            
            project_root = os.path.abspath(os.path.join(current_dir, '..'))
            pieces_path = os.path.abspath(os.path.join(project_root, 'pieces'))
            logger.info(f"Using pieces path: {pieces_path}")
            
            # Check if pieces path exists
            if not os.path.exists(pieces_path):
                logger.error(f"Pieces path does not exist: {pieces_path}")
                return
                
            # Check if board.png exists
            board_png = os.path.join(pieces_path, 'board.png')
            if not os.path.exists(board_png):
                logger.error(f"Board image not found: {board_png}")
                return
                
            logger.info(f"Found board image: {board_png}")
            
            # העברת ה-game_id ליצירת המשחק
            current_game_id = self.game_id if self.game_id else "Unknown"
            self.game = create_game(pieces_path, ImgFactory(), current_game_id)
            
            self.setup_networked_game()
            
            # Update player names if we have them
            if hasattr(self, 'last_players_data'):
                self.update_player_names(self.last_players_data)
            
            logger.info("Networked game setup complete with sound and score integration")
            
            logger.info("Starting original game...")
            self.game.run()
            
        except Exception as e:
            logger.error(f"Error in original game: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                os.chdir(original_cwd)
            except:
                pass
            self.running = False
            
    def setup_networked_game(self):
        if not self.game:
            return
        
        if self.my_color:
            self.update_player_colors()
        
        self.game.networked_client = self
        
        original_process_all_inputs = self.game._process_all_inputs
        
        def networked_process_all_inputs():
            try:
                while not self.server_message_queue.empty():
                    msg = self.server_message_queue.get_nowait()
                    if msg['type'] == 'game_state':
                        logger.debug("Ignoring game_state update to prevent animation interruption")
                    elif msg['type'] == 'move_made':
                        self.handle_move_from_server(msg['data'])
            except queue.Empty:
                pass
                
            original_process_all_inputs()
                    
        self.game._process_all_inputs = networked_process_all_inputs
        
        original_process_input = self.game._process_input
        
        def networked_process_input(cmd):
            is_valid_move = True
            
            if hasattr(cmd, 'piece_id') and cmd.piece_id and self.my_color:
                piece_color_char = cmd.piece_id[1] if len(cmd.piece_id) > 1 else None
                expected_color_char = "W" if self.my_color == "white" else "B"
                
                if piece_color_char != expected_color_char:
                    logger.warning(f"Player tried to move opponent's piece: {cmd.piece_id} (expected {expected_color_char})")
                    is_valid_move = False
            
            result = original_process_input(cmd)
            
            if (is_valid_move and 
                not self.processing_opponent_move and 
                hasattr(cmd, 'piece_id') and 
                hasattr(cmd, 'params')):
                
                if len(cmd.params) >= 2:
                    from_pos = cmd.params[0] if len(cmd.params) > 0 else None
                    to_pos = cmd.params[1] if len(cmd.params) > 1 else None
                    
                    if from_pos and to_pos:
                        try:
                            asyncio.run_coroutine_threadsafe(
                                self.send_move_to_server(
                                    cmd.piece_id,
                                    from_pos,
                                    to_pos
                                ),
                                self.network_loop
                            )
                        except Exception as e:
                            logger.error(f"Failed to send move to server: {e}")
                
            return result
                
        self.game._process_input = networked_process_input
        
        logger.info("Networked game setup complete with sound and score integration")

async def main():
    logging.basicConfig(
        level=logging.INFO,  # Changed from DEBUG to INFO
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    player_name = input("Enter your name: ").strip() or "Player"
    preferred_color = input("Preferred color (white/black) [Enter for any]: ").strip().lower() or None
    
    if preferred_color and preferred_color not in ['white', 'black']:
        print(f"Invalid color '{preferred_color}'. Using any color.")
        preferred_color = None
        
    logger.info(f"Starting networked chess client for {player_name}")
    
    client = NetworkedChessClient(player_name, preferred_color)
    
    try:
        await client.connect_to_server()
        
        if not client.connected:
            logger.error("Failed to connect to server")
            return
            
        client.network_loop = asyncio.get_event_loop()
        
        await client.listen_to_server()
        
    except KeyboardInterrupt:
        logger.info("Client interrupted by user")
    except Exception as e:
        logger.error(f"Client error: {e}")
    finally:
        client.running = False
        if client.websocket:
            await client.websocket.close()
        logger.info("Client shutdown complete")

if __name__ == "__main__":
    print("Networked Chess Game Client")
    print("Make sure the server is running on localhost:8000")
    print("Press Ctrl+C to quit")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")
