/**
 * Professional Chess Game - WebSocket Client
 * Handles connection to chess server and message protocol
 */

class ChessWebSocketClient {
    constructor() {
        this.ws = null;
        this.gameId = null;
        this.playerColor = null;
        this.playerName = null;
        this.connectionStatus = 'disconnected';
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        
        this.eventHandlers = {
            'connection': [],
            'game_state': [],
            'move_response': [],
            'error': [],
            'chat': []
        };
    }

    // Event handling
    on(event, handler) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].push(handler);
        }
    }

    emit(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => handler(data));
        }
    }

    // Connection management
    async connect(serverUrl = null) {
        // Determine server URL
        const wsUrl = serverUrl || this.getServerUrl();
        
        try {
            console.log('Connecting to:', wsUrl);
            this.updateConnectionStatus('connecting');
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = (event) => {
                console.log('Connected to chess server');
                this.connectionStatus = 'connected';
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected');
                this.emit('connection', { status: 'connected' });
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(event.data);
            };

            this.ws.onclose = (event) => {
                console.log('Disconnected from server:', event.code, event.reason);
                this.connectionStatus = 'disconnected';
                this.updateConnectionStatus('disconnected');
                this.emit('connection', { status: 'disconnected', code: event.code, reason: event.reason });
                
                // Auto-reconnect
                if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.scheduleReconnect();
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.emit('error', { type: 'connection_error', error });
            };

        } catch (error) {
            console.error('Failed to connect:', error);
            this.updateConnectionStatus('error');
            this.emit('error', { type: 'connection_failed', error });
        }
    }

    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
        
        console.log(`Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            if (this.connectionStatus === 'disconnected') {
                this.connect();
            }
        }, delay);
    }

    disconnect() {
        if (this.ws) {
            this.ws.close(1000, 'User disconnect');
            this.ws = null;
        }
        this.connectionStatus = 'disconnected';
        this.updateConnectionStatus('disconnected');
    }

    // Message handling
    handleMessage(data) {
        try {
            const message = JSON.parse(data);
            console.log('Received message:', message);

            switch (message.type) {
                case 'game_state':
                    this.handleGameState(message.data);
                    break;
                case 'move_response':
                    this.handleMoveResponse(message.data);
                    break;
                case 'error':
                    this.handleError(message.data);
                    break;
                case 'chat':
                    this.handleChat(message.data);
                    break;
                default:
                    console.warn('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Failed to parse message:', error, data);
        }
    }

    handleGameState(data) {
        this.gameId = data.game_id;
        
        // Update player info if available
        if (data.players) {
            const playerKeys = Object.keys(data.players);
            for (const playerId of playerKeys) {
                const player = data.players[playerId];
                if (player.name === this.playerName) {
                    this.playerColor = player.color;
                    break;
                }
            }
        }

        this.emit('game_state', data);
    }

    handleMoveResponse(data) {
        this.emit('move_response', data);
    }

    handleError(data) {
        console.error('Server error:', data);
        this.emit('error', { type: 'server_error', data });
    }

    handleChat(data) {
        this.emit('chat', data);
    }

    // Game actions
    joinGame(playerName, preferredColor = null) {
        if (!this.isConnected()) {
            throw new Error('Not connected to server');
        }

        this.playerName = playerName;
        
        const message = {
            type: 'player_join',
            data: {
                player_name: playerName,
                preferred_color: preferredColor
            }
        };

        this.sendMessage(message);
    }

    makeMove(from, to, promotion = null) {
        if (!this.isConnected()) {
            throw new Error('Not connected to server');
        }

        const message = {
            type: 'player_move',
            data: {
                from: from,
                to: to,
                promotion: promotion,
                game_id: this.gameId
            }
        };

        this.sendMessage(message);
    }

    sendChatMessage(text) {
        if (!this.isConnected()) {
            throw new Error('Not connected to server');
        }

        const message = {
            type: 'chat',
            data: {
                message: text,
                game_id: this.gameId
            }
        };

        this.sendMessage(message);
    }

    resign() {
        if (!this.isConnected()) {
            throw new Error('Not connected to server');
        }

        const message = {
            type: 'resign',
            data: {
                game_id: this.gameId
            }
        };

        this.sendMessage(message);
    }

    offerDraw() {
        if (!this.isConnected()) {
            throw new Error('Not connected to server');
        }

        const message = {
            type: 'draw_offer',
            data: {
                game_id: this.gameId
            }
        };

        this.sendMessage(message);
    }

    // Utility methods
    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
            console.log('Sent message:', message);
        } else {
            console.error('Cannot send message: WebSocket not open');
            throw new Error('WebSocket connection not available');
        }
    }

    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }

    getServerUrl() {
        // Try to determine server URL automatically
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const hostname = window.location.hostname;
        
        // Production URLs (update these for your deployment)
        if (hostname.includes('netlify.app') || hostname.includes('vercel.app')) {
            return 'wss://chess-server.railway.app'; // Your production server
        }
        
        // Development
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'ws://localhost:8000';
        }
        
        // Default fallback
        return 'ws://localhost:8000';
    }

    updateConnectionStatus(status) {
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        if (!statusIndicator || !statusText) return;

        statusIndicator.className = `status-indicator ${status}`;
        
        switch (status) {
            case 'connected':
                statusText.textContent = 'מחובר';
                break;
            case 'connecting':
                statusText.textContent = 'מתחבר...';
                break;
            case 'disconnected':
                statusText.textContent = 'מנותק';
                break;
            case 'error':
                statusText.textContent = 'שגיאת חיבור';
                break;
            default:
                statusText.textContent = status;
        }
    }

    // Connection info
    getConnectionInfo() {
        return {
            status: this.connectionStatus,
            gameId: this.gameId,
            playerName: this.playerName,
            playerColor: this.playerColor,
            reconnectAttempts: this.reconnectAttempts
        };
    }
}

// Export for use in other modules
window.ChessWebSocketClient = ChessWebSocketClient;
