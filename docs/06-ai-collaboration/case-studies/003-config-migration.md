# Case Study #003: 配置系统迁移

> **问题**: 硬编码路径和参数导致维护困难
> **解决方案**: 多层配置系统 (环境变量 > YAML > 默认值)
> **关键决策**: 使用 Pydantic 进行配置验证

---

## 背景

### 问题

1. 路径硬编码在代码中，难以修改
2. 不同环境需要不同配置
3. 配置错误导致运行时失败

---

## 技术方案

### 配置优先级

```
环境变量 > YAML 配置 > 默认值
```

### 代码实现

**文件**: `aerotri-web/backend/app/config.py`

```python
from pydantic import BaseModel
from typing import Optional
import yaml
import os

class Settings(BaseModel):
    """应用配置."""

    # 数据库
    db_path: str = "/root/work/aerotri-web/data/aerotri.db"

    # 图像根路径
    image_root: Optional[str] = None
    image_roots: Optional[str] = None

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "Settings":
        """从 YAML 文件加载配置."""
        with open(yaml_path) as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data)

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量加载配置."""
        return cls(
            db_path=os.getenv("AEROTRI_DB_PATH", cls.db_path),
            image_root=os.getenv("AEROTRI_IMAGE_ROOT"),
            image_roots=os.getenv("AEROTRI_IMAGE_ROOTS"),
        )
```

---

## 经验总结

### 1. 向后兼容

```python
# 支持旧的环境变量
image_root = os.getenv("AEROTRI_IMAGE_ROOT")  # 单路径（兼容）
image_roots = os.getenv("AEROTRI_IMAGE_ROOTS")  # 多路径（新功能）
```

### 2. 验证机制

```python
class Settings(BaseModel):
    image_roots: List[str] = []

    @validator("image_roots")
    def validate_paths(cls, v):
        """验证路径是否存在."""
        return [p for p in v if os.path.exists(p)]
```

---

**相关文件**:
- `app/config.py` - 配置类
- `backend/config/settings.yaml` - 配置文件
- `backend/config/defaults.yaml` - 默认值

