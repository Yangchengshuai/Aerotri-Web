R"glsl(
#version 330 core

out vec4 FragColor;

uniform vec3 selectionColor = vec3(1.0, 0.0, 0.0);

void main() {
    FragColor = vec4(selectionColor, 1.0);
}
)glsl"
