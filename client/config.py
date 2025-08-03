"""
Client Configuration for Chess Game
Supports both local development and production deployment
"""

import os

class ClientConfig:
    """Configuration for chess game client"""
    
    # Server settings - can be overridden by environment variables
    DEFAULT_HOST = os.getenv('CHESS_SERVER_HOST', 'localhost')
    DEFAULT_PORT = int(os.getenv('CHESS_SERVER_PORT', 8000))
    
    # Production server URL (update after Railway deployment)
    PRODUCTION_URL = os.getenv('CHESS_SERVER_URL', 'wss://your-chess-server.railway.app')
    
    # Determine if we're in production mode
    USE_PRODUCTION = os.getenv('CHESS_PRODUCTION', 'false').lower() == 'true'
    
    @classmethod
    def get_server_url(cls):
        """Get the appropriate server URL"""
        if cls.USE_PRODUCTION:
            return cls.PRODUCTION_URL
        else:
            # Local development
            protocol = 'ws'  # WebSocket (not secure)
            return f"{protocol}://{cls.DEFAULT_HOST}:{cls.DEFAULT_PORT}"
    
    @classmethod
    def get_connection_info(cls):
        """Get connection information for display"""
        return {
            'url': cls.get_server_url(),
            'mode': 'Production' if cls.USE_PRODUCTION else 'Development',
            'host': cls.DEFAULT_HOST if not cls.USE_PRODUCTION else 'Railway Cloud',
            'port': cls.DEFAULT_PORT if not cls.USE_PRODUCTION else 443
        }
