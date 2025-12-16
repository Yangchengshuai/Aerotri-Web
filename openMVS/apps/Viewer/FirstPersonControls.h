/*
 * FirstPersonControls.h
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

/**
 * FirstPersonControls class implementing first-person camera navigation.
 * 
 * This class provides traditional first-person camera controls where:
 * - Mouse movement rotates the camera view (look around)
 * - WASD keys move the camera position
 * - Mouse wheel controls movement speed
 * - The camera moves freely through 3D space like a first-person game
 */
class FirstPersonControls {
public:
	EIGEN_MAKE_ALIGNED_OPERATOR_NEW

	// Constructor
	FirstPersonControls(Camera& cam);
	~FirstPersonControls();

	void reset();

	// Input handling
	void handleMouseButton(int button, int action, const Eigen::Vector2d& pos);
	void handleMouseMove(const Eigen::Vector2d& pos);
	void handleScroll(double yOffset);
	void handleKeyboard(int key, int action, int mods);

	// Update
	void update(double deltaTime);

	// Settings
	void setMouseSensitivity(double sensitivity) { mouseSensitivity = sensitivity; }
	void setMovementSpeed(double speed) { movementSpeed = speed; }
	void setSprintMultiplier(double multiplier) { sprintMultiplier = multiplier; }

	double getMouseSensitivity() const { return mouseSensitivity; }
	double getMovementSpeed() const { return movementSpeed; }
	double getSprintMultiplier() const { return sprintMultiplier; }

	// Camera state
	Eigen::Vector3d getPosition() const;
	Eigen::Vector3d getDirection() const;
	Eigen::Vector3d getUp() const;

private:
	// Camera reference
	Camera& camera;

	// Mouse state
	bool isDragging;
	Eigen::Vector2d lastMousePos;
	bool firstMouse;

	// Camera orientation (Euler angles)
	double yaw;   // Horizontal rotation
	double pitch; // Vertical rotation

	// Movement state
	bool keys[512]; // Track key states - increased size for GLFW keys

	// Settings
	double mouseSensitivity;
	double movementSpeed;
	double sprintMultiplier;

	// Constraints
	double maxPitch; // Limit vertical look angle

	// Internal methods
	void updateCameraVectors();
	void processMovement(double deltaTime);
	void rotate(double deltaYaw, double deltaPitch);
	void move(const Eigen::Vector3d& direction, double distance);

	// Utility
	Eigen::Vector3d getForward() const;
	Eigen::Vector3d getRight() const;
	void constrainPitch();
};
/*----------------------------------------------------------------*/

} // namespace VIEWER
