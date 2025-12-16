R"glsl(
#version 330 core

layout (location = 0) in vec3 position;  // 3D world position
layout (location = 1) in vec2 texCoord;  // Texture coordinates

layout (std140) uniform ViewProjection {
    mat4 view;
    mat4 projection;
    mat4 viewProjection;
    vec3 cameraPos;
};

out vec2 TexCoord;

void main() {
    gl_Position = viewProjection * vec4(position, 1.0);
    TexCoord = texCoord;
}
)glsl"
