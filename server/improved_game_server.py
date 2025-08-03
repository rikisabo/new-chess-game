"""
Improved Chess Game Server - WebSocket Server for Chess Game
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, Set, Optional, List
from datetime import datetime
import sys
import os
import traceback

current_dir = os.path.dirname(__file__)
shared_dir = os.path.join(current_dir, '..', 'shared')
kfc_dir = os.path.join(current_dir, '..', 'KFC_Py')

sys.path.insert(0, shared_dir)
sys.path.insert(0, kfc_dir)

from protocol import (
    ProtocolMessage, MessageType, 
    create_game_state_message, create_error_message,
    PlayerJoinMessage, PlayerMoveMessage, PieceState,
    DEFAULT_SERVER_PORT, DEFAULT_SERVER_HOST, ErrorCodes
)

from ServerGame import ServerGame
from GameFactory import create_game
from GraphicsFactory import MockImgFactory
from Command import Command

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChessGameServer:
    
    def __init__(self):
        self.clients = {}
        # שינוי: במקום משתנים יחידים, נשתמש במילון של משחקים
        self.games = {}  # game_id -> game_data
        self.waiting_players = []  # רשימת שחקנים הממתינים למשחק
        self.player_to_game = {}  # player_id -> game_id
        self.next_game_id = 1
       
    def register_client(self, websocket, player_id: str):
        """Add new client to the server."""
        self.clients[websocket] = player_id
        logger.info(f"Registered client {player_id}")
        
    def create_new_game(self) -> str:
        """יצירת משחק חדש"""
        game_id = f"game_{self.next_game_id}"
        self.next_game_id += 1
        
        # יצירת מבנה נתונים למשחק חדש
        self.games[game_id] = {
            'players': {},
            'game': None,
            'game_started': False,
            'current_player': 'white',
            'created_at': datetime.now()
        }
        
        logger.info(f"Created new game: {game_id}")
        return game_id
    
    def find_available_game(self) -> Optional[str]:
        """מצא משחק זמין (עם פחות מ-2 שחקנים)"""
        for game_id, game_data in self.games.items():
            if len(game_data['players']) < 2:
                return game_id
        return None
    
    def get_game_data(self, game_id: str) -> Optional[dict]:
        """קבל נתונים של משחק ספציפי"""
        return self.games.get(game_id)
    
    def add_player_to_game(self, game_id: str, player_id: str, player_data: dict):
        """הוסף שחקן למשחק ספציפי"""
        if game_id in self.games:
            self.games[game_id]['players'][player_id] = player_data
            self.player_to_game[player_id] = game_id
            logger.info(f"Added player {player_id} to game {game_id}")
    
    def remove_game_if_empty(self, game_id: str):
        """הסר משחק אם הוא ריק"""
        if game_id in self.games:
            game_data = self.games[game_id]
            if len(game_data['players']) == 0:
                del self.games[game_id]
                logger.info(f"Removed empty game: {game_id}")
                
    def get_player_game_id(self, player_id: str) -> Optional[str]:
        """קבל את ה-game_id של שחקן ספציפי"""
        return self.player_to_game.get(player_id)
        
    def unregister_client(self, websocket):
        """Remove client from the server."""
        if websocket is None:
            return
        if websocket in self.clients:
            player_id = self.clients[websocket]
            del self.clients[websocket]
            
            # מצא את המשחק של השחקן ונתק אותו
            game_id = self.get_player_game_id(player_id)
            if game_id and game_id in self.games:
                game_data = self.games[game_id]
                if player_id in game_data['players']:
                    game_data['players'][player_id]['connected'] = False
                    logger.info(f"Player {player_id} disconnected from game {game_id}")
                    
                    # אם אין שחקנים מחוברים, הסר את המשחק
                    connected_players = [p for p in game_data['players'].values() if p.get('connected', False)]
                    if len(connected_players) == 0:
                        self.remove_game_if_empty(game_id)
                
            # הסר מהמיפוי
            if player_id in self.player_to_game:
                del self.player_to_game[player_id]
                
            logger.info(f"Unregistered client {player_id}")
            
    def get_pieces_state(self):
        """Get the current state of all pieces in the game."""
        if not self.game:
            return []
            
        pieces_state = []
        
        try:
            for piece in self.game.pieces:
                if hasattr(piece, 'id'):
                    position = [0, 0]
                    if hasattr(piece, 'current_cell'):
                        row, col = piece.current_cell()
                        position = [row, col]
                    
                    # Create simple dict instead of complex object
                    piece_state = {
                        "id": piece.id,
                        "position": position,
                        "selected": False
                    }
                    pieces_state.append(piece_state)
                    
        except Exception as e:
            logger.error(f"Error getting pieces state: {e}")
            
        return pieces_state
            
    async def send_to_client(self, websocket, message):
        try:
            await websocket.send(message.to_json())
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            
    async def handle_player_join(self, websocket, join_data):
        """Handle a new player joining the game - תמיכה במשחקים מרובים"""
        player_name = join_data.get("player_name")
        preferred_color = join_data.get("preferred_color")
        
        # יצירת player_id ייחודי
        player_id = f"player_{len(self.clients) + 1}_{int(datetime.now().timestamp())}"
        
        # מצא משחק זמין או צור חדש
        game_id = self.find_available_game()
        if game_id is None:
            game_id = self.create_new_game()
        
        game_data = self.get_game_data(game_id)
        existing_colors = [p['color'] for p in game_data['players'].values()]
        
        # קבע צבע לשחקן
        if preferred_color and preferred_color not in existing_colors:
            assigned_color = preferred_color
        else:
            if 'white' not in existing_colors:
                assigned_color = 'white'
            elif 'black' not in existing_colors:
                assigned_color = 'black'
            else:
                # זה לא אמור לקרות כי מצאנו משחק זמין
                error_msg = create_error_message(ErrorCodes.GAME_FULL, "Game is full")
                await self.send_to_client(websocket, error_msg)
                await websocket.close()
                return
        
        # הוסף שחקן למשחק
        player_data = {
            'name': player_name,
            'color': assigned_color,
            'connected': True,
            'websocket': websocket
        }
        
        self.add_player_to_game(game_id, player_id, player_data)
        self.register_client(websocket, player_id)
        
        logger.info(f"Player {player_name} joined game {game_id} as {assigned_color} (ID: {player_id})")
        
        # אם יש 2 שחקנים במשחק ולא התחיל, התחל
        if len(game_data['players']) == 2 and not game_data['game_started']:
            await self.start_game(game_id)
        else:
            await self.broadcast_game_state_to_game(game_id)
            
    async def start_game(self, game_id: str):
        """התחל משחק ספציפי"""
        try:
            logger.info(f"Starting game {game_id}...")
            
            game_data = self.get_game_data(game_id)
            if not game_data:
                return
            
            pieces_path = os.path.abspath(os.path.join(current_dir, '..', 'pieces'))
            logger.info(f"Using pieces path: {pieces_path}")
            
            # צור משחק חדש עבור ה-game_id הזה
            game_data['game'] = create_game(pieces_path, MockImgFactory(), game_id)
            game_data['game_started'] = True
            game_data['current_player'] = "white"
            
            await self.broadcast_game_state_to_game(game_id)
            
            logger.info(f"Game {game_id} started successfully!")
            
        except Exception as e:
            logger.error(f"Error starting game {game_id}: {e}")
            traceback.print_exc()
    
    async def broadcast_game_state_to_game(self, game_id: str):
        """שדר מצב משחק לכל השחקנים במשחק ספציפי"""
        game_data = self.get_game_data(game_id)
        if not game_data:
            return
        
        try:
            pieces_state = []
            if game_data['game']:
                pieces_state = self.get_pieces_state_for_game(game_data['game'])
            
            # קבע סטטוס המשחק
            if len(game_data['players']) < 2:
                game_status = "waiting"
            elif game_data['game_started']:
                game_status = "active"
            else:
                game_status = "ready"
            
            # צור הודעת מצב משחק
            message_data = {
                "status": game_status,
                "current_player": game_data['current_player'],
                "players": {pid: {
                    'name': pdata.get('name', 'Unknown'),
                    'color': pdata.get('color', 'white'),
                    'connected': pdata.get('connected', False)
                } for pid, pdata in game_data['players'].items()},
                "pieces": pieces_state,
                "game_id": game_id  # הוסף את ה-game_id להודעה
            }
            
            # שלח לכל השחקנים במשחק
            for player_id, player_data in game_data['players'].items():
                websocket = player_data.get('websocket')
                if websocket and player_data.get('connected', False):
                    try:
                        message = ProtocolMessage(MessageType.GAME_STATE, message_data)
                        await websocket.send(message.to_json())
                    except Exception as e:
                        logger.error(f"Error sending game state to player {player_id}: {e}")
                        player_data['connected'] = False
            
        except Exception as e:
            logger.error(f"Error broadcasting game state for game {game_id}: {e}")
            traceback.print_exc()
    
    def get_pieces_state_for_game(self, game):
        """קבל מצב הכלים למשחק ספציפי"""
        if not game:
            return []
            
        pieces_state = []
        
        try:
            for piece in game.piece_by_id.values():
                piece_dict = {
                    'id': piece.id,
                    'position': piece.current_cell(),  # שימוש ב-current_cell() במקום position
                    'selected': False
                }
                pieces_state.append(piece_dict)
                
        except Exception as e:
            logger.error(f"Error getting pieces state: {e}")
            
        return pieces_state
            
    def validate_move(self, piece_id: str, player_color: str) -> bool:
        if not piece_id or len(piece_id) < 2:
            return False
            
        piece_color_char = piece_id[1]
        expected_char = "W" if player_color == "white" else "B"
        
        if piece_color_char != expected_char:
            logger.warning(f"Player {player_color} tried to move {piece_id} (wrong color)")
            return False
            
        return True
        
    async def handle_player_move(self, websocket, move_data):
        """Handle a player's move request - תמיכה במשחקים מרובים"""
        player_id = self.clients.get(websocket)
        if not player_id:
            logger.warning("Move from unregistered client")
            return
        
        # מצא איזה משחק השחקן שייך אליו
        game_id = self.player_to_game.get(player_id)
        if not game_id:
            logger.warning(f"Player {player_id} is not in any game")
            return
            
        game_data = self.get_game_data(game_id)
        if not game_data or not game_data.get('game'):
            logger.warning(f"No game instance available for game {game_id}")
            return
            
        player_info = game_data['players'].get(player_id)
        if not player_info:
            logger.warning(f"Move from unknown player {player_id} in game {game_id}")
            return
            
        piece_id = move_data.get("piece_id")
        from_pos = tuple(move_data.get("from_position", [0, 0]))
        to_pos = tuple(move_data.get("to_position", [0, 0]))
        player_color = player_info['color']
        
        logger.info(f"Processing move from {player_id} ({player_color}) in game {game_id}: {piece_id} {from_pos} -> {to_pos}")
        
        if not self.validate_move(piece_id, player_color):
            error_msg = create_error_message(ErrorCodes.INVALID_MOVE, "Invalid move - wrong piece color")
            await self.send_to_client(websocket, error_msg)
            return
            
        try:
            cmd = Command(piece_id)
            cmd.params = [from_pos, to_pos]
            
            result = game_data['game']._process_input(cmd)
            
            if result:
                await self.broadcast_move_made_to_game(game_id, piece_id, from_pos, to_pos, player_color)
                logger.info(f"Move processed successfully in game {game_id}: {piece_id} {from_pos} -> {to_pos}")
            else:
                logger.warning(f"Move rejected by game engine in game {game_id}: {piece_id} {from_pos} -> {to_pos}")
                error_msg = create_error_message(ErrorCodes.INVALID_MOVE, "Move rejected by game engine")
                await self.send_to_client(websocket, error_msg)
                
        except Exception as e:
            logger.error(f"Error processing move in game {game_id}: {e}")
            traceback.print_exc()
            error_msg = create_error_message(ErrorCodes.SERVER_ERROR, f"Internal server error: {str(e)}")
            await self.send_to_client(websocket, error_msg)
    
    async def broadcast_move_made_to_game(self, game_id: str, piece_id: str, from_pos: tuple, to_pos: tuple, player_color: str):
        """שדר תזוזה לכל השחקנים במשחק ספציפי"""
        game_data = self.get_game_data(game_id)
        if not game_data:
            return
            
        move_data = {
            "piece_id": piece_id,
            "from": from_pos,
            "to": to_pos,
            "color": player_color,
            "timestamp": datetime.now().isoformat(),
            "game_id": game_id
        }
        
        message = ProtocolMessage("MOVE_MADE", move_data)
        
        # שלח לכל השחקנים במשחק
        for player_id, player_data in game_data['players'].items():
            websocket = player_data.get('websocket')
            if websocket and player_data.get('connected', False):
                try:
                    await websocket.send(message.to_json())
                    logger.info(f"Sent move to player {player_id} in game {game_id}: {piece_id} {from_pos} -> {to_pos}")
                except Exception as e:
                    logger.error(f"Error sending move to player {player_id}: {e}")
                    player_data['connected'] = False
            
    async def handle_client_message(self, websocket, message: str):
        try:
            protocol_msg = ProtocolMessage.from_json(message)
            message_type = MessageType(protocol_msg.type)
            
            if message_type == MessageType.PLAYER_JOIN:
                await self.handle_player_join(websocket, protocol_msg.data)
                
            elif message_type == MessageType.PLAYER_MOVE:
                await self.handle_player_move(websocket, protocol_msg.data)
                
            else:
                logger.warning(f"Unknown message type: {protocol_msg.type}")
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            import traceback
            traceback.print_exc()
            error_msg = create_error_message(ErrorCodes.INVALID_MESSAGE, "Invalid message format")
            await self.send_to_client(websocket, error_msg)
            
    async def handle_client(self, websocket):
        logger.info(f"New client connected from {websocket.remote_address}")
        
        try:
            async for message in websocket:
                await self.handle_client_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {websocket.remote_address} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {websocket.remote_address}: {e}")
        finally:
            self.unregister_client(websocket)

async def run_server():
    server = ChessGameServer()
    
    # Railway compatibility - use environment variables
    host = os.getenv('HOST', '0.0.0.0')  # Railway requires 0.0.0.0
    port = int(os.getenv('PORT', 8000))  # Railway provides PORT
    
    logger.info(f"Starting chess server on {host}:{port}")
    
    async with websockets.serve(server.handle_client, host, port):
        logger.info("Chess server started! Waiting for connections...")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
