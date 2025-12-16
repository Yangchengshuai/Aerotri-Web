# OpenMVS Copilot Instructions

OpenMVS is a multi-view stereo reconstruction library implementing a complete photogrammetry pipeline from camera poses + sparse point-cloud to textured mesh. The codebase is mature C++ with custom framework patterns.

## Project Architecture

### Core Namespaces & Structure
- **MVS namespace**: Core reconstruction algorithms (`libs/MVS/`)
- **VIEWER namespace**: 3D visualization application (`apps/Viewer/`)
- **SEACAVE namespace**: Low-level utilities (`libs/Common/`)

### Key Libraries (libs/)
- `Common/`: Custom framework (types, logging, containers, math utilities)
- `MVS/`: Core MVS algorithms (Scene, Image, Camera, Mesh, PointCloud, etc.)
- `IO/`: File format support (PLY, OBJ, MVS formats)
- `Math/`: Mathematical primitives and operations

### Applications (apps/)
Each app is a standalone executable for specific pipeline stages:
- `DensifyPointCloud`: Dense reconstruction from sparse points
- `ReconstructMesh`: Surface reconstruction from dense points
- `RefineMesh`: Mesh quality improvement
- `TextureMesh`: Apply textures to meshes
- `Viewer`: Interactive 3D visualization with OpenGL
- `Interface*`: Import/export to other pipelines (COLMAP, OpenMVG, etc.)

## Build System & Workflows

### Building
```bash
# Standard build (uses vcpkg for dependencies)
mkdir make && cd make
cmake ..
cmake --build . -j4  # or ninja (generates ninja files)
```

### Key Build Tools
- **vcpkg**: Automatic dependency management (see `vcpkg.json`)
- **CMake**: Primary build system with custom utilities in `build/Utils.cmake`
- **ninja**: Preferred generator (faster than make)

### Development Builds
- Debug builds in `make/bin/Debug/`
- Built executables: `./bin/Debug/Viewer`, `./bin/Debug/DensifyPointCloud`, etc.
- Use `cmake --build . -j4` from `make/` directory for incremental builds

## Code Patterns & Conventions

### Memory Management
- Reference counting with automatic cleanup
- RAII patterns throughout

### Logging & Debugging
```cpp
DEBUG("Message");           // Level 0 (always shown in debug)
DEBUG_EXTRA("Details");     // Level 1 (verbose)
VERBOSE("Info: %s", str);   // General logging
```

### Error Handling
- `ASSERT(condition)` for debug checks
- Return false/NULL for failures

### Common Typedefs
```cpp
typedef SEACAVE::Point3f Point3f;  // 3D points
typedef SEACAVE::String String;    // String type
#define NO_ID ((uint32_t)-1)       // Invalid index
```
Most of OpenMVS code uses custom point and matrix types derived from OpenCV types, e.g., `SEACAVE::Point3f`, `SEACAVE::Matrix4f`. Hoewever, some components use Eigen3 types, e.g. `SEACAVE::AABB3d` and `SEACAVE::Ray3d` classes. There custom types support convertion operation to and from Eigen3 types.

### Configuration
- Build-time config in `ConfigLocal.h` (generated)
- Runtime options via boost::program_options pattern
- Feature flags like `OpenMVS_USE_CUDA`, `OpenMVS_USE_CERES`
- Each library uses a precompiled header (`Common.h`) for common includes, like Eigen, OpenCV, etc.

## Viewer Application Specifics

### Key Classes
- `Scene`: Main data container (MVS::Scene + rendering state)
- `Window`: GLFW window management + input handling
- `Renderer`: OpenGL rendering (points, meshes, cameras)
- `Camera`: View/projection matrices + navigation
- `UI`: ImGui interface components

### Rendering Pipeline
```cpp
window.Run(scene) → 
  Render(scene) → 
    renderer->RenderPointCloud/RenderMesh → 
      OpenGL draw calls
```

### Event System
- GLFW events → Window callbacks → Control system updates
- Render-only-on-change optimization uses `glfwWaitEventsTimeout()`
- `Window::RequestRedraw()` triggers frame updates

## Integration Points

### File Formats
- `.mvs`: Native binary format (boost serialization)
- `.ply`: Point clouds and meshes (ASCII/binary)
- `.obj`: Mesh export with MTL materials
- Interface apps handle external formats (COLMAP, etc.)

### External Dependencies
- **Eigen3**: Linear algebra (matrices, vectors)
- **OpenCV**: Image processing and I/O
- **CGAL**: Computational geometry
- **Boost**: Serialization, program options, containers
- **CUDA**: GPU acceleration (optional)
- **GLFW/OpenGL**: Viewer rendering

### Cross-Component Communication
- `MVS::Scene` is the central data exchange format
- Applications typically: load scene → process → save scene
- Viewer loads and visualizes any stage of the pipeline

## Testing & Debugging

### Running Tests
```bash
# From make/ directory
ctest                    # Run all tests
./bin/Debug/Tests        # Direct test executable
```

### Common Debugging
- Use `DEBUG()` macros liberally
- Check `ASSERT()` failures for logic errors
- Viewer: Use F1 for help dialog, check console output
- Memory issues: Build with `_DEBUG` for additional checks

## Performance Considerations

- Multi-threading via OpenMP (`#pragma omp parallel`)
- CUDA kernels for GPU acceleration (when enabled)
- Memory-mapped files for large datasets
- Spatial data structures (octrees) for efficient queries
- Viewer optimizations: frustum culling, render-only-on-change mode
