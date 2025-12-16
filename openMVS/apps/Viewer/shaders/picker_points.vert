R"glsl(
#version 330 core

layout (location = 0) in vec3 aPos;
flat out uint vVertexID;

uniform uint uBaseID;

layout (std140) uniform ViewProjection {
    mat4 view;
    mat4 projection;
    mat4 viewProjection;
    vec3 cameraPos;
};

void main() {
    gl_Position = viewProjection * vec4(aPos, 1.0);
    vVertexID = uBaseID + uint(gl_VertexID);
}
)glsl"
