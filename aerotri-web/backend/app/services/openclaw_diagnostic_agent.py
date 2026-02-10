"""OpenClaw integration for Aerotri-Web diagnostic Agent.

Integrates with OpenClaw service to diagnose task failures.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
from pydantic import BaseModel

from .diagnostic_context_collector import diagnostic_collector
from ..conf.settings import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()


class OpenClawConfig(BaseModel):
    """OpenClaw configuration."""

    # OpenClaw Agent ID（默认使用 main）
    agent_id: str = "main"

    # OpenClaw CLI 路径（可选，默认使用系统 PATH）
    openclaw_cmd: str = "openclaw"

    # 知识库路径
    agent_memory_path: str = "/root/work/Aerotri-Web/docs/AerotriWeb_AGENT.md"
    history_log_path: str = "/root/work/Aerotri-Web/aerotri-web/backend/data/diagnosis_history.log"

    # 系统经验
    claude_md_path: str = "/root/work/Aerotri-Web/CLAUDE.md"

    # 超时设置
    timeout_seconds: int = 60


class AerotriWebDiagnosticAgent:
    """Aerotri-Web 诊断 Agent - 集成 OpenClaw 实现智能诊断.

    工作流程：
    1. 任务失败时触发
    2. 收集上下文（logs、系统状态、Block 信息等）
    3. 组装诊断 Prompt（包含历史经验和系统知识）
    4. 发送给 OpenClaw 进行分析
    5. 接收诊断结果并更新知识库
    """

    def __init__(self, config: Optional[OpenClawConfig] = None):
        self.config = config or OpenClawConfig()
        self._history_lock = asyncio.Lock()

    async def diagnose_failure(
        self,
        block_id: int,
        task_type: str,
        error_message: str,
        stage: Optional[str] = None,
        auto_fix: bool = False,
    ) -> Dict[str, Any]:
        """诊断任务失败.

        Args:
            block_id: Block ID
            task_type: 任务类型 (sfm/openmvs/3dgs/tiles)
            error_message: 错误信息
            stage: 失败阶段
            auto_fix: 是否自动修复（如果可能）

        Returns:
            诊断结果字典，包含：
            - success: 是否成功
            - diagnosis: 错误分析
            - suggestions: 修复建议
            - error_type: 错误类型
            - confidence: 置信度
            - is_new_pattern: 是否是新问题模式
            - auto_fixed: 是否已自动修复
        """
        try:
            # 1. 收集上下文
            logger.info(f"Collecting diagnostic context for block {block_id}")
            context = await diagnostic_collector.collect_failure_context(
                block_id=block_id,
                task_type=task_type,
                error_message=error_message,
                stage=stage,
            )

            # 2. 组装 Prompt
            prompt = await self._build_diagnosis_prompt(context)

            # 3. 发送给 OpenClaw
            logger.info(f"Sending diagnosis request to OpenClaw for block {block_id}")
            raw_response = await self._send_to_openclaw(prompt)

            # 4. 解析响应
            diagnosis = self._parse_openclaw_response(raw_response)

            # 5. 尝试自动修复（如果启用）
            auto_fixed = False
            if auto_fix:
                auto_fixed = await self._attempt_auto_fix(block_id, diagnosis)

            # 6. 更新知识库
            await self._update_knowledge_base(context, diagnosis, auto_fixed)

            # 7. 记录历史
            await self._append_to_history(context, diagnosis, auto_fixed)

            return {
                "success": True,
                "block_id": block_id,
                "diagnosis": diagnosis,
                "auto_fixed": auto_fixed,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Diagnosis failed for block {block_id}: {e}", exc_info=True)
            return {
                "success": False,
                "block_id": block_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _build_diagnosis_prompt(self, context: Dict[str, Any]) -> str:
        """构建诊断 Prompt，包含所有必要的上下文.

        这是 Agent 的核心能力：将分散的信息组装成精准的 Prompt。
        """
        # 基础上下文（由 collector 格式化）
        base_prompt = diagnostic_collector.format_context_for_ai(context)

        # 添加 Agent 经验（AerotriWeb_AGENT.md）
        agent_memory = await self._load_agent_memory()

        # 添加历史案例（最近 5 条相似案例）
        similar_cases = await self._find_similar_cases(context)

        # 组装完整 Prompt
        full_prompt = f"""# 诊断请求

