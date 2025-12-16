R"glsl(
#version 330 core

flat in uint vVertexID;
layout (location = 0) out uint outID;

void main() {
    outID = vVertexID;
}
)glsl"
