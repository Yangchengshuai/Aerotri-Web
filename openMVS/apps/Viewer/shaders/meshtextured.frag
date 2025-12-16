R"glsl(
#version 330 core

in vec2 texCoord;

out vec4 FragColor;

uniform sampler2D diffuseTexture;
uniform bool wireframe = false;

void main() {
    vec3 color;
    if (wireframe) {
        color = vec3(0.0, 0.0, 0.0);
    } else {
        color = texture(diffuseTexture, texCoord).rgb;
    }
    FragColor = vec4(color, 1.0);
}
)glsl"
