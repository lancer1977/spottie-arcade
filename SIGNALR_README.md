# SignalR Hub for ANSI Arcade

This directory contains a SignalR-compatible WebSocket hub that serves the ANSI arcade games with web API key authentication.

## Overview

The SignalR hub allows you to stream the self-playing arcade games over WebSocket connections with authentication. It follows the pattern: `BASE_URL/<hub>?webkey=$WEBKEY`

## Features

- **Web API Key Authentication**: Secure access using API keys
- **Real-time Game Streaming**: Live ANSI game output over WebSocket
- **Multiple Game Support**: Snake, Pac-Man, and Dig Dug
- **Session Management**: Track active sessions and game statistics
- **Automatic Cleanup**: Graceful process and connection management

## Architecture

```
Client (WebSocket) → SignalR Hub → Game Process (Python)
     ↑                    ↑              ↑
  API Key Auth        WebSockets    ANSI Output
```

## Usage

### 1. Start the SignalR Hub

```bash
# Install dependencies
pip install -r requirements.txt

# Start the hub (generates random API key)
python3 signalr_hub.py

# Or use a specific API key via environment variable
export WEB_API_KEY="your-secret-key-123"
python3 signalr_hub.py
```

**Output:**
```
INFO:__main__:Generated API Key: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
INFO:__main__:SignalR Hub started on ws://0.0.0.0:8765
INFO:__main__:Available games: snake, pacman, digdug
INFO:__main__:Authentication required: API Key = a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

### 2. Connect with Client

```bash
# Connect to Snake game
python3 signalr_client_example.py ws://localhost:8765 your-api-key snake

# Connect to Pac-Man
python3 signalr_client_example.py ws://localhost:8765 your-api-key pacman

# Connect to Dig Dug
python3 signalr_client_example.py ws://localhost:8765 your-api-key digdug
```

## URL Pattern

The hub follows this URL pattern:

```
ws://<host>:<port>/<game_type>?webkey=<api_key>
```

**Examples:**
- `ws://localhost:8765/snake?webkey=abc123`
- `ws://localhost:8765/pacman?webkey=abc123`
- `ws://localhost:8765/digdug?webkey=abc123`

## Authentication

### Client Authentication Flow

1. **Connect** to WebSocket URL with game type
2. **Send Authentication Message**:
   ```json
   {
     "type": "authentication",
     "apiKey": "your-api-key"
   }
   ```
3. **Receive Response**:
   ```json
   {
     "type": "authentication_response",
     "status": "success|failed",
     "message": "Authentication successful|Invalid API key"
   }
   ```
4. **Start Streaming** if authentication succeeds

### API Key Management

- **Generate Random**: Hub generates a random 32-character hex key if `WEB_API_KEY` env var is not set
- **Environment Variable**: Set `WEB_API_KEY` to use a specific key
- **Security**: Store API keys securely and rotate regularly

## Message Protocol

### Client → Server Messages

#### Authentication
```json
{
  "type": "authentication",
  "apiKey": "your-api-key-here"
}
```

### Server → Client Messages

#### Authentication Response
```json
{
  "type": "authentication_response",
  "status": "success|failed",
  "message": "Authentication successful|Invalid API key"
}
```

#### Session Started
```json
{
  "type": "session_started",
  "sessionId": "a1b2c3d4e5f6g7h8",
  "gameType": "snake|pacman|digdug",
  "message": "Starting snake game session"
}
```

#### Game Frame
```json
{
  "type": "game_frame",
  "sessionId": "a1b2c3d4e5f6g7h8",
  "gameType": "snake|pacman|digdug",
  "frame": "ANSI game output here...",
  "frameCount": 1234,
  "score": 500,
  "timestamp": 1640995200.123
}
```

#### Error
```json
{
  "type": "error",
  "message": "Error description"
}
```

## Game Types

### Snake
- **Path**: `/snake`
- **Description**: Self-playing snake that navigates toward food
- **Features**: BFS pathfinding, flood-fill survival logic

### Pac-Man
- **Path**: `/pacman`
- **Description**: Pac-Man style game with ghosts and pellets
- **Features**: Maze navigation, ghost AI, power pellets

### Dig Dug
- **Path**: `/digdug`
- **Description**: Dig Dug style game with digging and enemy pumping
- **Features**: Line-of-sight pumping, rock physics

## Configuration

### Environment Variables

- `WEB_API_KEY`: Custom API key (optional, generates random if not set)
- `PORT`: Server port (default: 8765)

### Server Configuration

```python
# In signalr_hub.py
hub = SignalRHub(api_key="your-key", port=9000)
```

## Security Considerations

1. **API Keys**: Use strong, unique API keys
2. **HTTPS/WSS**: Use secure WebSocket (wss://) in production
3. **Rate Limiting**: Consider implementing rate limiting for connections
4. **Process Isolation**: Each game runs in a separate process
5. **Input Validation**: All client messages are validated

## Monitoring and Debugging

### Logs
The hub provides detailed logging:
- Connection events
- Authentication attempts
- Game process management
- Error conditions

### Statistics
Get hub statistics via the `get_stats()` method:
```python
stats = await hub.get_stats()
print(f"Active connections: {stats['activeConnections']}")
print(f"Active sessions: {stats['activeSessions']}")
```

## Production Deployment

### Docker Example
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python3", "signalr_hub.py"]
```

### Reverse Proxy (nginx)
```nginx
location /ws/ {
    proxy_pass http://localhost:8765;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check API key matches server key
   - Verify JSON format in authentication message

2. **Connection Timeout**
   - Check server is running
   - Verify network connectivity
   - Check firewall settings

3. **Game Not Starting**
   - Ensure game files exist in `src/` directory
   - Check Python path and permissions
   - Verify game commands in `game_commands` dict

4. **Poor Performance**
   - Monitor CPU usage of game processes
   - Adjust frame rate in client
   - Consider limiting concurrent connections

### Debug Mode
Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## API Reference

### SignalRHub Class

#### Methods
- `start_server()`: Start the WebSocket server
- `authenticate_connection(websocket)`: Authenticate client connection
- `get_stats()`: Get current hub statistics
- `broadcast_message(message)`: Broadcast to all clients

#### Properties
- `active_connections`: Set of active WebSocket connections
- `sessions`: Dictionary of active game sessions
- `game_processes`: Dictionary of running game processes

### GameSession Class

#### Properties
- `session_id`: Unique session identifier
- `game_type`: Type of game being played
- `start_time`: Session start timestamp
- `frame_count`: Number of frames streamed
- `score`: Current game score

## Examples

### Custom Client (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:8765/snake');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'authentication',
    apiKey: 'your-api-key'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'game_frame') {
    document.getElementById('game').innerText = data.frame;
  }
};
```

### Multiple Game Instances
```bash
# Terminal 1: Start hub
python3 signalr_hub.py

# Terminal 2: Snake client
python3 signalr_client_example.py ws://localhost:8765 mykey snake

# Terminal 3: Pac-Man client  
python3 signalr_client_example.py ws://localhost:8765 mykey pacman
```

This allows multiple clients to stream different games simultaneously.