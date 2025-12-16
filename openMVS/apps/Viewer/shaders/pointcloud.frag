R"glsl(
#version 330 core

in vec3 FragColor;
out vec4 FragColorOut;

void main() {
    FragColorOut = vec4(FragColor, 1.0);
}
)glsl"
