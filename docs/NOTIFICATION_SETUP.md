# AeroTri Web 通知服务配置指南

本文档介绍如何配置 AeroTri Web 的通知服务，包括钉钉（DingTalk）和飞书（Feishu）机器人的设置。

## 目录

- [概述](#概述)
- [快速开始](#快速开始)
- [钉钉机器人配置](#钉钉机器人配置)
- [飞书机器人配置](#飞书机器人配置)
- [通知事件类型](#通知事件类型)
- [多通道配置](#多通道配置)
- [AI诊断Agent通知](#ai诊断agent通知)
- [故障排查](#故障排查)

---

## 概述

AeroTri Web 通知服务用于在系统关键事件发生时发送实时通知到钉钉或飞书群聊。

**主要功能：**
- **任务生命周期通知**：任务开始、完成、失败
- **系统状态监控**：后端启动/关闭、系统资源状态
- **AI诊断结果**：任务失败时的智能诊断分析和修复建议
- **周期性报告**：任务汇总、系统健康检查

**设计原则：**
- **可选启用**：默认禁用，不影响主流程
- **优雅降级**：通知发送失败不会阻塞业务逻辑
- **多通道支持**：可配置多个群聊接收不同类型的通知
- **签名验证**：支持钉钉机器人签名加密（推荐生产环境）

---

## 快速开始

### 1. 启用通知服务

复制示例配置文件并启用：

```bash
cd aerotri-web/backend/config
cp notification.yaml.example notification.yaml
```

编辑 `notification.yaml`，将全局开关设为 `true`：

```yaml
notification:
  enabled: true  # 改为 true 启用通知服务
  dingtalk:
    channels:
      block_events:
        enabled: true
        webhook_url: "你的钉钉机器人Webhook URL"
        secret: "你的钉钉机器人加签密钥"
        events:
          - task_started
          - task_completed
          - task_failed
```

### 2. 重启后端服务

```bash
# 开发环境
cd aerotri-web/backend
uvicorn app.main:app --reload

# 生产环境（使用 systemd）
sudo systemctl restart aerotri-web
```

### 3. 验证通知

后端启动时会发送启动通知（如果配置了 `backend_startup` 事件），检查群聊是否收到消息。

---

## 钉钉机器人配置

### 创建钉钉机器人

1. **打开群聊设置**
   - 进入需要接收通知的钉钉群
   - 点击右上角 "..." → "群设置"
   - 选择 "智能群助手" → "添加机器人"

2. **选择机器人类型**
   - 选择 "自定义" 机器人
   - 点击 "添加"

3. **配置机器人**
   - 机器人名称：例如 "AeroTri通知"
   - 安全设置：
     - **方式一：加签（推荐）** - 勾选 "加签"，复制密钥
     - **方式二：自定义关键词** - 添加关键词如 "任务"、"通知"、"AeroTri"
     - **方式三：IP地址** - 填入服务器IP（不推荐动态IP）

4. **获取Webhook地址**
   - 创建完成后复制 Webhook 地址
   - 格式：`https://oapi.dingtalk.com/robot/send?access_token=xxx`

### 配置文件示例

```yaml
notification:
  enabled: true

  dingtalk:
    channels:
      # 任务事件通知群
      block_events:
        enabled: true
        webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
        secret: "SECxxxxxxxxxxxxx"  # 加签密钥（可选但推荐）
        events:
          - task_started
          - task_completed
          - task_failed

      # 系统监控群
      backend_status:
        enabled: true
        webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
        secret: "SECxxxxxxxxxxxxx"
        events:
          - system_status
          - backend_startup
          - backend_shutdown
```

### 签名验证原理

钉钉机器人使用 HMAC-SHA256 签名验证请求的合法性：

```python
# 伪代码
timestamp = current_timestamp_millis
string_to_sign = f"{timestamp}\n{secret}"
hmac_code = hmac_sha256(secret, string_to_sign)
sign = base64_encode(hmac_code)
url_encode(sign)
```

后端会自动计算签名并附加到请求URL中，无需手动配置。

---

## 飞书机器人配置

> **注意**：飞书支持正在开发中，当前版本暂未实现。

### 创建飞书机器人（预留）

1. **打开群聊设置**
   - 进入飞书群
   - 点击右上角 "..." → "群机器人"
   - 选择 "添加机器人"

2. **创建自定义机器人**
   - 机器人名称：例如 "AeroTri通知"
   - 描述：任务通知和系统监控

3. **获取Webhook地址**
   - 复制 Webhook URL
   - 格式：`https://open.feishu.cn/open-apis/bot/v2/hook/xxx`

### 配置文件示例（预留）

```yaml
notification:
  enabled: true

  feishu:
    enabled: true  # 暂未实现
    channels:
      block_events:
        enabled: true
        webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_URL"
        verify_key: "your_verify_key"  # 签名验证密钥
        events:
          - task_started
          - task_completed
          - task_failed
```

---

## 通知事件类型

### 任务事件

| 事件类型 | 触发时机 | 建议群组 |
|---------|---------|---------|
| `task_started` | 任务开始执行 | 任务执行群 |
| `task_completed` | 任务成功完成 | 任务执行群 |
| `task_failed` | 任务执行失败 | 任务执行群 + 运维群 |

**消息示例（task_failed）：**

```markdown
### 任务失败

**Block**: 测试项目_20250211

**任务类型**: SfM 空三

**失败阶段**: mapper

**运行时长**: 15.2分钟

**错误信息**:
```
RuntimeError: CUDA out of memory. Tried to allocate 2.5GB
```

---

### 🤖 AI 诊断分析

**错误类型**: GPU内存不足

**根本原因**: 数据集包含5000+高分辨率图像，超出GPU显存限制

**修复建议**:
1. 降低 `Mapper.max_num_images` 参数到 3000
2. 使用分区模式处理大型数据集
3. 更换到显存更大的GPU（至少24GB）
4. 启用深度图补全减少内存占用
```

### 后端事件

| 事件类型 | 触发时机 | 建议群组 |
|---------|---------|---------|
| `backend_startup` | 后端服务启动 | 运维监控群 |
| `backend_shutdown` | 后端服务正常关闭 | 运维监控群 |
| `backend_error` | 后端发生未捕获异常 | 运维监控群 |

### 周期性报告

| 事件类型 | 触发时机 | 建议群组 |
|---------|---------|---------|
| `system_status` | 定时检查系统资源 | 运维监控群 |
| `periodic_task_summary` | 每日任务汇总 | 项目管理群 |

**配置定时任务：**

```yaml
notification:
  periodic:
    system_status:
      enabled: true
      interval: 14400  # 每4小时（秒）

    task_summary:
      enabled: true
      cron: "0 21 * * *"  # 每天21:00
```

---

## 多通道配置

通知服务支持配置多个独立的通道，每个通道可以：
- 接收不同类型的事件
- 发送到不同的群聊
- 独立启用/禁用

### 推荐的多群组架构

```yaml
notification:
  enabled: true

  dingtalk:
    channels:
      # 通道1: 实时任务通知（面向任务执行人员）
      task_team:
        enabled: true
        webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=TASK_TEAM_TOKEN"
        secret: "TASK_TEAM_SECRET"
        events:
          - task_started
          - task_completed
          - task_failed

      # 通道2: 系统监控（面向运维人员）
      ops_team:
        enabled: true
        webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=OPS_TEAM_TOKEN"
        secret: "OPS_TEAM_SECRET"
        events:
          - backend_startup
          - backend_shutdown
          - backend_error
          - system_status

      # 通道3: AI诊断（面向开发人员）
      dev_team:
        enabled: true
        webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=DEV_TEAM_TOKEN"
        secret: "DEV_TEAM_SECRET"
        events:
          - task_failed  # 包含AI诊断结果
          - diagnosis_completed
```

### 事件路由规则

- 一个事件可以发送到多个通道
- 每个通道独立检查是否订阅了该事件
- 通道禁用时不会发送任何通知

---

## AI诊断Agent通知

AeroTri Web 集成了 AI 诊断 Agent，任务失败时会自动调用 OpenClaw 进行智能分析，并将诊断结果包含在通知中。

### 启用AI诊断

编辑 `backend/config/settings.yaml`：

```yaml
diagnostic:
  enabled: true  # 启用AI诊断
  openclaw_cmd: "openclaw"
  agent_id: "main"
  timeout_seconds: 60
  auto_fix: false  # 谨慎启用自动修复
```

### 诊断结果通知

当任务失败且 AI 诊断完成时，`task_failed` 通知会包含额外的诊断信息：

```markdown
### 任务失败
...
**错误信息**:
```
RuntimeError: Camera model not supported
```

---

### 🤖 AI 诊断分析

**错误类型**: 相机模型不兼容

**根本原因**: COLMAP 使用了 OPENCV 模型，但 3DGS 仅支持 PINHOLE/SIMPLE_PINHOLE

**修复建议**:
1. 运行 `image_undistorter` 进行相机模型转换
2. 或在 SfM 参数中指定 `camera_model: SIMPLE_PINHOLE`
3. 重新运行 3DGS 训练
```

### OpenClaw 配置（可选）

如果使用 OpenClaw 进行诊断，可以进一步配置其通知功能：

```bash
# 安装 OpenClaw
npm install -g openclaw

# 配置 OpenClaw 机器人
openclaw config set dingtalk.webhook_url "YOUR_WEBHOOK_URL"
openclaw config set dingtalk.secret "YOUR_SECRET"
openclaw config set feishu.webhook_url "YOUR_FEISHU_URL"

# 验证配置
openclaw config list
```

OpenClaw 可以独立于 AeroTri Web 发送通知，适用于：
- AI 诊断完成时的额外通知
- OpenClaw 自身的状态监控
- 开发调试时的实时反馈

---

## 故障排查

### 问题1：通知未发送

**检查步骤：**

1. 确认通知服务已启用：
   ```bash
   # 检查配置文件
   cat aerotri-web/backend/config/notification.yaml | grep "enabled: true"
   ```

2. 检查后端日志：
   ```bash
   # 应该看到以下日志
   tail -f aerotri-web/backend/logs/app.log | grep -i notification
   # 输出示例:
   # INFO - NotificationManager initialized successfully
   # INFO - DingTalk message sent to block_events
   ```

3. 验证 Webhook URL 和密钥：
   - 在钉钉群中手动删除并重新创建机器人
   - 确认复制了完整的 URL 和密钥

### 问题2：钉钉报错 "sign not match"

**原因**：签名密钥配置错误

**解决方案**：
1. 在钉钉机器人设置中重新复制密钥（SEC 开头）
2. 确认密钥中没有多余空格
3. 验证系统时间是否准确（签名依赖时间戳）

### 问题3：通知被限流

**钉钉限流规则**：
- 每个机器人每分钟最多发送 20 条消息
- 超过后会返回 `errcode: 130101`

**解决方案**：
- 使用多通道分散通知
- 配置合理的通知频率（避免每个任务阶段都通知）
- 汇总通知而非实时通知

```yaml
notification:
  dingtalk:
    rate_limit: 15  # 每分钟最多15条（保守设置）
```

### 问题4：AI诊断未显示

**检查诊断是否启用：**
```bash
# 检查 settings.yaml
cat aerotri-web/backend/config/settings.yaml | grep -A 5 "diagnostic:"

# 应该看到 enabled: true
```

**检查 OpenClaw 是否可用：**
```bash
# 测试 OpenClaw CLI
openclaw --version

# 测试诊断功能
cd aerotri-web/backend
python -c "
import asyncio
from app.services.openclaw_diagnostic_agent import AerotriWebDiagnosticAgent
agent = AerotriWebDiagnosticAgent()
print('OpenClaw initialized successfully')
"
```

**查看诊断日志：**
```bash
# 诊断历史
cat aerotri-web/backend/data/diagnostics/diagnosis_history.log

# 调试日志
tail -f aerotri-web/backend/logs/app.log | grep -i diagnosis
```

### 问题5：敏感信息泄露

**建议**：
- Webhook URL 包含 `access_token`，不要提交到 Git
- `secret` 密钥应妥善保管
- 使用环境变量替代配置文件：

```bash
export DINGTALK_WEBHOOK_BLOCK="https://oapi.dingtalk.com/robot/send?access_token=xxx"
export DINGTALK_SECRET_BLOCK="SECxxxxx"
```

然后在配置文件中引用：
```yaml
dingtalk:
  channels:
    block_events:
      webhook_url: "${DINGTALK_WEBHOOK_BLOCK}"
      secret: "${DINGTALK_SECRET_BLOCK}"
```

---

## 配置文件完整示例

```yaml
# AeroTri Web 通知配置
# 位置: aerotri-web/backend/config/notification.yaml

notification:
  # 全局开关
  enabled: true

  # 钉钉多通道配置
  dingtalk:
    channels:
      # 任务执行群
      block_events:
        enabled: true
        webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=XXX"
        secret: "SECXXX"
        events:
          - task_started
          - task_completed
          - task_failed

      # 运维监控群
      ops_monitor:
        enabled: true
        webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=YYY"
        secret: "SECYYY"
        events:
          - system_status
          - backend_startup
          - backend_shutdown
          - backend_error

      # AI诊断群（开发人员）
      ai_diagnosis:
        enabled: true
        webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=ZZZ"
        secret: "SECZZZ"
        events:
          - diagnosis_completed

  # 飞书配置（预留）
  feishu:
    enabled: false
    channels: {}

  # 周期性报告
  periodic:
    task_summary:
      enabled: true
      cron: "0 21 * * *"  # 每天21:00

    system_status:
      enabled: true
      interval: 14400  # 每4小时
```

---

## 参考链接

- [钉钉开放平台 - 自定义机器人](https://open.dingtalk.com/document/robots/custom-robot-access)
- [飞书开放平台 - 机器人](https://open.feishu.cn/document/ukTMukTMukTM/uEjNwUjLxYDM14SM2ATN)
- [OpenClaw 文档](https://github.com/fengbopenclaw/openclaw)
