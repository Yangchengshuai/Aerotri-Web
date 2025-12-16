R"glsl(
#version 330 core

layout (location = 0) in vec2 position;

void main() {
    // Coordinates are already in NDC space [-1, 1]
    gl_Position = vec4(position.x, position.y, 0.0, 1.0);
}
)glsl"
