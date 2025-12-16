R"glsl(
#version 330 core

layout(location = 0) in vec3 position;

layout(std140) uniform ViewProjection {
    mat4 view;
    mat4 projection;
    mat4 viewProjection;
    vec3 cameraPos;
};

uniform mat4 modelMatrix;

void main() {
    gl_Position = viewProjection * modelMatrix * vec4(position, 1.0);
}
)glsl"
