R"glsl(
#version 330 core

out vec4 FragColor;

uniform vec3 boundsColor = vec3(0.0, 1.0, 0.0);

void main() {
    FragColor = vec4(boundsColor, 1.0);
}
)glsl"
