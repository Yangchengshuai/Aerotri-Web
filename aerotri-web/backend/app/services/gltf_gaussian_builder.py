"""glTF Gaussian Splatting builder.

This module provides functionality to build glTF 2.0 files with
KHR_gaussian_splatting extension for 3D Gaussian Splatting data.
"""

import json
import struct
import numpy as np
from pathlib import Path
from typing import Dict, Optional, List, Tuple


class GLTFGaussianBuilder:
    """Builder for glTF files with KHR_gaussian_splatting extension."""
    
    def __init__(self):
        self.positions = None
        self.rotations = None
        self.scales = None
        self.colors = None
        self.alphas = None
        self.sh_coefficients = None
        self.sh_degree = 0
        self.num_points = 0
    
    def set_gaussian_data(
        self,
        positions: np.ndarray,
        rotations: np.ndarray,
        scales: np.ndarray,
        colors: np.ndarray,
        alphas: np.ndarray,
        sh_coefficients: Optional[np.ndarray] = None,
        sh_degree: int = 0
    ):
        """Set Gaussian splatting data.
        
        Args:
            positions: (N, 3) array of positions
            rotations: (N, 4) array of quaternions (x, y, z, w)
            scales: (N, 3) array of scales
            colors: (N, 3) array of RGB colors
            alphas: (N,) array of alpha values
            sh_coefficients: (N, M) array of SH coefficients (optional)
            sh_degree: Spherical harmonics degree (0-3)
        """
        self.num_points = positions.shape[0]
        self.positions = positions.astype(np.float32).flatten()
        self.rotations = rotations.astype(np.float32).flatten()
        self.scales = scales.astype(np.float32).flatten()
        self.colors = colors.astype(np.float32).flatten()
        # 应用 sigmoid 函数将 opacity 转换为 [0, 1] 范围的 alpha
        # PLY 文件中的 opacity 是原始值，需要转换为标准的 alpha 值
        self.alphas = (1.0 / (1.0 + np.exp(-alphas))).astype(np.float32)
        self.sh_coefficients = sh_coefficients.astype(np.float32).flatten() if sh_coefficients is not None else None
        self.sh_degree = sh_degree
    
    def build_gltf(self, output_path: Path, use_glb: bool = False) -> Path:
        """Build glTF file with Gaussian splatting extension.
        
        Args:
            output_path: Output file path
            use_glb: Whether to generate binary GLB format
            
        Returns:
            Path to generated file
        """
        if use_glb:
            return self._build_glb(output_path)
        else:
            return self._build_gltf_json(output_path)
    
    def _build_gltf_json(self, output_path: Path) -> Path:
        """Build JSON glTF file."""
        # Create buffers directory
        buffers_dir = output_path.parent / f"{output_path.stem}_buffers"
        buffers_dir.mkdir(exist_ok=True)
        
        # Build binary buffer
        buffer_data = self._build_buffer()
        buffer_file = buffers_dir / "data.bin"
        with open(buffer_file, 'wb') as f:
            f.write(buffer_data)
        
        buffer_uri = f"{output_path.stem}_buffers/data.bin"
        buffer_size = len(buffer_data)
        
        # Calculate byte offsets
        positions_offset = 0
        positions_size = len(self.positions) * 4
        
        rotations_offset = positions_offset + positions_size
        rotations_size = len(self.rotations) * 4
        
        scales_offset = rotations_offset + rotations_size
        scales_size = len(self.scales) * 4
        
        colors_offset = scales_offset + scales_size
        colors_size = len(self.colors) * 4
        
        alphas_offset = colors_offset + colors_size
        alphas_size = len(self.alphas) * 4
        
        sh_offset = alphas_offset + alphas_size
        sh_size = len(self.sh_coefficients) * 4 if self.sh_coefficients is not None else 0
        
        # Build glTF structure
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "AeroTri 3DGS Tiles Converter"
            },
            "extensionsUsed": ["KHR_gaussian_splatting"],
            "extensionsRequired": ["KHR_gaussian_splatting"],
            "buffers": [
                {
                    "uri": buffer_uri,
                    "byteLength": buffer_size
                }
            ],
            "bufferViews": [
                {
                    "buffer": 0,
                    "byteOffset": positions_offset,
                    "byteLength": positions_size,
                    "target": 34962  # ARRAY_BUFFER
                },
                {
                    "buffer": 0,
                    "byteOffset": rotations_offset,
                    "byteLength": rotations_size,
                    "target": 34962
                },
                {
                    "buffer": 0,
                    "byteOffset": scales_offset,
                    "byteLength": scales_size,
                    "target": 34962
                },
                {
                    "buffer": 0,
                    "byteOffset": colors_offset,
                    "byteLength": colors_size,
                    "target": 34962
                },
                {
                    "buffer": 0,
                    "byteOffset": alphas_offset,
                    "byteLength": alphas_size,
                    "target": 34962
                }
            ],
            "accessors": [
                {
                    "bufferView": 0,
                    "componentType": 5126,  # FLOAT
                    "count": self.num_points,
                    "type": "VEC3",
                    "min": self._calculate_min(self.positions.reshape(-1, 3)),
                    "max": self._calculate_max(self.positions.reshape(-1, 3))
                },
                {
                    "bufferView": 1,
                    "componentType": 5126,  # FLOAT
                    "count": self.num_points,
                    "type": "VEC4"
                },
                {
                    "bufferView": 2,
                    "componentType": 5126,  # FLOAT
                    "count": self.num_points,
                    "type": "VEC3"
                },
                {
                    "bufferView": 3,
                    "componentType": 5126,  # FLOAT
                    "count": self.num_points,
                    "type": "VEC3"
                },
                {
                    "bufferView": 4,
                    "componentType": 5126,  # FLOAT
                    "count": self.num_points,
                    "type": "SCALAR"
                }
            ],
            "meshes": [
                {
                    "name": "GaussianSplats",
                    # Cesium 需要通过 POSITION 对应 accessor 的 count 推断点的数量，
                    # 因此这里至少要提供 POSITION 属性，指向 accessors[0]。
                    "primitives": [
                        {
                            "attributes": {
                                "POSITION": 0
                            },
                            "mode": 0  # POINTS
                        }
                    ],
                    "extensions": {
                        "KHR_gaussian_splatting": {
                            "positions": 0,
                            "rotations": 1,
                            "scales": 2,
                            "colors": 3,
                            "alphas": 4
                        }
                    }
                }
            ],
            "nodes": [
                {
                    "mesh": 0,
                    "children": []
                }
            ],
            "scenes": [
                {
                    "nodes": [0]
                }
            ],
            "scene": 0
        }
        
        # Add SH coefficients if available
        if self.sh_coefficients is not None and len(self.sh_coefficients) > 0:
            sh_buffer_view = {
                "buffer": 0,
                "byteOffset": sh_offset,
                "byteLength": sh_size,
                "target": 34962
            }
            gltf["bufferViews"].append(sh_buffer_view)
            
            sh_accessor = {
                "bufferView": len(gltf["bufferViews"]) - 1,
                "componentType": 5126,  # FLOAT
                "count": self.num_points,
                "type": "SCALAR"
            }
            gltf["accessors"].append(sh_accessor)
            
            gltf["meshes"][0]["extensions"]["KHR_gaussian_splatting"]["sphericalHarmonics"] = len(gltf["accessors"]) - 1
            gltf["meshes"][0]["extensions"]["KHR_gaussian_splatting"]["sphericalHarmonicsDegree"] = self.sh_degree
        
        # Write glTF JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(gltf, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def _build_glb(self, output_path: Path) -> Path:
        """Build binary GLB file."""
        # Build binary buffer
        buffer_data = self._build_buffer()
        
        # Build glTF JSON (without buffer URI)
        gltf_json = self._build_gltf_json_dict_for_glb()
        json_str = json.dumps(gltf_json, separators=(',', ':'), ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        
        # Pad JSON to 4-byte boundary
        json_padding = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b' ' * json_padding
        
        # Pad buffer to 4-byte boundary
        buffer_padding = (4 - (len(buffer_data) % 4)) % 4
        buffer_data += b'\x00' * buffer_padding
        
        # GLB structure:
        # - 12-byte header
        # - JSON chunk (chunk length + type + data)
        # - Binary chunk (chunk length + type + data)
        
        json_chunk_length = len(json_bytes)
        buffer_chunk_length = len(buffer_data)
        
        # Update buffer byteLength in JSON
        gltf_json["buffers"][0]["byteLength"] = buffer_chunk_length
        
        # Re-serialize JSON with updated length
        json_str = json.dumps(gltf_json, separators=(',', ':'), ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        json_padding = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b' ' * json_padding
        json_chunk_length = len(json_bytes)
        
        # Write GLB file
        with open(output_path, 'wb') as f:
            # GLB header (12 bytes)
            # magic (4 bytes): "glTF"
            f.write(b'glTF')
            # version (4 bytes): 2
            f.write(struct.pack('<I', 2))
            # total length (4 bytes): will be calculated
            total_length = 12 + 8 + json_chunk_length + 8 + buffer_chunk_length
            f.write(struct.pack('<I', total_length))
            
            # JSON chunk
            # chunk length (4 bytes)
            f.write(struct.pack('<I', json_chunk_length))
            # chunk type (4 bytes): 0x4E4F534A ("JSON")
            f.write(b'JSON')
            # chunk data
            f.write(json_bytes)
            
            # Binary chunk
            # chunk length (4 bytes)
            f.write(struct.pack('<I', buffer_chunk_length))
            # chunk type (4 bytes): 0x004E4942 ("BIN\0")
            f.write(b'BIN\0')
            # chunk data
            f.write(buffer_data)
        
        return output_path
    
    def _build_gltf_json_dict_for_glb(self) -> Dict:
        """Build glTF JSON structure for GLB (without buffer URI)."""
        buffer_size = len(self._build_buffer())
        
        positions_offset = 0
        positions_size = len(self.positions) * 4
        rotations_offset = positions_offset + positions_size
        rotations_size = len(self.rotations) * 4
        scales_offset = rotations_offset + rotations_size
        scales_size = len(self.scales) * 4
        colors_offset = scales_offset + scales_size
        colors_size = len(self.colors) * 4
        alphas_offset = colors_offset + colors_size
        alphas_size = len(self.alphas) * 4
        sh_offset = alphas_offset + alphas_size
        sh_size = len(self.sh_coefficients) * 4 if self.sh_coefficients is not None else 0
        
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "AeroTri 3DGS Tiles Converter"
            },
            "extensionsUsed": ["KHR_gaussian_splatting"],
            "extensionsRequired": ["KHR_gaussian_splatting"],
            "buffers": [
                {
                    "byteLength": buffer_size
                }
            ],
            "bufferViews": [
                {
                    "buffer": 0,
                    "byteOffset": positions_offset,
                    "byteLength": positions_size,
                    "target": 34962
                },
                {
                    "buffer": 0,
                    "byteOffset": rotations_offset,
                    "byteLength": rotations_size,
                    "target": 34962
                },
                {
                    "buffer": 0,
                    "byteOffset": scales_offset,
                    "byteLength": scales_size,
                    "target": 34962
                },
                {
                    "buffer": 0,
                    "byteOffset": colors_offset,
                    "byteLength": colors_size,
                    "target": 34962
                },
                {
                    "buffer": 0,
                    "byteOffset": alphas_offset,
                    "byteLength": alphas_size,
                    "target": 34962
                }
            ],
            "accessors": [
                {
                    "bufferView": 0,
                    "componentType": 5126,
                    "count": self.num_points,
                    "type": "VEC3",
                    "min": self._calculate_min(self.positions.reshape(-1, 3)),
                    "max": self._calculate_max(self.positions.reshape(-1, 3))
                },
                {
                    "bufferView": 1,
                    "componentType": 5126,
                    "count": self.num_points,
                    "type": "VEC4"
                },
                {
                    "bufferView": 2,
                    "componentType": 5126,
                    "count": self.num_points,
                    "type": "VEC3"
                },
                {
                    "bufferView": 3,
                    "componentType": 5126,
                    "count": self.num_points,
                    "type": "VEC3"
                },
                {
                    "bufferView": 4,
                    "componentType": 5126,
                    "count": self.num_points,
                    "type": "SCALAR"
                }
            ],
            "meshes": [
                {
                    "name": "GaussianSplats",
                    "primitives": [
                        {
                            # 为了兼容 Cesium 的 glTF 加载流程，这里需要提供一个
                            # 至少包含 POSITION 的 attributes。Cesium 会通过
                            # POSITION 对应 accessor 的 count 来推断点的数量，
                            # 如果缺失则会在访问 accessor.count 时抛出
                            # “Cannot read properties of undefined (reading 'count')”。
                            "attributes": {
                                "POSITION": 0  # 对应 accessors[0]（positions）
                            },
                            "mode": 0  # POINTS
                        }
                    ],
                    "extensions": {
                        "KHR_gaussian_splatting": {
                            "positions": 0,
                            "rotations": 1,
                            "scales": 2,
                            "colors": 3,
                            "alphas": 4
                        }
                    }
                }
            ],
            "nodes": [
                {
                    "mesh": 0,
                    "children": []
                }
            ],
            "scenes": [
                {
                    "nodes": [0]
                }
            ],
            "scene": 0
        }
        
        if self.sh_coefficients is not None and len(self.sh_coefficients) > 0:
            sh_buffer_view = {
                "buffer": 0,
                "byteOffset": sh_offset,
                "byteLength": sh_size,
                "target": 34962
            }
            gltf["bufferViews"].append(sh_buffer_view)
            
            sh_accessor = {
                "bufferView": len(gltf["bufferViews"]) - 1,
                "componentType": 5126,
                "count": self.num_points,
                "type": "SCALAR"
            }
            gltf["accessors"].append(sh_accessor)
            
            gltf["meshes"][0]["extensions"]["KHR_gaussian_splatting"]["sphericalHarmonics"] = len(gltf["accessors"]) - 1
            gltf["meshes"][0]["extensions"]["KHR_gaussian_splatting"]["sphericalHarmonicsDegree"] = self.sh_degree
        
        return gltf
    
    def _build_buffer(self) -> bytes:
        """Build binary buffer containing all Gaussian data."""
        buffer_parts = []
        
        # Positions (N * 3 * 4 bytes)
        buffer_parts.append(self.positions.tobytes())
        
        # Rotations (N * 4 * 4 bytes)
        buffer_parts.append(self.rotations.tobytes())
        
        # Scales (N * 3 * 4 bytes)
        buffer_parts.append(self.scales.tobytes())
        
        # Colors (N * 3 * 4 bytes)
        buffer_parts.append(self.colors.tobytes())
        
        # Alphas (N * 4 bytes)
        buffer_parts.append(self.alphas.tobytes())
        
        # SH coefficients (if available)
        if self.sh_coefficients is not None and len(self.sh_coefficients) > 0:
            buffer_parts.append(self.sh_coefficients.tobytes())
        
        return b''.join(buffer_parts)
    
    def _calculate_min(self, data: np.ndarray) -> List[float]:
        """Calculate minimum values for each component."""
        return data.min(axis=0).tolist()
    
    def _calculate_max(self, data: np.ndarray) -> List[float]:
        """Calculate maximum values for each component."""
        return data.max(axis=0).tolist()


def build_gltf_gaussian(
    gaussian_data: Dict,
    output_path: Path,
    use_glb: bool = False
) -> Path:
    """Convenience function to build glTF Gaussian file.
    
    Args:
        gaussian_data: Dictionary containing Gaussian data from PLY parser
        output_path: Output file path
        use_glb: Whether to generate binary GLB format
        
    Returns:
        Path to generated file
    """
    builder = GLTFGaussianBuilder()
    
    # Extract data
    positions = gaussian_data['positions']
    rotations = gaussian_data['rotations']
    scales = gaussian_data['scales']
    colors = gaussian_data['colors']
    alphas = gaussian_data['alphas']
    sh_coefficients = gaussian_data.get('sh_coefficients')
    sh_degree = gaussian_data.get('sh_degree', 0)
    
    builder.set_gaussian_data(
        positions=positions,
        rotations=rotations,
        scales=scales,
        colors=colors,
        alphas=alphas,
        sh_coefficients=sh_coefficients,
        sh_degree=sh_degree
    )
    
    return builder.build_gltf(output_path, use_glb=use_glb)
