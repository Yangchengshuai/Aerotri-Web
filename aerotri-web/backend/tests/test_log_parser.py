"""Tests for log parser."""
import pytest
from app.services.log_parser import LogParser, ParsedProgress


class TestLogParser:
    """Tests for LogParser class."""
    
    def test_parse_loading_images(self):
        """Test parsing loading images progress."""
        parser = LogParser()
        
        result = parser.parse_line("Loading Images 50 / 100")
        
        assert result is not None
        assert result.stage == "loading"
        assert result.progress == 50.0
        assert result.current == 50
        assert result.total == 100
    
    def test_parse_feature_extraction(self):
        """Test parsing feature extraction progress."""
        parser = LogParser()
        
        result = parser.parse_line("Processed image 25 of 100")
        
        assert result is not None
        assert result.stage == "feature_extraction"
        assert result.progress == 25.0
    
    def test_parse_relative_pose(self):
        """Test parsing relative pose estimation."""
        parser = LogParser()
        
        result = parser.parse_line("Estimating relative pose: 75%")
        
        assert result is not None
        assert result.stage == "relative_pose"
        assert result.progress == 75.0
    
    def test_parse_track_establishment(self):
        """Test parsing track establishment progress."""
        parser = LogParser()
        
        result = parser.parse_line("Establishing tracks 5000 / 10000")
        
        assert result is not None
        assert result.stage == "track_establishment"
        assert result.progress == 50.0
    
    def test_parse_triangulation(self):
        """Test parsing triangulation progress."""
        parser = LogParser()
        
        result = parser.parse_line("Triangulating image 200 / 279")
        
        assert result is not None
        assert result.stage == "retriangulation"
        assert result.current == 200
        assert result.total == 279
    
    def test_parse_bundle_adjustment(self):
        """Test parsing bundle adjustment iteration."""
        parser = LogParser()
        
        result = parser.parse_line("Global bundle adjustment iteration 3 / 5")
        
        assert result is not None
        assert result.stage == "bundle_adjustment"
        assert result.progress == 60.0
    
    def test_parse_completion(self):
        """Test parsing completion message."""
        parser = LogParser()
        
        result = parser.parse_line("Reconstruction done in 266.525 seconds")
        
        assert result is not None
        assert result.stage == "completed"
        assert result.progress == 100.0
    
    def test_stage_detection(self):
        """Test stage detection from log lines."""
        parser = LogParser()
        
        # Process stage header
        parser.parse_line("-------------------------------------")
        parser.parse_line("Running preprocessing ...")
        parser.parse_line("-------------------------------------")
        
        assert parser.current_stage == "preprocessing"
    
    def test_stage_times(self):
        """Test stage timing tracking."""
        parser = LogParser()
        
        # Simulate processing through stages
        parser.parse_line("Running preprocessing ...")
        parser.parse_line("Running rotation averaging ...")
        
        times = parser.get_stage_times()
        assert "preprocessing" in times
    
    def test_parse_empty_line(self):
        """Test parsing empty line returns None."""
        parser = LogParser()
        
        result = parser.parse_line("")
        assert result is None
        
        result = parser.parse_line("   ")
        assert result is None
    
    def test_parse_irrelevant_line(self):
        """Test parsing irrelevant log line returns None."""
        parser = LogParser()
        
        result = parser.parse_line("Some random log message")
        assert result is None