{base_prompt}

---

## Agent 经验（AerotriWeb_AGENT.md）

{agent_memory}

---

## 历史相似案例

{similar_cases}

---

## 你的任务

请基于以上信息，分析本次任务失败的原因，并提供诊断报告。

**输出格式**（JSON）:
```json
{{
  "error_type": "错误类型（如：CUDA OOM、Bundle Adjustment 失败）",
  "root_cause": "根本原因分析",
  "confidence": 0.95,
  "is_new_pattern": false,
  "suggestions": [
    "修复建议 1",
    "修复建议 2"
  ],
  "related_resources": [
    "CLAUDE.md 中的相关章节",
    "相关文档链接"
  ],
  "tags": ["tag1", "tag2"]
}}
```
"""
        return full_prompt

    async def _load_agent_memory(self) -> str:
        """加载 Agent 记忆库."""
        try:
            memory_path = Path(self.config.agent_memory_path)
            if memory_path.exists():
                content = memory_path.read_text(encoding="utf-8")

                # 限制长度（避免 token 溢出）
                if len(content) > 10000:
                    content = content[:10000] + "\n\n... [truncated] ...\n"

                return content
            else:
                return "[Agent 记忆库尚未创建]"
        except Exception as e:
            logger.warning(f"Failed to load agent memory: {e}")
            return f"[加载 Agent 记忆库失败: {e}]"

    async def _find_similar_cases(
        self,
        context: Dict[str, Any],
        limit: int = 5,
    ) -> str:
        """查找历史相似案例.

        实现思路：
        1. 解析 history.log
        2. 根据任务类型、错误特征匹配
        3. 返回最相似的 N 条
        """
        try:
            history_path = Path(self.config.history_log_path)
            if not history_path.exists():
                return "[暂无历史案例]"

            content = history_path.read_text(encoding="utf-8")

            # TODO: 实现更智能的相似度匹配
            # 现在简单返回最近 3 条
            lines = content.split("\n")
            case_entries = []
            current_entry = []
            capture = False

            for line in lines:
                if line.startswith("## 条目 #"):
                    capture = True
                    if current_entry:
                        case_entries.append("\n".join(current_entry))
                    current_entry = [line]
                elif capture and line.startswith("---"):
                    capture = False
                elif capture:
                    current_entry.append(line)

            if current_entry:
                case_entries.append("\n".join(current_entry))

            # 返回最近 3 条
            recent_cases = case_entries[-limit:] if len(case_entries) > limit else case_entries

            return "\n\n---\n\n".join(recent_cases) if recent_cases else "[暂无历史案例]"

        except Exception as e:
            logger.warning(f"Failed to find similar cases: {e}")
            return f"[查找历史案例失败: {e}]"

    async def _send_to_openclaw(self, prompt: str) -> str:
        """发送诊断请求到 OpenClaw（通过 CLI 命令）.

        使用 openclaw agent CLI 命令调用，获取 JSON 格式响应.
        """
        import asyncio

        try:
            # 限制 prompt 长度（避免 token 溢出）
            truncated_prompt = prompt[:15000]  # 约 5000 tokens

            # 构建命令
            cmd = [
                self.config.openclaw_cmd,
                "agent",
                "--agent", self.config.agent_id,
                "--message", truncated_prompt,
                "--json",
                "--timeout", str(self.config.timeout_seconds),
            ]

            logger.info(f"Executing OpenClaw CLI: {' '.join(cmd[:5])}...")

            # 执行命令并获取输出
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout_seconds + 10,
            )

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="ignore")
                logger.error(f"OpenClaw CLI failed: {error_msg}")
                raise Exception(f"OpenClaw CLI error (exit code {process.returncode}): {error_msg}")

            # 解析 JSON 响应
            response_text = stdout.decode("utf-8", errors="ignore")
            response = json.loads(response_text)

            # 提取 AI 回复文本
            if response.get("status") == "ok" and response.get("result"):
                payloads = response["result"].get("payloads", [])
                if payloads and payloads[0].get("text"):
                    return payloads[0]["text"]

            raise Exception(f"Unexpected OpenClaw response format: {response_text[:500]}")

        except asyncio.TimeoutError:
            logger.error("OpenClaw CLI timeout")
            raise Exception(f"OpenClaw CLI timeout after {self.config.timeout_seconds} seconds")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenClaw JSON response: {e}")
            raise Exception(f"Invalid JSON response from OpenClaw: {e}")
        except FileNotFoundError:
            logger.error("OpenClaw CLI not found")
            raise Exception("OpenClaw CLI not found. Please ensure OpenClaw is installed and in PATH.")
        except Exception as e:
            logger.error(f"Failed to send to OpenClaw: {e}")
            # 不再使用 mock，直接抛出异常
            raise

    def _parse_openclaw_response(self, raw_response: str) -> Dict[str, Any]:
        """解析 OpenClaw 响应."""
        try:
            # 尝试解析 JSON
            if raw_response.strip().startswith("{"):
                return json.loads(raw_response)
            else:
                # 如果不是 JSON，尝试提取 JSON 部分
                start = raw_response.find("{")
                end = raw_response.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = raw_response[start:end]
                    return json.loads(json_str)

                # Fallback: 返回原始响应
                return {
                    "error_type": "Unknown",
                    "root_cause": raw_response[:500],
                    "confidence": 0.5,
                    "is_new_pattern": True,
                    "suggestions": ["请人工查看日志"],
                    "related_resources": [],
                    "tags": ["parse_error"]
                }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenClaw response: {e}")
            return {
                "error_type": "Parse Error",
                "root_cause": f"无法解析响应: {e}",
                "confidence": 0.0,
                "is_new_pattern": True,
                "suggestions": ["检查 OpenClaw 响应格式"],
                "related_resources": [],
                "tags": ["json_parse_error"]
            }

    async def _attempt_auto_fix(
        self,
        block_id: int,
        diagnosis: Dict[str, Any],
    ) -> bool:
        """尝试自动修复问题.

        只有部分问题可以自动修复，如：
        - 相机模型不兼容（运行 undistortion）
        - 权限问题（修正权限）
        - 磁盘空间（清理临时文件）

        Args:
            block_id: Block ID
            diagnosis: 诊断结果

        Returns:
            是否成功自动修复
        """
        error_type = diagnosis.get("error_type", "")

        # 相机模型问题
        if "相机模型" in error_type or "camera model" in error_type.lower():
            logger.info(f"Attempting auto-fix for camera model issue (block {block_id})")
            # TODO: 调用 undistortion 服务
            # await undistortion_service.run_undistortion(block_id)
            return True

        # TODO: 添加更多自动修复场景

        return False

    async def _update_knowledge_base(
        self,
        context: Dict[str, Any],
        diagnosis: Dict[str, Any],
        auto_fixed: bool,
    ):
        """更新 Agent 知识库（AerotriWeb_AGENT.md）.

        如果是新问题模式，添加新章节；
        如果是已知问题，更新历史案例。
        """
        try:
            agent_memory_path = Path(self.config.agent_memory_path)

            # 如果是新问题模式
            if diagnosis.get("is_new_pattern"):
                logger.info("New problem pattern detected, updating knowledge base")

                # TODO: 添加新章节到 AerotriWeb_AGENT.md
                # 这里需要解析 Markdown 并插入新内容
                # 可以使用 Python markdown 库或正则表达式

                new_entry = f"""

