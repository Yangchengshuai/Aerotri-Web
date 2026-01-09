"""Queue scheduler for automatic task dispatching."""
import asyncio
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from ..models.block import Block, BlockStatus
from ..models.database import AsyncSessionLocal
from ..api.queue import get_max_concurrent


class QueueScheduler:
    """Scheduler for automatically dispatching queued tasks."""
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._check_interval = 5  # seconds
        self._dispatch_lock = asyncio.Lock()  # Prevent concurrent dispatch
    
    async def start(self):
        """Start the scheduler background task."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        print("QueueScheduler started")
        
        # Initial dispatch check
        await self._check_and_dispatch()
    
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("QueueScheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop - runs every check_interval seconds."""
        while self._running:
            try:
                await self._check_and_dispatch()
            except Exception as e:
                print(f"QueueScheduler error: {e}")
                import traceback
                traceback.print_exc()
            
            await asyncio.sleep(self._check_interval)
    
    async def _check_and_dispatch(self):
        """Check queue and dispatch tasks if possible.
        
        Uses a lock to prevent concurrent dispatch operations.
        """
        # Use lock to prevent race conditions in concurrent dispatch calls
        async with self._dispatch_lock:
            try:
                async with AsyncSessionLocal() as db:
                    # Get current running count
                    result = await db.execute(
                        select(func.count(Block.id))
                        .where(Block.status == BlockStatus.RUNNING)
                    )
                    running_count = result.scalar() or 0
                    
                    max_concurrent = get_max_concurrent()
                    
                    # Calculate how many tasks we can start
                    available_slots = max_concurrent - running_count
                    
                    if available_slots <= 0:
                        return
                    
                    # Get queued tasks ordered by position
                    result = await db.execute(
                        select(Block)
                        .where(Block.status == BlockStatus.QUEUED)
                        .order_by(Block.queue_position.asc())
                        .limit(available_slots)
                    )
                    queued_blocks = result.scalars().all()
                    
                    if not queued_blocks:
                        return
                    
                    # Import here to avoid circular import
                    from .task_runner import task_runner
                    
                    for block in queued_blocks:
                        try:
                            # Double-check block is still queued (could have been dequeued)
                            if block.status != BlockStatus.QUEUED:
                                print(f"QueueScheduler: Block {block.id} is no longer queued, skipping")
                                continue
                            
                            print(f"QueueScheduler: Starting task for block {block.name} ({block.id})")
                            
                            # Clear queue fields
                            old_position = block.queue_position
                            block.queue_position = None
                            block.queued_at = None
                            
                            # Start the task (gpu_index=0 by default for queued tasks)
                            await task_runner.start_task(block, gpu_index=0, db=db)
                            
                            # Reorder remaining queue
                            await self._reorder_queue_after_dispatch(db, old_position)
                            
                            await db.commit()
                            
                            print(f"QueueScheduler: Task started for block {block.name}")
                            
                        except Exception as e:
                            print(f"QueueScheduler: Failed to start task for block {block.id}: {e}")
                            import traceback
                            traceback.print_exc()
                            try:
                                await db.rollback()
                            except Exception:
                                pass
            except SQLAlchemyError as e:
                print(f"QueueScheduler: Database error during dispatch: {e}")
    
    async def _reorder_queue_after_dispatch(self, db: AsyncSession, removed_position: int):
        """Reorder queue positions after a task is dispatched."""
        result = await db.execute(
            select(Block)
            .where(Block.status == BlockStatus.QUEUED)
            .where(Block.queue_position > removed_position)
            .order_by(Block.queue_position.asc())
        )
        blocks_to_shift = result.scalars().all()
        
        for b in blocks_to_shift:
            b.queue_position -= 1
    
    async def trigger_dispatch(self):
        """Manually trigger a dispatch check (called after task completion)."""
        try:
            await self._check_and_dispatch()
        except Exception as e:
            print(f"QueueScheduler trigger_dispatch error: {e}")


# Global scheduler instance
queue_scheduler = QueueScheduler()
