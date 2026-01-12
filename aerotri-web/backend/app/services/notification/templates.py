"""Message templates for notifications."""

from datetime import datetime
from typing import Any, Dict, List, Optional


def format_duration(seconds: Optional[float]) -> str:
    """Format duration in human-readable format."""
    if seconds is None:
        return "N/A"
    
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def format_timestamp(dt: Optional[datetime]) -> str:
    """Format timestamp for display."""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_progress(progress: float) -> str:
    """Format progress percentage."""
    return f"{progress:.1f}%"


class NotificationTemplates:
    """Templates for notification messages."""
    
    # ==================== Task Events ====================
    
    @staticmethod
    def task_started(
        block_name: str,
        task_type: str,
        started_at: Optional[datetime] = None,
        **kwargs: Any,
    ) -> tuple:
        """Template for task started notification.
        
        Returns:
            Tuple of (title, content)
        """
        task_type_names = {
            "sfm": "SfM 空三",
            "recon": "OpenMVS 重建",
            "gs": "3DGS 训练",
            "gs_tiles": "GS Tiles 转换",
            "tiles": "3D Tiles 转换",
        }
        type_name = task_type_names.get(task_type, task_type)
        
        title = f"🚀 任务开始: {block_name}"
        content = f"""### 任务开始

**Block**: {block_name}

**任务类型**: {type_name}

**开始时间**: {format_timestamp(started_at or datetime.utcnow())}
"""
        return title, content
    
    @staticmethod
    def task_completed(
        block_name: str,
        task_type: str,
        duration: Optional[float] = None,
        output_summary: Optional[str] = None,
        **kwargs: Any,
    ) -> tuple:
        """Template for task completed notification."""
        task_type_names = {
            "sfm": "SfM 空三",
            "recon": "OpenMVS 重建",
            "gs": "3DGS 训练",
            "gs_tiles": "GS Tiles 转换",
            "tiles": "3D Tiles 转换",
        }
        type_name = task_type_names.get(task_type, task_type)
        
        title = f"✅ 任务完成: {block_name}"
        content = f"""### 任务完成

**Block**: {block_name}

**任务类型**: {type_name}

**耗时**: {format_duration(duration)}
"""
        if output_summary:
            content += f"\n**产出**: {output_summary}\n"
        
        return title, content
    
    @staticmethod
    def task_failed(
        block_name: str,
        task_type: str,
        error: Optional[str] = None,
        stage: Optional[str] = None,
        duration: Optional[float] = None,
        log_tail: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> tuple:
        """Template for task failed notification."""
        task_type_names = {
            "sfm": "SfM 空三",
            "recon": "OpenMVS 重建",
            "gs": "3DGS 训练",
            "gs_tiles": "GS Tiles 转换",
            "tiles": "3D Tiles 转换",
        }
        type_name = task_type_names.get(task_type, task_type)
        
        title = f"❌ 任务失败: {block_name}"
        content = f"""### 任务失败

**Block**: {block_name}

**任务类型**: {type_name}

**失败阶段**: {stage or "未知"}

**运行时长**: {format_duration(duration)}

**错误信息**: 
```
{error or "无错误信息"}
```
"""
        if log_tail:
            log_text = "\n".join(log_tail[-10:])  # Last 10 lines
            content += f"""
**最后日志**:
```
{log_text}
```
"""
        
        return title, content
    
    # ==================== Backend Events ====================
    
    @staticmethod
    def backend_startup(
        version: str = "1.0.0",
        started_at: Optional[datetime] = None,
        **kwargs: Any,
    ) -> tuple:
        """Template for backend startup notification."""
        title = "🟢 AeroTri Web 后端启动"
        content = f"""### 后端服务启动

**版本**: {version}

**启动时间**: {format_timestamp(started_at or datetime.utcnow())}

**状态**: 运行中
"""
        return title, content
    
    @staticmethod
    def backend_shutdown(
        uptime: Optional[float] = None,
        shutdown_at: Optional[datetime] = None,
        **kwargs: Any,
    ) -> tuple:
        """Template for backend shutdown notification."""
        title = "🔴 AeroTri Web 后端关闭"
        content = f"""### 后端服务关闭

**关闭时间**: {format_timestamp(shutdown_at or datetime.utcnow())}

**运行时长**: {format_duration(uptime)}
"""
        return title, content
    
    @staticmethod
    def backend_error(
        error: str,
        traceback: Optional[str] = None,
        **kwargs: Any,
    ) -> tuple:
        """Template for backend error notification."""
        title = "⚠️ AeroTri Web 后端异常"
        content = f"""### 后端服务异常

**错误信息**: 
```
{error}
```
"""
        if traceback:
            # Truncate long tracebacks
            tb_lines = traceback.split("\n")
            if len(tb_lines) > 20:
                tb_lines = tb_lines[-20:]
            tb_text = "\n".join(tb_lines)
            content += f"""
**堆栈摘要**:
```
{tb_text}
```
"""
        return title, content
    
    # ==================== Periodic Reports ====================
    
    @staticmethod
    def system_status(
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
        gpu_info: Optional[List[Dict[str, Any]]] = None,
        running_tasks: int = 0,
        queued_tasks: int = 0,
        **kwargs: Any,
    ) -> tuple:
        """Template for system status report."""
        title = "📊 AeroTri Web 系统状态"
        content = f"""### 系统状态汇总

**CPU**: {cpu_percent:.1f}%

**内存**: {memory_percent:.1f}%

**磁盘**: {disk_percent:.1f}%
"""
        if gpu_info:
            content += "\n**GPU**:\n"
            for gpu in gpu_info:
                name = gpu.get("name", "Unknown")
                util = gpu.get("utilization", 0)
                mem_used = gpu.get("memory_used", 0)
                mem_total = gpu.get("memory_total", 0)
                content += f"- {name}: {util}% (显存 {mem_used}/{mem_total} MB)\n"
        
        content += f"""
**任务状态**:
- 运行中: {running_tasks}
- 排队中: {queued_tasks}

**时间**: {format_timestamp(datetime.utcnow())}
"""
        return title, content
    
    @staticmethod
    def periodic_task_summary(
        running_tasks: int = 0,
        queued_tasks: int = 0,
        completed_today: int = 0,
        failed_today: int = 0,
        **kwargs: Any,
    ) -> tuple:
        """Template for periodic task summary report."""
        title = "📋 AeroTri Web 任务汇总"
        content = f"""### 任务汇总报告

**当前状态**:
- 运行中: {running_tasks}
- 排队中: {queued_tasks}

**今日统计**:
- 完成: {completed_today}
- 失败: {failed_today}

**时间**: {format_timestamp(datetime.utcnow())}
"""
        return title, content
