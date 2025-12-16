/*
 * FirstPersonControls.cpp
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
#include "FirstPersonControls.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

using namespace VIEWER;

FirstPersonControls::FirstPersonControls(Camera& cam)
	: camera(cam)
	, lastMousePos(0, 0)
	, yaw(-90.0) // Start facing forward (-Z direction)
	, pitch(0.0)
	, mouseSensitivity(0.5)
	, movementSpeed(5.0)
	, sprintMultiplier(2.0)
	, maxPitch(89.0)
{
	reset();
}

FirstPersonControls::~FirstPersonControls() {
}

void FirstPersonControls::reset() {
	// Initialize orientation from current camera state instead of hardcoded defaults
	Eigen::Vector3d forward = (camera.GetTarget() - camera.GetPosition()).normalized();

	// Calculate yaw and pitch from current forward vector
	yaw = R2D(ATAN2(forward.z(), forward.x()));
	pitch = R2D(ASIN(forward.y()));

	firstMouse = true;
	isDragging = false;

	// Reset key states
	for (int i = 0; i < 512; ++i)
		keys[i] = false;

	updateCameraVectors();
}

void FirstPersonControls::handleMouseButton(int button, int action, const Eigen::Vector2d& pos) {
	if (button == GLFW_MOUSE_BUTTON_LEFT) {
		if (action == GLFW_PRESS) {
			isDragging = true;
			lastMousePos = pos;
			firstMouse = true;
		} else if (action == GLFW_RELEASE) {
			isDragging = false;
		}
	}
}

void FirstPersonControls::handleMouseMove(const Eigen::Vector2d& pos) {
	if (!isDragging)
		return;

	if (firstMouse) {
		lastMousePos = pos;
		firstMouse = false;
		return;
	}

	// Calculate mouse movement delta
	Eigen::Vector2d delta = pos - lastMousePos;
	lastMousePos = pos;

	// Convert NDC coordinates to screen-like coordinates for sensitivity
	double xOffset = delta.x() * mouseSensitivity * camera.GetSize().width * 0.5;
	double yOffset = delta.y() * mouseSensitivity * camera.GetSize().height * 0.5;

	// Update camera rotation
	rotate(xOffset, yOffset); // Negative Y for inverted mouse
}

void FirstPersonControls::handleScroll(double yOffset) {
	// Use scroll wheel to adjust movement speed
	movementSpeed = CLAMP(movementSpeed + yOffset * 0.5, 0.1, 50.0);
}

void FirstPersonControls::handleKeyboard(int key, int action, int mods) {
	if (key >= 0 && key < 512) {
		if (action == GLFW_PRESS) {
			keys[key] = true;
		} else if (action == GLFW_RELEASE) {
			keys[key] = false;
		}
	}
}

void FirstPersonControls::update(double deltaTime) {
	processMovement(deltaTime);
}

void FirstPersonControls::rotate(double deltaYaw, double deltaPitch) {
	yaw += deltaYaw;
	pitch += deltaPitch;

	constrainPitch();
	updateCameraVectors();
}

void FirstPersonControls::move(const Eigen::Vector3d& direction, double distance) {
	Eigen::Vector3d newPosition = camera.GetPosition() + direction * distance;

	// Keep the same target relative to the camera
	Eigen::Vector3d forward = getForward();
	Eigen::Vector3d newTarget = newPosition + forward;

	camera.SetLookAt(newPosition, newTarget, camera.GetUp());
}

void FirstPersonControls::processMovement(double deltaTime) {
	double speed = movementSpeed;

	// Sprint modifier
	if (keys[GLFW_KEY_LEFT_SHIFT] || keys[GLFW_KEY_RIGHT_SHIFT])
		speed *= sprintMultiplier;

	double velocity = speed * deltaTime;

	// Calculate movement vectors
	Eigen::Vector3d forward = getForward();
	Eigen::Vector3d right = getRight();
	Eigen::Vector3d up = Eigen::Vector3d(0, 1, 0); // World up for flying

	// WASD movement
	if (keys[GLFW_KEY_W])
		move(forward, velocity);
	if (keys[GLFW_KEY_S])
		move(-forward, velocity);
	if (keys[GLFW_KEY_A])
		move(-right, velocity);
	if (keys[GLFW_KEY_D])
		move(right, velocity);

	// Vertical movement (flying)
	if (keys[GLFW_KEY_Q] || keys[GLFW_KEY_E]) {
		if (keys[GLFW_KEY_Q])
			move(-up, velocity);
		if (keys[GLFW_KEY_E])
			move(up, velocity);
	}
}

void FirstPersonControls::updateCameraVectors() {
	// Calculate the new forward vector from yaw and pitch
	Eigen::Vector3d forward = getForward();
	Eigen::Vector3d right = getRight();
	Eigen::Vector3d up = right.cross(forward).normalized();

	// Update camera target based on current position and forward direction
	Eigen::Vector3d position = camera.GetPosition();
	Eigen::Vector3d target = position + forward;

	camera.SetLookAt(position, target, up);
}

void FirstPersonControls::constrainPitch() {
	pitch = CLAMP(pitch, -maxPitch, maxPitch);
}

Eigen::Vector3d FirstPersonControls::getForward() const {
	double yawRad = D2R(yaw);
	double pitchRad = D2R(pitch);

	Eigen::Vector3d forward;
	forward.x() = COS(yawRad) * COS(pitchRad);
	forward.y() = SIN(pitchRad);
	forward.z() = SIN(yawRad) * COS(pitchRad);

	return forward.normalized();
}

Eigen::Vector3d FirstPersonControls::getRight() const {
	Eigen::Vector3d forward = getForward();
	Eigen::Vector3d worldUp(0, 1, 0);
	return forward.cross(worldUp).normalized();
}

Eigen::Vector3d FirstPersonControls::getPosition() const {
	return camera.GetPosition();
}

Eigen::Vector3d FirstPersonControls::getDirection() const {
	return getForward();
}

Eigen::Vector3d FirstPersonControls::getUp() const {
	return camera.GetUp();
}
/*----------------------------------------------------------------*/
