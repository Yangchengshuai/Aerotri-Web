/*
 * Shader.cpp
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
#include "Shader.h"

using namespace VIEWER;

Shader::Shader(const std::string& vertexSrc, const std::string& fragmentSrc, const std::string& geometrySrc) {
	// Load shader sources
	std::string vertexCode = Util::getFileExt(vertexSrc) == ".vert" ? LoadShaderFile(vertexSrc) : vertexSrc;
	std::string fragmentCode = Util::getFileExt(fragmentSrc) == ".frag" ? LoadShaderFile(fragmentSrc) : fragmentSrc;
	std::string geometryCode = Util::getFileExt(geometrySrc) == ".geom" ? LoadShaderFile(geometrySrc) : geometrySrc;

	// Compile shaders
	GLuint vertex = CompileShader(vertexCode, GL_VERTEX_SHADER);
	GLuint fragment = CompileShader(fragmentCode, GL_FRAGMENT_SHADER);
	GLuint geometry = geometryCode.empty() ? 0 : CompileShader(geometryCode, GL_GEOMETRY_SHADER);

	// Create program
	program = glCreateProgram();
	GL_CHECK(glAttachShader(program, vertex));
	GL_CHECK(glAttachShader(program, fragment));
	if (geometry)
		GL_CHECK(glAttachShader(program, geometry));

	GL_CHECK(glLinkProgram(program));
	CheckCompileErrors(program, "PROGRAM");

	// Clean up shaders
	GL_CHECK(glDeleteShader(vertex));
	GL_CHECK(glDeleteShader(fragment));
	if (geometry)
		GL_CHECK(glDeleteShader(geometry));
}

Shader::~Shader() {
	if (program != 0) {
		GL_CHECK(glDeleteProgram(program));
	}
}

void Shader::Use() const {
	GL_CHECK(glUseProgram(program));
}

void Shader::SetMatrix4(const std::string& name, const Eigen::Matrix4f& matrix) {
	glUniformMatrix4fv(GetUniformLocation(name), 1, GL_FALSE, matrix.data());
}

void Shader::SetMatrix3(const std::string& name, const Eigen::Matrix3f& matrix) {
	glUniformMatrix3fv(GetUniformLocation(name), 1, GL_FALSE, matrix.data());
}

void Shader::SetVector3(const std::string& name, const Eigen::Vector3f& vector) {
	glUniform3fv(GetUniformLocation(name), 1, vector.data());
}

void Shader::SetVector2(const std::string& name, const Eigen::Vector2f& vector) {
	glUniform2fv(GetUniformLocation(name), 1, vector.data());
}

void Shader::SetFloat(const std::string& name, float value) {
	glUniform1f(GetUniformLocation(name), value);
}

void Shader::SetUInt(const std::string& name, unsigned value) {
	glUniform1ui(GetUniformLocation(name), value);
}

void Shader::SetInt(const std::string& name, int value) {
	glUniform1i(GetUniformLocation(name), value);
}

void Shader::SetBool(const std::string& name, bool value) {
	glUniform1i(GetUniformLocation(name), value ? 1 : 0);
}

GLint Shader::GetUniformLocation(const std::string& name) {
	auto it = uniformLocations.find(name);
	if (it != uniformLocations.end())
		return it->second;

	GLint location = glGetUniformLocation(program, name.c_str());
	uniformLocations[name] = location;

	if (location == -1)
		DEBUG("Warning: Uniform '%s' not found in shader", name.c_str());
	return location;
}

GLuint Shader::CompileShader(const std::string& source, GLenum type) {
	GLuint shader = glCreateShader(type);
	const char* src = source.c_str();
	GL_CHECK(glShaderSource(shader, 1, &src, NULL));
	GL_CHECK(glCompileShader(shader));
	CheckCompileErrors(shader, type == GL_VERTEX_SHADER ? "VERTEX" : 
						type == GL_FRAGMENT_SHADER ? "FRAGMENT" : "GEOMETRY");
	return shader;
}

void Shader::CheckCompileErrors(GLuint shader, const std::string& type) {
	GLint success;
	GLchar infoLog[1024];

	if (type != "PROGRAM") {
		GL_CHECK(glGetShaderiv(shader, GL_COMPILE_STATUS, &success));
		if (!success) {
			GL_CHECK(glGetShaderInfoLog(shader, 1024, NULL, infoLog));
			DEBUG("ERROR::SHADER_COMPILATION_ERROR of type: %s\n%s\n -- --------------------------------------------------- --", type.c_str(), infoLog);
		}
	} else {
		GL_CHECK(glGetProgramiv(shader, GL_LINK_STATUS, &success));
		if (!success) {
			GL_CHECK(glGetProgramInfoLog(shader, 1024, NULL, infoLog));
			DEBUG("ERROR::PROGRAM_LINKING_ERROR of type: %s\n%s\n -- --------------------------------------------------- --", type.c_str(), infoLog);
		}
	}
}

std::string Shader::LoadShaderFile(const std::string& filename) {
	std::ifstream file(filename, std::ios::in);
	if (!file.is_open()) {
		DEBUG("Failed to open shader file: %s in %s", filename.c_str(), Util::getCurrentFolder().c_str());
		return "";
	}
	std::stringstream buffer;
	buffer << file.rdbuf();
	return buffer.str();
}
/*----------------------------------------------------------------*/
