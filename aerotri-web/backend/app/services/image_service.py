"""Image processing service."""
import os
import hashlib
from pathlib import Path
from PIL import Image

# Thumbnail cache directory
THUMBNAIL_CACHE_DIR = "/root/work/aerotri-web/data/thumbnails"


class ImageService:
    """Service for image operations."""
    
    @staticmethod
    async def get_thumbnail(image_path: str, size: int = 200) -> str:
        """Get or generate thumbnail for an image.
        
        Args:
            image_path: Path to the original image
            size: Maximum dimension for thumbnail
            
        Returns:
            Path to the thumbnail file
        """
        # Create cache directory if not exists
        os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)
        
        # Generate cache key from path and size
        cache_key = hashlib.md5(f"{image_path}_{size}".encode()).hexdigest()
        thumbnail_path = os.path.join(THUMBNAIL_CACHE_DIR, f"{cache_key}.jpg")
        
        # Return cached thumbnail if exists and is newer than original
        if os.path.exists(thumbnail_path):
            orig_mtime = os.path.getmtime(image_path)
            thumb_mtime = os.path.getmtime(thumbnail_path)
            if thumb_mtime > orig_mtime:
                return thumbnail_path
        
        # Generate thumbnail
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Calculate new size maintaining aspect ratio
                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                
                # Save thumbnail
                img.save(thumbnail_path, "JPEG", quality=85)
                
                return thumbnail_path
        except Exception as e:
            raise RuntimeError(f"Failed to generate thumbnail: {e}")
    
    @staticmethod
    def get_image_dimensions(image_path: str) -> tuple:
        """Get image dimensions.
        
        Args:
            image_path: Path to the image
            
        Returns:
            Tuple of (width, height)
        """
        with Image.open(image_path) as img:
            return img.size
    
    @staticmethod
    def count_images(directory: str) -> int:
        """Count images in a directory.
        
        Args:
            directory: Path to the directory
            
        Returns:
            Number of image files
        """
        extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
        count = 0
        
        path = Path(directory)
        if path.exists():
            for f in path.iterdir():
                if f.is_file() and f.suffix.lower() in extensions:
                    count += 1
        
        return count
