"""Tests for GPU monitoring API."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_gpu_status(client: AsyncClient):
    """Test getting GPU status."""
    response = await client.get("/api/gpu/status")
    
    assert response.status_code == 200
    data = response.json()
    assert "gpus" in data
    # May be empty list if no GPU available
    assert isinstance(data["gpus"], list)


@pytest.mark.asyncio
async def test_get_single_gpu_status(client: AsyncClient):
    """Test getting single GPU status."""
    # First get list to see if any GPUs available
    list_response = await client.get("/api/gpu/status")
    gpus = list_response.json()["gpus"]
    
    if gpus:
        # Get first GPU
        response = await client.get(f"/api/gpu/status/0")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "memory_total" in data
        assert "memory_free" in data
        assert "utilization" in data


@pytest.mark.asyncio
async def test_get_invalid_gpu(client: AsyncClient):
    """Test getting non-existent GPU."""
    response = await client.get("/api/gpu/status/99")
    
    assert response.status_code == 404
