R"glsl(
#version 330 core

in vec2 TexCoord;
out vec4 FragColor;

uniform sampler2D overlayTexture;
uniform float opacity;

void main() {
    vec4 texColor = texture(overlayTexture, TexCoord);
    FragColor = vec4(texColor.rgb, texColor.a * opacity);
}
)glsl"
