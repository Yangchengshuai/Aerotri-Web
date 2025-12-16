R"glsl(
#version 330 core

in vec3 FragColor;
out vec4 FragColorOut;

uniform float highlightOpacity = 0.8;

void main() {
    FragColorOut = vec4(FragColor, highlightOpacity);
}
)glsl"
