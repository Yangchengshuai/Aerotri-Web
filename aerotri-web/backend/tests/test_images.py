"""Tests for image management API."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_images(client: AsyncClient, test_image_path: str):
    """Test listing images in a block."""
    # Create block
    create_response = await client.post(
        "/api/blocks",
        json={"name": "Image Test", "image_path": test_image_path}
    )
    block_id = create_response.json()["id"]
    
    # List images
    response = await client.get(f"/api/blocks/{block_id}/images")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["images"]) > 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_images_pagination(client: AsyncClient, test_image_path: str):
    """Test image listing with pagination."""
    # Create block
    create_response = await client.post(
        "/api/blocks",
        json={"name": "Pagination Test", "image_path": test_image_path}
    )
    block_id = create_response.json()["id"]
    
    # Get first page with small page size
    response = await client.get(
        f"/api/blocks/{block_id}/images",
        params={"page": 1, "page_size": 10}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["images"]) <= 10
    assert data["page"] == 1
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_get_image_thumbnail(client: AsyncClient, test_image_path: str):
    """Test getting image thumbnail."""
    # Create block
    create_response = await client.post(
        "/api/blocks",
        json={"name": "Thumbnail Test", "image_path": test_image_path}
    )
    block_id = create_response.json()["id"]
    
    # Get image list
    images_response = await client.get(f"/api/blocks/{block_id}/images")
    images = images_response.json()["images"]
    
    if images:
        image_name = images[0]["name"]
        
        # Get thumbnail
        response = await client.get(
            f"/api/blocks/{block_id}/images/{image_name}/thumbnail"
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_image_not_found(client: AsyncClient, test_image_path: str):
    """Test getting non-existent image."""
    # Create block
    create_response = await client.post(
        "/api/blocks",
        json={"name": "Not Found Test", "image_path": test_image_path}
    )
    block_id = create_response.json()["id"]
    
    # Try to get non-existent image
    response = await client.get(
        f"/api/blocks/{block_id}/images/nonexistent.jpg/thumbnail"
    )
    
    assert response.status_code == 404
