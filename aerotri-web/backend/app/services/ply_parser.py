"""PLY file parser for 3D Gaussian Splatting.

This module provides functionality to parse PLY files containing
3D Gaussian Splatting data (positions, rotations, scales, colors, alphas, SH coefficients).
"""

import struct
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple


class PLYParser:
    """Parser for 3DGS PLY files."""
    
    def __init__(self):
        self.positions = None
        self.rotations = None
        self.scales = None
        self.colors = None
        self.alphas = None
        self.sh_coefficients = None
        self.sh_degree = None
        self.num_points = 0
    
    def parse(self, ply_path: Path) -> Dict:
        """Parse a PLY file and extract Gaussian splatting data.
        
        Args:
            ply_path: Path to the PLY file
            
        Returns:
            Dictionary containing parsed data:
            {
                'positions': np.ndarray (N, 3),
                'rotations': np.ndarray (N, 4),  # quaternion (x, y, z, w)
                'scales': np.ndarray (N, 3),
                'colors': np.ndarray (N, 3),  # RGB
                'alphas': np.ndarray (N,),
                'sh_coefficients': np.ndarray (N, M),  # M depends on SH degree
                'sh_degree': int,
                'num_points': int
            }
        """
        with open(ply_path, 'rb') as f:
            # Read header
            header_lines = []
            while True:
                line = f.readline()
                header_lines.append(line)
                if line.startswith(b'end_header'):
                    break
            
            header = b''.join(header_lines).decode('ascii', errors='ignore')
            
            # Parse header to get format and properties
            format_type = None
            num_vertices = 0
            properties = []
            
            for line in header.split('\n'):
                line = line.strip()
                if line.startswith('format'):
                    parts = line.split()
                    format_type = parts[1]  # ascii or binary_little_endian
                elif line.startswith('element vertex'):
                    num_vertices = int(line.split()[-1])
                elif line.startswith('property'):
                    parts = line.split()
                    if len(parts) >= 3:
                        prop_type = parts[1]
                        prop_name = parts[2]
                        properties.append((prop_name, prop_type))
            
            self.num_points = num_vertices
            
            # Determine SH degree from properties
            sh_props = [p for p in properties if p[0].startswith('f_dc_') or p[0].startswith('f_rest_')]
            if sh_props:
                # Count SH coefficients
                dc_props = [p for p in properties if p[0].startswith('f_dc_')]
                rest_props = [p for p in properties if p[0].startswith('f_rest_')]
                if dc_props and rest_props:
                    # Degree 0: 3 coefficients (f_dc_0, f_dc_1, f_dc_2)
                    # Degree 1: 3 + 9 = 12 coefficients
                    # Degree 2: 3 + 9 + 15 = 27 coefficients
                    # Degree 3: 3 + 9 + 15 + 21 = 48 coefficients
                    num_rest = len(rest_props)
                    if num_rest == 0:
                        self.sh_degree = 0
                    elif num_rest == 9:
                        self.sh_degree = 1
                    elif num_rest == 24:
                        self.sh_degree = 2
                    elif num_rest == 45:
                        self.sh_degree = 3
                    else:
                        self.sh_degree = 3  # Default to highest
                else:
                    self.sh_degree = 0
            else:
                self.sh_degree = 0
            
            # Read data
            if format_type == 'ascii':
                data = self._parse_ascii(f, num_vertices, properties)
            else:
                data = self._parse_binary(f, num_vertices, properties)
            
            return data
    
    def _parse_ascii(self, f, num_vertices: int, properties: list) -> Dict:
        """Parse ASCII PLY format."""
        positions = []
        rotations = []
        scales = []
        colors = []
        alphas = []
        sh_coeffs = []
        
        for _ in range(num_vertices):
            line = f.readline().decode('ascii').strip().split()
            values = [float(x) for x in line]
            
            idx = 0
            pos = [0.0, 0.0, 0.0]
            rot = [0.0, 0.0, 0.0, 1.0]  # quaternion (x, y, z, w)
            scale = [0.0, 0.0, 0.0]
            color = [0.0, 0.0, 0.0]
            alpha = 0.0
            sh = []
            
            for prop_name, prop_type in properties:
                if prop_name == 'x':
                    pos[0] = values[idx]
                elif prop_name == 'y':
                    pos[1] = values[idx]
                elif prop_name == 'z':
                    pos[2] = values[idx]
                elif prop_name in ['nx', 'rot_0']:
                    rot[0] = values[idx]
                elif prop_name in ['ny', 'rot_1']:
                    rot[1] = values[idx]
                elif prop_name in ['nz', 'rot_2']:
                    rot[2] = values[idx]
                elif prop_name in ['nw', 'rot_3']:
                    rot[3] = values[idx]
                elif prop_name in ['scale_0', 'scale_x']:
                    scale[0] = values[idx]
                elif prop_name in ['scale_1', 'scale_y']:
                    scale[1] = values[idx]
                elif prop_name in ['scale_2', 'scale_z']:
                    scale[2] = values[idx]
                elif prop_name in ['f_dc_0', 'red']:
                    color[0] = values[idx]
                elif prop_name in ['f_dc_1', 'green']:
                    color[1] = values[idx]
                elif prop_name in ['f_dc_2', 'blue']:
                    color[2] = values[idx]
                elif prop_name == 'opacity':
                    alpha = values[idx]
                elif prop_name.startswith('f_rest_'):
                    sh.append(values[idx])
                
                idx += 1
            
            positions.append(pos)
            rotations.append(rot)
            scales.append(scale)
            colors.append(color)
            alphas.append(alpha)
            sh_coeffs.append(sh)
        
        return {
            'positions': np.array(positions, dtype=np.float32),
            'rotations': np.array(rotations, dtype=np.float32),
            'scales': np.array(scales, dtype=np.float32),
            'colors': np.array(colors, dtype=np.float32),
            'alphas': np.array(alphas, dtype=np.float32),
            'sh_coefficients': np.array(sh_coeffs, dtype=np.float32) if sh_coeffs[0] else None,
            'sh_degree': self.sh_degree,
            'num_points': num_vertices
        }
    
    def _parse_binary(self, f, num_vertices: int, properties: list) -> Dict:
        """Parse binary PLY format (little-endian)."""
        positions = []
        rotations = []
        scales = []
        colors = []
        alphas = []
        sh_coeffs = []
        
        # Map property types to struct format
        type_map = {
            'char': 'b',
            'uchar': 'B',
            'short': 'h',
            'ushort': 'H',
            'int': 'i',
            'uint': 'I',
            'float': 'f',
            'double': 'd'
        }
        
        # Build struct format string
        fmt_parts = []
        prop_info = []
        
        for prop_name, prop_type in properties:
            if prop_type in type_map:
                fmt_parts.append(type_map[prop_type])
                prop_info.append((prop_name, prop_type))
            elif prop_type.startswith('list'):
                # Skip list types for now (complex)
                continue
        
        fmt = '<' + ''.join(fmt_parts)  # Little-endian
        
        for _ in range(num_vertices):
            data = struct.unpack(fmt, f.read(struct.calcsize(fmt)))
            
            pos = [0.0, 0.0, 0.0]
            rot = [0.0, 0.0, 0.0, 1.0]
            scale = [0.0, 0.0, 0.0]
            color = [0.0, 0.0, 0.0]
            alpha = 0.0
            sh = []
            
            idx = 0
            for prop_name, prop_type in prop_info:
                value = data[idx]
                
                if prop_name == 'x':
                    pos[0] = float(value)
                elif prop_name == 'y':
                    pos[1] = float(value)
                elif prop_name == 'z':
                    pos[2] = float(value)
                elif prop_name in ['nx', 'rot_0']:
                    rot[0] = float(value)
                elif prop_name in ['ny', 'rot_1']:
                    rot[1] = float(value)
                elif prop_name in ['nz', 'rot_2']:
                    rot[2] = float(value)
                elif prop_name in ['nw', 'rot_3']:
                    rot[3] = float(value)
                elif prop_name in ['scale_0', 'scale_x']:
                    scale[0] = float(value)
                elif prop_name in ['scale_1', 'scale_y']:
                    scale[1] = float(value)
                elif prop_name in ['scale_2', 'scale_z']:
                    scale[2] = float(value)
                elif prop_name in ['f_dc_0', 'red']:
                    color[0] = float(value)
                elif prop_name in ['f_dc_1', 'green']:
                    color[1] = float(value)
                elif prop_name in ['f_dc_2', 'blue']:
                    color[2] = float(value)
                elif prop_name == 'opacity':
                    alpha = float(value)
                elif prop_name.startswith('f_rest_'):
                    sh.append(float(value))
                
                idx += 1
            
            positions.append(pos)
            rotations.append(rot)
            scales.append(scale)
            colors.append(color)
            alphas.append(alpha)
            sh_coeffs.append(sh)
        
        return {
            'positions': np.array(positions, dtype=np.float32),
            'rotations': np.array(rotations, dtype=np.float32),
            'scales': np.array(scales, dtype=np.float32),
            'colors': np.array(colors, dtype=np.float32),
            'alphas': np.array(alphas, dtype=np.float32),
            'sh_coefficients': np.array(sh_coeffs, dtype=np.float32) if sh_coeffs[0] else None,
            'sh_degree': self.sh_degree,
            'num_points': num_vertices
        }


def parse_ply_file(ply_path: Path) -> Dict:
    """Convenience function to parse a PLY file.
    
    Args:
        ply_path: Path to the PLY file
        
    Returns:
        Dictionary containing parsed Gaussian data
    """
    parser = PLYParser()
    return parser.parse(ply_path)
