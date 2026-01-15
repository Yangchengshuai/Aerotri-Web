# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MCP Usage Rules

**Context7 MCP**: Always use Context7 MCP when I need library/API documentation, code generation, setup or configuration steps without me having to explicitly ask. This is especially important for:
- Finding up-to-date API documentation for external libraries (FastAPI, Vue.js, SQLAlchemy, Pinia, etc.)
- Getting code examples for specific library versions
- Configuration and setup instructions
- Best practices and patterns

## Project Overview

**AeroTri** is a photogrammetry and 3D reconstruction platform that integrates multiple computer vision libraries with a web interface for aerotriangulation (SfM - Structure from Motion) workflows.

### Core Components
- **aerotri-web/**: Main web application (FastAPI backend + Vue.js frontend)
- **colmap/**: Incremental SfM library source code
- **glomap/**: Global SfM optimization library
- **openMVG/**: CPU-friendly global SfM alternative
- **openMVS/**: Multi-view stereo dense reconstruction
- **instantsfm/**: Fast global SfM implementation
- **gs_workspace/gaussian-splatting/**: 3D Gaussian Splatting framework
- **visionary/**: WebGPU 3DGS viewer
- **ceres-solver/**: Non-linear optimization library

## Development Commands

### Backend (aerotri-web/backend)
```bash
cd aerotri-web/backend

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run specific test
pytest tests/test_specific.py::test_function
```

### Frontend (aerotri-web/frontend)
```bash
cd aerotri-web/frontend

# Install dependencies
npm install

# Run tests
npm run test

# Start development server
npm run dev -- --host 0.0.0.0 --port 5173

# Build for production
npm run build

# Lint code
npm run lint
```

## Architecture Overview

### Backend Architecture (FastAPI)

**Core Modules:**
- `app/api/`: REST API endpoints organized by resource (blocks, queue, reconstruction, tiles, georef, system, unified_tasks, etc.)
- `app/models/`: SQLAlchemy ORM models (Block, ReconVersion, BlockGS, etc.)
- `app/services/`: Business logic layer
  - `task_runner.py`: Core SfM execution service (COLMAP/GLOMAP/InstantSfM/OpenMVG) with georeferencing support
  - `gpu_service.py`: GPU monitoring via PyNVML (lazy loading to avoid crashes)
  - `gs_runner.py`: 3D Gaussian Splatting training orchestration
  - `tiles_runner.py`: 3D Tiles conversion (OBJ/GLB → 3D Tiles) with version support and georef transform injection
  - `openmvs_runner.py`: OpenMVS dense reconstruction pipeline
  - `result_reader.py`: COLMAP binary format parsing
  - `notification.py`: Task notification service (startup/shutdown, task start/complete/fail)
- `app/ws/`: WebSocket handlers for real-time progress updates
- `app/schemas.py`: Pydantic models for request/response validation

**Key Design Patterns:**
- **Task State Management**: Tasks use `*_status`, `*_progress`, `*_current_stage` fields for state tracking (e.g., `status`, `progress`, `current_stage` for SfM; `gs_status`, `gs_progress` for 3DGS)
- **Working Directory Pattern**: Creates safe working directories with hardlinks to source images at `data/outputs/{block_id}/`
- **Async Task Processing**: Background tasks with progress tracking via WebSocket
- **Version Management**: Supports multiple reconstruction versions per Block with parameter comparison

**Database Models:**
- `Block`: Main project entity (image collection + SfM state, includes `statistics.num_images` for image count)
- `ReconVersion`: OpenMVS reconstruction versions (dense/mesh/texture) with 3D Tiles conversion fields (`tiles_status`, `tiles_progress`, etc.)
- `BlockGS`: 3DGS training state and outputs
- `BlockGSTiles`: 3DGS → 3D Tiles conversion state
- `BlockTiles`: OpenMVS → 3D Tiles conversion state (legacy, block-level)

### Frontend Architecture (Vue 3 + TypeScript)

**Key Directories:**
- `src/views/`: Page-level components (HomeView, BlockDetail, ReconCompareView)
- `src/components/`: Reusable components (ParameterForm, ReconstructionPanel, TilesConversionPanel, BlockCard)
- `src/stores/`: Pinia state management
- `src/api/`: HTTP client wrappers for backend APIs
- `src/types/`: TypeScript type definitions

**State Management:**
- Pinia stores for global state (blocks, GPU status, queue)
- Local component state for UI-specific data

### Algorithm Pipeline Flow

```
1. Block Creation (images + metadata)
   ↓
2. Feature Extraction (SIFT/EXIF GPS)
   ↓
3. Feature Matching (sequential/spatial/exhaustive)
   ↓
4. SfM Reconstruction (COLMAP/GLOMAP/InstantSfM/OpenMVG)
   - sparse/0/ output (cameras.bin, images.bin, points3D.bin)
   ↓
5. [Optional] GLOMAP mapper_resume optimization
   - Creates new version with optimized poses
   ↓
6. [Optional] OpenMVS Dense Reconstruction
   - Densify → Mesh → Refine → Texture
   - Creates BlockReconstructionVersion
   ↓
7. [Optional] 3DGS Training
   - Requires PINHOLE/SIMPLE_PINHOLE camera model
   - Auto-undistortion if needed
   ↓
8. [Optional] 3D Tiles Conversion
   - OpenMVS OBJ → GLB → 3D Tiles
   - 3DGS PLY → [SPZ] → GLTF → 3D Tiles
```

## Environment Variables

**Required Paths:**
```bash
# Backend
AEROTRI_DB_PATH=/root/work/aerotri-web/data/aerotri.db

# Image Root Paths (for directory browsing when creating Blocks)
# Single root (backward compatible):
AEROTRI_IMAGE_ROOT=/path/to/images

# Multiple roots (colon-separated, recommended for production):
AEROTRI_IMAGE_ROOTS=/data/images:/mnt/storage:/mnt/nas

# Or use YAML config file: backend/config/image_roots.yaml
# Priority: AEROTRI_IMAGE_ROOTS > AEROTRI_IMAGE_ROOT > config file > default

# Algorithm Executables
COLMAP_PATH=/usr/local/bin/colmap
GLOMAP_PATH=/usr/local/bin/glomap
INSTANTSFM_PATH=/path/to/ins-sfm
OPENMVG_BIN_DIR=/root/work/openMVG/openMVG_Build/Linux-x86_64-Release
OPENMVG_SENSOR_DB=/root/work/openMVG/src/openMVG/exif/sensor_width_database/sensor_width_camera_database.txt

# 3DGS
GS_REPO_PATH=/root/work/gs_workspace/gaussian-splatting
GS_PYTHON=/root/work/gs_workspace/gs_env/bin/python

# SPZ Compression (optional)
SPZ_PYTHON=/root/miniconda3/envs/spz-env/bin/python
```

## Key API Endpoints

**Block Management:**
- `GET/POST /api/blocks` - List/create blocks
- `GET/PATCH/DELETE /api/blocks/{id}` - Block details
- `POST /api/blocks/{id}/run` - Start SfM reconstruction
- `GET /api/blocks/{id}/status` - Task status

**Reconstruction:**
- `POST /api/blocks/{id}/reconstruct` - Start OpenMVS reconstruction (legacy, single version)
- `GET/POST /api/blocks/{id}/recon-versions` - List/create reconstruction versions
- `DELETE /api/blocks/{id}/recon-versions/{version_id}` - Delete version
- `POST /api/blocks/{id}/recon-versions/{version_id}/cancel` - Cancel running version

**3DGS:**
- `POST /api/blocks/{id}/gs/train` - Start 3DGS training
- `GET /api/blocks/{id}/gs/status` - Training status
- `POST /api/blocks/{id}/gs/cancel` - Cancel training

**3D Tiles:**
- `POST /api/blocks/{id}/tiles/convert` - Convert OpenMVS → 3D Tiles (block-level, legacy)
- `POST /api/blocks/{id}/recon-versions/{version_id}/tiles/convert` - Convert version → 3D Tiles
- `GET /api/blocks/{id}/recon-versions/{version_id}/tiles/status` - Get version tiles status
- `GET /api/blocks/{id}/recon-versions/{version_id}/tiles/files` - List version tiles files
- `GET /api/blocks/{id}/recon-versions/{version_id}/tiles/tileset_url` - Get version tileset URL
- `POST /api/blocks/{id}/gs/tiles/convert` - Convert 3DGS → 3D Tiles

**Georeferencing:**
- `GET /api/blocks/{id}/georef/download` - Download geo_ref.json file

**Queue & GPU:**
- `GET/PUT /api/queue/config` - Queue concurrency settings
- `POST /api/queue/blocks/{id}/enqueue` - Add to queue
- `GET /api/gpu/status` - GPU monitoring

**WebSocket:**
- `/ws/blocks/{id}/progress` - Real-time progress updates
- `/ws/blocks/{id}/visualization` - InstantSfM real-time visualization

## Important Implementation Details

### Image Root Path Configuration (Multi-Path Support)
- **Multiple Image Roots**: System supports configuring multiple image root directories for flexible directory browsing
- **Configuration Priority**:
  1. Environment variable `AEROTRI_IMAGE_ROOTS` (colon-separated paths, e.g., `/data/images:/mnt/storage`)
  2. Environment variable `AEROTRI_IMAGE_ROOT` (single path, backward compatible)
  3. YAML config file `backend/config/image_roots.yaml` (supports named paths)
  4. Default path `/mnt/work_odm/chengshuai`
- **Frontend Integration**: Directory browser shows root selector when multiple paths configured
- **Security**: All paths validated on backend, prevents directory traversal attacks
- **API Endpoint**: `GET /api/filesystem/roots` returns available image roots
- **Configuration Module**: `backend/app/config.py` - `get_image_roots()`, `get_image_root()`
- **See Also**: `IMAGE_ROOTS_CONFIG.md` for detailed configuration guide

### Camera Model Handling
- COLMAP supports various camera models (OPENCV, SIMPLE_RADIAL, RADIAL, etc.)
- 3DGS requires PINHOLE or SIMPLE_PINHOLE
- Backend automatically runs `image_undistorter` if model mismatch before 3DGS training

### Pose Prior (GPS Position Priors)
- EXIF GPS data used to accelerate reconstruction
- COLMAP/GLOMAP automatically detect coordinate type (GPS vs Cartesian) from database
- No manual `spatial_is_gps` parameter needed

### Partition SfM
- For large datasets: process in partitions, then merge
- Merge strategies: `rigid_keep_one`, `sim3_keep_one`
- Merged results stored in `merged/sparse/0/`
- Critical: ID remapping starts from 1 to avoid overflow (image_id, camera_id, point_id)

### Reprojection Error Calculation
- Supports both text (images.txt) and binary (images.bin) formats
- Error threshold configurable (default 1.0px)
- Color coding: green (normal), blue (problem), yellow (no data)

### SPZ Compression for 3DGS Tiles
- Reduces file size by ~90%
- Uses conda environment `spz-env` for Python bindings
- `KHR_gaussian_splatting_compression_spz_2` extension

### RTX 5090 Support
- Automatically sets `TORCH_CUDA_ARCH_LIST=12.0` for Blackwell architecture

### Georeferencing (GPS → UTM → ENU)
- Optional georeferencing step after SfM mapping stage
- Extracts EXIF GPS data, converts to UTM, aligns model using COLMAP `model_aligner`
- Creates local ENU frame by shifting origin to mean of reference images
- Outputs `geo_ref.json` with UTM EPSG, origin coordinates, and ENU→ECEF transform matrix
- 3D Tiles conversion automatically injects `root.transform` for Cesium real-world placement
- Supports external reference images file (`georef_ref_images_path`) for images without EXIF GPS

### Queue Concurrency Configuration
- Default max concurrent tasks: 1 (historical behavior)
- Can be overridden via `QUEUE_MAX_CONCURRENT` environment variable (range: 1-10)
- Queue scheduler automatically dispatches tasks based on this limit

### Notification Service
- Optional notification service for task lifecycle events
- Sends notifications on: backend startup/shutdown, task start/complete/fail
- Configured via `notification` config section, can be disabled gracefully

## File Structure Conventions

**Working Directory Layout:**
```
data/outputs/{block_id}/
├── sparse/0/              # SfM reconstruction output
│   ├── cameras.bin
│   ├── images.bin
│   └── points3D.bin
├── merged/sparse/0/       # Partition merge result
├── recon_{version_id}/    # OpenMVS reconstruction output
│   ├── dense/
│   ├── mesh/
│   └── texture/
├── 3dgs/                  # 3DGS training output
│   ├── point_cloud/iteration_*/
│   └── train/
├── tiles/                 # 3D Tiles output (OpenMVS)
└── gs_tiles/              # 3D Tiles output (3DGS)
```

## Common Patterns

### Adding New Algorithm Parameters
1. Update `app/schemas.py` - add field to appropriate Pydantic model
2. Update `app/services/task_runner.py` - pass parameter to algorithm
3. Update frontend `src/types/index.ts` - add TypeScript type
4. Update `ParameterForm.vue` - add UI control

### Adding New Task Types
1. Create new runner in `app/services/` inheriting from task execution patterns
2. Add status fields to Block model in `app/models/block.py`
3. Create API endpoints in `app/api/`
4. Add frontend UI components
5. Add WebSocket progress reporting

## Testing

- Backend tests use `pytest` with `pytest-asyncio` for async endpoints
- Frontend tests use `vitest` with `@vue/test-utils`
- Test files located in `aerotri-web/backend/tests/` and `aerotri-web/frontend/tests/`
