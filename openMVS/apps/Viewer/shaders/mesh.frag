R"glsl(
#version 330 core

in vec3 fragPos;
in vec3 normal;
in vec3 viewDir;

out vec4 FragColor;

uniform bool wireframe = false;
uniform vec3 meshColor = vec3(0.8, 0.8, 0.8);

layout (std140) uniform Lighting {
    vec3 lightDirection;
    float lightIntensity;
    vec3 lightColor;
    float ambientStrength;
    vec3 ambientColor;
};

void main() {
    float ambientStrength = 0.3;
    float diffuseStrength = 1.0;
    float specularStrength = 0.2;
    vec3 norm = normal;
    if (dot(norm, viewDir) < 0.0) {
        // Two-sided lighting
        norm = -norm;
        ambientStrength = 0.1;
        diffuseStrength = 0.5;
    }
    
    // Ambient lighting
    vec3 ambient = ambientStrength * ambientColor;
    
    // Diffuse lighting
    float diff = max(dot(norm, viewDir), 0.0);
    vec3 diffuse = diffuseStrength * diff * lightColor;
    
    // Specular lighting
    vec3 reflectDir = reflect(lightDirection, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
    vec3 specular = specularStrength * spec * lightColor;
    
    vec3 color;
    if (wireframe) {
        color = vec3(0.0, 0.0, 0.0);
    } else {
        color = meshColor * (ambient + diffuse + specular);
    }
    FragColor = vec4(color, 1.0);
}
)glsl"
