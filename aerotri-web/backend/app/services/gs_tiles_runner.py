"""3D GS PLY to 3D Tiles conversion runner.

This module is responsible for converting 3D Gaussian Splatting PLY files
to 3D Tiles format for CesiumJS display.
"""

import asyncio
import json
import os
import shlex
import sys
import time
import struct
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.block import Block
from ..models.database import AsyncSessionLocal
from .ply_parser import parse_ply_file
from .gltf_gaussian_builder import build_gltf_gaussian
from .tiles_slicer import TilesSlicer, TileInfo


# Compatibility helper for Python < 3.9
# asyncio.to_thread was introduced in Python 3.9
if sys.version_info >= (3, 9):
    async def run_in_thread(func, *args, **kwargs):
        """Run function in thread (Python 3.9+)."""
        return await asyncio.to_thread(func, *args, **kwargs)
else:
    # For Python 3.8, use run_in_executor
    _thread_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gs_tiles")
    
    async def run_in_thread(func, *args, **kwargs):
        """Run function in thread (Python 3.8 compatibility)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_thread_executor, partial(func, *args, **kwargs))


class GSTilesProcessError(Exception):
    """Exception raised when a conversion tool fails."""

    def __init__(self, stage: str, return_code: int, logs: List[str]):
        self.stage = stage
        self.return_code = return_code
        self.logs = logs
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        msg = f"3D GS Tiles conversion stage '{self.stage}' failed with exit code {self.return_code}"
        if self.logs:
            msg += f"\nLast {min(10, len(self.logs))} log lines:\n"
            msg += "\n".join(self.logs[-10:])
        return msg


class GSTilesRunner:
    """Runner for 3D GS PLY to 3D Tiles conversion pipeline."""

    def __init__(self) -> None:
        # Per-block in-memory log buffers (keyed by block_id)
        self._log_buffers: Dict[str, Deque[str]] = {}
        # Track running conversion subprocesses for cancellation
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        # Simple cancelled flags per block
        self._cancelled: Dict[str, bool] = {}
        self._recovery_done = False

    def _log(self, block_id: str, message: str) -> None:
        """Log a message for a block."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        
        if block_id not in self._log_buffers:
            self._log_buffers[block_id] = deque(maxlen=10000)
        self._log_buffers[block_id].append(log_line)

    def get_log_tail(self, block_id: str, lines: int = 200) -> List[str]:
        """Get the last N lines of logs for a block."""
        if block_id not in self._log_buffers:
            return []
        buffer = self._log_buffers[block_id]
        return list(buffer)[-lines:]

    async def _find_ply_file(self, gs_output_path: Path, iteration: Optional[int] = None) -> Optional[Path]:
        """Find PLY file in GS output directory.
        
        Args:
            gs_output_path: Path to GS output directory
            iteration: Optional iteration number (e.g., 7000, 15000)
        
        Returns:
            Path to PLY file if found, None otherwise
        """
        if iteration is not None:
            # Look for iteration-specific PLY file
            ply_path = gs_output_path / "model" / "point_cloud" / f"iteration_{iteration}" / "point_cloud.ply"
            if ply_path.exists() and ply_path.is_file():
                return ply_path
        
        # Look for latest iteration PLY file
        point_cloud_dir = gs_output_path / "model" / "point_cloud"
        if not point_cloud_dir.exists():
            return None
        
        # Find all iteration directories
        iteration_dirs = sorted(
            [d for d in point_cloud_dir.iterdir() if d.is_dir() and d.name.startswith("iteration_")],
            key=lambda x: int(x.name.split("_")[1]) if x.name.split("_")[1].isdigit() else 0,
            reverse=True
        )
        
        for iter_dir in iteration_dirs:
            ply_path = iter_dir / "point_cloud.ply"
            if ply_path.exists() and ply_path.is_file():
                return ply_path
        
        return None

    async def start_conversion(
        self,
        block: Block,
        db: AsyncSession,
        convert_params: Optional[dict] = None,
    ) -> None:
        """Start 3D GS PLY to 3D Tiles conversion for a block.
        
        Args:
            block: Block instance
            db: Database session
            convert_params: Optional conversion parameters (iteration, use_spz, etc.)
        """
        if convert_params is None:
            convert_params = {}
        
        block_id = block.id
        self._cancelled[block_id] = False
        
        # Use getattr for backward compatibility (in case DB migration not done yet)
        current_status = getattr(block, 'gs_tiles_status', None)
        if current_status == "RUNNING":
            raise ValueError(f"3D GS Tiles conversion is already running for block {block_id}")
        
        if not block.gs_output_path:
            raise ValueError(f"GS output path not found for block {block_id}")
        
        # Update block status (use setattr for backward compatibility)
        setattr(block, 'gs_tiles_status', "RUNNING")
        setattr(block, 'gs_tiles_progress', 0.0)
        setattr(block, 'gs_tiles_current_stage', "初始化")
        setattr(block, 'gs_tiles_error_message', None)
        await db.commit()
        
        # Start conversion task
        asyncio.create_task(self._run_conversion(block, db, convert_params))

    async def _run_conversion(
        self,
        block: Block,
        db: AsyncSession,
        convert_params: dict,
    ) -> None:
        """Run the conversion pipeline."""
        block_id = block.id
        
        try:
            self._log(block_id, "开始 3D GS PLY 转 3D Tiles 转换")
            
            gs_output_path = Path(block.gs_output_path)
            if not gs_output_path.exists():
                raise ValueError(f"GS output path does not exist: {gs_output_path}")
            
            # Find PLY file
            iteration = convert_params.get("iteration")
            ply_file = await self._find_ply_file(gs_output_path, iteration)
            if not ply_file:
                raise ValueError(f"PLY file not found in {gs_output_path}")
            
            self._log(block_id, f"找到 PLY 文件: {ply_file}")
            self._log(block_id, f"文件大小: {ply_file.stat().st_size / (1024 * 1024):.2f} MB")
            
            # Create output directory
            output_dir = gs_output_path / "3dtiles"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Update progress
            async with AsyncSessionLocal() as update_db:
                result = await update_db.execute(select(Block).where(Block.id == block_id))
                update_block = result.scalar_one()
                setattr(update_block, 'gs_tiles_progress', 10.0)
                setattr(update_block, 'gs_tiles_current_stage', "准备转换工具")
                await update_db.commit()
            
            # Stage 1: Parse PLY or convert to SPZ
            self._log(block_id, "阶段 1: 处理输入文件")
            use_spz = convert_params.get("use_spz", False)
            optimize_compression = convert_params.get("optimize_compression", False)
            
            gaussian_data = None
            
            if use_spz:
                # Convert PLY to SPZ first
                self._log(block_id, "使用 SPZ 压缩")
                spz_file = await self._convert_ply_to_spz(ply_file, output_dir, block_id)
                if spz_file:
                    # For now, we still need to parse PLY for glTF generation
                    # TODO: Implement SPZ loading when Python bindings are available
                    self._log(block_id, "SPZ 文件已生成，继续解析 PLY 用于 glTF 生成")
                else:
                    self._log(block_id, "SPZ 转换失败，回退到直接解析 PLY")
                    use_spz = False
            
            # Parse PLY file (with memory optimization for large files)
            self._log(block_id, "解析 PLY 文件")
            try:
                # For large files, parse in thread to avoid blocking
                file_size_mb = ply_file.stat().st_size / (1024 * 1024)
                if file_size_mb > 500:  # Files larger than 500MB
                    self._log(block_id, f"大文件检测 ({file_size_mb:.2f} MB)，使用优化解析")
                gaussian_data = await run_in_thread(parse_ply_file, ply_file)
                self._log(block_id, f"PLY 解析完成: {gaussian_data['num_points']} 个 splats")
                self._log(block_id, f"SH 度数: {gaussian_data.get('sh_degree', 0)}")
            except Exception as e:
                raise ValueError(f"PLY 解析失败: {str(e)}")
            
            # Update progress
            async with AsyncSessionLocal() as update_db:
                result = await update_db.execute(select(Block).where(Block.id == block_id))
                update_block = result.scalar_one()
                setattr(update_block, 'gs_tiles_progress', 20.0)
                setattr(update_block, 'gs_tiles_current_stage', "生成 glTF Gaussian")
                await update_db.commit()
            
            # Stage 2: Generate glTF Gaussian
            self._log(block_id, "阶段 2: 生成 glTF Gaussian")
            if gaussian_data is None:
                raise ValueError("Gaussian 数据未准备好，无法生成 glTF")
            
            gltf_output = output_dir / "gaussian.gltf"
            try:
                use_glb = optimize_compression
                build_gltf_gaussian(gaussian_data, gltf_output, use_glb=use_glb)
                gltf_size = gltf_output.stat().st_size / (1024 * 1024)
                self._log(block_id, f"glTF 生成完成: {gltf_output.name} ({gltf_size:.2f} MB)")
            except Exception as e:
                raise ValueError(f"glTF 生成失败: {str(e)}")
            
            # Update progress
            async with AsyncSessionLocal() as update_db:
                result = await update_db.execute(select(Block).where(Block.id == block_id))
                update_block = result.scalar_one()
                setattr(update_block, 'gs_tiles_progress', 40.0)
                setattr(update_block, 'gs_tiles_current_stage', "空间切片")
                await update_db.commit()
            
            # Stage 3: Spatial slicing
            self._log(block_id, "阶段 3: 空间切片")
            max_splats_per_tile = convert_params.get("max_splats_per_tile", 100000)
            slicer = TilesSlicer(max_splats_per_tile=max_splats_per_tile)
            
            try:
                tiles = await run_in_thread(slicer.slice_gaussian_data, gaussian_data, output_dir)
                self._log(block_id, f"空间切片完成: {len(tiles)} 个 tiles")
            except Exception as e:
                raise ValueError(f"空间切片失败: {str(e)}")
            
            # Update progress
            async with AsyncSessionLocal() as update_db:
                result = await update_db.execute(select(Block).where(Block.id == block_id))
                update_block = result.scalar_one()
                setattr(update_block, 'gs_tiles_progress', 60.0)
                setattr(update_block, 'gs_tiles_current_stage', "生成 LOD")
                await update_db.commit()
            
            # Stage 4: Generate LOD levels (optional)
            generate_lod = convert_params.get("generate_lod", True)
            lod_tiles = {0: tiles}
            
            if generate_lod and len(tiles) > 0:
                self._log(block_id, "阶段 4: 生成 LOD 层级")
                try:
                    lod_levels = convert_params.get("lod_levels", [0.5, 0.25])
                    lod_tiles = await run_in_thread(
                        slicer.generate_lod_levels,
                        gaussian_data,
                        tiles,
                        lod_levels
                    )
                    total_lod_tiles = sum(len(tiles) for tiles in lod_tiles.values())
                    self._log(block_id, f"LOD 生成完成: {len(lod_tiles)} 个层级，共 {total_lod_tiles} 个 tiles")
                except Exception as e:
                    self._log(block_id, f"LOD 生成失败，继续使用基础 tiles: {str(e)}")
                    lod_tiles = {0: tiles}
            else:
                self._log(block_id, "跳过 LOD 生成")
            
            # Update progress
            async with AsyncSessionLocal() as update_db:
                result = await update_db.execute(select(Block).where(Block.id == block_id))
                update_block = result.scalar_one()
                setattr(update_block, 'gs_tiles_progress', 70.0)
                setattr(update_block, 'gs_tiles_current_stage', "B3DM 转换")
                await update_db.commit()
            
            # Stage 5: Convert glTF to B3DM for each tile
            self._log(block_id, "阶段 5: B3DM 转换")
            b3dm_tiles = []
            total_tiles = sum(len(tiles) for tiles in lod_tiles.values())
            processed_tiles = 0
            
            for lod_level, tile_list in lod_tiles.items():
                for tile_idx, tile in enumerate(tile_list):
                    try:
                        # Extract tile data from gaussian_data
                        tile_gaussian_data = {
                            'positions': gaussian_data['positions'][tile.indices],
                            'rotations': gaussian_data['rotations'][tile.indices],
                            'scales': gaussian_data['scales'][tile.indices],
                            'colors': gaussian_data['colors'][tile.indices],
                            'alphas': gaussian_data['alphas'][tile.indices],
                            'sh_coefficients': gaussian_data.get('sh_coefficients'),
                            'sh_degree': gaussian_data.get('sh_degree', 0),
                            'num_points': len(tile.indices)
                        }
                        
                        if tile_gaussian_data['sh_coefficients'] is not None:
                            tile_gaussian_data['sh_coefficients'] = tile_gaussian_data['sh_coefficients'][tile.indices]
                        
                        # 修复颜色值处理：PLY 中的颜色值（f_dc）是 SH 系数，需要归一化到 [0, 1] 范围
                        colors = tile_gaussian_data['colors']
                        if colors.max() > 1.0 or colors.min() < 0.0:
                            # Clip 到合理范围并归一化
                            # f_dc 值通常在 [-3, 3] 范围内，映射到 [0, 1]
                            colors = np.clip(colors, -3.0, 3.0)
                            colors = (colors + 3.0) / 6.0  # 从 [-3, 3] 映射到 [0, 1]
                            colors = np.clip(colors, 0.0, 1.0)  # 确保在 [0, 1] 范围
                            tile_gaussian_data['colors'] = colors
                        
                        # Generate GLB for this tile
                        # 说明：
                        # - 之前这里生成的是 .gltf（JSON + 外部二进制），然后交给 3d-tiles-tools glbToB3dm
                        # - glbToB3dm 在处理 JSON glTF 时会重新打包 GLB，但会在 JSON chunk 末尾填充 0 字节，
                        #   Cesium 在解析 JSON 时会因为这些 0 字节导致
                        #   「Unexpected token \\u0000 in JSON」以及后续的 length 相关错误
                        # - 这里直接生成符合 GLB 规范（JSON 使用空格 padding）的 .glb，
                        #   再交给 glbToB3dm 包装为 B3DM，可以避免 JSON 解析错误
                        tile_glb = output_dir / f"tile_{tile.tile_id}_L{lod_level}.glb"
                        build_gltf_gaussian(tile_gaussian_data, tile_glb, use_glb=True)
                        
                        # Convert GLB to B3DM
                        tile_b3dm = output_dir / f"tile_{tile.tile_id}_L{lod_level}.b3dm"
                        b3dm_file = await self._convert_gltf_to_b3dm(tile_glb, tile_b3dm, block_id)
                        
                        if b3dm_file:
                            b3dm_tiles.append((tile, b3dm_file, lod_level))
                            processed_tiles += 1
                            
                            # Update progress
                            progress = 70.0 + (processed_tiles / total_tiles) * 20.0
                            async with AsyncSessionLocal() as update_db:
                                result = await update_db.execute(select(Block).where(Block.id == block_id))
                                update_block = result.scalar_one()
                                setattr(update_block, 'gs_tiles_progress', progress)
                                setattr(update_block, 'gs_tiles_current_stage', f"B3DM 转换 ({processed_tiles}/{total_tiles})")
                                await update_db.commit()
                        
                        # Clean up intermediate GLB file
                        if tile_glb.exists():
                            tile_glb.unlink()
                            
                    except Exception as e:
                        self._log(block_id, f"Tile {tile.tile_id} L{lod_level} 转换失败: {str(e)}")
                        continue
            
            self._log(block_id, f"B3DM 转换完成: {len(b3dm_tiles)} 个 tiles")
            
            # Check if we have any successful B3DM files
            if len(b3dm_tiles) == 0:
                # Log detailed error information
                self._log(block_id, "错误: 没有成功转换的 B3DM 文件")
                self._log(block_id, f"总 tiles 数: {total_tiles}, 已处理: {processed_tiles}")
                if total_tiles == 0:
                    raise ValueError("没有 tiles 需要转换，可能是空间切片失败")
                else:
                    raise ValueError(f"所有 {total_tiles} 个 tiles 的 B3DM 转换都失败了，请检查转换日志")
            
            # Update progress
            async with AsyncSessionLocal() as update_db:
                result = await update_db.execute(select(Block).where(Block.id == block_id))
                update_block = result.scalar_one()
                setattr(update_block, 'gs_tiles_progress', 90.0)
                setattr(update_block, 'gs_tiles_current_stage', "生成 tileset.json")
                await update_db.commit()
            
            # Stage 6: Generate tileset.json
            self._log(block_id, "阶段 6: 生成 tileset.json")
            try:
                # Extract tiles for tileset generation (use LOD 0 tiles)
                tileset_tiles = [tile for tile, _, lod in b3dm_tiles if lod == 0]
                
                if len(tileset_tiles) == 0:
                    # Fallback: use all tiles if no LOD 0 tiles
                    self._log(block_id, "警告: 没有 LOD 0 tiles，使用所有 tiles")
                    tileset_tiles = [tile for tile, _, _ in b3dm_tiles]
                
                if len(tileset_tiles) == 0:
                    raise ValueError("没有可用的 tiles 用于生成 tileset.json")
                
                tileset_path = self._create_tileset_json(tileset_tiles, output_dir, block_id, b3dm_tiles)
                self._log(block_id, f"tileset.json 生成完成: {tileset_path}")
                self._log(block_id, f"包含 {len(tileset_tiles)} 个 tiles")
            except Exception as e:
                raise ValueError(f"tileset.json 生成失败: {str(e)}")
            
            # Update progress and statistics
            async with AsyncSessionLocal() as update_db:
                result = await update_db.execute(select(Block).where(Block.id == block_id))
                update_block = result.scalar_one()
                setattr(update_block, 'gs_tiles_progress', 100.0)
                setattr(update_block, 'gs_tiles_current_stage', "完成")
                setattr(update_block, 'gs_tiles_status', "COMPLETED")
                setattr(update_block, 'gs_tiles_output_path', str(output_dir))
                
                # Calculate statistics
                stats = {
                    'input_file_size_mb': ply_file.stat().st_size / (1024 * 1024),
                    'num_splats': gaussian_data['num_points'],
                    'num_tiles': len(b3dm_tiles),
                    'num_lod_levels': len(lod_tiles),
                    'sh_degree': gaussian_data.get('sh_degree', 0),
                    'used_spz': use_spz,
                }
                
                # Calculate output size
                output_size = sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file())
                stats['output_size_mb'] = output_size / (1024 * 1024)
                
                setattr(update_block, 'gs_tiles_statistics', stats)
                await update_db.commit()
            
            self._log(block_id, "转换完成")
            self._log(block_id, f"统计信息: {len(b3dm_tiles)} 个 tiles, {gaussian_data['num_points']} 个 splats")
            
        except Exception as e:
            error_msg = str(e)
            self._log(block_id, f"转换失败: {error_msg}")
            
            async with AsyncSessionLocal() as update_db:
                result = await update_db.execute(select(Block).where(Block.id == block_id))
                update_block = result.scalar_one()
                setattr(update_block, 'gs_tiles_status', "FAILED")
                setattr(update_block, 'gs_tiles_error_message', error_msg)
                await update_db.commit()
        
        finally:
            # Clean up
            if block_id in self._processes:
                del self._processes[block_id]
    
    async def _convert_ply_to_spz(
        self,
        ply_file: Path,
        output_dir: Path,
        block_id: str
    ) -> Optional[Path]:
        """Convert PLY file to SPZ format using CLI tool.
        
        Args:
            ply_file: Path to input PLY file
            output_dir: Output directory
            block_id: Block ID for logging
            
        Returns:
            Path to generated SPZ file, or None if conversion failed
        """
        try:
            # Find ply_to_spz executable
            spz_build_dir = Path(__file__).parent.parent.parent / "third_party" / "spz" / "build"
            ply_to_spz_exe = spz_build_dir / "ply_to_spz"
            
            if not ply_to_spz_exe.exists():
                self._log(block_id, f"警告: ply_to_spz 未找到: {ply_to_spz_exe}")
                return None
            
            # Generate output SPZ file path
            spz_file = output_dir / f"{ply_file.stem}.spz"
            
            self._log(block_id, f"开始 PLY → SPZ 转换: {ply_file.name}")
            
            # Run conversion
            process = await asyncio.create_subprocess_exec(
                str(ply_to_spz_exe),
                str(ply_file),
                str(spz_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                self._log(block_id, f"SPZ 转换失败: {error_msg}")
                return None
            
            if spz_file.exists():
                ply_size = ply_file.stat().st_size
                spz_size = spz_file.stat().st_size
                compression_ratio = ply_size / spz_size if spz_size > 0 else 0
                
                self._log(block_id, f"SPZ 转换成功")
                self._log(block_id, f"  原始大小: {ply_size / (1024*1024):.2f} MB")
                self._log(block_id, f"  SPZ 大小: {spz_size / (1024*1024):.2f} MB")
                self._log(block_id, f"  压缩比: {compression_ratio:.2f}x")
                
                return spz_file
            else:
                self._log(block_id, "SPZ 文件未生成")
                return None
                
        except Exception as e:
            self._log(block_id, f"SPZ 转换异常: {str(e)}")
            return None

    async def _convert_gltf_to_b3dm(
        self,
        gltf_file: Path,
        output_file: Path,
        block_id: str
    ) -> Optional[Path]:
        """Wrap an input GLB file into a B3DM container.
        
        说明：
        - 早期实现依赖 `npx 3d-tiles-tools glbToB3dm` 做封装，但该工具在某些版本下
          会错误地把 glTF JSON 片段写入 feature table，从而截断真正的 glTF JSON，
          导致 Cesium 解析时出现
          `Failed to load glTF / Unexpected character after JSON ...` 等错误。
        - 这里改为**完全在 Python 里手动封装 B3DM**，只做非常简单、标准的打包：
          
          [b3dm header][feature table JSON(空)][feature table BIN(空)][batch table JSON(空)][batch table BIN(空)][GLB 数据]
          
        - 这样可以确保：
          * feature / batch table 长度为 0
          * GLB 按原样写入，不会破坏内部的 glTF 结构
        """
        try:
            if not gltf_file.exists():
                self._log(block_id, f"B3DM 转换失败: GLB 文件不存在: {gltf_file}")
                return None

            glb_data = gltf_file.read_bytes()

            # 构造 b3dm header
            magic = b"b3dm"          # 4 bytes
            version = 1               # uint32

            # 我们不使用 feature / batch table，全部设为 0
            feature_json = b""       # 可选: 也可以写入 {"BATCH_LENGTH":0}
            feature_bin = b""
            batch_json = b""
            batch_bin = b""

            ft_json_len = len(feature_json)
            ft_bin_len = len(feature_bin)
            bt_json_len = len(batch_json)
            bt_bin_len = len(batch_bin)

            header_length = 28  # 固定长度
            byte_length = header_length + ft_json_len + ft_bin_len + bt_json_len + bt_bin_len + len(glb_data)

            header = bytearray()
            header.extend(magic)
            header.extend(struct.pack('<I', version))
            header.extend(struct.pack('<I', byte_length))
            header.extend(struct.pack('<I', ft_json_len))
            header.extend(struct.pack('<I', ft_bin_len))
            header.extend(struct.pack('<I', bt_json_len))
            header.extend(struct.pack('<I', bt_bin_len))

            # 写出 B3DM 文件
            with output_file.open('wb') as f:
                f.write(header)
                if feature_json:
                    f.write(feature_json)
                if feature_bin:
                    f.write(feature_bin)
                if batch_json:
                    f.write(batch_json)
                if batch_bin:
                    f.write(batch_bin)
                f.write(glb_data)

            if output_file.exists():
                self._log(block_id, f"B3DM 封装成功: {output_file.name} (byteLength={byte_length})")
                return output_file
            else:
                self._log(block_id, "B3DM 文件未生成")
                return None

        except Exception as e:
            self._log(block_id, f"B3DM 封装异常: {str(e)}")
            return None
    
    def _create_tileset_json(
        self,
        tiles: List[TileInfo],
        output_dir: Path,
        block_id: str,
        b3dm_files: Optional[List[Tuple[TileInfo, Path, int]]] = None
    ) -> Path:
        """Create tileset.json file.
        
        Args:
            tiles: List of tile information
            output_dir: Output directory
            block_id: Block ID for logging
            b3dm_files: Optional list of (tile, b3dm_path, lod_level) tuples for file name mapping
            
        Returns:
            Path to tileset.json
        """
        # Create mapping from tile_id to actual B3DM file name
        tile_to_b3dm = {}
        if b3dm_files:
            for tile, b3dm_path, lod_level in b3dm_files:
                tile_to_b3dm[tile.tile_id] = b3dm_path.name
        
        # Calculate root bounding box
        if tiles:
            bboxes = [tile.bounding_box for tile in tiles]
            min_x = min(bb[0] for bb in bboxes)
            min_y = min(bb[1] for bb in bboxes)
            min_z = min(bb[2] for bb in bboxes)
            max_x = max(bb[3] for bb in bboxes)
            max_y = max(bb[4] for bb in bboxes)
            max_z = max(bb[5] for bb in bboxes)
            
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            center_z = (min_z + max_z) / 2
            half_x = (max_x - min_x) / 2
            half_y = (max_y - min_y) / 2
            half_z = (max_z - min_z) / 2
            
            # Box format: [center_x, center_y, center_z, half_x, 0, 0, 0, half_y, 0, 0, 0, half_z]
            root_box = [
                center_x, center_y, center_z,
                half_x, 0, 0,
                0, half_y, 0,
                0, 0, half_z
            ]
        else:
            root_box = [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]
        
        # Build tileset structure
        tileset = {
            "asset": {
                "version": "1.1"
            },
            "geometricError": 1000.0,
            "root": {
                "boundingVolume": {
                    "box": root_box
                },
                "geometricError": 1000.0,
                "children": []
            }
        }
        
        # Add tile children
        for tile in tiles:
            min_x, min_y, min_z, max_x, max_y, max_z = tile.bounding_box
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            center_z = (min_z + max_z) / 2
            half_x = (max_x - min_x) / 2
            half_y = (max_y - min_y) / 2
            half_z = (max_z - min_z) / 2
            
            tile_box = [
                center_x, center_y, center_z,
                half_x, 0, 0,
                0, half_y, 0,
                0, 0, half_z
            ]
            
            # Get the actual B3DM file name
            if tile.tile_id in tile_to_b3dm:
                b3dm_filename = tile_to_b3dm[tile.tile_id]
            else:
                # Fallback: construct filename
                b3dm_filename = f"tile_{tile.tile_id}_L0.b3dm"
            
            child = {
                "boundingVolume": {
                    "box": tile_box
                },
                "geometricError": tile.geometric_error,
                "content": {
                    "uri": b3dm_filename
                }
            }
            tileset["root"]["children"].append(child)
        
        # Write tileset.json
        tileset_path = output_dir / "tileset.json"
        with open(tileset_path, "w", encoding="utf-8") as f:
            json.dump(tileset, f, indent=2)
        
        self._log(block_id, f"创建 tileset.json: {tileset_path}")
        self._log(block_id, f"包含 {len(tiles)} 个 tiles")
        return tileset_path

    async def cancel_conversion(self, block_id: str) -> None:
        """Cancel a running conversion."""
        self._cancelled[block_id] = True
        
        if block_id in self._processes:
            process = self._processes[block_id]
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Block).where(Block.id == block_id))
            block = result.scalar_one()
            setattr(block, 'gs_tiles_status', "CANCELLED")
            await db.commit()
        
        self._log(block_id, "转换已取消")


# Global instance
gs_tiles_runner = GSTilesRunner()
