# AeroTri-Web Configuration Guide

This guide explains how to configure AeroTri-Web for your environment.

## Quick Start

1. **Copy example configuration:**
   ```bash
   cd aerotri-web/backend
   cp config/settings.yaml.example config/settings.yaml
   ```

2. **Edit with your paths:**
   ```bash
   vim config/settings.yaml
   ```

3. **Or use environment variables (highest priority):**
   ```bash
   export COLMAP_PATH=/usr/local/bin/colmap
   export GS_REPO_PATH=/path/to/gaussian-splatting
   ```

4. **Start the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Configuration Priority

The configuration system uses a three-tier priority system (highest to lowest):

1. **Environment Variables** - Runtime overrides
2. **config/settings.yaml** - User custom configuration (optional, git-ignored)
3. **config/defaults.yaml** - Default values (version-controlled)

### Example: COLMAP Path

If you set `COLMAP_PATH` in all three places:

```bash
# Environment variable (highest priority - used)
export COLMAP_PATH=/usr/local/bin/colmap

# config/settings.yaml (ignored if env var set)
algorithms:
  colmap:
    path: /opt/colmap/bin/colmap

# config/defaults.yaml (ignored if either above is set)
algorithms:
  colmap:
    path: colmap  # uses system PATH
```

The application will use `/usr/local/bin/colmap` from the environment variable.

## Configuration Files

### config/defaults.yaml

**Purpose:** Version-controlled default configuration for all users.

**When to edit:** Never. This file is tracked in git.

**Contents:**
- Application name, version, debug mode
- Default paths (relative to project root)
- Algorithm configurations with safe defaults
- 3DGS, queue, GPU, and SPZ settings

### config/settings.yaml

**Purpose:** Your local custom configuration.

**When to edit:** When you need custom paths or settings.

**Contents:** Only override what you need. Example:

```yaml
# Override algorithm paths
algorithms:
  colmap:
    path: /usr/local/bin/colmap
  glomap:
    path: /usr/local/bin/glomap

# Override 3DGS settings
gaussian_splatting:
  repo_path: /opt/gaussian-splatting
  python: /opt/gs-env/bin/python
```

**Note:** This file is git-ignored. Never commit it!

### config/image_roots.yaml

**Purpose:** Configure multiple image root directories for browsing.

**Example:**
```yaml
default: /data/images
paths:
  - name: local
    path: /data/images
  - name: nas
    path: /mnt/nas/images
  - name: backup
    path: /mnt/backup/images
```

**Priority:** `AEROTRI_IMAGE_ROOTS` env var > `AEROTRI_IMAGE_ROOT` > this file > default

### config/notification.yaml

**Purpose:** Configure DingTalk notifications for task events.

**Optional:** Can be disabled by omitting this file.

**See:** `config/notification.yaml.example`

## Common Configuration Options

### Algorithm Paths

Configure paths to SfM algorithm executables:

**In settings.yaml:**
```yaml
algorithms:
  colmap:
    path: /usr/local/bin/colmap
  glomap:
    path: /usr/local/bin/glomap
  instantsfm:
    path: /usr/local/bin/ins-sfm
  openmvg:
    bin_dir: /usr/local/bin
    sensor_db: /usr/local/share/sensor_width_camera_database.txt
  openmvs:
    bin_dir: /usr/local/lib/openmvs/bin
```

**Via environment variables:**
```bash
export COLMAP_PATH=/usr/local/bin/colmap
export GLOMAP_PATH=/usr/local/bin/glomap
export INSTANTSFM_PATH=/usr/local/bin/ins-sfm
export OPENMVG_BIN_DIR=/usr/local/bin
export OPENMVG_SENSOR_DB=/usr/local/share/sensor_db.txt
export OPENMVS_BIN_DIR=/usr/local/lib/openmvs/bin
```

### 3D Gaussian Splatting

Configure 3DGS training:

**In settings.yaml:**
```yaml
gaussian_splatting:
  repo_path: /root/work/gs_workspace/gaussian-splatting
  python: /root/work/gs_workspace/gs_env/bin/python
  tensorboard_path: tensorboard
  tensorboard_port_start: 6006
  network_gui_ip: "127.0.0.1"
  network_gui_port_start: 6009
```

**Via environment variables:**
```bash
export GS_REPO_PATH=/path/to/gaussian-splatting
export GS_PYTHON=/path/to/gs-env/bin/python
export TENSORBOARD_PATH=/path/to/tensorboard
```

### Database Path

Configure SQLite database location:

**In settings.yaml:**
```yaml
database:
  path: ./data/aerotri.db
  pool_size: 5
  max_overflow: 10
```

**Via environment variable:**
```bash
export AEROTRI_DB_PATH=/custom/path/to/aerotri.db
```

### Queue Configuration

Configure task queue concurrency:

**In settings.yaml:**
```yaml
queue:
  max_concurrent: 2
  scheduler_interval: 5
```

**Via environment variable:**
```bash
export QUEUE_MAX_CONCURRENT=2
```

**Range:** 1-10 (default: 1)

### GPU Configuration

Configure GPU monitoring and selection:

**In settings.yaml:**
```yaml
gpu:
  monitor_interval: 2
  auto_selection: "most_free"
  default_device: 0
```

**Auto selection options:**
- `most_free` - Select GPU with most free memory (default)
- `least_used` - Select GPU with lowest utilization
- `first_available` - Select first available GPU

### cuDSS (Optional)

Configure cuDSS for GPU-accelerated Bundle Adjustment:

**Via environment variable:**
```bash
export CUDSS_DIR=/opt/cudss
```

**Impact:** Without cuDSS, Bundle Adjustment falls back to CPU (10-100x slower).

## Path Resolution

