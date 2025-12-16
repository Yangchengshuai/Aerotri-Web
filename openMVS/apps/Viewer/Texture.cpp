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
#include "Texture.h"

using namespace VIEWER;

Texture::Texture()
	: texID(0), width(0), height(0), channels(0) {}

Texture::~Texture() {
	Release();
}

Texture::Texture(Texture&& other) noexcept
	: texID(other.texID), width(other.width), height(other.height), channels(other.channels) {
	other.texID = 0;
	other.width = other.height = other.channels = 0;
}

Texture& Texture::operator=(Texture&& other) noexcept {
	if (this != &other) {
		Release();
		texID = other.texID;
		width = other.width;
		height = other.height;
		channels = other.channels;
		other.texID = 0;
		other.width = other.height = other.channels = 0;
	}
	return *this;
}

// Create texture from an OpenCV image:
//  - genMipmaps: if true, generate mipmaps and set min filter to a mipmap-friendly filter.
//  - srgb: if true, use sRGB internal formats (when available) for correct colorspace on upload.
bool Texture::Create(cv::InputArray img, bool genMipmaps, bool srgb) {
	if (img.empty())
		return false;
	Release();

	ASSERT(img.depth() == CV_8U, "Expect 8-bit images");
	cv::Mat image(img.getMat());
	width = image.cols;
	height = image.rows;
	channels = image.channels();

	GLenum internalFormat = GL_RGB8;
	GLenum pixelFormat = GL_BGR;
	switch (channels) {
	case 1:
		internalFormat = GL_R8;
		pixelFormat = GL_RED;
		break;
	case 3:
		internalFormat = srgb ? GL_SRGB8 : GL_RGB8;
		pixelFormat = GL_BGR;
		break;
	case 4:
		internalFormat = srgb ? GL_SRGB8_ALPHA8 : GL_RGBA8;
		pixelFormat = GL_BGRA;
		break;
	default:
		// Unsupported
		return false;
	}

	GL_CHECK(glGenTextures(1, &texID));
	GL_CHECK(glBindTexture(GL_TEXTURE_2D, texID));

	GL_CHECK(glPixelStorei(GL_UNPACK_ALIGNMENT, 1));
	GL_CHECK(glTexImage2D(GL_TEXTURE_2D, 0, internalFormat, width, height, 0, pixelFormat, GL_UNSIGNED_BYTE, image.ptr<uint8_t>()));

	if (genMipmaps) {
		GL_CHECK(glGenerateMipmap(GL_TEXTURE_2D));
		GL_CHECK(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR));
	} else {
		GL_CHECK(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR));
	}
	GL_CHECK(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR));
	GL_CHECK(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE));
	GL_CHECK(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE));
	return true;
}

void Texture::Release() {
	if (texID) {
		GL_CHECK(glDeleteTextures(1, &texID));
		texID = 0;
	}
	width = height = channels = 0;
}

void Texture::Bind() const {
	ASSERT(texID);
	GL_CHECK(glBindTexture(GL_TEXTURE_2D, texID));
}
/*----------------------------------------------------------------*/
