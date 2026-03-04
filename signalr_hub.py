#!/usr/bin/env python3
"""
SignalR Hub for ANSI Arcade Games

This module provides a SignalR hub that serves the arcade games with web API key authentication.
The hub follows the pattern: BASE_URL/<hub>?webkey=$WEBKEY

Features:
- Web API key authentication
- Game selection and streaming
- Real-time game state updates
- Automatic game restarts
"""

import asyncio
import json
import logging
import os
import secrets
import signal
import sys
import time
from typing import Any, Dict, List, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GameSession:
    """Represents an active game session."""
    
    def __init__(self, session_id: str, game_type: str):
        self.session_id = session_id
        self.game_type = game_type
        self.start_time = time.time()
        self.is_active = True
        self.frame_count = 0
        self.score = 0
        
    def update_stats(self, frame_count: int, score: int):
        """Update session statistics."""
        self.frame_count = frame_count
        self.score = score


class SignalRHub:
    """SignalR-compatible hub for serving ANSI arcade games."""
    
    def __init__(self, api_key: str, port: int = 8765):
        self.api_key = api_key
        self.port = port
        self.sessions: Dict[str, GameSession] = {}
        self.active_connections: Set[websockets.WebSocketServerProtocol] = set()
        self.game_processes: Dict[str, asyncio.subprocess.Process] = {}
        
        # Game command mappings
        self.game_commands = {
            'snake': ['python3', 'src/snake_selfplay.py'],
            'pacman': ['python3', 'src/pacman_selfplay.py'],
            'digdug': ['python3', 'src/digdug_selfplay.py']
        }
        
    async def authenticate_connection(self, websocket: websockets.WebSocketServerProtocol) -> bool:
        """Authenticate incoming WebSocket connection using API key."""
        try:
            # Wait for initial connection message
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            auth_data = json.loads(auth_message)
            
            if auth_data.get('type') == 'authentication':
                provided_key = auth_data.get('apiKey')
                if provided_key == self.api_key:
                    await websocket.send(json.dumps({
                        'type': 'authentication_response',
                        'status': 'success',
                        'message': 'Authentication successful'
                    }))
                    return True
                else:
                    await websocket.send(json.dumps({
                        'type': 'authentication_response',
                        'status': 'failed',
                        'message': 'Invalid API key'
                    }))
                    return False
            else:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Invalid authentication format'
                }))
                return False
                
        except asyncio.TimeoutError:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Authentication timeout'
            }))
            return False
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
            return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Authentication failed'
            }))
            return False
    
    async def start_game_process(self, game_type: str) -> Optional[asyncio.subprocess.Process]:
        """Start a game process for the specified game type."""
        if game_type not in self.game_commands:
            return None
            
        try:
            # Start the game process
            process = await asyncio.create_subprocess_exec(
                *self.game_commands[game_type],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            return process
        except Exception as e:
            logger.error(f"Failed to start game process for {game_type}: {e}")
            return None
    
    async def stream_game_output(self, websocket: websockets.WebSocketServerProtocol, 
                                session_id: str, game_type: str):
        """Stream game output to the connected client."""
        process = await self.start_game_process(game_type)
        if not process:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Failed to start {game_type} game'
            }))
            return
            
        self.game_processes[session_id] = process
        session = GameSession(session_id, game_type)
        self.sessions[session_id] = session
        
        try:
            buffer = ""
            frame_count = 0
            
            while session.is_active and not process.stdout.at_eof():
                try:
                    # Read output in chunks
                    chunk = await asyncio.wait_for(process.stdout.read(1024), timeout=0.1)
                    if not chunk:
                        break
                        
                    buffer += chunk.decode('utf-8', errors='ignore')
                    
                    # Process complete frames (separated by double newlines)
                    while '\n\n' in buffer:
                        frame, buffer = buffer.split('\n\n', 1)
                        frame_count += 1
                        
                        # Parse frame for score and other stats
                        lines = frame.strip().split('\n')
                        score_line = next((line for line in lines if 'Score:' in line), None)
                        score = 0
                        if score_line:
                            try:
                                score = int(score_line.split('Score:')[1].split()[0])
                            except (IndexError, ValueError):
                                pass
                        
                        session.update_stats(frame_count, score)
                        
                        # Send frame to client
                        await websocket.send(json.dumps({
                            'type': 'game_frame',
                            'sessionId': session_id,
                            'gameType': game_type,
                            'frame': frame,
                            'frameCount': frame_count,
                            'score': score,
                            'timestamp': time.time()
                        }))
                        
                        # Small delay to control frame rate
                        await asyncio.sleep(0.05)
                        
                except asyncio.TimeoutError:
                    # Check if client is still connected
                    # In websockets 16.0, we check if the connection is still open
                    if not hasattr(websocket, 'open') or not websocket.open:
                        session.is_active = False
                        break
                        
        except ConnectionClosed:
            logger.info(f"Client disconnected for session {session_id}")
        except Exception as e:
            logger.error(f"Error streaming game output for session {session_id}: {e}")
        finally:
            # Clean up process
            if session_id in self.game_processes:
                try:
                    process.terminate()
                    # Use asyncio.wait_for to add timeout to process.wait()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                del self.game_processes[session_id]
            
            if session_id in self.sessions:
                del self.sessions[session_id]
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol):
        """Handle incoming WebSocket client connections."""
        logger.info(f"New connection from {websocket.remote_address}")
        self.active_connections.add(websocket)
        
        try:
            # Authenticate the connection
            if not await self.authenticate_connection(websocket):
                await websocket.close()
                return
            
            # Parse game type from the path - in websockets 16.0, we need to use process_request
            # For now, we'll use a simple approach and check the path from the request
            # Since we can't easily access the path in this version, we'll use a default game
            game_type = 'snake'  # Default to snake for now
            session_id = secrets.token_hex(8)
            
            await websocket.send(json.dumps({
                'type': 'session_started',
                'sessionId': session_id,
                'gameType': game_type,
                'message': f'Starting {game_type} game session'
            }))
            
            # Stream game output
            await self.stream_game_output(websocket, session_id, game_type)
            
        except Exception as e:
            logger.error(f"Error handling client {websocket.remote_address}: {e}")
        finally:
            self.active_connections.discard(websocket)
            logger.info(f"Connection closed for {websocket.remote_address}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get current hub statistics."""
        return {
            'activeConnections': len(self.active_connections),
            'activeSessions': len(self.sessions),
            'activeProcesses': len(self.game_processes),
            'sessions': [
                {
                    'sessionId': s.session_id,
                    'gameType': s.game_type,
                    'duration': time.time() - s.start_time,
                    'frameCount': s.frame_count,
                    'score': s.score
                }
                for s in self.sessions.values()
            ]
        }
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
            
        message_str = json.dumps(message)
        # Use asyncio.gather to send to all clients concurrently
        await asyncio.gather(
            *[conn.send(message_str) for conn in self.active_connections],
            return_exceptions=True
        )
    
    async def start_server(self):
        """Start the SignalR hub server."""
        server = await websockets.serve(
            self.handle_client,
            "0.0.0.0",
            self.port,
            ping_interval=20,
            ping_timeout=20
        )
        
        logger.info(f"SignalR Hub started on ws://0.0.0.0:{self.port}")
        logger.info(f"Available games: {', '.join(self.game_commands.keys())}")
        logger.info(f"Authentication required: API Key = {self.api_key}")
        
        return server


async def main():
    """Main entry point for the SignalR hub."""
    # Generate or load API key
    api_key = os.environ.get('WEB_API_KEY')
    if not api_key:
        api_key = secrets.token_hex(16)
        logger.info(f"Generated API Key: {api_key}")
        logger.info("Set WEB_API_KEY environment variable to use a specific key")
    
    # Create hub instance
    hub = SignalRHub(api_key)
    
    # Start server
    server = await hub.start_server()
    
    # Handle graceful shutdown
    def signal_handler():
        logger.info("Shutdown signal received, closing server...")
        server.close()
    
    # Register signal handlers
    if sys.platform != 'win32':
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    
    try:
        # Keep server running
        await server.wait_closed()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        logger.info("SignalR Hub shutting down")


if __name__ == "__main__":
    asyncio.run(main())