R"glsl(
#version 330 core

layout (location = 0) out uint outID;

uniform uint uBaseID;

void main() {
    outID = uBaseID + uint(gl_PrimitiveID);
}
)glsl"
