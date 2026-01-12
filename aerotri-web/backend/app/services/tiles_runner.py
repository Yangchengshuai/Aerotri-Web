"""3D Tiles conversion runner.

This module is responsible for converting OpenMVS texture output (.obj/.mtl)
to 3D Tiles format for CesiumJS display.
"""

import asyncio
import os
import shlex
import time
import json
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.block import Block
from ..models.database import AsyncSessionLocal
from .task_notifier import task_notifier


class TilesProcessError(Exception):
    """Exception raised when a conversion tool fails."""

    def __init__(self, stage: str, return_code: int, logs: List[str]):
        self.stage = stage
        self.return_code = return_code
        self.logs = logs
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        msg = f"3D Tiles conversion stage '{self.stage}' failed with exit code {self.return_code}"
        if self.logs:
            msg += f"\nLast {min(10, len(self.logs))} log lines:\n"
            msg += "\n".join(self.logs[-10:])
        return msg


class TilesRunner:
    """Runner for 3D Tiles conversion pipeline."""

    def __init__(self) -> None:
        # Per-block in-memory log buffers (keyed by block_id)
        self._log_buffers: Dict[str, Deque[str]] = {}
        # Track running conversion subprocesses for cancellation
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        # Simple cancelled flags per block
        self._cancelled: Dict[str, bool] = {}
        self._recovery_done = False

    def _get_obj2gltf_path(self) -> str:
        """Get obj2gltf command path."""
        return os.environ.get("OBJ2GLTF_PATH", "obj2gltf")

    def _get_3dtiles_tools_path(self) -> str:
        """Get 3d-tiles-tools command path."""
        # Use npx for 3d-tiles-tools since it's installed via npm
        return os.environ.get("3DTILES_TOOLS_PATH", "npx")

    def _maybe_inject_georef_transform(self, block: Block, tiles_output_dir: Path, log_path: Path) -> None:
        """If geo_ref.json exists, write ENU->ECEF transform into tileset.json root.transform.

        We use a local ENU model for reconstruction/tiles (small coordinates),
        then place it in Cesium world coordinates via tileset root.transform (ECEF).
        """
        try:
            # geo_ref.json is stored at <block.output_path>/geo/geo_ref.json
            if not block.output_path:
                return
            geo_ref = Path(block.output_path) / "geo" / "geo_ref.json"
            tileset_path = tiles_output_dir / "tileset.json"
            if not geo_ref.is_file() or not tileset_path.is_file():
                return

            geo = json.loads(geo_ref.read_text(encoding="utf-8"))
            M = geo.get("enu_to_ecef_transform_column_major")
            if not (isinstance(M, list) and len(M) == 16):
                return

            tileset = json.loads(tileset_path.read_text(encoding="utf-8"))
            root = tileset.get("root") or {}
            root["transform"] = M
            tileset["root"] = root
            tileset_path.write_text(json.dumps(tileset, ensure_ascii=False, indent=2), encoding="utf-8")

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[GEOREF] Injected root.transform from {geo_ref}\n")
        except Exception as e:
            # Non-fatal: tiles can still be viewed as local if transform injection fails
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[GEOREF][WARNING] Failed to inject root.transform: {e}\n")
            except Exception:
                pass

    def _find_texture_obj_file(self, texture_dir: Path) -> Optional[Path]:
        """Find the texture OBJ file in the texture directory."""
        # Try common naming patterns
        patterns = [
            "scene_dense_texture.obj",
            "scene_dense_mesh_refine_texture.obj",
        ]
        for pattern in patterns:
            obj_path = texture_dir / pattern
            if obj_path.exists() and obj_path.is_file():
                return obj_path
        return None

    def _find_texture_mtl_file(self, texture_dir: Path, obj_path: Path) -> Optional[Path]:
        """Find the corresponding MTL file for the OBJ file."""
        # Try same name with .mtl extension
        mtl_path = obj_path.with_suffix(".mtl")
        if mtl_path.exists() and mtl_path.is_file():
            return mtl_path
        # Try scene_dense_texture.mtl
        mtl_path = texture_dir / "scene_dense_texture.mtl"
        if mtl_path.exists() and mtl_path.is_file():
            return mtl_path
        return None

    async def start_conversion(
        self,
        block: Block,
        db: AsyncSession,
        convert_params: Optional[dict] = None,
    ) -> None:
        """Start 3D Tiles conversion for a block.
        
        Args:
            block: Block instance
            db: Database session
            convert_params: Optional conversion parameters (keep_glb, optimize)
        """
        if convert_params is None:
            convert_params = {}

        # Check prerequisites
        if not block.recon_output_path:
            raise ValueError("Reconstruction output path not found. Please complete reconstruction first.")

        texture_dir = Path(block.recon_output_path) / "texture"
        if not texture_dir.exists():
            raise ValueError(f"Texture directory not found: {texture_dir}")

        # Find OBJ and MTL files
        obj_path = self._find_texture_obj_file(texture_dir)
        if not obj_path:
            raise ValueError(f"Texture OBJ file not found in {texture_dir}")

        mtl_path = self._find_texture_mtl_file(texture_dir, obj_path)
        if not mtl_path:
            raise ValueError(f"Texture MTL file not found for {obj_path}")

        # Setup output directory
        tiles_output_dir = Path(block.recon_output_path) / "tiles"
        tiles_output_dir.mkdir(parents=True, exist_ok=True)

        log_path = tiles_output_dir / "run_tiles.log"

        # Initialize log buffer
        block_id = block.id
        if block_id not in self._log_buffers:
            self._log_buffers[block_id] = deque(maxlen=1000)

        # Update block status
        block.tiles_status = "RUNNING"
        block.tiles_progress = 0.0
        block.tiles_current_stage = "obj_to_glb"
        block.tiles_output_path = str(tiles_output_dir)
        block.tiles_error_message = None
        await db.commit()
        
        # Send task started notification
        asyncio.create_task(task_notifier.on_task_started(
            block_id=block.id,
            block_name=block.name,
            task_type="tiles",
        ))

        # Start conversion task
        asyncio.create_task(
            self._run_conversion(
                block_id=block_id,
                obj_path=obj_path,
                mtl_path=mtl_path,
                texture_dir=texture_dir,
                tiles_output_dir=tiles_output_dir,
                log_path=log_path,
                keep_glb=convert_params.get("keep_glb", False),
            )
        )

    async def _run_conversion(
        self,
        block_id: str,
        obj_path: Path,
        mtl_path: Path,
        texture_dir: Path,
        tiles_output_dir: Path,
        log_path: Path,
        keep_glb: bool,
    ) -> None:
        """Run the conversion pipeline."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Block).where(Block.id == block_id))
            block = result.scalar_one_or_none()
            if not block:
                return

            log_buffer = self._log_buffers.get(block_id, deque(maxlen=1000))
            start_time = time.time()

            try:
                # Stage 1: OBJ → GLB
                if self._cancelled.get(block_id, False):
                    block.tiles_status = "CANCELLED"
                    await db.commit()
                    return

                block.tiles_current_stage = "obj_to_glb"
                block.tiles_progress = 10.0
                await db.commit()

                glb_path = tiles_output_dir / "model.glb"
                await self._convert_obj_to_glb(
                    obj_path=obj_path,
                    glb_path=glb_path,
                    texture_dir=texture_dir,
                    log_buffer=log_buffer,
                    log_path=log_path,
                )

                # Stage 2: GLB → 3D Tiles
                if self._cancelled.get(block_id, False):
                    block.tiles_status = "CANCELLED"
                    await db.commit()
                    return

                block.tiles_current_stage = "glb_to_tiles"
                block.tiles_progress = 60.0
                await db.commit()

                await self._convert_glb_to_tiles(
                    glb_path=glb_path,
                    tiles_output_dir=tiles_output_dir,
                    log_buffer=log_buffer,
                    log_path=log_path,
                )

                # Optional: inject geo transform for Cesium real-world placement
                self._maybe_inject_georef_transform(block, tiles_output_dir, log_path)

                # Cleanup intermediate GLB if not keeping
                if not keep_glb and glb_path.exists():
                    glb_path.unlink()

                # Update completion status
                block.tiles_status = "COMPLETED"
                block.tiles_progress = 100.0
                block.tiles_current_stage = "completed"
                
                # Calculate statistics
                elapsed_time = time.time() - start_time
                tileset_path = tiles_output_dir / "tileset.json"
                b3dm_files = list(tiles_output_dir.glob("*.b3dm"))
                
                block.tiles_statistics = {
                    "conversion_time_seconds": round(elapsed_time, 2),
                    "glb_size_bytes": glb_path.stat().st_size if glb_path.exists() else 0,
                    "tileset_size_bytes": tileset_path.stat().st_size if tileset_path.exists() else 0,
                    "b3dm_count": len(b3dm_files),
                    "b3dm_total_size_bytes": sum(f.stat().st_size for f in b3dm_files),
                }
                
                await db.commit()
                
                # Send task completed notification
                await task_notifier.on_task_completed(
                    block_id=block.id,
                    block_name=block.name,
                    task_type="tiles",
                    duration=elapsed_time,
                )

            except TilesProcessError as e:
                block.tiles_status = "FAILED"
                block.tiles_error_message = str(e)
                await db.commit()
                
                # Send task failed notification
                log_tail = list(log_buffer)[-10:] if log_buffer else None
                await task_notifier.on_task_failed(
                    block_id=block.id,
                    block_name=block.name,
                    task_type="tiles",
                    error=str(e),
                    stage=block.tiles_current_stage,
                    log_tail=log_tail,
                )
            except Exception as e:
                block.tiles_status = "FAILED"
                block.tiles_error_message = f"Unexpected error: {str(e)}"
                await db.commit()
                
                # Send task failed notification
                log_tail = list(log_buffer)[-10:] if log_buffer else None
                await task_notifier.on_task_failed(
                    block_id=block.id,
                    block_name=block.name,
                    task_type="tiles",
                    error=str(e),
                    stage=block.tiles_current_stage,
                    log_tail=log_tail,
                )
            finally:
                # Cleanup
                if block_id in self._processes:
                    del self._processes[block_id]
                if block_id in self._cancelled:
                    del self._cancelled[block_id]

    async def _convert_obj_to_glb(
        self,
        obj_path: Path,
        glb_path: Path,
        texture_dir: Path,
        log_buffer: Deque[str],
        log_path: Path,
    ) -> None:
        """Convert OBJ to GLB using obj2gltf."""
        obj2gltf_cmd = self._get_obj2gltf_path()
        
        # obj2gltf command: -i input.obj -o output.glb --binary
        cmd = [
            obj2gltf_cmd,
            "-i", str(obj_path),
            "-o", str(glb_path),
            "--binary",
        ]

        # Run in texture directory to ensure texture paths resolve correctly
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(texture_dir),
        )

        # Note: We track processes by block_id in _run_conversion
        # For now, we'll handle cancellation at the task level

        # Read output line by line
        output_lines = []
        async for line in process.stdout:
            line_str = line.decode("utf-8", errors="replace").rstrip()
            log_buffer.append(line_str)
            output_lines.append(line_str)
            
            # Write to log file
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line_str + "\n")

        return_code = await process.wait()
        
        if return_code != 0:
            raise TilesProcessError("obj_to_glb", return_code, output_lines[-20:])

    async def _convert_glb_to_tiles(
        self,
        glb_path: Path,
        tiles_output_dir: Path,
        log_buffer: Deque[str],
        log_path: Path,
    ) -> None:
        """Convert GLB to 3D Tiles using 3d-tiles-tools."""
        # First: GLB → B3DM
        b3dm_path = tiles_output_dir / "model.b3dm"
        tools_cmd = self._get_3dtiles_tools_path()
        
        # npx 3d-tiles-tools@latest glbToB3dm -i model.glb -o model.b3dm
        cmd = [
            tools_cmd,
            "3d-tiles-tools@latest",
            "glbToB3dm",
            "-i", str(glb_path),
            "-o", str(b3dm_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(tiles_output_dir),
        )

        output_lines = []
        async for line in process.stdout:
            line_str = line.decode("utf-8", errors="replace").rstrip()
            log_buffer.append(line_str)
            output_lines.append(line_str)
            
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line_str + "\n")

        return_code = await process.wait()
        
        if return_code != 0:
            raise TilesProcessError("glb_to_b3dm", return_code, output_lines[-20:])

        # Second: Create tileset.json
        tileset_path = tiles_output_dir / "tileset.json"
        cmd = [
            tools_cmd,
            "3d-tiles-tools@latest",
            "createTilesetJson",
            "-i", str(b3dm_path),
            "-o", str(tileset_path),
            "-f",  # Force overwrite
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(tiles_output_dir),
        )

        output_lines = []
        async for line in process.stdout:
            line_str = line.decode("utf-8", errors="replace").rstrip()
            log_buffer.append(line_str)
            output_lines.append(line_str)
            
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line_str + "\n")

        return_code = await process.wait()
        
        if return_code != 0:
            raise TilesProcessError("create_tileset", return_code, output_lines[-20:])

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
            except Exception:
                pass

        # Update status
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Block).where(Block.id == block_id))
            block = result.scalar_one_or_none()
            if block:
                block.tiles_status = "CANCELLED"
                await db.commit()

    def get_log_tail(self, block_id: str, lines: int = 200) -> List[str]:
        """Get the last N lines of conversion logs."""
        # Prefer in-memory buffer when running
        if block_id in self._log_buffers:
            buf = self._log_buffers[block_id]
            return list(buf)[-lines:]

        # Fallback to persisted run_tiles.log on disk
        # We infer path from typical layout: <output>/recon/tiles/run_tiles.log
        base_outputs_dir = "/root/work/aerotri-web/data/outputs"
        tiles_log = Path(base_outputs_dir) / block_id / "recon" / "tiles" / "run_tiles.log"
        if not tiles_log.is_file():
            return []

        dq: Deque[str] = deque(maxlen=lines)
        try:
            with open(tiles_log, "r", encoding="utf-8", errors="replace") as fp:
                for line in fp:
                    dq.append(line.rstrip("\n"))
        except Exception:
            return []

        return list(dq)

    async def recover_orphaned_tiles_tasks(self) -> None:
        """Recover orphaned conversion tasks on startup."""
        if self._recovery_done:
            return

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Block).where(Block.tiles_status == "RUNNING")
            )
            blocks = result.scalars().all()

            for block in blocks:
                # Check if process is still running (we can't check this easily,
                # so we check if output files exist)
                if block.tiles_output_path:
                    tileset_path = Path(block.tiles_output_path) / "tileset.json"
                    if tileset_path.exists():
                        # Conversion likely completed
                        block.tiles_status = "COMPLETED"
                        block.tiles_progress = 100.0
                        block.tiles_current_stage = "completed"
                    else:
                        # Conversion likely failed
                        block.tiles_status = "FAILED"
                        block.tiles_error_message = "Conversion process was interrupted (server restart)"
                else:
                    block.tiles_status = "FAILED"
                    block.tiles_error_message = "Conversion process was interrupted (server restart)"

            await db.commit()
            self._recovery_done = True

    # ==================== Version-based 3D Tiles Conversion ====================
    
    async def start_version_conversion(
        self,
        block: Block,
        version,  # ReconVersion
        db: AsyncSession,
        convert_params: Optional[dict] = None,
    ) -> None:
        """Start 3D Tiles conversion for a specific reconstruction version.
        
        Args:
            block: Block instance
            version: ReconVersion instance
            db: Database session
            convert_params: Optional conversion parameters (keep_glb, optimize)
        """
        if convert_params is None:
            convert_params = {}

        # Check prerequisites
        if not version.output_path:
            raise ValueError("Version output path not found.")

        texture_dir = Path(version.output_path) / "texture"
        if not texture_dir.exists():
            raise ValueError(f"Texture directory not found: {texture_dir}")

        # Find OBJ and MTL files
        obj_path = self._find_texture_obj_file(texture_dir)
        if not obj_path:
            raise ValueError(f"Texture OBJ file not found in {texture_dir}")

        mtl_path = self._find_texture_mtl_file(texture_dir, obj_path)
        if not mtl_path:
            raise ValueError(f"Texture MTL file not found for {obj_path}")

        # Setup output directory (tiles in version directory)
        tiles_output_dir = Path(version.output_path) / "tiles"
        tiles_output_dir.mkdir(parents=True, exist_ok=True)

        log_path = tiles_output_dir / "run_tiles.log"

        # Initialize log buffer using version_id
        version_id = version.id
        if version_id not in self._log_buffers:
            self._log_buffers[version_id] = deque(maxlen=1000)

        # Update version tiles status
        version.tiles_status = "RUNNING"
        version.tiles_progress = 0.0
        version.tiles_current_stage = "obj_to_glb"
        version.tiles_output_path = str(tiles_output_dir)
        version.tiles_error_message = None
        await db.commit()
        
        # Send task started notification
        asyncio.create_task(task_notifier.on_task_started(
            block_id=block.id,
            block_name=f"{block.name} (v{version.version_index})",
            task_type="tiles",
        ))

        # Start conversion task
        asyncio.create_task(
            self._run_version_conversion(
                block_id=block.id,
                version_id=version_id,
                obj_path=obj_path,
                mtl_path=mtl_path,
                texture_dir=texture_dir,
                tiles_output_dir=tiles_output_dir,
                log_path=log_path,
                keep_glb=convert_params.get("keep_glb", False),
            )
        )

    async def _run_version_conversion(
        self,
        block_id: str,
        version_id: str,
        obj_path: Path,
        mtl_path: Path,
        texture_dir: Path,
        tiles_output_dir: Path,
        log_path: Path,
        keep_glb: bool,
    ) -> None:
        """Run the conversion pipeline for a version."""
        from ..models.recon_version import ReconVersion
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ReconVersion).where(ReconVersion.id == version_id))
            version = result.scalar_one_or_none()
            if not version:
                return
            
            # Get block for geo-ref injection
            result = await db.execute(select(Block).where(Block.id == block_id))
            block = result.scalar_one_or_none()

            log_buffer = self._log_buffers.get(version_id, deque(maxlen=1000))
            start_time = time.time()

            try:
                # Stage 1: OBJ → GLB
                if self._cancelled.get(version_id, False):
                    version.tiles_status = "CANCELLED"
                    await db.commit()
                    return

                version.tiles_current_stage = "obj_to_glb"
                version.tiles_progress = 10.0
                await db.commit()

                glb_path = tiles_output_dir / "model.glb"
                await self._convert_obj_to_glb(
                    obj_path=obj_path,
                    glb_path=glb_path,
                    texture_dir=texture_dir,
                    log_buffer=log_buffer,
                    log_path=log_path,
                )

                # Stage 2: GLB → 3D Tiles
                if self._cancelled.get(version_id, False):
                    version.tiles_status = "CANCELLED"
                    await db.commit()
                    return

                version.tiles_current_stage = "glb_to_tiles"
                version.tiles_progress = 60.0
                await db.commit()

                await self._convert_glb_to_tiles(
                    glb_path=glb_path,
                    tiles_output_dir=tiles_output_dir,
                    log_buffer=log_buffer,
                    log_path=log_path,
                )

                # Optional: inject geo transform for Cesium real-world placement
                if block:
                    self._maybe_inject_georef_transform(block, tiles_output_dir, log_path)

                # Cleanup intermediate GLB if not keeping
                if not keep_glb and glb_path.exists():
                    glb_path.unlink()

                # Update completion status
                version.tiles_status = "COMPLETED"
                version.tiles_progress = 100.0
                version.tiles_current_stage = "completed"
                
                # Calculate statistics
                elapsed_time = time.time() - start_time
                tileset_path = tiles_output_dir / "tileset.json"
                b3dm_files = list(tiles_output_dir.glob("*.b3dm"))
                
                version.tiles_statistics = {
                    "conversion_time_seconds": round(elapsed_time, 2),
                    "glb_size_bytes": glb_path.stat().st_size if glb_path.exists() else 0,
                    "tileset_size_bytes": tileset_path.stat().st_size if tileset_path.exists() else 0,
                    "b3dm_count": len(b3dm_files),
                    "b3dm_total_size_bytes": sum(f.stat().st_size for f in b3dm_files),
                }
                
                await db.commit()
                
                # Send task completed notification
                if block:
                    await task_notifier.on_task_completed(
                        block_id=block.id,
                        block_name=f"{block.name} (v{version.version_index})",
                        task_type="tiles",
                        duration=elapsed_time,
                    )

            except TilesProcessError as e:
                version.tiles_status = "FAILED"
                version.tiles_error_message = str(e)
                await db.commit()
                
                # Send task failed notification
                if block:
                    log_tail = list(log_buffer)[-10:] if log_buffer else None
                    await task_notifier.on_task_failed(
                        block_id=block.id,
                        block_name=f"{block.name} (v{version.version_index})",
                        task_type="tiles",
                        error=str(e),
                        log_tail=log_tail,
                    )

            except Exception as e:
                version.tiles_status = "FAILED"
                version.tiles_error_message = f"Unexpected error: {e}"
                await db.commit()

            finally:
                # Cleanup
                self._log_buffers.pop(version_id, None)
                self._cancelled.pop(version_id, None)


# Singleton instance
tiles_runner = TilesRunner()

