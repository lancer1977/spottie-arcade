#!/usr/bin/env python3
"""
SignalR Client Example for ANSI Arcade Games

This example demonstrates how to connect to the SignalR hub and stream game output.
"""

import asyncio
import json
import sys
import websockets
from typing import Dict, Any


class ArcadeClient:
    """Client for connecting to the SignalR hub and streaming games."""
    
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url
        self.api_key = api_key
        self.websocket = None
        
    async def connect(self, game_type: str):
        """Connect to the SignalR hub and start streaming a game."""
        try:
            # Construct the WebSocket URL
            ws_url = f"{self.server_url}/{game_type}"
            print(f"Connecting to {ws_url}")
            
            self.websocket = await websockets.connect(ws_url)
            
            # Send authentication
            auth_message = {
                'type': 'authentication',
                'apiKey': self.api_key
            }
            await self.websocket.send(json.dumps(auth_message))
            
            # Wait for authentication response
            response = await self.websocket.recv()
            auth_response = json.loads(response)
            
            if auth_response.get('status') == 'success':
                print("✅ Authentication successful!")
            else:
                print(f"❌ Authentication failed: {auth_response.get('message')}")
                await self.websocket.close()
                return
            
            # Wait for session start confirmation
            session_msg = await self.websocket.recv()
            session_response = json.loads(session_msg)
            
            if session_response.get('type') == 'session_started':
                session_id = session_response.get('sessionId')
                print(f"🎮 Game session started: {session_response.get('gameType')}")
                print(f"Session ID: {session_id}")
                print("-" * 50)
            else:
                print(f"❌ Session failed to start: {session_response.get('message')}")
                await self.websocket.close()
                return
            
            # Stream game frames
            await self.stream_game_frames()
            
        except websockets.exceptions.ConnectionClosed:
            print("❌ Connection closed by server")
        except Exception as e:
            print(f"❌ Connection error: {e}")
        finally:
            if self.websocket:
                await self.websocket.close()
    
    async def stream_game_frames(self):
        """Stream and display game frames from the server."""
        try:
            while True:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data.get('type') == 'game_frame':
                    # Clear screen and display frame
                    print("\033[2J\033[H", end="")  # Clear screen and move cursor to top
                    
                    frame = data.get('frame', '')
                    score = data.get('score', 0)
                    frame_count = data.get('frameCount', 0)
                    
                    print(frame)
                    print(f"Frame: {frame_count} | Score: {score}")
                    
                elif data.get('type') == 'error':
                    print(f"❌ Server error: {data.get('message')}")
                    break
                    
        except websockets.exceptions.ConnectionClosed:
            print("❌ Connection closed by server")
        except Exception as e:
            print(f"❌ Streaming error: {e}")


async def main():
    """Main entry point for the client example."""
    if len(sys.argv) < 3:
        print("Usage: python3 signalr_client_example.py <server_url> <api_key> [game_type]")
        print("Example: python3 signalr_client_example.py ws://localhost:8765 myapikey123 snake")
        print("\nAvailable games: snake, pacman, digdug")
        sys.exit(1)
    
    server_url = sys.argv[1]
    api_key = sys.argv[2]
    game_type = sys.argv[3] if len(sys.argv) > 3 else 'snake'
    
    # Validate game type
    valid_games = ['snake', 'pacman', 'digdug']
    if game_type not in valid_games:
        print(f"❌ Invalid game type: {game_type}")
        print(f"Available games: {', '.join(valid_games)}")
        sys.exit(1)
    
    print(f"🚀 Connecting to SignalR Hub: {server_url}")
    print(f"🎮 Game: {game_type}")
    print(f"🔑 API Key: {api_key}")
    print("Press Ctrl+C to exit\n")
    
    client = ArcadeClient(server_url, api_key)
    
    try:
        await client.connect(game_type)
    except KeyboardInterrupt:
        print("\n👋 Client shutting down...")
    except Exception as e:
        print(f"❌ Client error: {e}")


if __name__ == "__main__":
    asyncio.run(main())