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
        self.spz_file = None  # Path to SPZ file for compression
        self.spz_data = None  # SPZ binary data
    
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
    
    def set_spz_compression(self, spz_file: Path) -> None:
        """Set SPZ file for compression extension.
        
        Args:
            spz_file: Path to SPZ file
        """
        self.spz_file = spz_file
        if spz_file.exists():
            self.spz_data = spz_file.read_bytes()
    
    def build_gltf(self, output_path: Path, use_glb: bool = False) -> Path:
        """Build glTF file with Gaussian splatting extension.
        
        Args:
            output_path: Output file path
            use_glb: Whether to generate binary GLB format
            
        Returns:
            Path to generated file
        """
        # If SPZ compression is enabled, use compression extension
        if self.spz_file and self.spz_data:
            if use_glb:
                return self._build_glb_with_spz(output_path)
            else:
                return self._build_gltf_json_with_spz(output_path)
        else:
            # Use uncompressed format
            if use_glb:
                return self._build_glb(output_path)
            else:
                return self._build_gltf_json(output_path)
    
    def _build_gltf_json_with_spz(self, output_path: Path) -> Path:
        """Build JSON glTF file with SPZ compression extension."""
        if not self.spz_data:
            raise ValueError("SPZ data not set")
        if self.positions is None:
            raise ValueError("Positions data not set (required for POSITION accessor)")
        
        # Create buffers directory
        buffers_dir = output_path.parent / f"{output_path.stem}_buffers"
        buffers_dir.mkdir(exist_ok=True)
        
        # Write SPZ binary data
        buffer_file = buffers_dir / "compressed_data.bin"
        with open(buffer_file, 'wb') as f:
            f.write(self.spz_data)
        
        buffer_uri = f"{output_path.stem}_buffers/compressed_data.bin"
        buffer_size = len(self.spz_data)
        
        # Calculate actual position bounds (required for Cesium)
        positions_3d = self.positions.reshape(-1, 3)
        pos_min = self._calculate_min(positions_3d)
        pos_max = self._calculate_max(positions_3d)
        
        # Write POSITION data to a separate buffer (required by Cesium for bounding box)
        # Even with SPZ compression, Cesium needs POSITION accessor with valid bounds
        position_buffer_file = buffers_dir / "positions.bin"
        positions_bytes = positions_3d.astype(np.float32).tobytes()
        with open(position_buffer_file, 'wb') as f:
            f.write(positions_bytes)
        
        position_buffer_uri = f"{output_path.stem}_buffers/positions.bin"
        position_buffer_size = len(positions_bytes)
        
        # Build glTF structure with compression extension
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "AeroTri 3DGS Tiles Converter (SPZ Compressed)"
            },
            "extensionsUsed": [
                "KHR_gaussian_splatting",
                "KHR_gaussian_splatting_compression_spz_2"
            ],
            "extensionsRequired": [
                "KHR_gaussian_splatting",
                "KHR_gaussian_splatting_compression_spz_2"
            ],
            "buffers": [
                {
                    "uri": position_buffer_uri,
                    "byteLength": position_buffer_size
                },
                {
                    "uri": buffer_uri,
                    "byteLength": buffer_size
                }
            ],
            "meshes": [
                {
                    "name": "GaussianSplats",
                    "primitives": [
                        {
                            # POSITION and COLOR_0 accessors required by Cesium
                            # COLOR_0 is required even with SPZ compression (data is in SPZ, but accessor is metadata)
                            "attributes": {
                                "POSITION": 0,
                                "COLOR_0": 1
                            },
                            "mode": 0  # POINTS
                        }
                    ],
                    "extensions": {
                        "KHR_gaussian_splatting": {
                            "compression": {
                                "extension": "KHR_gaussian_splatting_compression_spz_2",
                                "buffer": 1,  # SPZ data is in buffer 1
                                "byteOffset": 0,
                                "byteLength": buffer_size
                            },
                            # Include count for metadata
                            "count": self.num_points,
                            "sphericalHarmonicsDegree": self.sh_degree
                        }
                    }
                }
            ],
            "accessors": [
                {
                    # POSITION accessor with actual bounds (required by Cesium)
                    "bufferView": 0,
                    "componentType": 5126,  # FLOAT
                    "count": self.num_points,
                    "type": "VEC3",
                    "min": pos_min,
                    "max": pos_max
                },
                {
                    # COLOR_0 accessor (required by Cesium, even with SPZ compression)
                    # Note: No bufferView - color data is in SPZ compressed buffer
                    # This accessor serves as metadata for Cesium to understand color structure
                    "componentType": 5121,  # UNSIGNED_BYTE
                    "count": self.num_points,
                    "type": "VEC3",
                    "normalized": True  # Colors are normalized to [0, 1]
                }
            ],
            "bufferViews": [
                {
                    # POSITION buffer view (buffer 0)
                    "buffer": 0,
                    "byteOffset": 0,
                    "byteLength": position_buffer_size,
                    "target": 34962  # ARRAY_BUFFER
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
        
        # Write glTF JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(gltf, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def _build_glb_with_spz(self, output_path: Path) -> Path:
        """Build binary GLB file with SPZ compression extension."""
        if not self.spz_data:
            raise ValueError("SPZ data not set")
        if self.positions is None:
            raise ValueError("Positions data not set (required for POSITION accessor)")
        
        # Build glTF JSON structure
        gltf_json = self._build_gltf_json_dict_for_glb_with_spz()
        
        # Prepare POSITION buffer data
        positions_3d = self.positions.reshape(-1, 3)
        position_buffer_data = positions_3d.astype(np.float32).tobytes()
        
        # Pad buffers to 4-byte boundaries
        position_padding = (4 - (len(position_buffer_data) % 4)) % 4
        position_buffer_data += b'\x00' * position_padding
        
        spz_padding = (4 - (len(self.spz_data) % 4)) % 4
        spz_buffer_data = self.spz_data + b'\x00' * spz_padding
        
        # Update buffer byteLengths in JSON
        gltf_json["buffers"][0]["byteLength"] = len(position_buffer_data)
        gltf_json["buffers"][1]["byteLength"] = len(spz_buffer_data)
        
        # Serialize JSON
        json_str = json.dumps(gltf_json, separators=(',', ':'), ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        
        # Pad JSON to 4-byte boundary
        json_padding = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b' ' * json_padding
        json_chunk_length = len(json_bytes)
        
        # Combine binary buffers: POSITION + SPZ
        binary_data = position_buffer_data + spz_buffer_data
        binary_chunk_length = len(binary_data)
        
        # GLB structure:
        # - 12-byte header
        # - JSON chunk (chunk length + type + data)
        # - Binary chunk (chunk length + type + data)
        #   Binary chunk contains: [POSITION buffer][SPZ buffer]
        
        # Write GLB file
        with open(output_path, 'wb') as f:
            # GLB header (12 bytes)
            f.write(b'glTF')
            f.write(struct.pack('<I', 2))  # version
            total_length = 12 + 8 + json_chunk_length + 8 + binary_chunk_length
            f.write(struct.pack('<I', total_length))
            
            # JSON chunk
            f.write(struct.pack('<I', json_chunk_length))
            f.write(b'JSON')
            f.write(json_bytes)
            
            # Binary chunk (POSITION + SPZ data)
            f.write(struct.pack('<I', binary_chunk_length))
            f.write(b'BIN\0')
            f.write(binary_data)
        
        return output_path
    
    def _build_gltf_json_dict_for_glb_with_spz(self) -> Dict:
        """Build glTF JSON structure for GLB with SPZ compression (without buffer URI)."""
        if self.positions is None:
            raise ValueError("Positions data not set (required for POSITION accessor)")
        
        buffer_size = len(self.spz_data)
        
        # Calculate actual position bounds (required for Cesium)
        positions_3d = self.positions.reshape(-1, 3)
        pos_min = self._calculate_min(positions_3d)
        pos_max = self._calculate_max(positions_3d)
        
        # Calculate position buffer size
        position_buffer_size = len(positions_3d) * 3 * 4  # N * 3 * sizeof(float32)
        
        # In GLB format:
        # - Buffer 0: POSITION data (for bounding box)
        # - Buffer 1: SPZ compressed data
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "AeroTri 3DGS Tiles Converter (SPZ Compressed)"
            },
            "extensionsUsed": [
                "KHR_gaussian_splatting",
                "KHR_gaussian_splatting_compression_spz_2"
            ],
            "extensionsRequired": [
                "KHR_gaussian_splatting",
                "KHR_gaussian_splatting_compression_spz_2"
            ],
            "buffers": [
                {
                    "byteLength": position_buffer_size
                },
                {
                    "byteLength": buffer_size
                }
            ],
            "meshes": [
                {
                    "name": "GaussianSplats",
                    "primitives": [
                        {
                            # POSITION and COLOR_0 accessors required by Cesium
                            # COLOR_0 is required even with SPZ compression (data is in SPZ, but accessor is metadata)
                            "attributes": {
                                "POSITION": 0,
                                "COLOR_0": 1
                            },
                            "mode": 0  # POINTS
                        }
                    ],
                    "extensions": {
                        "KHR_gaussian_splatting": {
                            "compression": {
                                "extension": "KHR_gaussian_splatting_compression_spz_2",
                                "buffer": 1,  # SPZ data is in buffer 1
                                "byteOffset": 0,
                                "byteLength": buffer_size
                            },
                            "count": self.num_points,
                            "sphericalHarmonicsDegree": self.sh_degree
                        }
                    }
                }
            ],
            "accessors": [
                {
                    # POSITION accessor with actual bounds (required by Cesium)
                    "bufferView": 0,
                    "componentType": 5126,  # FLOAT
                    "count": self.num_points,
                    "type": "VEC3",
                    "min": pos_min,
                    "max": pos_max
                },
                {
                    # COLOR_0 accessor (required by Cesium, even with SPZ compression)
                    # Note: No bufferView - color data is in SPZ compressed buffer
                    # This accessor serves as metadata for Cesium to understand color structure
                    "componentType": 5121,  # UNSIGNED_BYTE
                    "count": self.num_points,
                    "type": "VEC3",
                    "normalized": True  # Colors are normalized to [0, 1]
                }
            ],
            "bufferViews": [
                {
                    "buffer": 0,  # POSITION buffer
                    "byteOffset": 0,
                    "byteLength": position_buffer_size,
                    "target": 34962  # ARRAY_BUFFER
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
        
        return gltf
    
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
                    "type": "VEC3",
                    "min": self._calculate_min(self.colors.reshape(-1, 3)),
                    "max": self._calculate_max(self.colors.reshape(-1, 3))
                },
                {
                    "bufferView": 4,
                    "componentType": 5126,  # FLOAT
                    "count": self.num_points,
                    "type": "SCALAR",
                    "min": [float(self.alphas.min())],
                    "max": [float(self.alphas.max())]
                }
            ],
            "meshes": [
                {
                    "name": "GaussianSplats",
                    # Cesium 需要通过 POSITION 对应 accessor 的 count 推断点的数量，
                    # 因此这里至少要提供 POSITION 属性，指向 accessors[0]。
                    "primitives": [
                        {
                            # POSITION and COLOR_0 accessors required by Cesium
                            "attributes": {
                                "POSITION": 0,
                                "COLOR_0": 3  # Colors accessor (index 3 in accessors array)
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
                    "type": "VEC3",
                    "min": self._calculate_min(self.colors.reshape(-1, 3)),
                    "max": self._calculate_max(self.colors.reshape(-1, 3))
                },
                {
                    "bufferView": 4,
                    "componentType": 5126,
                    "count": self.num_points,
                    "type": "SCALAR",
                    "min": [float(self.alphas.min())],
                    "max": [float(self.alphas.max())]
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
                                "POSITION": 0,  # 对应 accessors[0]（positions）
                                "COLOR_0": 3  # Colors accessor (index 3 in accessors array)
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
    use_glb: bool = False,
    spz_file: Optional[Path] = None
) -> Path:
    """Convenience function to build glTF Gaussian file.
    
    Args:
        gaussian_data: Dictionary containing Gaussian data from PLY parser or SPZ loader
        output_path: Output file path
        use_glb: Whether to generate binary GLB format
        spz_file: Optional path to SPZ file for compression extension
        
    Returns:
        Path to generated file
    """
    builder = GLTFGaussianBuilder()
    
    # If SPZ file is provided, use compression extension
    if spz_file and spz_file.exists():
        builder.set_spz_compression(spz_file)
        # Still need to set basic data for metadata (count, etc.)
        builder.set_gaussian_data(
            positions=gaussian_data['positions'],
            rotations=gaussian_data['rotations'],
            scales=gaussian_data['scales'],
            colors=gaussian_data['colors'],
            alphas=gaussian_data['alphas'],
            sh_coefficients=gaussian_data.get('sh_coefficients'),
            sh_degree=gaussian_data.get('sh_degree', 0)
        )
    else:
        # Extract data for uncompressed format
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
