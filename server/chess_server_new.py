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
original_dir = os.path.join(current_dir, '..', 'original')

sys.path.insert(0, shared_dir)
sys.path.insert(0, original_dir)

from protocol import (
    ProtocolMessage, MessageType, 
    create_game_state_message, create_error_message,
    PlayerJoinMessage, PlayerMoveMessage, PieceState,
    DEFAULT_SERVER_PORT, DEFAULT_SERVER_HOST, ErrorCodes
)

from game_server import Game
from GameFactory import create_game
from GraphicsFactory import MockImgFactory
from Command import Command

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChessGameServer:
    
    def __init__(self):
        self.clients = {}
        self.players = {}
        self.game = None
        self.game_started = False
        self.current_player = "white"
        
    def register_client(self, websocket, player_id: str):
        self.clients[websocket] = player_id
        logger.info(f"Registered client {player_id}")
        
    def unregister_client(self, websocket):
        if websocket in self.clients:
            player_id = self.clients[websocket]
            del self.clients[websocket]
            
            if player_id in self.players:
                self.players[player_id]['connected'] = False
                logger.info(f"Player {player_id} disconnected")
                
            logger.info(f"Unregistered client {player_id}")
            
    def get_pieces_state(self):
        if not self.game:
            return []
            
        pieces_state = []
        
        try:
            for piece in self.game.pieces:
                if hasattr(piece, 'piece_id') and hasattr(piece, 'state'):
                    position = [0, 0]
                    if hasattr(piece.state, 'physics'):
                        position = piece.state.physics.get_position()
                    
                    pieces_state.append(PieceState(
                        piece_id=piece.piece_id,
                        position=position,
                        selected=False
                    ))
                    
        except Exception as e:
            logger.error(f"Error getting pieces state: {e}")
            
        return pieces_state
        
    async def broadcast_game_state(self):
        if not self.clients:
            return
            
        try:
            pieces_state = self.get_pieces_state()
            
            game_status = "waiting"
            if self.game_started:
                connected_players = len([p for p in self.players.values() if p['connected']])
                if connected_players == 2:
                    game_status = "ongoing"
                else:
                    game_status = "paused"
            
            message = create_game_state_message(
                game_status=game_status,
                current_player=self.current_player,
                players=self.players,
                pieces=pieces_state
            )
            
            disconnected_clients = []
            for client in self.clients:
                try:
                    await client.send(message.to_json())
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.append(client)
                except Exception as e:
                    logger.error(f"Error sending game state to client: {e}")
                    disconnected_clients.append(client)
            
            for client in disconnected_clients:
                self.unregister_client(client)
                
        except Exception as e:
            logger.error(f"Error broadcasting game state: {e}")
            
    async def broadcast_move_made(self, piece_id: str, from_pos: tuple, to_pos: tuple, player_color: str):
        if not self.clients:
            return
            
        move_data = {
            "piece_id": piece_id,
            "from": from_pos,
            "to": to_pos,
            "color": player_color,
            "timestamp": datetime.now().isoformat()
        }
        
        message = ProtocolMessage("MOVE_MADE", move_data)
        
        disconnected_clients = []
        for client in self.clients:
            try:
                await client.send(message.to_json())
                logger.info(f"Sent move to client: {piece_id} {from_pos} -> {to_pos}")
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client)
            except Exception as e:
                logger.error(f"Error sending move to client: {e}")
                disconnected_clients.append(client)
        
        for client in disconnected_clients:
            self.unregister_client(client)
            
    async def send_to_client(self, websocket, message):
        try:
            await websocket.send(message.to_json())
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            
    async def handle_player_join(self, websocket, join_data):
        player_name = join_data.player_name
        preferred_color = join_data.preferred_color
        
        player_id = f"player_{len(self.players) + 1}"
        
        existing_colors = [p['color'] for p in self.players.values()]
        
        if preferred_color and preferred_color not in existing_colors:
            assigned_color = preferred_color
        else:
            if 'white' not in existing_colors:
                assigned_color = 'white'
            elif 'black' not in existing_colors:
                assigned_color = 'black'
            else:
                error_msg = create_error_message(ErrorCodes.GAME_FULL, "Game is full")
                await self.send_to_client(websocket, error_msg)
                await websocket.close()
                return
        
        self.players[player_id] = {
            'name': player_name,
            'color': assigned_color,
            'connected': True,
            'websocket': websocket
        }
        
        self.register_client(websocket, player_id)
        
        logger.info(f"Player {player_name} joined as {assigned_color} (ID: {player_id})")
        
        if len(self.players) == 2 and not self.game_started:
            await self.start_new_game()
        else:
            await self.broadcast_game_state()
            
    async def start_new_game(self):
        try:
            logger.info("Starting new game...")
            
            pieces_path = os.path.abspath(os.path.join(current_dir, '..', 'pieces'))
            logger.info(f"Using pieces path: {pieces_path}")
            
            self.game = create_game(pieces_path, MockImgFactory())
            self.game_started = True
            self.current_player = "white"
            
            await self.broadcast_game_state()
            
            logger.info("Game started successfully!")
            
        except Exception as e:
            logger.error(f"Error starting game: {e}")
            traceback.print_exc()
            
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
        player_id = self.clients.get(websocket)
        if not player_id:
            logger.warning("Move from unregistered client")
            return
            
        player_info = self.players.get(player_id)
        if not player_info:
            logger.warning(f"Move from unknown player {player_id}")
            return
            
        piece_id = move_data.piece_id
        from_pos = tuple(move_data.from_position)
        to_pos = tuple(move_data.to_position)
        player_color = player_info['color']
        
        logger.info(f"Processing move from {player_id} ({player_color}): {piece_id} {from_pos} -> {to_pos}")
        
        if not self.validate_move(piece_id, player_color):
            error_msg = create_error_message(ErrorCodes.INVALID_MOVE, "Invalid move - wrong piece color")
            await self.send_to_client(websocket, error_msg)
            return
        
        if not self.game:
            logger.warning("No game instance available")
            return
            
        try:
            cmd = Command(piece_id)
            cmd.params = [from_pos, to_pos]
            
            result = self.game._process_input(cmd)
            
            if result:
                await self.broadcast_move_made(piece_id, from_pos, to_pos, player_color)
                logger.info(f"Move processed successfully: {piece_id} {from_pos} -> {to_pos}")
            else:
                logger.warning(f"Move rejected by game engine: {piece_id} {from_pos} -> {to_pos}")
                error_msg = create_error_message(ErrorCodes.INVALID_MOVE, "Move rejected by game engine")
                await self.send_to_client(websocket, error_msg)
                
        except Exception as e:
            logger.error(f"Error processing move: {e}")
            traceback.print_exc()
            error_msg = create_error_message(ErrorCodes.SERVER_ERROR, f"Internal server error: {str(e)}")
            await self.send_to_client(websocket, error_msg)
            
    async def handle_client_message(self, websocket, message: str):
        try:
            protocol_msg = ProtocolMessage.from_json(message)
            message_type = MessageType(protocol_msg.type)
            
            if message_type == MessageType.PLAYER_JOIN:
                join_data = PlayerJoinMessage.from_dict(protocol_msg.data)
                await self.handle_player_join(websocket, join_data)
                
            elif message_type == MessageType.PLAYER_MOVE:
                move_data = PlayerMoveMessage.from_dict(protocol_msg.data)
                await self.handle_player_move(websocket, move_data)
                
            else:
                logger.warning(f"Unknown message type: {protocol_msg.type}")
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
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
    
    logger.info(f"Starting chess server on {DEFAULT_SERVER_HOST}:{DEFAULT_SERVER_PORT}")
    
    async with websockets.serve(server.handle_client, DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT):
        logger.info("Chess server started! Waiting for connections...")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
