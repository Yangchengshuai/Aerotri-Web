"""WebSocket endpoint for InstantSfM visualization updates."""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.instantsfm_visualizer_proxy import (
    get_visualizer_proxy,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/visualization/{block_id}")
async def visualization_websocket(websocket: WebSocket, block_id: str):
    """WebSocket endpoint for real-time visualization updates.
    
    Args:
        websocket: WebSocket connection
        block_id: Block ID to monitor
    """
    await websocket.accept()
    
    # Get visualizer proxy (may not exist yet if viser server hasn't started)
    proxy = get_visualizer_proxy(block_id)
    if not proxy:
        # Send error and close
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Visualization not available for this block. Make sure enable_visualization is enabled and InstantSfM is running."
            })
        except Exception:
            pass
        await websocket.close(code=1008, reason="Visualization not available")
        return
    
    # Register this client with the proxy
    proxy.register_client(websocket)
    
    try:
        logger.info(f"Visualization client connected for block {block_id}")
        
        # Send initial status
        try:
            await websocket.send_json({
                "type": "status",
                "connected": True,
                "has_data": proxy.latest_scene_data is not None,
                "viser_ready": proxy.viser_port is not None
            })
        except Exception:
            pass
        
        # Keep connection alive and forward messages
        while True:
            try:
                # Receive message from client (ping/pong or status requests)
                data = await websocket.receive_text()
                
                if data == "ping":
                    await websocket.send_text("pong")
                elif data == "status":
                    # Send current scene data if available
                    if proxy.latest_scene_data:
                        await websocket.send_json(proxy.latest_scene_data)
                    else:
                        await websocket.send_json({
                            "type": "status",
                            "connected": True,
                            "has_data": False,
                            "viser_ready": proxy.viser_port is not None
                        })
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.error(f"Error in visualization WebSocket: {e}", exc_info=True)
    finally:
        # Unregister client
        if proxy:
            proxy.unregister_client(websocket)
        logger.info(f"Visualization client disconnected for block {block_id}")