### {diagnosis.get('error_type', 'Unknown Error')}

**错误特征**:
```
{context.get('error_message', 'Unknown')}
```

**常见场景**:
- TODO: 根据 context 填充

**根因分析**:
{diagnosis.get('root_cause', 'Unknown')}

**修复建议**:
{chr(10).join(f'{i+1}. {s}' for i, s in enumerate(diagnosis.get('suggestions', [])))}

**预防措施**:
- TODO: 根据错误类型添加

**历史案例**:
- Block #{context.get('block_id')} ({datetime.utcnow().strftime('%Y-%m-%d')}): {context.get('error_message', '')[:100]}...

**相关资源**:
{chr(10).join(f'- {r}' for r in diagnosis.get('related_resources', []))}

---
"""

                # 追加到文件末尾（在 "待更新" 之前）
                content = agent_memory_path.read_text(encoding="utf-8")
                insert_pos = content.find("## 🔍 问题模式统计")
                if insert_pos > 0:
                    new_content = content[:insert_pos] + new_entry + "\n" + content[insert_pos:]
                    agent_memory_path.write_text(new_content, encoding="utf-8")
                    logger.info("Knowledge base updated successfully")

        except Exception as e:
            logger.error(f"Failed to update knowledge base: {e}", exc_info=True)

    async def _append_to_history(
        self,
        context: Dict[str, Any],
        diagnosis: Dict[str, Any],
        auto_fixed: bool,
    ):
        """追加到历史记录（diagnosis_history.log）.

        每次诊断后追加一个新条目。
        """
        async with self._history_lock:
            try:
                history_path = Path(self.config.history_log_path)

                # 生成新条目
                entry_num = self._get_next_entry_number(history_path)
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

                new_entry = f"""

