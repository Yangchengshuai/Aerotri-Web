"""Tests for GLOMAP mapper_resume API wiring (smoke-level, no real SfM)."""
import os
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_glomap_mapper_resume_creates_child_block_and_task(
    client: AsyncClient,
    test_image_path: str,
    tmp_path: Path,
):
    """Ensure /blocks/{id}/glomap/mapper_resume creates a new block and returns TaskStatus."""
    # Create a fake parent block
    create_resp = await client.post(
        "/api/blocks",
        json={
            "name": "GLOMAP Parent",
            "image_path": test_image_path,
            "algorithm": "glomap",
        },
    )
    assert create_resp.status_code == 201
    parent = create_resp.json()
    parent_id = parent["id"]

    # Prepare a dummy COLMAP-style sparse/0 directory for the parent
    outputs_root = Path("/root/work/aerotri-web/data/outputs")
    parent_output = outputs_root / parent_id
    sparse0 = parent_output / "sparse" / "0"
    os.makedirs(sparse0, exist_ok=True)
    # Touch minimal COLMAP files (empty but present)
    for stem in ("cameras", "images", "points3D"):
        (sparse0 / f"{stem}.bin").write_bytes(b"")

    # Call mapper_resume endpoint
    resp = await client.post(
        f"/api/blocks/{parent_id}/glomap/mapper_resume",
        json={
            "gpu_index": 0,
            "glomap_params": {"skip_pruning": True},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    # New child block id should be different
    assert data["block_id"] != parent_id
    assert data["status"] in ("running", "created", "completed", "failed")




