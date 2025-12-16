# SelectionController - Geometry Selection System

## Overview

The SelectionController is a new control mode for the OpenMVS Viewer that enables users to select areas of geometry (point clouds and meshes) using interactive 2D selection tools and perform operations on the selected regions. This system operates independently of existing ray-cast selection functionality and provides a dedicated workflow for geometry manipulation.

## Architecture Integration

### Controller Pattern
The SelectionController follows the established pattern used by ArcballControls and FirstPersonControls:

```cpp
class SelectionController {
    // Input handling (similar interface to existing controllers)
    void handleMouseButton(int button, int action, const Eigen::Vector2d& pos);
    void handleMouseMove(const Eigen::Vector2d& pos);
    void handleKeyboard(int key, int action, int mods);
    void update(double deltaTime);
    
    // Selection-specific functionality
    void reset();
    void setViewport(int width, int height);
};
```

### Window Integration
Extends the existing control mode system:

```cpp
enum ControlMode {
    CONTROL_ARCBALL,
    CONTROL_FIRST_PERSON,
    CONTROL_SELECTION      // New mode
};

// In Window class
std::unique_ptr<SelectionController> selectionController;
```

### Scene Integration
Adds new geometry manipulation methods to Scene class:

```cpp
// New methods in Scene class (NOT using CropToBounds)
void ApplyGeometrySelection(const SelectionController& controller);
void RemoveSelectedGeometry();
void InvertGeometrySelection();
void ClearGeometrySelection();
```

## Core Functionality

### Selection Modes
1. **Box Selection**: Rectangular region selection
2. **Lasso Selection**: Free-form polygon selection  
3. **Circle Selection**: Circular region selection

### Selection Operations
- **Add to Selection**: Extend current selection with new area
- **Invert Selection**: Flip selected/unselected status of all geometry
- **Clear Selection**: Remove all selections
- **Apply Operations**: Remove selected geometry or invert selection

### Workflow
1. Switch to Selection Mode (G key or UI button)
2. Choose selection tool (Box/Lasso/Circle)
3. Draw selection areas (additive - can select multiple regions)
4. Preview selection with visual highlighting
5. Apply operations (Remove Selected/Invert Selection)
6. Invert selection if needed
7. Switch back to navigation mode

## Data Structures

### Selection State
```cpp
class SelectionController {
private:
    enum SelectionMode {
        MODE_BOX,     // Rectangular selection
        MODE_LASSO,   // Free-form polygon
        MODE_CIRCLE   // Circular selection
    };
    
    enum SelectionState {
        STATE_IDLE,       // Not selecting
        STATE_SELECTING,  // Currently drawing selection
        STATE_SELECTED    // Selection complete, ready for operations
    };
    
    // Current selection mode and state
    SelectionMode currentMode;
    SelectionState currentState;
    
    // Selection geometry (2D screen space)
    std::vector<Eigen::Vector2d> selectionPath;  // For lasso/box
    Eigen::Vector2d selectionStart, selectionEnd; // For box/circle
    float circleRadius; // For circle mode
    
    // Geometry classification results
    std::vector<bool> pointsSelected;   // Which points are selected
    std::vector<bool> facesSelected;    // Which faces are selected
    
    // Selection accumulation (multiple selection areas)
    std::vector<std::vector<Eigen::Vector2d>> allSelectionPaths;
    std::vector<SelectionMode> selectionModes; // Mode for each path
};
```

### Geometry Testing
```cpp
// 3D to 2D projection testing
bool IsPointInSelection(const Point3f& worldPoint, const Camera& camera);

// 2D geometric tests
bool IsPointInPolygon(const Eigen::Vector2d& point, const std::vector<Eigen::Vector2d>& polygon);
bool IsPointInCircle(const Eigen::Vector2d& point, const Eigen::Vector2d& center, float radius);
bool IsPointInBox(const Eigen::Vector2d& point, const Eigen::Vector2d& min, const Eigen::Vector2d& max);
```

## Renderer Integration

### Selection Visualization
```cpp
// New rendering methods in Renderer class
void RenderSelectionOverlay(const SelectionController& controller);
void RenderSelectedGeometry(const Window& window, const MVS::Scene& scene);
void RenderSelectionPath(const std::vector<Eigen::Vector2d>& path, SelectionMode mode);
```

### Visual Feedback
- **Active Selection**: Real-time overlay showing current selection area being drawn
- **Selected Geometry**: Highlighted points/faces that are currently selected
- **Selection History**: Optional visualization of all selection areas
- **Selection Statistics**: Count of selected points/faces in UI

## UI Integration

### Selection Panel
```cpp
// New UI methods
void ShowSelectionControls(SelectionController& controller);
void ShowSelectionStatistics(const SelectionController& controller);
void ShowSelectionOperations(Scene& scene, SelectionController& controller);
```

### UI Elements
- **Mode Selection**: Radio buttons for Box/Lasso/Circle
- **Operations**: Buttons for Remove Selected/Invert Selection/Clear
- **Statistics**: Display count of selected points/faces
- **Undo Support**: Button to undo last geometry operation

## Input Handling