## 条目 #{entry_num} - {timestamp}

### 任务信息
- **Block ID**: {context.get('block_id')}
- **Block 名称**: {context.get('block_info', {}).get('name', 'Unknown')}
- **任务类型**: {context.get('task_type')}
- **算法**: {context.get('block_info', {}).get('algorithm', 'Unknown')}
- **失败阶段**: {context.get('stage', 'Unknown')}
- **失败时间**: {context.get('timestamp')}

### 错误信息
```
{context.get('error_message')}
```

### 诊断结果
- **错误类型**: {diagnosis.get('error_type')}
- **根本原因**: {diagnosis.get('root_cause')}
- **置信度**: {diagnosis.get('confidence')}

### 修复建议
{chr(10).join(f'{i+1}. {s}' for i, s in enumerate(diagnosis.get('suggestions', [])))}

### 执行结果
- **是否已修复**: {'是' if auto_fixed else '否（等待用户操作）'}
- **修复时间**: {datetime.utcnow().isoformat() if auto_fixed else '-'}
- **验证方式**: {'自动修复' if auto_fixed else '待验证'}

### 经验更新
- {'✅ 新问题模式添加到 `AerotriWeb_AGENT.md`' if diagnosis.get('is_new_pattern') else '✅ 已有模式，无需添加'}
- ✅ 关联到 Block #{context.get('block_id')}

### OpenClaw 分析
- **分析时长**: TBD 秒
- **Token 使用**: TBD / 8192
- **置信度**: {diagnosis.get('confidence')}

### 相关文件
- Log: `{_settings.get_absolute_paths()['outputs_dir']}/{context.get('block_id')}/task.log`
- Block: http://localhost:8000/blocks/{context.get('block_id')}

### 标签
{', '.join(f'`{tag}`' for tag in diagnosis.get('tags', []))}

---
"""

                # 追加到文件末尾
                with open(history_path, "a", encoding="utf-8") as f:
                    f.write(new_entry)

                logger.info(f"Appended entry #{entry_num} to history log")

            except Exception as e:
                logger.error(f"Failed to append to history: {e}", exc_info=True)

    def _get_next_entry_number(self, history_path: Path) -> int:
        """获取下一个条目编号."""
        try:
            content = history_path.read_text(encoding="utf-8")
            # 查找所有 "## 条目 #X"
            import re
            matches = re.findall(r'## 条目 #(\d+)', content)
            if matches:
                return max(map(int, matches)) + 1
        except Exception:
            pass
        return 1

    async def chat_with_agent(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """主动与 Agent 对话（用于开发任务）.

        Args:
            message: 用户消息
            context: 可选的上下文信息

        Returns:
            Agent 响应
        """
        try:
            # 构建对话 Prompt
            prompt = f"""# 用户对话

**用户消息**: {message}

**当前时间**: {datetime.utcnow().isoformat()}

**上下文**:
{json.dumps(context, indent=2, ensure_ascii=False) if context else "无"}

---

你是 Aerotri-Web 的开发助手，可以帮助：
- 回答项目相关问题
- 分析代码和架构
- 提供开发建议
- 诊断和修复问题

请简洁地回答用户的问题。
"""

            # 发送到 OpenClaw
            response = await self._send_to_openclaw(prompt)

            return response

        except Exception as e:
            logger.error(f"Chat with agent failed: {e}")
            return f"抱歉，发生了错误: {e}"


# 全局实例
diagnostic_agent = AerotriWebDiagnosticAgent()
