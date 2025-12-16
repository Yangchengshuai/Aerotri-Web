/*
 * ArcballControls.h
 *
 * Copyright (c) 2014-2025 SEACAVE
 *
 * Author(s):
 *
 *      cDc <cdc.seacave@gmail.com>
 *
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 *
 * Additional Terms:
 *
 *      You are required to preserve legal notices and author attributions in
 *      that material or in the Appropriate Legal Notices displayed by works
 *      containing it.
 */

#pragma once

#include "Camera.h"

namespace VIEWER {
	class Camera; // Forward declaration

/**
 * ArcballControls class implementing intuitive 3D camera navigation.
 * 
 * Based on the three.js ArcballControls implementation, this class provides
 * a virtual trackball interface for camera manipulation. The core concept
 * involves projecting 2D mouse movements onto a virtual sphere (trackball)
 * centered at the camera's target point.
 * 
 * Key Features:
 * - Arcball rotation: Intuitive 3D rotation using virtual trackball
 * - Pan: Translation of camera and target together
 * - Zoom: Moving camera closer/farther from target
 * - FOV: Field of view manipulation (vertigo effect)
 * - Focus: Double-click to focus on a point
 * - Animation: Smooth transitions for focus operations
 * - State management: Save/restore camera states
 * 
 * The implementation uses a state machine to handle different interaction modes
 * and provides smooth, conservative rotation (returning to start position
 * returns camera to original orientation).
 */
class ArcballControls {
public:
	EIGEN_MAKE_ALIGNED_OPERATOR_NEW

	// State machine for trackball interactions
	enum State {
		STATE_IDLE,
		STATE_ROTATE,
		STATE_PAN,
		STATE_SCALE,
		STATE_FOV,
		STATE_FOCUS,
		STATE_ZROTATE,
		STATE_TOUCH_MULTI,
		STATE_ANIMATION_FOCUS,
		STATE_ANIMATION_ROTATE
	};

	// Input type detection
	enum InputType {
		INPUT_NONE,
		INPUT_ONE_FINGER,
		INPUT_ONE_FINGER_SWITCHED,
		INPUT_TWO_FINGER,
		INPUT_MULT_FINGER,
		INPUT_CURSOR
	};

	// Mouse action configuration
	struct MouseAction {
		int mouse;		    // Mouse button (0=left, 1=middle, 2=right) or -1 for wheel
		int key;			// Key modifier (GLFW_MOD_CONTROL, GLFW_MOD_SHIFT, 0=none)
		State operation;    // ROTATE, PAN, ZOOM, FOV
	};

private:
	// Core components
	Camera& camera;

	// State management
	State currentState;
	InputType inputType;

	// Mouse/touch interaction
	bool isDragging;
	int dragButton;
	Eigen::Vector2d lastMousePos;
	Eigen::Vector2d startMousePos;
	std::vector<MouseAction> mouseActions;

	// Trackball parameters
	double radiusFactor;	 // Size of trackball relative to screen
	double sensitivity;
	double rotationSensitivity;
	double zoomSensitivity;
	double panSensitivity;

	// Gizmo settings
	bool enableGizmos;       // Enable/disable gizmo rendering
	bool gizmosActive;       // Current gizmo activation state
	bool enableGizmosCenter; // Enable/disable gizmo center rendering

	// Animation system
	bool isAnimating;
	double animationProgress;
	double animationDuration;
	Eigen::Vector3d animStartPos, animEndPos;
	Eigen::Vector3d animStartTarget, animEndTarget;

public:
	ArcballControls(Camera& camera);
	~ArcballControls();

	// Core interface
	void update(double deltaTime);
	void reset();

	// Input handling
	void handleMouseButton(int button, int action, const Eigen::Vector2d& pos);
	void handleMouseMove(const Eigen::Vector2d& pos);
	void handleScroll(double yOffset);
	void handleKeyboard(int key, int action, int mods);

	// Configuration - setters
	void setRadiusFactor(double factor) { radiusFactor = factor; }
	void setSensitivity(double sens) { sensitivity = sens; }
	void setRotationSensitivity(double sens) { rotationSensitivity = sens; }
	void setZoomSensitivity(double sens) { zoomSensitivity = sens; }
	void setPanSensitivity(double sens) { panSensitivity = sens; }

	// Configuration - getters
	double getRadiusFactor() const { return radiusFactor; }
	double getSensitivity() const { return sensitivity; }
	double getRotationSensitivity() const { return rotationSensitivity; }
	double getZoomSensitivity() const { return zoomSensitivity; }
	double getPanSensitivity() const { return panSensitivity; }

	// Gizmo configuration
	void setEnableGizmos(bool enable) { enableGizmos = enable; }
	bool getEnableGizmos() const { return enableGizmos; }
	bool getGizmosActive() const { return gizmosActive; }
	void activateGizmos(bool active) { gizmosActive = active; }
	void setEnableGizmosCenter(bool enable) { enableGizmosCenter = enable; }
	bool getEnableGizmosCenter() const { return enableGizmosCenter; }

	// Mouse actions configuration
	bool setMouseAction(const State operation, int mouse, int key = 0);
	bool unsetMouseAction(int mouse, int key = 0);
	State getOpFromAction(int mouse, int key) const;

	// State management
	String getStateJSON() const;
	void setStateFromJSON(const String& json);

	// Animation
	void animateTo(const Eigen::Vector3d& newPos, const Eigen::Vector3d& newTarget, double duration = 1.0);
	void focus(const Eigen::Vector3d& point, double size = 1.0, double amount = 1.0);

	// Getters
	State getCurrentState() const { return currentState; }
	bool getIsAnimating() const { return isAnimating; }

private:
	// Core operations
	void rotate(const Eigen::Vector3d& axis, double angle);
	void pan(const Eigen::Vector3d& delta);
	void zoom(double delta);
	void setFOV(double newFov);

	// Internal camera operations
	void rotateArcball(const Eigen::Vector2d& delta);
	void panCamera(const Eigen::Vector2d& delta);
	void zoomCamera(double delta);
	void changeFOV(double delta);

	// Trackball mathematics
	Eigen::Vector3d projectOntoTrackball(const Eigen::Vector2d& mouseNDC) const;
	double calculateTrackballRadius() const;

	// State management
	void applyTransformation(const Eigen::Matrix4d& transform);

	// Animation helpers
	void updateAnimation(double deltaTime);

	// Mouse action helpers
	void initializeMouseActions();
	bool compareMouseAction(const MouseAction& action1, const MouseAction& action2) const;
	static String getNameFromState(const State operation);
    static State getStateFromName(const String& operation);

	// Ray casting for focus operations
	Eigen::Vector3d unprojectOnObject(const Eigen::Vector2d& cursor) const;
	Eigen::Vector3d unprojectOnTrackballSurface(const Eigen::Vector2d& cursor) const;
	Eigen::Vector3d unprojectOnTrackballPlane(const Eigen::Vector2d& cursor) const;
};
/*----------------------------------------------------------------*/

} // namespace VIEWER
