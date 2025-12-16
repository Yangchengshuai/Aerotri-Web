R"glsl(
#version 330 core

uniform vec3 overlayColor;
uniform float overlayOpacity;

out vec4 FragColor;

void main() {
    FragColor = vec4(overlayColor, overlayOpacity);
}
)glsl"
