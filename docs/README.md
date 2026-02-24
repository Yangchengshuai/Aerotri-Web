# Aerotri-Web 文档

欢迎使用 Aerotri-Web 文档！这里包含了项目的完整使用和开发指南。

## 📚 快速导航

### 🚀 快速上手

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [快速开始](./01-quickstart/) | 5 分钟快速体验 | 所有用 |
| [安装指南](./02-installation/) | 详细安装步骤和依赖 | 新用户 |
| [配置指南](./CONFIGURATION.md) | 完整配置系统说明 | 所有用户 |

### 👥 用户文档

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [用户指南](./03-user-guide/) | 功能使用说明 | 所有用户 |
| [算法文档](./04-algorithms/) | 算法详解和参数配置 | 高级用户 |
| [监控配置](./NOTIFICATION_SETUP.md) | 通知和诊断服务配置 | 运维人员 |

### 🛠️ 开发文档

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [开发指南](./05-development/) | 架构和开发流程 | 开发者 |
| [贡献指南](./07-contribution/) | 如何参与贡献 | 贡献者 |
| [AI 协作](./06-ai-collaboration/) | AI 协作理念和案例 | AI 工程师 |

### 📋 参考资料

| 文档 | 说明 |
|------|------|
| [特性详解](./FEATURES.md) | 所有功能详细说明 |
| [系统架构](./ARCHITECTURE.md) | 技术架构和设计 |
| [依赖说明](./DEPENDENCIES.md) | 第三方库和工具 |
| [开发路线图](./ROADMAP.md) | 未来规划 |
| [配置迁移](./MIGRATION.md) | 旧配置迁移指南 |
| [常见问题](./08-appendix/) | FAQ 和故障排查 |

## 🔍 按主题查找

### 算法相关

- [COLMAP](./04-algorithms/#colmap) - 增量式 SfM，适合常规摄影测量
- [GLOMAP](./04-algorithms/#glomap) - 全局式 SfM，适合大规模数据集
- [InstantSfM](./04-algorithms/#instantsfm) - 快速 SfM，支持实时可视化
- [OpenMVG](./04-algorithms/#openmvg) - CPU 友好 SfM
- [OpenMVS](./04-algorithms/#openmvs) - 密集重建、网格、纹理
- [3D Gaussian Splatting](./04-algorithms/#d-gaussian-splatting) - 高质量 3D 渲染

### 配置相关

- [应用配置](./CONFIGURATION.md/#配置分类详解) - 路径、数据库、算法配置
- [环境变量](./CONFIGURATION.md/#环境变量) - 完整环境变量列表
- [通知服务](./NOTIFICATION_SETUP.md) - 钉钉/飞书配置
- [诊断 Agent](./NOTIFICATION_SETUP.md/#ai诊断agent通知) - OpenClaw 集成

### 高级功能

- [分区处理](./03-user-guide/#分区处理) - 大数据集分区和合并
- [模型对比](./FEATURES.md/#模型对比) - Block 和版本对比
- [地理参考](./03-user-guide/#地理参考) - GPS 坐标转换
- [3D Tiles](./FEATURES.md/#d-tiles-转换) - 3D Tiles 转换和部署
- [任务队列](./FEATURES.md/#任务队列) - 队列管理和并发控制

## 🎯 学习路径

### 新手用户

1. 阅读 [快速开始](./01-quickstart/)
2. 查看 [演示视频](../README.md/#-演示)
3. 学习 [用户指南](./03-user-guide/)
4. 了解 [算法文档](./04-algorithms/)

### 运维人员

1. 阅读 [安装指南](./02-installation/)
2. 配置 [应用配置](./CONFIGURATION.md/)
3. 配置 [监控服务](./NOTIFICATION_SETUP.md/)
4. 学习 [故障排查](./08-appendix/)

### 开发者

1. 阅读 [开发指南](./05-development/)
2. 了解 [系统架构](./ARCHITECTURE.md/)
3. 查看 [依赖说明](./DEPENDENCIES.md/)
4. 学习 [贡献指南](./07-contribution/)

### AI 工程师

1. 阅读 [AI 协作理念](./06-ai-collaboration/philosophy.md) - 核心原则
2. 学习 [AI 协作最佳实践](./06-ai-collaboration/best-practices.md) - 34条实战经验
3. 查看 [AI 开发方法论](./06-ai-collaboration/ai-development-methodology.md) - 95% 自动化路径 ⭐ 新
4. 阅读 [案例研究](./06-ai-collaboration/case-studies/) - 实际应用案例
5. 了解 [诊断 Agent](./NOTIFICATION_SETUP.md/#ai诊断agent通知) - 智能诊断系统

## 🆘 获取帮助

### 快速解决

- [常见问题](./08-appendix/) - FAQ 和快速解决方案
- [配置迁移](./MIGRATION.md) - 从旧版本升级
- [故障排查](./02-installation/#故障排查) - 安装和配置问题

### 深入学习

- [算法选择指南](./04-algorithms/#算法选择指南) - 如何选择合适的算法
- [参数调优](./04-algorithms/) - 各算法参数详解
- [API 文档](./05-development/#api-文档) - 完整 API 参考

### 社区支持

- [GitHub Issues](https://github.com/Yangchengshuai/Aerotri-Web/issues) - 问题反馈
- [GitHub Discussions](https://github.com/Yangchengshuai/Aerotri-Web/discussions) - 功能讨论
- 邮件: yyccssyyds@gmail.com

## 📝 文档反馈

发现文档问题？欢迎：

1. 直接提交 PR 修复
2. 在 Issues 中提出改进建议
3. 联系维护者

---

**最后更新**: 2026-02-16
