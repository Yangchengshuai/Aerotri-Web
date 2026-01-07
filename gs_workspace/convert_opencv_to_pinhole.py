#!/usr/bin/env python3
"""
将 COLMAP cameras.txt 中的 OPENCV 模型转换为 PINHOLE 模型
OPENCV: fx, fy, cx, cy, k1, k2, p1, p2
PINHOLE: fx, fy, cx, cy
"""
import sys
import os

def convert_cameras_file(input_path, output_path):
    """将 cameras.txt 从 OPENCV 转换为 PINHOLE"""
    with open(input_path, 'r') as f:
        lines = f.readlines()
    
    output_lines = []
    for line in lines:
        if line.strip().startswith('#') or not line.strip():
            output_lines.append(line)
            continue
        
        parts = line.strip().split()
        if len(parts) < 5:
            output_lines.append(line)
            continue
        
        camera_id = parts[0]
        model = parts[1]
        width = parts[2]
        height = parts[3]
        params = parts[4:]
        
        if model == 'OPENCV' and len(params) >= 4:
            # 提取前 4 个参数 (fx, fy, cx, cy)，忽略畸变参数
            pinhole_params = params[:4]
            new_line = f"{camera_id} PINHOLE {width} {height} {' '.join(pinhole_params)}\n"
            output_lines.append(new_line)
            print(f"转换相机 {camera_id}: OPENCV -> PINHOLE (忽略畸变参数)")
        else:
            output_lines.append(line)
    
    with open(output_path, 'w') as f:
        f.writelines(output_lines)
    
    print(f"转换完成: {input_path} -> {output_path}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("用法: python convert_opencv_to_pinhole.py <输入cameras.txt> <输出cameras.txt>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if not os.path.exists(input_path):
        print(f"错误: 文件不存在: {input_path}")
        sys.exit(1)
    
    convert_cameras_file(input_path, output_path)

