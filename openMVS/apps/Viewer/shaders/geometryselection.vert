R"glsl(
#version 330 core

layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;

out vec3 FragColor;

uniform vec3 highlightColor = vec3(1.0, 0.0, 0.0);
uniform bool useHighlight = false;
uniform float pointSize = 5.0;

layout (std140) uniform ViewProjection {
    mat4 view;
    mat4 projection;
    mat4 viewProjection;
    vec3 cameraPos;
};

void main() {
    gl_Position = viewProjection * vec4(aPos, 1.0);
    FragColor = useHighlight ? highlightColor : aColor;
    gl_PointSize = pointSize;
}
)glsl"
