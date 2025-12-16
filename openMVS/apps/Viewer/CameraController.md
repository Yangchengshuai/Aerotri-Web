Camera controller is implemented in `ArcballControls` as `Arcball` navigation system, similar to how it is implemented in `Meshlab` or `three.js`. This type of control allows a user to manipulate a 3D camera by interacting with a virtual trackball, offering an intuitive way to control the camera in 3D applications, similar to rotating a physical object with your hand.

Here's a detailed breakdown of its functionality:

### 1. Core Concept: The Virtual Trackball

The central idea is to imagine a sphere (the "arcball" or "trackball") in the 3D scene. The user's mouse on the 2D screen is projected onto the surface of this 3D sphere. When the user clicks and drags, the point on the sphere's surface is "grabbed" and dragged, causing the sphere to rotate. This rotation is then applied to the camera, making it orbit around the center of the trackball.

### 2. State Machine

The controls use a state machine to manage the current user interaction. The possible states are defined in the `STATE` constant:

- **IDLE**: No interaction is happening.
- **ROTATE**: The user is rotating the camera.
- **PAN**: The user is panning the camera (moving it left, right, up, or down).
- **SCALE**: The user is zooming the camera in or out.
- **FOV**: The user is changing the camera's field of view (vertigo-style zoom).
- **FOCUS**: The user is focusing on a point in the scene.
- **ZROTATE**: The user is rotating the camera around its own Z-axis.

The `_state` property of the `ArcballControls` class holds the current state. The code transitions between these states based on user input (mouse clicks, wheel movements).

### 3. User Input Handling

The controls listen for various DOM events to capture user input:

- **MouseButton**: When a mouse button is pressed or released.
- **MouseMove**: When the mouse is moved.
- **Scroll**: When the mouse wheel is scrolled.

The `connect` and `disconnect` methods are used to add and remove these event listeners.

### 4. Mouse Actions

The `mouseActions` array allows the user to customize which mouse buttons and key combinations trigger which actions. The `setMouseAction` and `unsetMouseAction` methods are used to configure these actions. By default, the controls are set up with common actions like:

- **Left-click + drag**: Rotate
- **Right-click + drag**: Pan
- **Middle-click + drag**: Zoom
- **Mouse wheel**: Zoom
- **Shift + Mouse wheel**: Change FOV

### 5. Transformations

The core of the controls is in how it translates user input into camera transformations. This is done through a series of matrix operations.

- **Rotation**: When the user rotates, the code projects the cursor's starting and current positions onto the virtual trackball's surface. It then calculates the rotation axis (the cross product of the two vectors from the trackball's center to the projected points) and the rotation angle. This rotation is then applied to the camera's matrix.
- **Panning**: For panning, the cursor's movement is projected onto a plane that is perpendicular to the camera's viewing direction and passes through the trackball's center. The difference between the start and current projected points gives the translation vector, which is then applied to the camera.
- **Zooming**: Zooming is handled by scaling the camera's position relative to the trackball's center. The `scaleFactor` property controls the zoom speed.
- **Center and Zooming**: When the user double-taps to focus on a new target point, the camera will center its position and orientation to focus on that point.
- **FOV (Field of View)**: This is a "vertigo" or "dolly zoom" effect. When the user changes the FOV, the camera's distance to the target is also adjusted to keep the target appearing the same size in the frame. This creates a dramatic effect where the background seems to expand or contract.

### 6. Gizmos (optional)

The controls can display gizmos to visualize the virtual trackball. These are three circles (one for each axis: X, Y, and Z) that show the orientation of the trackball. The `enableGizmos` property controls whether the gizmos are visible. The `activateGizmos` method makes the gizmos more or less opaque depending on whether the user is interacting with them. The `enableGizmosCenter` property controls whether the center of the gizmos sphere is visible.

### 7. Camera State Management

The controls can save and restore the camera's state. The `_cameraMatrixState`, `_cameraProjectionState`, `_fovState`, `_upState`, and `_zoomState` properties are used to store the camera's current state.

### 8. Grid (optional)

When `enableGrid` is true, a grid is displayed on the pan plane during a pan operation. This can help the user to better understand the spatial relationship of the objects in the scene. The `drawGrid` and `disposeGrid` methods are used to create and remove the grid.

### How it all works together: A typical interaction

1.  **Initialization**: An `ArcballControls` instance is created with a `Camera`, and event listeners.
2.  **User Interaction**: The user presses a mouse button. The `HandleMouseButton` function is called.
3.  **State Change**: The controls determine the intended operation (rotate, pan, zoom) based on the mouse button and any modifier keys. The state is changed from `IDLE` to the appropriate state (e.g., `ROTATE`).
4.  **Transformation**: As the user drags the mouse, the `HandleMouseMove` function is called repeatedly. Inside this function, the code calculates the necessary transformation (rotation, pan, etc.) based on the current state and the cursor's movement. The transformation is then applied to the camera's matrix.
5.  **Rendering**: The `change` event is dispatched, which signals to the application that the camera has been updated and the scene needs to be re-rendered.
6.  **Interaction End**: When the user releases the mouse button, the `HandleMouseButton` function is called again.
7.  **Return to Idle**: The state is set back to `IDLE`, and the `end` event is dispatched.
