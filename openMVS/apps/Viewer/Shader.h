/*
 * Shader.h
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

namespace VIEWER {

class Shader {
private:
	GLuint program;
	std::unordered_map<std::string, GLint> uniformLocations;
	
public:
	Shader(const std::string& vertexSrc, const std::string& fragmentSrc, const std::string& geometrySrc = "");
	~Shader();

	// Non-copyable
	Shader(const Shader&) = delete;
	Shader& operator=(const Shader&) = delete;

	void Use() const;
	GLuint GetProgram() const { return program; }

	// Uniform setters with Eigen types
	void SetMatrix4(const std::string& name, const Eigen::Matrix4f& matrix);
	void SetMatrix3(const std::string& name, const Eigen::Matrix3f& matrix);
	void SetVector3(const std::string& name, const Eigen::Vector3f& vector);
	void SetVector2(const std::string& name, const Eigen::Vector2f& vector);
	void SetFloat(const std::string& name, float value);
	void SetUInt(const std::string& name, unsigned value);
	void SetInt(const std::string& name, int value);
	void SetBool(const std::string& name, bool value);

	static std::string LoadShaderFile(const std::string& filename);

private:
	GLint GetUniformLocation(const std::string& name);
	GLuint CompileShader(const std::string& source, GLenum type);
	void CheckCompileErrors(GLuint shader, const std::string& type);
};
/*----------------------------------------------------------------*/

} // namespace VIEWER
