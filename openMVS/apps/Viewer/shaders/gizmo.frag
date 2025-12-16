R"glsl(
#version 330 core

uniform vec3 gizmoColor;
uniform float opacity;

out vec4 FragColor;

void main() {
    FragColor = vec4(gizmoColor, opacity);
}
)glsl"
