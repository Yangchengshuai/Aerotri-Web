R"glsl(
#version 330 core

layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;

out vec3 FragColor;

// Uniforms
uniform float pointSize;

// Uniform Block for ViewProjection
layout (std140) uniform ViewProjection {
    mat4 view;
    mat4 projection;
    mat4 viewProjection;
    vec3 cameraPos;
    float padding;
};

void main() {
    gl_Position = viewProjection * vec4(aPos, 1.0);
    FragColor = aColor;
    gl_PointSize = pointSize;
}
)glsl"
