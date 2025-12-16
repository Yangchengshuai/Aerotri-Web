R"glsl(
#version 330 core

out vec4 FragColorOut;

uniform vec3 normalColor;

void main() {
    FragColorOut = vec4(normalColor, 1.0);
}
)glsl"
