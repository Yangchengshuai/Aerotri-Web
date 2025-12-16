/*
 * ArcballControls.cpp
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

#include "Common.h"
#include "ArcballControls.h"

using namespace VIEWER;

ArcballControls::ArcballControls(Camera& cam)
	: camera(cam)
	, currentState(STATE_IDLE)
	, inputType(INPUT_NONE)
	, isDragging(false)
	, dragButton(-1)
	, lastMousePos(0, 0)
	, startMousePos(0, 0)
	, radiusFactor(0.67)
	, sensitivity(1.0)
	, rotationSensitivity(1.0)
	, zoomSensitivity(1.0)
	, panSensitivity(1.0)
	, enableGizmos(true)
	, gizmosActive(false)
	, enableGizmosCenter(true)
	, isAnimating(false)
	, animationProgress(0.0)
	, animationDuration(1.0)
	, animStartPos(0, 0, 0)
	, animEndPos(0, 0, 0)
	, animStartTarget(0, 0, 0)
	, animEndTarget(0, 0, 0)
{
	initializeMouseActions();
}

ArcballControls::~ArcballControls() {
}

void ArcballControls::update(double deltaTime) {
	if (isAnimating)
		updateAnimation(deltaTime);
}

void ArcballControls::reset() {
	currentState = STATE_IDLE;
	isDragging = false;
	isAnimating = false;
	gizmosActive = false;
}

void ArcballControls::handleMouseButton(int button, int action, const Eigen::Vector2d& pos) {
	switch (action) {
	case GLFW_PRESS:
		isDragging = true;
		dragButton = button;
		lastMousePos = pos;
		startMousePos = pos;
		// Determine operation based on mouse action
		currentState = getOpFromAction(button, 0);
		if (enableGizmos)
			gizmosActive = true;
        break;

	case GLFW_RELEASE:
		isDragging = false;
		dragButton = -1;
		currentState = STATE_IDLE;
		if (enableGizmos)
			gizmosActive = false;
	}
}

void ArcballControls::handleMouseMove(const Eigen::Vector2d& pos) {
	if (!isDragging)
		return;

	Eigen::Vector2d delta = pos - lastMousePos;

	switch (currentState) {
		case STATE_ROTATE:
			rotateArcball(delta);
			break;
		case STATE_PAN:
			panCamera(delta);
			break;
		case STATE_SCALE:
			zoomCamera(delta.y());
			break;
		case STATE_FOV:
			changeFOV(delta.y());
			break;
		default:
			break;
	}

	lastMousePos = pos;
}

void ArcballControls::handleScroll(double yOffset) {
	zoomCamera(-yOffset);
}

void ArcballControls::handleKeyboard(int key, int action, int mods) {
	// Handle keyboard shortcuts for state management
}

void ArcballControls::initializeMouseActions() {
	// Default mouse actions
    mouseActions.clear();
	mouseActions.insert(mouseActions.end(), {
		{0, 0, STATE_ROTATE}, // Left button
		{1, 0, STATE_PAN}, // Middle button
		{2, 0, STATE_PAN}, // Right button
		{-1, 0, STATE_SCALE} // Scroll wheel
	});
}

bool ArcballControls::setMouseAction(const State operation, int mouse, int key) {
	// Remove existing action with same mouse/key combination
	unsetMouseAction(mouse, key);

	// Add new action
	mouseActions.emplace_back(MouseAction{mouse, key, operation});
	return true;
}

bool ArcballControls::unsetMouseAction(int mouse, int key) {
	for (size_t i = 0; i < mouseActions.size(); ++i) {
		if (mouseActions[i].mouse == mouse && mouseActions[i].key == key) {
			// Shift remaining actions down
			for (size_t j = i; j < mouseActions.size() - 1; ++j)
				mouseActions[j] = mouseActions[j + 1];
			mouseActions.pop_back();
			return true;
		}
	}
	return false;
}

ArcballControls::State ArcballControls::getOpFromAction(int mouse, int key) const {
	for (size_t i = 0; i < mouseActions.size(); ++i) {
		if (mouseActions[i].mouse == mouse && mouseActions[i].key == key)
			return mouseActions[i].operation;
	}
	return STATE_IDLE;
}

String ArcballControls::getNameFromState(const State operation) {
	switch (operation) {
		case STATE_ROTATE: return "ROTATE";
		case STATE_PAN: return "PAN";
		case STATE_SCALE: return "ZOOM";
		case STATE_FOV: return "FOV";
		default: return "IDLE";
	}
}
ArcballControls::State ArcballControls::getStateFromName(const String& operation) {
    if (operation == "ROTATE") return STATE_ROTATE;
    if (operation == "PAN") return STATE_PAN;
    if (operation == "ZOOM") return STATE_SCALE;
    if (operation == "FOV") return STATE_FOV;
    return STATE_IDLE; // Default to idle if not recognized
}

void ArcballControls::rotateArcball(const Eigen::Vector2d& delta) {
	if (delta.norm() < 1e-6) return;

	// Mouse positions are already in NDC, so we can use them directly
	// Get current and previous cursor positions (already normalized)
	Eigen::Vector2d currentNDC = lastMousePos + delta;
	Eigen::Vector2d previousNDC = lastMousePos;

	// Project cursor positions onto trackball surface
	Eigen::Vector3d currentCursorPosition = unprojectOnTrackballSurface(currentNDC);
	Eigen::Vector3d startCursorPosition = unprojectOnTrackballSurface(previousNDC);

	// Calculate rotation axis and angle using trackball approach
	// Calculate the cross product to get rotation axis
	Eigen::Vector3d rotationAxis = startCursorPosition.cross(currentCursorPosition);
	if (rotationAxis.norm() < 1e-6)
        return;
	rotationAxis.normalize();

	// Transform the axis based on current camera orientation
	// This follows the three.js approach of applying camera rotation to the axis
	rotationAxis = camera.GetRotationMatrix() * rotationAxis;

	// Calculate the angle between the two positions
	double dotProduct = CLAMP(startCursorPosition.dot(currentCursorPosition), -1.0, 1.0);
	double angle = ACOS(dotProduct);

	// Apply rotation speed
	angle *= rotationSensitivity;

	// Apply the rotation
	rotate(rotationAxis, angle);
}

void ArcballControls::panCamera(const Eigen::Vector2d& delta) {
	const Eigen::Vector3d& cameraPos = camera.GetPosition();
	const Eigen::Vector3d& cameraTarget = camera.GetTarget();
	const Eigen::Vector3d& cameraUp = camera.GetUp();

	Eigen::Vector3d forward = (cameraTarget - cameraPos).normalized();
	Eigen::Vector3d right = forward.cross(cameraUp).normalized();
	Eigen::Vector3d up = right.cross(forward).normalized();

	double distance = (cameraPos - cameraTarget).norm();
	double panSpeed = distance * panSensitivity;

	Eigen::Vector3d panVector = right * (delta.x() * panSpeed) + up * (delta.y() * panSpeed);
	pan(-panVector);
}

void ArcballControls::zoomCamera(double delta) {
	const double distance = MINF(camera.GetSceneDistance()*0.3, (camera.GetPosition() - camera.GetTarget()).norm());
	const double speed = MAXF(0.001, 0.15 * distance * zoomSensitivity);
	zoom(delta * speed);
}

void ArcballControls::changeFOV(double delta) {
	double currentFOV = camera.GetFOV();
	double newFOV = currentFOV + delta * 0.1;
	setFOV(newFOV);
}

void ArcballControls::rotate(const Eigen::Vector3d& axis, double angle) {
	if (ABS(angle) < 1e-6) return;

	Eigen::Vector3d cameraPos = camera.GetPosition();
	Eigen::Vector3d cameraUp = camera.GetUp();
	Eigen::Vector3d target = camera.GetTarget();

	// Normalize the rotation axis
	Eigen::Vector3d normalizedAxis = axis.normalized();

	// Create rotation quaternion - note the angle direction
	Eigen::Quaterniond rotation(Eigen::AngleAxisd(-angle, normalizedAxis)); // Negative for correct direction

	// Rotate camera position around target
	Eigen::Vector3d offset = cameraPos - target;
	offset = rotation * offset;
	Eigen::Vector3d newPos = target + offset;

	// Also rotate the up vector to maintain proper orientation
	Eigen::Vector3d newUp = rotation * cameraUp;
	newUp.normalize();

	// Update camera - ensure up vector is normalized
	camera.SetLookAt(newPos, target, newUp);
}

void ArcballControls::pan(const Eigen::Vector3d& delta) {
	Eigen::Vector3d newPos = camera.GetPosition() + delta;
	Eigen::Vector3d newTarget = camera.GetTarget() + delta;

	camera.SetLookAt(newPos, newTarget, camera.GetUp());
}

void ArcballControls::zoom(double delta) {
	const Eigen::Vector3d& cameraPos = camera.GetPosition();
	const Eigen::Vector3d& target = camera.GetTarget();
	Eigen::Vector3d direction = (target - cameraPos).normalized();
	Eigen::Vector3d newPos = cameraPos + direction * delta * sensitivity;

	// Prevent zooming too close to the target
	// Compute dynamic minimum distance as a percentage of the scene size
	const double distance = (newPos - target).norm();
	if (distance < camera.GetNearPlane())
		return;
	if (distance > camera.GetFarPlane())
		return;
	camera.SetLookAt(newPos, target, camera.GetUp());
}

void ArcballControls::setFOV(double newFov) {
	camera.SetFOV(CLAMP(newFov, 1.0, 179.0));
}

void ArcballControls::focus(const Eigen::Vector3d& target, double size, double amount) {
	// Move camera closer for focus effect
	Eigen::Vector3d cameraPos = camera.GetPosition();
	Eigen::Vector3d direction = (cameraPos - target);
	Eigen::Vector3d newPos = target + direction * 0.8;

	if (amount < 1.0) {
		// Animate to focus position
		animateTo(newPos, target, 1.0);
	} else {
		// Immediate focus
		camera.SetLookAt(newPos, target, camera.GetUp());
	}
}

Eigen::Vector3d ArcballControls::projectOntoTrackball(const Eigen::Vector2d& mouseNDC) const {
	const double trackballRadius = 1.0;

	double x = mouseNDC.x();
	double y = mouseNDC.y();
	double lengthSquared = x * x + y * y;
	double length = sqrt(lengthSquared);

	Eigen::Vector3d point(x, y, 0);

	if (length <= trackballRadius * 0.70710678118654752440) {
		// Inside sphere
		point.z() = sqrt(trackballRadius * trackballRadius - lengthSquared);
	} else {
		// Outside sphere - hyperbolic sheet
		double t = trackballRadius / (1.41421356237309504880 * length);
		point.x() *= t;
		point.y() *= t;
		point.z() = trackballRadius * trackballRadius / (2.0 * length);
	}

	return point.normalized();
}

double ArcballControls::calculateTrackballRadius() const {
	// Use radiusFactor to scale the trackball size
	// This approach is similar to three.js calculateTbRadius
	double radius;
	const int minSide = MINF(camera.GetSize().width, camera.GetSize().height);
	if (camera.IsOrthographic()) {
		// For orthographic camera, use zoom and viewport
		double zoom = 1.0; // TODO: Get actual zoom from camera if available
		radius = minSide * radiusFactor / (2.0 * zoom);
	} else {
		// Calculate radius based on camera distance and viewport
		double distance = (camera.GetPosition() - camera.GetTarget()).norm();

		// For perspective camera, calculate based on FOV and distance
		double fov = D2R(camera.GetFOV()); // Convert to radians
		radius = distance * TAN(fov / 2.0) * radiusFactor * minSide / camera.GetSize().height;
	}
	return radius;
}

void ArcballControls::animateTo(const Eigen::Vector3d& newPos, const Eigen::Vector3d& newTarget, double duration) {
	animStartPos = camera.GetPosition();
	animStartTarget = camera.GetTarget();
	animEndPos = newPos;
	animEndTarget = newTarget;
	animationDuration = duration;
	animationProgress = 0.0;
	isAnimating = true;
}

void ArcballControls::updateAnimation(double deltaTime) {
	animationProgress += deltaTime / animationDuration;
	if (animationProgress >= 1.0) {
		animationProgress = 1.0;
		isAnimating = false;
	}

	// Smooth interpolation (ease-out cubic)
	double t = 1.0 - POW(1.0 - animationProgress, 3.0);

	// Interpolate position and target
	Eigen::Vector3d currentPos = animStartPos * (1.0 - t) + animEndPos * t;
	Eigen::Vector3d currentTarget = animStartTarget * (1.0 - t) + animEndTarget * t;

	camera.SetLookAt(currentPos, currentTarget, camera.GetUp());
}

String ArcballControls::getStateJSON() const {
	// Simple state serialization
	// In a real implementation, this would use a proper JSON library
	return String("{}");
}

void ArcballControls::setStateFromJSON(const String& json) {
	// Simple state deserialization
	// In a real implementation, this would parse JSON
}

void ArcballControls::applyTransformation(const Eigen::Matrix4d& transform) {
	// Apply transformation matrix to camera
	// This is a placeholder implementation
}

Eigen::Vector3d ArcballControls::unprojectOnTrackballSurface(const Eigen::Vector2d& cursor) const {
	// cursor is already in NDC coordinates (-1 to 1)
	const double length = cursor.norm();
	const double trackballRadius = 1.0;
	Eigen::Vector3d dir(cursor.x(), cursor.y(), 0);

	if (length <= trackballRadius * M_SQRT1_2) {
		// Inside sphere - use sphere equation
		dir.z() = SQRT(SQUARE(trackballRadius) - SQUARE(length));
	} else {
		// Outside sphere - use hyperbolic sheet for smooth transition
		double t = trackballRadius / (M_SQRT2 * length);
		dir.x() *= t;
		dir.y() *= t;
		dir.z() = SQUARE(trackballRadius) / (2.0 * length);
	}
	return dir.normalized();
}

Eigen::Vector3d ArcballControls::unprojectOnTrackballPlane(const Eigen::Vector2d& cursor) const {
	// Project cursor onto plane passing through target
	// This is a simplified implementation
	return Eigen::Vector3d(cursor.x(), cursor.y(), 0) + camera.GetTarget();
}
/*----------------------------------------------------------------*/
