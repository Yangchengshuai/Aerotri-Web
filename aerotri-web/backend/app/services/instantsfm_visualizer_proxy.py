"""Proxy service for InstantSfM visualization via viser server."""
import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional, Set, Any
from urllib.parse import urljoin

import aiohttp
try:
    import websockets
    from websockets.exceptions import ConnectionClosed, WebSocketException
except ImportError:
    # websockets library not required for FastAPI WebSocket compatibility
    websockets = None
    ConnectionClosed = Exception
    WebSocketException = Exception

logger = logging.getLogger(__name__)


class InstantSfMVisualizerProxy:
    """Proxy service that connects to viser server and forwards visualization data to frontend clients.
    
    This class manages the connection to the viser server (started by InstantSfM with --enable_gui)
    and forwards the visualization data (point clouds, camera poses) to frontend WebSocket clients.
    """
    
    def __init__(self, block_id: str, viser_port: Optional[int] = None):
        """Initialize the visualization proxy.
        
        Args:
            block_id: Block ID for this visualization session
            viser_port: Port number of the viser server (if None, will try to detect)
        """
        self.block_id = block_id
        self.viser_port = viser_port
        self.viser_base_url = f"http://localhost:{viser_port}" if viser_port else None
        
        # WebSocket clients (frontend connections)
        # Can be FastAPI WebSocket or websockets.WebSocketServerProtocol
        self.ws_clients: Set[Any] = set()
        
        # Viser server connection
        self.viser_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.viser_http_session: Optional[aiohttp.ClientSession] = None
        
        # State
        self.running = False
        self._update_task: Optional[asyncio.Task] = None
        
        # Latest scene data
        self.latest_scene_data: Optional[Dict[str, Any]] = None
        self.last_update_time = 0.0
        
    async def start(self) -> bool:
        """Start the proxy service.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.running:
            return True
        
        # Start polling task that will wait for viser server to be ready
        self.running = True
        self._update_task = asyncio.create_task(self._wait_and_connect_to_viser())
        
        logger.info(f"InstantSfM visualization proxy starting for block {self.block_id}, waiting for viser server...")
        return True
    
    async def _wait_and_connect_to_viser(self):
        """Wait for viser server to start and then connect."""
        max_wait_time = 300  # Wait up to 5 minutes
        check_interval = 2.0  # Check every 2 seconds
        start_time = time.time()
        
        # Try to detect port from environment or common ports
        ports_to_try = []
        if self.viser_port:
            ports_to_try.append(self.viser_port)
        else:
            # Try environment variable
            viser_port_env = os.environ.get("VISER_PORT")
            if viser_port_env:
                try:
                    ports_to_try.append(int(viser_port_env))
                except ValueError:
                    pass
            
            # Try common viser ports
            if not ports_to_try:
                ports_to_try = list(range(8080, 8100))  # Try ports 8080-8099
        
        while self.running and (time.time() - start_time) < max_wait_time:
            for port in ports_to_try:
                try:
                    test_url = f"http://localhost:{port}"
                    async with aiohttp.ClientSession() as session:
                        try:
                            async with session.get(
                                f"{test_url}/health", 
                                timeout=aiohttp.ClientTimeout(total=2)
                            ) as resp:
                                if resp.status == 200:
                                    # Found viser server!
                                    self.viser_port = port
                                    self.viser_base_url = test_url
                                    self.viser_http_session = aiohttp.ClientSession()
                                    logger.info(f"Found viser server on port {port} for block {self.block_id}")
                                    
                                    # Start polling for scene updates
                                    asyncio.create_task(self._poll_scene_updates())
                                    return
                        except (aiohttp.ClientError, asyncio.TimeoutError):
                            # Port not ready yet, continue
                            pass
                except Exception as e:
                    logger.debug(f"Error checking port {port}: {e}")
                    continue
            
            # Wait before next check
            await asyncio.sleep(check_interval)
        
        if self.running:
            logger.warning(f"Viser server not found after {max_wait_time}s for block {self.block_id}")
            # Keep running but don't try to connect - clients can still connect and we'll retry later
    
    async def stop(self):
        """Stop the proxy service and clean up resources."""
        self.running = False
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        # Close viser WebSocket connection
        if self.viser_ws:
            try:
                await self.viser_ws.close()
            except Exception:
                pass
            self.viser_ws = None
        
        # Close HTTP session
        if self.viser_http_session:
            await self.viser_http_session.close()
            self.viser_http_session = None
        
        # Close all client connections
        for client in list(self.ws_clients):
            try:
                await client.close()
            except Exception:
                pass
        self.ws_clients.clear()
        
        logger.info(f"InstantSfM visualization proxy stopped for block {self.block_id}")
    
    def register_client(self, ws):
        """Register a frontend WebSocket client.
        
        Args:
            ws: WebSocket connection from frontend (FastAPI WebSocket or websockets.WebSocketServerProtocol)
        """
        self.ws_clients.add(ws)
        logger.info(f"Registered visualization client for block {self.block_id} (total: {len(self.ws_clients)})")
        
        # Send latest scene data if available
        if self.latest_scene_data:
            asyncio.create_task(self._send_to_client(ws, self.latest_scene_data))
    
    def unregister_client(self, ws):
        """Unregister a frontend WebSocket client.
        
        Args:
            ws: WebSocket connection from frontend (FastAPI WebSocket or websockets.WebSocketServerProtocol)
        """
        self.ws_clients.discard(ws)
        logger.info(f"Unregistered visualization client for block {self.block_id} (remaining: {len(self.ws_clients)})")
    
    async def _poll_scene_updates(self):
        """Poll viser server for scene updates."""
        if not self.viser_http_session or not self.viser_base_url:
            # Wait for viser server to be ready
            return
        
        update_interval = 0.5  # Poll every 500ms
        
        while self.running and self.viser_http_session:
            try:
                # Note: viser's actual API may be different
                # For now, we'll try to get scene data via HTTP API
                # If viser doesn't expose HTTP API, we may need to use WebSocket or modify InstantSfM
                
                # Try to get scene data (this is a placeholder - actual implementation depends on viser API)
                # For now, we'll just keep the connection alive and wait for actual implementation
                
                await asyncio.sleep(update_interval)
                
                # TODO: Implement actual scene data fetching from viser
                # Options:
                # 1. Use viser's HTTP API if available (e.g., /api/scene)
                # 2. Connect to viser's WebSocket directly
                # 3. Modify InstantSfM to expose data via a callback or file
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Error polling scene updates: {e}")
                await asyncio.sleep(1.0)  # Wait longer on error
    
    async def update_scene_data(self, scene_data: Dict[str, Any]):
        """Update scene data and broadcast to all clients.
        
        Args:
            scene_data: Scene data in Three.js compatible format
                {
                    "step": int,
                    "stepName": str,
                    "cameras": List[CameraInfo],
                    "points": List[Point3D],
                    "timestamp": float
                }
        """
        self.latest_scene_data = scene_data
        self.last_update_time = time.time()
        
        # Broadcast to all clients
        if self.ws_clients:
            await asyncio.gather(
                *[self._send_to_client(client, scene_data) for client in list(self.ws_clients)],
                return_exceptions=True
            )
    
    async def _send_to_client(self, client, data: Dict[str, Any]):
        """Send data to a single client.
        
        Args:
            client: WebSocket client (FastAPI WebSocket or websockets.WebSocketServerProtocol)
            data: Data to send
        """
        try:
            # Handle FastAPI WebSocket
            if hasattr(client, 'send_json'):
                await client.send_json(data)
            # Handle websockets library WebSocket
            elif hasattr(client, 'send'):
                await client.send(json.dumps(data))
            else:
                logger.error(f"Unknown WebSocket client type: {type(client)}")
                self.unregister_client(client)
        except (ConnectionClosed, WebSocketException) as e:
            logger.debug(f"Client disconnected: {e}")
            self.unregister_client(client)
        except Exception as e:
            logger.error(f"Error sending data to client: {e}", exc_info=True)
            self.unregister_client(client)
    
    def convert_viser_to_threejs(self, viser_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert viser scene data to Three.js compatible format.
        
        Args:
            viser_data: Raw data from viser server
            
        Returns:
            Three.js compatible scene data
        """
        # This is a placeholder - actual conversion depends on viser's data format
        # We'll need to inspect viser's actual API to implement this properly
        
        threejs_data = {
            "step": viser_data.get("step", 0),
            "stepName": viser_data.get("step_name", "unknown"),
            "cameras": [],
            "points": [],
            "timestamp": time.time()
        }
        
        # Convert cameras
        if "cameras" in viser_data:
            for cam_id, cam_data in viser_data["cameras"].items():
                # viser uses wxyz quaternion format, Three.js uses xyzw
                wxyz = cam_data.get("wxyz", [1, 0, 0, 0])
                position = cam_data.get("position", [0, 0, 0])
                
                threejs_data["cameras"].append({
                    "id": int(cam_id),
                    "qx": wxyz[1],  # x
                    "qy": wxyz[2],  # y
                    "qz": wxyz[3],  # z
                    "qw": wxyz[0],  # w
                    "tx": position[0],
                    "ty": position[1],
                    "tz": position[2],
                    "fov": cam_data.get("fov", 0.8),
                    "aspect": cam_data.get("aspect", 1.0),
                })
        
        # Convert points
        if "points" in viser_data:
            points_array = viser_data["points"]
            colors_array = viser_data.get("colors", [])
            
            for i in range(len(points_array)):
                point = points_array[i]
                color = colors_array[i] if i < len(colors_array) else [128, 128, 128]
                
                threejs_data["points"].append({
                    "x": float(point[0]),
                    "y": float(point[1]),
                    "z": float(point[2]),
                    "r": int(color[0]),
                    "g": int(color[1]),
                    "b": int(color[2]),
                })
        
        return threejs_data


# Global registry of active proxies
_visualizer_proxies: Dict[str, InstantSfMVisualizerProxy] = {}


def get_visualizer_proxy(block_id: str) -> Optional[InstantSfMVisualizerProxy]:
    """Get the visualizer proxy for a block.
    
    Args:
        block_id: Block ID
        
    Returns:
        Visualizer proxy instance or None if not found
    """
    return _visualizer_proxies.get(block_id)


def register_visualizer_proxy(block_id: str, proxy: InstantSfMVisualizerProxy):
    """Register a visualizer proxy.
    
    Args:
        block_id: Block ID
        proxy: Visualizer proxy instance
    """
    _visualizer_proxies[block_id] = proxy


def unregister_visualizer_proxy(block_id: str):
    """Unregister a visualizer proxy.
    
    Args:
        block_id: Block ID
    """
    if block_id in _visualizer_proxies:
        proxy = _visualizer_proxies.pop(block_id)
        asyncio.create_task(proxy.stop())

