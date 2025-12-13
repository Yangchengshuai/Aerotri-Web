"""Tests for block management API."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_block(client: AsyncClient, test_image_path: str):
    """Test creating a new block."""
    response = await client.post(
        "/api/blocks",
        json={
            "name": "Test Block",
            "image_path": test_image_path,
            "algorithm": "glomap",
            "matching_method": "sequential",
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Block"
    assert data["image_path"] == test_image_path
    assert data["algorithm"] == "glomap"
    assert data["status"] == "created"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_block_invalid_path(client: AsyncClient):
    """Test creating block with invalid image path."""
    response = await client.post(
        "/api/blocks",
        json={
            "name": "Invalid Block",
            "image_path": "/nonexistent/path",
        }
    )
    
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_blocks(client: AsyncClient, test_image_path: str):
    """Test listing blocks."""
    # Create some blocks
    for i in range(3):
        await client.post(
            "/api/blocks",
            json={"name": f"Block {i}", "image_path": test_image_path}
        )
    
    response = await client.get("/api/blocks")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["blocks"]) == 3


@pytest.mark.asyncio
async def test_get_block(client: AsyncClient, test_image_path: str):
    """Test getting a specific block."""
    # Create block
    create_response = await client.post(
        "/api/blocks",
        json={"name": "Get Test", "image_path": test_image_path}
    )
    block_id = create_response.json()["id"]
    
    # Get block
    response = await client.get(f"/api/blocks/{block_id}")
    
    assert response.status_code == 200
    assert response.json()["name"] == "Get Test"


@pytest.mark.asyncio
async def test_get_block_not_found(client: AsyncClient):
    """Test getting non-existent block."""
    response = await client.get("/api/blocks/nonexistent-id")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_block(client: AsyncClient, test_image_path: str):
    """Test updating a block."""
    # Create block
    create_response = await client.post(
        "/api/blocks",
        json={"name": "Original", "image_path": test_image_path}
    )
    block_id = create_response.json()["id"]
    
    # Update block
    response = await client.patch(
        f"/api/blocks/{block_id}",
        json={"name": "Updated", "algorithm": "colmap"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["algorithm"] == "colmap"


@pytest.mark.asyncio
async def test_delete_block(client: AsyncClient, test_image_path: str):
    """Test deleting a block."""
    # Create block
    create_response = await client.post(
        "/api/blocks",
        json={"name": "To Delete", "image_path": test_image_path}
    )
    block_id = create_response.json()["id"]
    
    # Delete block
    response = await client.delete(f"/api/blocks/{block_id}")
    assert response.status_code == 204
    
    # Verify deleted
    get_response = await client.get(f"/api/blocks/{block_id}")
    assert get_response.status_code == 404
