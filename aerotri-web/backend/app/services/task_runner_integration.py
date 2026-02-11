"""Integration of diagnostic agent into task runners.

This module provides hooks to automatically trigger diagnosis when tasks fail.
Now with configuration support and graceful fallback for open-source readiness.
"""

import logging
from typing import Optional

from .openclaw_diagnostic_agent import diagnostic_agent
from ..conf.settings import get_settings

logger = logging.getLogger(__name__)


def is_diagnostic_enabled() -> bool:
    """Check if diagnostic agent is enabled in configuration.

    Returns:
        True if diagnostic.enabled is True in config
    """
    try:
        settings = get_settings()
        return settings.diagnostic.enabled
    except Exception as e:
        logger.warning(f"Failed to read diagnostic config: {e}")
        return False


async def on_task_failure(
    block_id: int,
    task_type: str,  # "sfm", "openmvs", "3dgs", "tiles"
    error_message: str,
    stage: Optional[str] = None,
    auto_diagnose: Optional[bool] = None,
    auto_fix: Optional[bool] = None,  # 兼容旧代码，已弃用
) -> None:
    """任务失败时的钩子函数 - 自动触发诊断.

    在各个 task_runner (task_runner.py, openmvs_runner.py, gs_runner.py 等)
    中捕获异常后调用此函数。

    **配置控制**: 诊断功能由 `settings.yaml` 中的 `diagnostic.enabled` 控制。
    默认禁用，适合开源环境。启用前需要确保 OpenClaw CLI 可用。

    **Graceful Fallback**: 如果 OpenClaw 不可用或诊断失败，静默跳过，
    不影响主流程的错误处理。

    Args:
        block_id: Block ID
        task_type: 任务类型
        error_message: 错误信息
        stage: 失败阶段
        auto_diagnose: 是否自动诊断（None=从配置读取，True/False=覆盖配置）

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
    # 兼容处理：auto_fix 是 auto_diagnose 的别名
    if auto_fix is not None:
        if auto_diagnose is not None:
            # 如果两个参数都提供了，使用 auto_diagnose
            logger.warning(f"Both auto_fix and auto_diagnose provided for block {block_id}, using auto_diagnose")
        else:
            auto_diagnose = auto_fix

    # 确定是否启用诊断（优先级：参数 > 配置）
    should_diagnose = auto_diagnose if auto_diagnose is not None else is_diagnostic_enabled()

    if not should_diagnose:
        logger.debug(f"Auto-diagnosis disabled for block {block_id}")
        return

    logger.info(f"Task failed for block {block_id}, triggering diagnosis...")

    try:
        # 获取配置
        settings = get_settings()
        diag_config = settings.diagnostic

        # 更新 diagnostic_agent 配置
        diagnostic_agent.config.agent_id = diag_config.agent_id
        diagnostic_agent.config.openclaw_cmd = diag_config.openclaw_cmd
        diagnostic_agent.config.agent_memory_path = str(diag_config.agent_memory_path)
        diagnostic_agent.config.history_log_path = str(diag_config.history_log_path)
        diagnostic_agent.config.claude_md_path = str(diag_config.claude_md_path)
        diagnostic_agent.config.timeout_seconds = diag_config.timeout_seconds

        # 异步执行诊断并在完成后发送补充通知
        import asyncio

        async def diagnose_and_notify():
            """执行诊断并在完成后发送补充通知"""
            try:
                # 执行诊断
                result = await diagnostic_agent.diagnose_failure(
                    block_id=block_id,
                    task_type=task_type,
                    error_message=error_message,
                    stage=stage,
                    auto_fix=diag_config.auto_fix,
                )

                # 如果诊断成功，发送补充通知
                if result and result.get("success"):
                    diagnosis = result.get("diagnosis")
                    if diagnosis:
                        logger.info(f"Diagnosis completed for block {block_id}, sending notification")

                        # 获取Block名称（从数据库或使用ID）
                        from ..models.database import AsyncSessionLocal
                        from ..models.block import Block

                        async with AsyncSessionLocal() as db:
                            block = await db.get(Block, block_id)
                            block_name = block.name if block else block_id

                        # 发送诊断完成通知
                        from .notification.manager import notification_manager
                        notification_manager.initialize()

                        await notification_manager.notify_diagnosis_completed(
                            block_id=block_id,
                            block_name=block_name,
                            task_type=task_type,
                            diagnosis=diagnosis,
                        )

                        logger.info(f"Diagnosis notification sent for block {block_id}")
            except Exception as e:
                logger.error(f"Error in diagnosis notification for block {block_id}: {e}")

        # 在后台运行诊断和通知
        asyncio.create_task(diagnose_and_notify())

        logger.info(f"Diagnosis task started for block {block_id}")

    except Exception as e:
        # 诊断失败不应该影响主流程
        # Graceful fallback: 静默跳过，只记录日志
        logger.debug(f"Failed to trigger diagnosis for block {block_id}: {e}")


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
from ..services.task_runner_integration import is_diagnostic_enabled

router = APIRouter()


@router.get("/api/diagnostics/status")
async def get_diagnostic_status():
    \"\"\"获取诊断Agent状态\"\"\"
    return {
        "enabled": is_diagnostic_enabled(),
        "openclaw_cmd": diagnostic_agent.config.openclaw_cmd,
        "agent_id": diagnostic_agent.config.agent_id,
    }


@router.post("/api/diagnostics/{block_id}/trigger")
async def trigger_diagnosis(
    block_id: int,
    task_type: str,
    error_message: str,
    stage: Optional[str] = None,
):
    \"\"\"手动触发诊断（用于测试或手动诊断）\"\"\"

    if not is_diagnostic_enabled():
        raise HTTPException(
            status_code=400,
            detail="Diagnostic agent is disabled. Enable it in settings.yaml"
        )

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

    if not is_diagnostic_enabled():
        raise HTTPException(
            status_code=400,
            detail="Diagnostic agent is disabled. Enable it in settings.yaml"
        )

    response = await diagnostic_agent.chat_with_agent(message, context)
    return {"response": response}
"""