The configuration system automatically resolves relative paths:

**Example:**
```yaml
# In config/settings.yaml
paths:
  project_root: ".."  # Relative to backend/app/conf/settings.py
  data_dir: "./data"
  outputs_dir: "./data/outputs"
```

**Resolution:**
- `backend/app/conf/settings.py` → `backend/` (parent)
- `backend/` + `..` → `/root/work/Aerotri-Web/` (project root)
- All relative paths resolved from project root

**Result:**
```python
settings.paths.project_root  # /root/work/Aerotri-Web
settings.paths.data_dir      # /root/work/Aerotri-Web/backend/data
settings.paths.outputs_dir   # /root/work/Aerotri-Web/backend/data/outputs
```

## Configuration Validation

On startup, the application validates:

1. **Executable paths:** Checks that algorithms exist and are executable
2. **Directory creation:** Creates data directories if missing
3. **Type safety:** Pydantic validates all configuration types

**Example validation output:**
```
INFO:     Validating configuration...
INFO:     ✓ COLMAP found: /usr/local/bin/colmap
INFO:     ✓ GLOMAP found: /usr/local/bin/glomap
INFO:     ✓ Database directory created: ./data
INFO:     Configuration validated successfully
```

**Validation failures:**
```
WARNING:  COLMAP not found: /invalid/path/colmap
ERROR:    Configuration validation failed
```

## Hot-Reload Configuration

Reload configuration without restarting:

```bash
curl -X POST http://localhost:8000/api/system/config/reload
```

**Use cases:**
- Updated `settings.yaml` and want to apply changes
- Changed environment variables and need to refresh
- Testing different configurations

**Note:** Some settings require restart (e.g., database path).

## Environment Variables Reference

### Algorithm Paths
- `COLMAP_PATH` - Path to COLMAP executable
- `GLOMAP_PATH` - Path to GLOMAP executable
- `INSTANTSFM_PATH` - Path to InstantSfM executable
- `OPENMVG_BIN_DIR` - OpenMVG binaries directory
- `OPENMVG_SENSOR_DB` - Camera sensor database path
- `OPENMVS_BIN_DIR` - OpenMVS binaries directory

### 3D Gaussian Splatting
- `GS_REPO_PATH` - Path to gaussian-splatting repository
- `GS_PYTHON` - Python interpreter for 3DGS
- `TENSORBOARD_PATH` - Path to tensorboard executable
- `SPZ_PYTHON` - Python with SPZ bindings

### Database
- `AEROTRI_DB_PATH` - SQLite database file path

### Image Roots
- `AEROTRI_IMAGE_ROOT` - Single image root path (backward compatible)
- `AEROTRI_IMAGE_ROOTS` - Multiple image roots (colon-separated)

### Queue
- `QUEUE_MAX_CONCURRENT` - Maximum concurrent tasks (1-10)

### Application
- `AEROTRI_DEBUG` - Enable debug mode (true/false)
- `AEROTRI_ENV` - Environment name (production/development)
- `AEROTRI_FRONTEND_ORIGIN` - CORS frontend origin

### cuDSS
- `CUDSS_DIR` - Path to cuDSS installation

## Troubleshooting

### Configuration not loading

**Check:**
1. YAML syntax is valid (no tabs, correct indentation)
2. File is in `backend/config/` directory
3. No Python syntax errors in configuration models

**Debug:**
```bash
python -c "import yaml; yaml.safe_load(open('config/defaults.yaml'))"
```

### Algorithm not found

**Check:**
1. Path is absolute or relative to project root
2. File is executable (`chmod +x /path/to/colmap`)
3. Environment variable takes precedence over YAML

**Debug:**
```bash
which colmap  # Check system PATH
ls -l /path/to/colmap  # Check executable exists
```

### Paths not resolving correctly

**Check:**
1. Relative paths are relative to project root (not backend directory)
2. Use `paths.project_root` to see detected root
3. Absolute paths unchanged by resolution

**Debug:**
```python
from app.conf.settings import get_settings
settings = get_settings()
print(f"Project root: {settings.paths.project_root}")
print(f"Data dir: {settings.paths.data_dir}")
```

## Configuration API

### Get current configuration

```bash
curl http://localhost:8000/api/system/config
```

### Reload configuration

```bash
curl -X POST http://localhost:8000/api/system/config/reload
```

### Validate configuration

```bash
curl http://localhost:8000/api/system/config/validate
```

## Best Practices

1. **Use environment variables for sensitive data** (API keys, paths with secrets)
2. **Keep settings.yaml in gitignore** (use .example for documentation)
3. **Use relative paths for portability** (resolved from project root)
4. **Document custom configurations** in comments within settings.yaml
5. **Test configuration changes** in development before production
6. **Use validation** to catch errors early (startup validation)

## Migration from Old Configuration

If migrating from the old `app/settings.py` system:

1. **Old:**
   ```python
   # app/settings.py
   COLMAP_PATH = "/usr/local/bin/colmap"
   GS_REPO_PATH = "/path/to/gs"
   ```

2. **New (Option A - YAML):**
   ```yaml
   # config/settings.yaml
   algorithms:
     colmap:
       path: /usr/local/bin/colmap
   gaussian_splatting:
     repo_path: /path/to/gs
   ```

3. **New (Option B - Environment):**
   ```bash
   export COLMAP_PATH=/usr/local/bin/colmap
   export GS_REPO_PATH=/path/to/gs
   ```

**Note:** All old environment variables still work with new system!

## Additional Resources

- **CLAUDE.md** - Architecture and development guide
- **config/defaults.yaml** - All available configuration options
- **config/settings.yaml.example** - Example custom configuration
- **app/conf/settings.py** - Configuration model definitions
