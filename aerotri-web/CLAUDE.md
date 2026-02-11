# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AeroTri Web is a web-based aerial triangulation tool for photogrammetry applications. It provides processing of image collections using multiple SfM (Structure-from-Motion) algorithms including COLMAP, GLOMAP, InstantSfM, and OpenMVG, with support for 3D reconstruction (OpenMVS), 3D Gaussian Splatting training, and 3D Tiles conversion.

**Architecture**: Frontend-backend separation with Vue 3 + TypeScript frontend and FastAPI + Python backend.

## Development Commands

### Backend Development
```bash
cd backend
# 安装核心依赖
pip install fastapi uvicorn sqlalchemy pydantic aiofiles python-multipart pyproj numpy scipy opencv-python
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev          # Start dev server on port 3000
npm run build        # Production build
npm run test         # Run vitest tests
npm run lint         # Run ESLint
```

### Testing
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

### API Documentation
Start the backend and visit http://localhost:8000/docs for Swagger API documentation.

## High-Level Architecture

### Backend Structure (`/backend`)

**Entry Point**: `backend/app/main.py` - FastAPI application with lifespan management for service initialization and recovery.

**Core Services** (`backend/app/services/`):
- `task_runner.py` - Core SfM execution service (COLMAP/GLOMAP/InstantSfM/OpenMVG) with georeferencing support
- `openmvs_runner.py` - OpenMVS dense reconstruction pipeline
- `gs_runner.py` - 3D Gaussian Splatting training orchestration
- `tiles_runner.py` - 3D Tiles conversion (OBJ/GLB → 3D Tiles) with version support and georef transform injection
- `gs_tiles_runner.py` - 3DGS PLY → 3D Tiles with SPZ compression
- `queue_scheduler.py` - Automatic task dispatching with concurrency control
- `gpu_service.py` - Real-time GPU monitoring and allocation (lazy pynvml loading)
- `partition_service.py` - Large dataset partitioning logic
- `sfm_merge_service.py` - Partition result merging
- `result_reader.py` - COLMAP binary format parsing (cameras, images, points)
- `log_parser.py` - Real-time progress tracking from algorithm logs
- `notification.py` - Task notification service (startup/shutdown, task lifecycle events)
- `task_notifier.py` - Task event notifier (start/complete/fail)

**API Layer** (`backend/app/api/`): RESTful endpoints organized by domain (blocks, queue, reconstruction, tiles, georef, system, unified_tasks, etc.)

**WebSocket Layer** (`backend/app/ws/`):
- `/ws/blocks/{id}/progress` - Real-time progress updates
- `/ws/blocks/{id}/visualization` - InstantSfM live visualization proxy

**Models** (`backend/app/models/`): SQLAlchemy ORM models with async SQLite backend

### Frontend Structure (`/frontend`)

**State Management** (`frontend/src/stores/`):
- `blocks.ts` - Block list and detail state
- `gpu.ts` - GPU monitoring state
- `queue.ts` - Queue management state
- `cameraSelection.ts` - 3D viewer camera selection state

**API Client** (`frontend/src/api/`): Axios-based API client with type-safe interfaces

**Components** (`frontend/src/components/`):
- `BlockCard.vue` - Block list item
- `ParameterForm.vue` - Dynamic parameter forms based on algorithm type
- `ReconstructionPanel.vue` - OpenMVS reconstruction controls
- `TilesConversionPanel.vue` - 3D Tiles conversion UI
- `ThreeJSScene.vue` - 3D visualization (camera poses + point cloud)

**Views** (`frontend/src/views/`):
- `HomeView.vue` - Main block list and management
- `ReconCompareView.vue` - Side-by-side reconstruction comparison

## Key Architectural Patterns

### Task-Based Processing Model
Each Block represents a photogrammetry processing task with:
- **Multi-stage pipelines**: Feature extraction → Matching → Mapping → Reconstruction
- **Queue System**: Blocks can be queued with automatic dispatching based on `max_concurrent` setting
- **Progress Tracking**: Real-time via WebSocket + log parsing
- **Orphan Recovery**: Services recover incomplete tasks on startup

### Algorithm Abstraction
The system provides a unified interface for multiple SfM algorithms:
- **COLMAP**: Incremental SfM with pose prior support
- **GLOMAP**: Global SfM with mapper_resume optimization (iterate on existing COLMAP results)
- **InstantSfM**: Fast global SfM with real-time visualization
- **OpenMVG**: CPU-friendly global SfM with automatic thread/memory adaptation

### Version Management
- **SfM Versions**: GLOMAP mapper_resume creates new Block versions (linked via `parent_block_id`, `version_index`)
- **Reconstruction Versions**: Multiple OpenMVS reconstructions per Block with independent parameters/outputs
- **Version-level 3D Tiles**: Each reconstruction version can have its own 3D Tiles conversion with independent status/progress
- Both types support parameter comparison and result analysis
- Frontend uses `BrushCompareViewer` (CesiumJS-based) for side-by-side version comparison
  - Uses single Cesium viewer with `splitDirection` for true split-screen rendering (LEFT/RIGHT)
  - More performant than dual-viewer approach, shared camera for synchronized viewing
  - Supports draggable divider to adjust viewport split ratio

