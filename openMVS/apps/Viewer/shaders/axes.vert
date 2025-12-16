R"glsl(
#version 330 core

layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;

uniform mat4 viewProjection;
uniform float axesScale = 0.9;

out vec3 vertexColor;

void main() {
    // Scale the vertex position
    vec3 scaledPos = aPos * axesScale;
    
    // Apply the view-projection matrix
    gl_Position = viewProjection * vec4(scaledPos, 1.0);
    
    // Pass color to fragment shader
    vertexColor = aColor;
}
)glsl"
