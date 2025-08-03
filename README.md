# Chess Game Server - Production Ready

A professional WebSocket chess server supporting multiple concurrent games with real-time synchronization.

## 🎯 Features

- **Multi-Game Architecture**: Support unlimited concurrent 2-player games
- **WebSocket Communication**: Real-time game state synchronization
- **Game ID System**: Unique identification for each game session
- **Player Management**: Automatic matchmaking and game assignment
- **Production Ready**: Comprehensive logging and error handling

## 🚀 Quick Start

### Local Development
```bash
cd server
pip install -r requirements.txt
python improved_game_server.py
```

### Production Deployment
Deploy to Railway, Heroku, or any WebSocket-compatible platform.

## 📡 WebSocket API

### Connect
```
ws://localhost:8000
```

### Join Game
```json
{
  "type": "player_join",
  "data": {
    "player_name": "PlayerName",
    "preferred_color": "white"
  }
}
```

### Game State Response
```json
{
  "type": "game_state",
  "data": {
    "game_id": "game_123",
    "status": "active",
    "current_player": "white",
    "players": {...},
    "pieces": [...]
  }
}
```

## 🏗️ Architecture

```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   Chess Client  │◄──────────────►│  Game Server    │
└─────────────────┘                 └─────────────────┘
                                            │
                                    ┌───────▼────────┐
                                    │  Game Manager  │
                                    │  - game_1      │
                                    │  - game_2      │
                                    │  - game_3      │
                                    └────────────────┘
```

## 🧪 Testing

Comprehensive test suite covering:
- Single player scenarios
- Multi-game functionality  
- Game ID system
- Server stability

```bash
python run_all_tests.py
```

## 📊 Production Metrics

- **Concurrent Games**: Unlimited (memory limited)
- **Players per Game**: 2
- **WebSocket Protocol**: RFC 6455 compliant
- **Message Format**: JSON
- **Latency**: <50ms typical

## 🔧 Configuration

Environment variables:
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: localhost)
- `LOG_LEVEL`: Logging level (default: INFO)

## 🎮 Game Logic

- Standard chess rules implementation
- Real-time move validation
- Game state persistence
- Player reconnection support

---

**Professional Chess Game Server** - Built with Python, WebSockets, and modern architecture patterns.