### Service Orchestration
Services are singletons managed at module level:
- Each runner (`task_runner`, `openmvs_runner`, `gs_runner`, `tiles_runner`) maintains its own task state
- `queue_scheduler` coordinates dispatching across all runners
- Services expose async methods for API layer to call

### WebSocket Communication
- **Progress Channel**: Broadcasts stage changes, progress updates, completion
- **Visualization Channel**: Proxies InstantSfM viser server for real-time 3D updates
- Connection managed via `aiohttp` WebSocketClientProtocol

## Environment Variables

### Backend Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `AEROTRI_DB_PATH` | SQLite database path | `/root/work/aerotri-web/data/aerotri.db` |
| `AEROTRI_IMAGE_ROOT` | Image browsing root | `/mnt/work_odm/chengshuai` |
| `COLMAP_PATH` | COLMAP executable | `/usr/local/bin/colmap` |
| `GLOMAP_PATH` | GLOMAP executable | `/usr/local/bin/glomap` |
| `INSTANTSFM_PATH` | InstantSfM executable | `ins-sfm` |
| `GS_REPO_PATH` | 3DGS repo (has train.py) | `/root/work/gs_workspace/gaussian-splatting` |
| `GS_PYTHON` | Python for 3DGS | `/root/work/gs_workspace/gs_env/bin/python` |
| `OPENMVG_BIN_DIR` | OpenMVG binaries | `/root/work/openMVG/openMVG_Build/Linux-x86_64-Release` |
| `OPENMVG_SENSOR_DB` | Camera sensor DB | `/root/work/openMVG/src/openMVG/exif/sensor_width_database/sensor_width_camera_database.txt` |
| `SPZ_PYTHON` | Python with SPZ bindings | `/root/miniconda3/envs/spz-env/bin/python` |
| `AEROTRI_FRONTEND_ORIGIN` | CORS frontend origin | Optional |
| `QUEUE_MAX_CONCURRENT` | Queue max concurrent tasks | `1` (range: 1-10) |
| `CUDSS_DIR` | cuDSS installation path for BA acceleration | `/opt/cudss` |

### Frontend Configuration
Build-time configuration in `frontend/src/api/index.ts` - set `BASE_URL` for backend API.

## Data Flow

### SfM Processing Pipeline
1. User creates Block with algorithm + parameters
2. [Optional] Enable partition mode for large datasets
3. Select GPU via real-time monitoring
4. Submit task (direct run or add to queue)
5. `task_runner.run_task()` executes algorithm stages
6. Progress broadcast via WebSocket
7. `result_reader.py` parses binary outputs for 3D visualization

### OpenMVS Reconstruction Pipeline
1. Prerequisite: Block SfM completed (`sparse/0` exists)
2. User creates reconstruction version with quality preset
3. `openmvs_runner.run_reconstruction()` executes stages: densify → mesh → refine → texture
4. Progress tracked per stage; outputs stored in version-specific directory

### 3DGS Training Pipeline
1. Prerequisite: Block SfM completed
2. Auto-detect camera model; run undistortion if not PINHOLE/SIMPLE_PINHOLE
3. `gs_runner.start_training()` launches external training process
4. Outputs: `point_cloud.ply` + iteration checkpoints

### 3D Tiles Conversion
- **From OpenMVS**: OBJ → GLB → 3D Tiles (via `tiles_runner`)
  - Supports both block-level (legacy) and version-level conversion
  - Version-level: each `ReconVersion` has its own `tiles_*` fields
  - Automatically injects `root.transform` (ENU→ECEF) if georeferencing is enabled
- **From 3DGS**: PLY → [SPZ compression] → GLTF → 3D Tiles (via `gs_tiles_runner`)

## Important Implementation Details

### GPU Selection and Allocation
- GPU status polled every 2 seconds via `gpu_service.py`
- User selects GPU index; passed to algorithm commands
- RTX 5090 support: `TORCH_CUDA_ARCH_LIST=12.0` set for 3DGS training

### Partition Processing
- Strategy: `name_range_with_overlap` splits images by filename range
- Overlap regions ensure seamless merging
- Merge strategies: `rigid_keep_one` (SIM3), `sim3_keep_one` (rigid + scale)
- Merging reassigns all IDs from 1 to avoid overflow

### OpenMVG Thread Adaptation
- `openmvg_runner.py` uses `psutil` to detect system memory
- Calculates optimal thread count: `min(cpu_count, max(1, int(total_memory_gb / 2)))`
- User can override via `openmvg_params.num_threads`

### SPZ Compression
- SPZ Python bindings installed in conda env `spz-env`
- Backend auto-detects SPZ Python; falls back gracefully if unavailable
- Reduces 3DGS file size by ~90%

