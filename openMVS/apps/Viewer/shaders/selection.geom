R"glsl(
#version 330 core

layout (lines) in;
layout (triangle_strip, max_vertices = 4) out;

layout (std140) uniform ViewProjection {
    mat4 view;
    mat4 projection;
    mat4 viewProjection;
    vec3 cameraPos;
};

uniform vec2 viewportSize;
uniform float lineWidth = 2.0;

void main() {
    vec4 clip0 = gl_in[0].gl_Position;
    vec4 clip1 = gl_in[1].gl_Position;

    // Compute normalized device coordinates
    vec2 ndc0 = clip0.xy / clip0.w;
    vec2 ndc1 = clip1.xy / clip1.w;
    vec2 segment = ndc1 - ndc0;

    // Ensure segment length and viewport are valid before dividing.
    float segLength = length(segment);
    if (segLength <= 1e-6 || viewportSize.x <= 0.0 || viewportSize.y <= 0.0)
        return;
    vec2 dir = segment / segLength;
    vec2 perp = vec2(-dir.y, dir.x);

    // Convert half-width from pixels to NDC units. For very thin lines
    // (lineWidth <= 1.0) ensure we still produce a one-pixel quad by
    // clamping halfWidth to at least 0.5. This avoids emitting only two
    // vertices (no triangle) when the shader output is a triangle_strip.
    float halfWidth = max(0.5, lineWidth * 0.5);
    vec2 screenOffset = perp * halfWidth;
    vec2 ndcOffset = screenOffset / viewportSize * 2.0;

    vec4 offset0 = vec4(ndcOffset * clip0.w, 0.0, 0.0);
    vec4 offset1 = vec4(ndcOffset * clip1.w, 0.0, 0.0);

    // Emit quad as triangle strip
    gl_Position = clip0 + offset0;
    EmitVertex();
    gl_Position = clip0 - offset0;
    EmitVertex();
    gl_Position = clip1 + offset1;
    EmitVertex();
    gl_Position = clip1 - offset1;
    EmitVertex();
    EndPrimitive();
}
)glsl"
