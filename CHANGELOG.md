# Changelog

All notable changes to Aerotri-Web will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- AI-Collaborated Development documentation and workflows
- Diagnostic Agent with OpenClaw integration
- Intelligent task failure diagnosis and auto-fix capabilities
- Documentation structure for open-source release
- GitHub templates (Bug Report, Feature Request, PR Template)

### Changed
- Migrated configuration system to YAML-based multi-layer config
- Improved error handling and logging throughout the system
- Enhanced GPU monitoring and allocation

### Fixed
- Camera model compatibility for 3DGS training
- Partition merge ID overflow issues
- Georeferencing coordinate system transforms

## [1.0.0] - 2025-02-09

### Added
- Multi-algorithm SfM support (COLMAP, GLOMAP, InstantSfM, OpenMVG)
- OpenMVS dense reconstruction pipeline
- 3D Gaussian Splatting training integration
- 3D Tiles conversion (OpenMVS and 3DGS)
- Georeferencing support (GPS → UTM → ENU)
- Partition SfM for large datasets
- Real-time progress tracking via WebSocket
- GPU monitoring and allocation
- Queue management with concurrency control
- Version management for reconstructions

### Features
- **SfM Algorithms**:
  - COLMAP incremental SfM with pose prior support
  - GLOMAP global SfM with mapper_resume optimization
  - InstantSfM fast global SfM with real-time visualization
  - OpenMVG CPU-friendly global SfM with automatic thread/memory adaptation

- **Dense Reconstruction**:
  - OpenMVS densify, mesh, refine, and texture stages
  - Multiple reconstruction versions per Block
  - Version-level 3D Tiles conversion

- **3D Gaussian Splatting**:
  - Training orchestration with auto-undistortion
  - PLY output and iteration checkpoints
  - SPZ compression for 3D Tiles

- **Georeferencing**:
  - EXIF GPS extraction using exiftool
  - GPS → UTM → ENU coordinate conversion
  - COLMAP model_aligner integration
  - Automatic transform injection for 3D Tiles

- **Partition Processing**:
  - Name range with overlap strategy
  - Multiple merge strategies (rigid_keep_one, sim3_keep_one)
  - ID remapping to prevent overflow

### Architecture
- **Backend**: FastAPI + SQLAlchemy + Async SQLite
- **Frontend**: Vue 3 + TypeScript + Pinia
- **Communication**: WebSocket for real-time updates
- **Visualization**: Three.js + CesiumJS integration

---

[Unreleased]: https://github.com/your-org/aerotri-web/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/aerotri-web/releases/tag/v1.0.0
