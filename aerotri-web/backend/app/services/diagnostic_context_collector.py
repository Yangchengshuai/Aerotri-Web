"""Diagnostic context collector for Aerotri-Web Agent.

Collects comprehensive context when a task fails for AI diagnosis.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from ..models.database import get_db
from ..models.block import Block
from .system_monitor import system_monitor
from ..conf.settings import get_settings

logger = logging.getLogger(__name__)


class DiagnosticContextCollector:
    """Collects diagnostic context when a task fails."""

    # 最大日志行数（避免 token 溢出）
    MAX_LOG_LINES = 500
    # 最大文件大小（MB）
    MAX_FILE_SIZE_MB = 5

    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            _settings = get_settings()
            base_path = str(_settings.get_absolute_paths()['outputs_dir'])
        self.base_path = Path(base_path)

    async def collect_failure_context(
        self,
        block_id: int,
        task_type: str,  # "sfm", "openmvs", "3dgs", "tiles"
        error_message: str,
        stage: Optional[str] = None,
    ) -> Dict[str, Any]:
        """收集任务失败的完整上下文。

        Args:
            block_id: Block ID
            task_type: 任务类型
            error_message: 错误信息
            stage: 失败阶段（可选）

        Returns:
            完整的诊断上下文字典
        """
        context = {
            "timestamp": datetime.utcnow().isoformat(),
            "block_id": block_id,
            "task_type": task_type,
            "stage": stage,
            "error_message": error_message,
            "block_info": await self._get_block_info(block_id),
            "system_status": system_monitor.get_system_status(),
            "log_content": await self._collect_logs(block_id, task_type),
            "directory_structure": self._get_directory_structure(block_id),
            "recent_files": self._get_recent_files(block_id),
        }

        logger.info(f"Collected diagnostic context for block {block_id}")
        return context

    async def _get_block_info(self, block_id: int) -> Dict[str, Any]:
        """获取 Block 信息."""
        try:
            async for db in get_db():
                block = await db.get(Block, block_id)
                if block:
                    return {
                        "id": block.id,
                        "name": block.name,
                        "algorithm": block.algorithm,
                        "status": block.status,
                        "progress": block.progress,
                        "current_stage": block.current_stage,
                        "error_message": block.error_message,
                        "num_images": block.statistics.get("num_images", 0) if block.statistics else 0,
                        "created_at": block.created_at.isoformat() if block.created_at else None,
                        "updated_at": block.updated_at.isoformat() if block.updated_at else None,
                    }
        except Exception as e:
            logger.warning(f"Failed to get block info: {e}")
            return {}

    async def _collect_logs(self, block_id: int, task_type: str) -> Dict[str, str]:
        """收集相关日志文件."""
        logs = {}

        block_dir = self.base_path / str(block_id)

        # 定义可能的日志文件位置
        log_patterns = {
            "main_log": block_dir / "task.log",
            "sfm_log": block_dir / "sparse" / "0" / "log.txt",
            "openmvs_log": block_dir / "openmvs.log",
            "3dgs_log": block_dir / "3dgs" / "train" / "log.txt",
            "error_log": block_dir / "error.log",
        }

        for log_name, log_path in log_patterns.items():
            if log_path.exists() and log_path.stat().st_size < self.MAX_FILE_SIZE_MB * 1024 * 1024:
                try:
                    content = self._read_last_n_lines(log_path, self.MAX_LOG_LINES)
                    logs[log_name] = content
                except Exception as e:
                    logger.warning(f"Failed to read log {log_path}: {e}")
                    logs[log_name] = f"[Error reading log: {e}]"

        return logs

    def _read_last_n_lines(self, file_path: Path, n: int) -> str:
        """读取文件的最后 N 行."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                if len(lines) > n:
                    lines = lines[-n:]
                    return f"[... showing last {n} lines of {len(lines) + n} total ...]\n" + "".join(lines)
                return "".join(lines)
        except Exception as e:
            return f"[Error: {e}]"

    def _get_directory_structure(self, block_id: int, max_depth: int = 3) -> Dict[str, Any]:
        """获取目录结构（用于理解输出文件）。"""
        block_dir = self.base_path / str(block_id)

        if not block_dir.exists():
            return {"error": "Block directory not found"}

        def build_tree(path: Path, depth: int = 0) -> Dict:
            if depth > max_depth:
                return {"type": "dir", "name": path.name, "truncated": True}

            if path.is_file():
                return {
                    "type": "file",
                    "name": path.name,
                    "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
                }

            children = []
            try:
                for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                    children.append(build_tree(item, depth + 1))
            except PermissionError:
                pass

            return {"type": "dir", "name": path.name, "children": children}

        return build_tree(block_dir)

    def _get_recent_files(self, block_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近修改的文件."""
        block_dir = self.base_path / str(block_id)

        if not block_dir.exists():
            return []

        files = []
        try:
            for item in block_dir.rglob("*"):
                if item.is_file():
                    stat = item.stat()
                    files.append({
                        "path": str(item.relative_to(block_dir)),
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })

            # 按修改时间排序
            files.sort(key=lambda x: x["modified"], reverse=True)
            return files[:limit]
        except Exception as e:
            logger.warning(f"Failed to get recent files: {e}")
            return []

    def format_context_for_ai(
        self,
        context: Dict[str, Any],
        include_system_prompt: bool = True,
    ) -> str:
        """格式化上下文为 AI 可读的 Prompt.

        这是最关键的函数：将收集到的上下文转化为精准的 AI Prompt。

        Args:
            context: 诊断上下文
            include_system_prompt: 是否包含系统提示词

        Returns:
            格式化的 Prompt 字符串
        """
        parts = []

        if include_system_prompt:
            parts.append(self._get_system_prompt())

        parts.append(self._format_failure_summary(context))
        parts.append(self._format_block_info(context))
        parts.append(self._format_system_status(context))
        parts.append(self._format_logs(context))
        parts.append(self._format_directory_structure(context))

        return "\n\n---\n\n".join(parts)

    def _get_system_prompt(self) -> str:
        """系统提示词：定义 Agent 的角色和任务."""
        return """你是 Aerotri-Web 的诊断 Agent，专门分析摄影测量任务失败的原因。

## 你的能力
1. 快速定位错误根因（算法、环境、数据、代码）
2. 提供可执行的修复建议
3. 识别新的问题模式，并记录到知识库

## 分析原则
1. **精准上下文**：只分析提供的日志和错误信息，不要臆测
2. **根因分析**：找到最根本的原因，而不是表面现象
3. **可执行建议**：每个建议都应该可以直接操作
4. **学习心态**：如果遇到新问题，记录下来供未来参考

## 输出格式
请按以下结构输出：

### 🔍 错误分析
[简述错误类型和根本原因]

### 💡 修复建议
1. [具体步骤 1]
2. [具体步骤 2]
3. [如果以上都失败，尝试...]

### 📚 问题模式
[这是一个已知问题还是新问题？如果已知，引用历史；如果新问题，描述其特征]

### 🔗 相关资源
[CLAUDE.md 中的相关章节、文档链接等]
"""

    def _format_failure_summary(self, context: Dict[str, Any]) -> str:
        """格式化失败摘要."""
        return f"""## 失败摘要

**任务**: {context['task_type'].upper()}
**Block ID**: {context['block_id']}
**Block 名称**: {context['block_info'].get('name', 'Unknown')}
**算法**: {context['block_info'].get('algorithm', 'Unknown')}
**阶段**: {context.get('stage', 'Unknown')}
**时间**: {context['timestamp']}

**错误信息**:
```
{context['error_message']}
```

**状态**:
- 当前进度: {context['block_info'].get('progress', 0)}%
- 图片数量: {context['block_info'].get('num_images', 0)} 张
"""

    def _format_block_info(self, context: Dict[str, Any]) -> str:
        """格式化 Block 信息."""
        block = context['block_info']
        return f"""## Block 信息

- **ID**: {block.get('id')}
- **名称**: {block.get('name')}
- **算法**: {block.get('algorithm')}
- **创建时间**: {block.get('created_at')}
- **最后更新**: {block.get('updated_at')}
"""

    def _format_system_status(self, context: Dict[str, Any]) -> str:
        """格式化系统状态."""
        sys = context['system_status']
        gpu_info = ""
        if sys.get('gpu_count', 0) > 0:
            gpu_info = f"\n**GPU**: {sys['gpu_count']} 个 GPU"
            for i, gpu in enumerate(sys.get('gpus', [])):
                gpu_model = gpu.get('model', 'Unknown') if isinstance(gpu, dict) else getattr(gpu, 'model', 'Unknown')
                gpu_mem = gpu.get('memory_used_mb', 0) if isinstance(gpu, dict) else getattr(gpu, 'memory_used_mb', 0)
                gpu_info += f"\n  - GPU {i}: {gpu_model} (已用: {gpu_mem} MB)"

        return f"""## 系统状态

**CPU**: {sys['cpu_percent']}%
**内存**: {sys['memory_used_gb']} GB / {sys['memory_total_gb']} GB ({sys['memory_percent']}%)
**磁盘**: {sys['disk_used_gb']} GB / {sys['disk_total_gb']} GB ({sys['disk_percent']}%){gpu_info}
"""

    def _format_logs(self, context: Dict[str, Any]) -> str:
        """格式化日志内容."""
        logs = context['log_content']
        if not logs:
            return "## 日志\n\n没有找到相关日志文件。"

        parts = ["## 日志内容"]
        for log_name, content in logs.items():
            if content.strip():
                parts.append(f"\n### {log_name}\n```\n{content}\n```")

        return "\n".join(parts)

    def _format_directory_structure(self, context: Dict[str, Any]) -> str:
        """格式化目录结构."""
        return f"""## 输出目录结构

```
{self._dict_to_tree(context['directory_structure'])}
```

### 最近修改的文件
{self._format_recent_files(context['recent_files'])}
"""

    def _dict_to_tree(self, d: Dict, indent: int = 0) -> str:
        """将字典树转换为字符串树."""
        prefix = "  " * indent
        name = d.get('name', 'unknown')

        if d.get('type') == 'file':
            size = d.get('size_mb', 0)
            return f"{prefix}📄 {name} ({size} MB)\n"
        elif d.get('type') == 'dir':
            if d.get('truncated'):
                return f"{prefix}📁 {name}/ ... (truncated)\n"
            result = f"{prefix}📁 {name}/\n"
            for child in d.get('children', []):
                result += self._dict_to_tree(child, indent + 1)
            return result
        else:
            return f"{prefix}❓ {name}\n"

    def _format_recent_files(self, files: List[Dict]) -> str:
        """格式化最近文件列表."""
        if not files:
            return "无"

        lines = []
        for f in files[:10]:  # 只显示前 10 个
            lines.append(f"- `{f['path']}` ({f['size_mb']} MB, {f['modified']})")

        return "\n".join(lines)


# 全局实例
diagnostic_collector = DiagnosticContextCollector()
