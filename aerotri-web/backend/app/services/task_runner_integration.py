"""Integration of diagnostic agent into task runners.

This module provides hooks to automatically trigger diagnosis when tasks fail.
"""

import logging
from typing import Optional

from .openclaw_diagnostic_agent import diagnostic_agent

logger = logging.getLogger(__name__)


async def on_task_failure(
    block_id: int,
    task_type: str,  # "sfm", "openmvs", "3dgs", "tiles"
    error_message: str,
    stage: Optional[str] = None,
    auto_diagnose: bool = True,
) -> None:
    """任务失败时的钩子函数 - 自动触发诊断.

    在各个 task_runner (task_runner.py, openmvs_runner.py, gs_runner.py 等)
    中捕获异常后调用此函数。

    Args:
        block_id: Block ID
        task_type: 任务类型
        error_message: 错误信息
        stage: 失败阶段
        auto_diagnose: 是否自动诊断（默认 True）

    Example:
        ```python
        try:
            await run_sfm_reconstruction(block)
        except Exception as e:
            await on_task_failure(
                block_id=block.id,
                task_type="sfm",
                error_message=str(e),
                stage="bundle_adjustment"
            )
            raise
        ```
    """
    if not auto_diagnose:
        logger.info(f"Auto-diagnosis disabled for block {block_id}")
        return

    logger.info(f"Task failed for block {block_id}, triggering diagnosis...")

    try:
        # 异步执行诊断（不阻塞主流程）
        # 使用 asyncio.create_task 在后台运行
        import asyncio
        asyncio.create_task(
            diagnostic_agent.diagnose_failure(
                block_id=block_id,
                task_type=task_type,
                error_message=error_message,
                stage=stage,
                auto_fix=True,  # 尝试自动修复
            )
        )

        logger.info(f"Diagnosis task started for block {block_id}")

    except Exception as e:
        # 诊断失败不应该影响主流程
        logger.error(f"Failed to trigger diagnosis for block {block_id}: {e}", exc_info=True)


# ============================================================================
# 在各个 runner 中的集成示例
# ============================================================================

# 1. task_runner.py (SfM)
"""
async def run_task(self, block_id: int, params: SfMParams):
    try:
        # ... SfM 处理逻辑 ...
        pass
    except Exception as e:
        logger.error(f"SfM task failed: {e}")
        await on_task_failure(
            block_id=block_id,
            task_type="sfm",
            error_message=str(e),
            stage=self.current_stage,
        )
        raise
"""

# 2. openmvs_runner.py (OpenMVS)
"""
async def run_reconstruction(self, block_id: int, version_id: int, params: OpenMVSParams):
    try:
        # ... OpenMVS 处理逻辑 ...
        pass
    except Exception as e:
        logger.error(f"OpenMVS task failed: {e}")
        await on_task_failure(
            block_id=block_id,
            task_type="openmvs",
            error_message=str(e),
            stage=params.current_stage,
        )
        raise
"""

# 3. gs_runner.py (3DGS)
"""
async def start_training(self, block_id: int, params: GSParams):
    try:
        # ... 3DGS 训练逻辑 ...
        pass
    except Exception as e:
        logger.error(f"3DGS task failed: {e}")
        await on_task_failure(
            block_id=block_id,
            task_type="3dgs",
            error_message=str(e),
            stage="training",
        )
        raise
"""

# 4. tiles_runner.py (3D Tiles)
"""
async def convert_to_tiles(self, block_id: int, version_id: Optional[int], params: TilesParams):
    try:
        # ... 3D Tiles 转换逻辑 ...
        pass
    except Exception as e:
        logger.error(f"Tiles conversion failed: {e}")
        await on_task_failure(
            block_id=block_id,
            task_type="tiles",
            error_message=str(e),
            stage=params.stage,
        )
        raise
"""

# ============================================================================
# 手动触发诊断的 API endpoint（可选）
# ============================================================================

"""
from fastapi import APIRouter, Depends, HTTPException
from ..services.openclaw_diagnostic_agent import diagnostic_agent

router = APIRouter()

@router.post("/api/diagnostics/{block_id}/trigger")
async def trigger_diagnosis(
    block_id: int,
    task_type: str,
    error_message: str,
    stage: Optional[str] = None,
):
    \"\"\"手动触发诊断（用于测试或手动诊断）\"\"\"
    result = await diagnostic_agent.diagnose_failure(
        block_id=block_id,
        task_type=task_type,
        error_message=error_message,
        stage=stage,
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.post("/api/agent/chat")
async def chat_with_agent(message: str, context: Optional[dict] = None):
    \"\"\"与 Agent 对话（用于开发任务）\"\"\"
    response = await diagnostic_agent.chat_with_agent(message, context)
    return {"response": response}
"""