### Mouse Controls
```cpp
// Selection mode input handling
void handleMouseButton(int button, int action, const Eigen::Vector2d& pos) {
    switch (currentState) {
    case STATE_IDLE:
        if (action == GLFW_PRESS && button == GLFW_MOUSE_BUTTON_LEFT) {
            startSelection(pos);
        }
        break;
    case STATE_SELECTING:
        if (action == GLFW_RELEASE && button == GLFW_MOUSE_BUTTON_LEFT) {
            finishSelection(pos);
        }
        break;
    }
}

void handleMouseMove(const Eigen::Vector2d& pos) {
    if (currentState == STATE_SELECTING) {
        updateSelection(pos);
    }
}
```

### Keyboard Shortcuts
- **G**: Toggle between navigation and selection modes
- **B**: Box selection mode
- **L**: Lasso selection mode  
- **C**: Circle selection mode
- **Delete**: Remove selected geometry
- **Ctrl+I**: Invert selection
- **Escape**: Clear selection and return to navigation
- **Ctrl+Z**: Undo last operation

## Geometry Processing

### Point Cloud Selection
```cpp
void classifyPointCloud(const MVS::PointCloud& pointcloud, const Camera& camera) {
    pointsSelected.resize(pointcloud.points.size(), false);
    
    for (size_t i = 0; i < pointcloud.points.size(); ++i) {
        if (IsPointInAnySelection(pointcloud.points[i], camera)) {
            pointsSelected[i] = true;
        }
    }
}
```

### Mesh Selection
```cpp
void classifyMesh(const MVS::Mesh& mesh, const Camera& camera) {
    facesSelected.resize(mesh.faces.size(), false);
    
    for (size_t i = 0; i < mesh.faces.size(); ++i) {
        const auto& face = mesh.faces[i];
        const Point3f& v0 = mesh.vertices[face[0]];
        const Point3f& v1 = mesh.vertices[face[1]];
        const Point3f& v2 = mesh.vertices[face[2]];
        
        if (IsPointInAnySelection(v0, camera) && 
            IsPointInAnySelection(v1, camera) && 
            IsPointInAnySelection(v2, camera)) {
            facesSelected[i] = true;
        }
    }
}
```

### Geometry Operations
```cpp
// In Scene class - NEW methods (not using CropToBounds)
void Scene::RemoveSelectedGeometry() {
    if (!selectionController->hasSelection()) return;
    
    // Remove selected points
    if (!scene.pointcloud.IsEmpty()) {
		// Fetch from selection controller the ordered (ascending) indices of the selected points
        const auto& selectedIndices = selectionController->getSelectedPoints();
        // Remove selected faces
        scene.pointcloud.RemovePoints(selectedIndices);
    }
    
    // Remove selected faces
    if (!scene.mesh.IsEmpty()) {
        MVS::Mesh newMesh;
		// Fetch from selection controller the ordered (ascending) indices of the selected faces
        const auto& selectedIndices = selectionController->getSelectedFaces();
        // Remove selected faces
        scene.mesh.RemoveFaces(selectedIndices);
    }
    
    // Update rendering
    window.UploadRenderData();
}
```

## Performance Considerations

### Spatial Optimization
- Use camera frustum culling to test only visible geometry
- Implement hierarchical testing for large datasets
- Cache projection calculations for real-time feedback

### Memory Management
- Stream geometry classification to avoid large temporary arrays
- Use bit vectors for selection state to minimize memory usage
- Implement progressive selection for very large datasets

### Rendering Optimization
- Use geometry shaders for selection overlay rendering
- Implement LOD for selection preview with large datasets
- Batch selection operations to minimize state changes

## Error Handling

### Edge Cases
- Empty selections (no-op)
- Selections outside geometry bounds
- Partial triangle selections (configurable behavior)
- Very small selections (minimum threshold)

### User Feedback
- Selection count updates in real-time
- Visual feedback for invalid operations
- Progress indication for large operations
- Undo/redo support with operation history

## File Format Integration

### Selection Persistence
```cpp
// Optional: Save/load selection state
struct SelectionData {
    std::vector<bool> selectedPoints;
    std::vector<bool> selectedFaces;
    std::string selectionName;
    double timestamp;
};

void SaveSelection(const std::string& filename);
void LoadSelection(const std::string& filename);
```

### Export Options
- Export selected geometry as separate files
- Export selection masks as binary data
- Integration with existing scene export functionality

## Implementation Phases

### Phase 1: Core Infrastructure
1. Create SelectionController class with basic box selection
2. Integrate into Window control system
3. Add basic UI panel for mode selection
4. Implement geometry classification for points and faces

### Phase 2: Advanced Selection
1. Add lasso and circle selection modes
2. Implement additive selection (multiple areas)
3. Add selection inversion functionality
4. Enhanced visual feedback and statistics

### Phase 3: Geometry Operations
1. Implement geometry removal operations
2. Add undo/redo support
3. Optimize for large datasets
4. Add selection persistence

### Phase 4: Polish & Integration
1. Keyboard shortcuts and workflow refinement
2. Performance optimization
3. Error handling and edge cases
4. Documentation and user guide

## Benefits Over Existing Systems

1. **Independent of CropToBounds**: Uses dedicated geometry operations instead of scene bounding box functionality
2. **Separate from Ray-casting**: Doesn't interfere with existing element selection under cursor
3. **Additive Selection**: Can build complex selections from multiple areas
4. **Simplified Operations**: Focus on add/invert workflow rather than complex inside/outside logic
5. **Visual Feedback**: Real-time preview of selections and operations
6. **Consistent Architecture**: Follows established controller patterns in the viewer