### CORS Configuration
- CORS middleware applied before all routes (including FileResponse)
- Configure origins via `frontend_origins` in `main.py` + `AEROTRI_FRONTEND_ORIGIN` env var

### Task Recovery on Startup
All runners implement `recover_orphaned_*()` methods called during app lifespan startup to detect and update status of tasks interrupted by server restart.

### Georeferencing (GPS → UTM → ENU)
- Optional step after SfM mapping stage (enabled via `mapper_params.georef_enabled`)
- Extracts EXIF GPS data using `exiftool`, converts to UTM using `pyproj`
- Aligns sparse model using COLMAP `model_aligner` with reference images
- Creates local ENU frame by shifting origin to mean of reference images
- Outputs `geo/geo_ref.json` with UTM EPSG, origin coordinates, and ENU→ECEF transform matrix
- 3D Tiles conversion automatically injects `root.transform` for Cesium real-world placement
- Supports external reference images file for images without EXIF GPS

### Image Count Statistics
- Block creation automatically counts images in the working directory
- Stored in `Block.statistics.num_images`
- Frontend displays image count tag in BlockCard component
- Backfills image count for older blocks that don't have it yet

### Texture File Serving
- Direct file serving endpoint for texture files (OBJ/MTL/texture images)
- Enables Three.js OBJLoader/MTLLoader to correctly resolve relative paths
- Path-based URL: `/api/blocks/{id}/recon-versions/{version_id}/texture/{filename:path}`

### Notification Service
- Optional notification service for task lifecycle events
- Sends notifications on: backend startup/shutdown, task start/complete/fail
- Configured via `notification` config section, can be disabled gracefully
- Periodic scheduler for recurring notifications (if enabled)

### cuDSS GPU Acceleration for Bundle Adjustment
- **Purpose**: cuDSS (CUDA Dense Sparse Solver) accelerates Ceres Solver's Bundle Adjustment in COLMAP/GLOMAP
- **Impact**: Without cuDSS, BA falls back to CPU-based solvers (10-100x slower)
- **Symptoms**: Log shows "Requested to use GPU for bundle adjustment, but Ceres was compiled without cuDSS support"
- **Verification**:
  ```bash
  ls /root/opt/ceres-2.3-cuda/lib | grep ceres
  ```
  Expected output includes `libceres.so` and cuDSS-related libraries
- **Installation**:
  1. Download cuDSS from NVIDIA (requires developer account): https://developer.nvidia.com/cudss
  2. Rebuild Ceres Solver with cuDSS support:
     ```bash
     cd ceres-solver && mkdir build && cd build
     cmake .. -DCMAKE_CUDA_ARCHITECTURES=native -DCUDSS_DIR=/path/to/cudss -DBUILD_SHARED_LIBS=ON
     make -j$(nproc) && sudo make install
     ```
  3. Rebuild COLMAP/GLOMAP against cuDSS-enabled Ceres
- **See Also**: Environment variable `CUDSS_DIR` for cuDSS installation path

## Common Modification Patterns

### Adding a New Algorithm Parameter
1. Update `frontend/src/types/index.ts` - add to appropriate params interface
2. Update `backend/app/schemas.py` - add to params schema
3. Update algorithm runner (`backend/app/services/*_runner.py`) - pass to CLI
4. Update `ParameterForm.vue` - add UI control

### Adding a New Processing Stage
1. Add stage to status enum in models
2. Update relevant runner's stage progression logic
3. Add progress tracking in log parser
4. Update frontend progress display

### Extending the 3D Visualization
- `result_reader.py` reads COLMAP binary formats
- `ThreeJSScene.vue` renders with Three.js
- For InstantSfM: use WebSocket visualization channel with viser proxy

## File Organization Conventions

### Backend Output Paths
```
data/outputs/{block_id}/
├── sparse/0/              # SfM result (COLMAP format)
├── merged/sparse/0/       # Partition merge result
├── dense/0/               # OpenMVS dense point cloud
├── mesh/0/                # OpenMVS mesh
├── refine/0/              # OpenMVS refined mesh
├── texture/0/             # OpenMVS textured mesh
├── gs_output/             # 3DGS training output
└── tiles_output/          # 3D Tiles conversion output
```

### Reconstruction Version Paths
```
data/outputs/{block_id}/recon_versions/{version_id}/
├── dense/, mesh/, refine/, texture/  # Stage outputs
├── tiles/                            # Version-level 3D Tiles output
│   ├── tileset.json
│   └── *.b3dm
└── version_info.json                 # Version metadata

# Georeferencing outputs (if enabled)
data/outputs/{block_id}/
├── geo/
│   ├── gps_raw.csv                   # EXIF GPS data
│   ├── gps_raw_ref_images.txt        # Reference images (UTM)
│   ├── geo_ref.json                  # Georef metadata (EPSG, origin, transform)
│   └── raw_to_utm_transform.txt      # COLMAP transform
├── sparse_utm/0/                     # UTM-aligned sparse model
└── sparse_enu_local/0/               # Local ENU frame (origin-shifted)
```
