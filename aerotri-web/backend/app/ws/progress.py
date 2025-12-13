"""WebSocket endpoint for progress updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.task_runner import task_runner

router = APIRouter()


@router.websocket("/ws/blocks/{block_id}/progress")
async def progress_websocket(websocket: WebSocket, block_id: str):
    """WebSocket endpoint for real-time progress updates.
    
    Args:
        websocket: WebSocket connection
        block_id: Block ID to monitor
    """
    await websocket.accept()
    
    # Register connection
    task_runner.register_websocket(block_id, websocket)
    
    try:
        # Keep connection alive and listen for messages
        while True:
            try:
                # Wait for any client messages (like ping/pong)
                data = await websocket.receive_text()
                
                # Client can request current status
                if data == "status":
                    log_tail = task_runner.get_log_tail(block_id, 10)
                    stage_times = task_runner.get_stage_times(block_id)
                    
                    await websocket.send_json({
                        "type": "status",
                        "log_tail": log_tail or [],
                        "stage_times": stage_times or {},
                    })
            except WebSocketDisconnect:
                break
    finally:
        # Unregister connection
        task_runner.unregister_websocket(block_id, websocket)
