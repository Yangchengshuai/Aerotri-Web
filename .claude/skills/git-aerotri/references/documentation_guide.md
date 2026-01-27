# Documentation Update Guidelines

## Documentation Files

This skill updates the following documentation files based on code changes:

1. **CLAUDE.md** (root `/root/work/Aerotri-Web/CLAUDE.md`)
   - Project overview and architecture
   - Core components and features
   - Development commands
   - Environment variables
   - API endpoints
   - Implementation details

2. **README.md** (root `/root/work/Aerotri-Web/README.md`)
   - Project overview (Chinese)
   - Feature list
   - Quick start guide
   - Directory structure

3. **aerotri-web/CLAUDE.md** (`/root/work/Aerotri-Web/aerotri-web/CLAUDE.md`)
   - Aerotri Web specific architecture
   - Backend/frontend structure
   - API documentation
   - Key patterns

4. **aerotri-web/README.md** (`/root/work/Aerotri-Web/aerotri-web/README.md`)
   - Aerotri Web specific documentation (Chinese)
   - Installation and setup
   - Environment variables
   - API endpoints

## When to Update Documentation

Update documentation when:

### Backend Changes
- New API endpoints added → Update API endpoints section
- New service/runner created → Update architecture overview
- New configuration options → Update environment variables
- New task types → Add to common patterns
- Database model changes → Update models section

### Frontend Changes
- New components added → Update component list
- New views added → Update views section
- New stores added → Update state management
- API changes → Update API client section

### Algorithm Changes
- New algorithm support → Update algorithm pipeline
- New parameters → Update parameter documentation
- New features → Update feature list

## Update Patterns

### Adding New API Endpoints
```markdown
**New Feature:**
- `POST /api/blocks/{id}/new-endpoint` - Description of what it does
```

### Adding New Parameters
```markdown
### Algorithm Name
- `new_param`: Description (default: value, range: min-max)
```

### Adding New Services
```markdown
**Core Services:**
- `new_service.py` - Description of what it does
```

## Documentation Structure

### CLAUDE.md (Root)
```markdown
## Project Overview
## Development Commands
## Architecture Overview
### Backend Architecture
### Frontend Architecture
### Algorithm Pipeline Flow
## Environment Variables
## Key API Endpoints
## Important Implementation Details
## File Structure Conventions
## Common Patterns
## Testing
```

### README.md (Root)
```markdown
## 项目总览
## 目录结构
## 文档
## AeroTri Web 功能概览
## 快速开始
## 许可证
```

### aerotri-web/CLAUDE.md
```markdown
## Project Overview
## Development Commands
## High-Level Architecture
### Backend Structure
### Frontend Structure
## Key Architectural Patterns
### Task-Based Processing Model
### Algorithm Abstraction
### Version Management
## Environment Variables
## Data Flow
## Important Implementation Details
## Common Modification Patterns
## File Organization Conventions
```

### aerotri-web/README.md
```markdown
## 功能特性
## 技术栈
## 快速开始
### 后端启动
### 前端启动
## 环境变量
## API 文档
## 目录结构
## 使用流程
## 3D Tiles 转换
## 3DGS 训练与预览
## 支持的算法参数
## 许可证
```
