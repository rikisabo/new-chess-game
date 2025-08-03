import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Production configuration for Chess Game Server"""
    
    # Server settings
    HOST = os.getenv('HOST', '0.0.0.0')  # Railway needs 0.0.0.0
    PORT = int(os.getenv('PORT', 8000))  # Railway provides PORT
    
    # WebSocket settings
    WS_MAX_SIZE = int(os.getenv('WS_MAX_SIZE', 1024 * 1024))  # 1MB
    WS_TIMEOUT = int(os.getenv('WS_TIMEOUT', 30))  # 30 seconds
    
    # Game settings
    MAX_CONCURRENT_GAMES = int(os.getenv('MAX_CONCURRENT_GAMES', 100))
    GAME_TIMEOUT_MINUTES = int(os.getenv('GAME_TIMEOUT_MINUTES', 60))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Development vs Production
    IS_DEVELOPMENT = os.getenv('NODE_ENV', 'production') == 'development'
    
    @classmethod
    def get_websocket_url(cls):
        """Get the WebSocket URL for clients"""
        if cls.IS_DEVELOPMENT:
            return f"ws://{cls.HOST}:{cls.PORT}"
        else:
            # Production URL will be provided by hosting platform
            railway_url = os.getenv('RAILWAY_PUBLIC_DOMAIN')
            if railway_url:
                return f"wss://{railway_url}"
            return f"wss://chess-server.railway.app"
