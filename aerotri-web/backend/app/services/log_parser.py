"""Log parser for COLMAP/GLOMAP output."""
import re
from typing import Optional, Tuple, Dict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedProgress:
    """Parsed progress information."""
    stage: str
    progress: float  # 0-100
    current: int = 0
    total: int = 0
    message: str = ""


@dataclass
class StageInfo:
    """Stage timing information."""
    name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    elapsed_seconds: float = 0.0


class LogParser:
    """Parser for COLMAP/GLOMAP log output."""
    
    # Stage patterns
    STAGE_PATTERNS = {
        "feature_extraction": [
            r"Running feature extraction",
            r"Processed image (\d+) of (\d+)",
        ],
        "matching": [
            r"Running feature matching",
            r"Matching images",
        ],
        "preprocessing": [
            r"Running preprocessing",
        ],
        "view_graph_calibration": [
            r"Running view graph calibration",
        ],
        "relative_pose_estimation": [
            r"Running relative pose estimation",
            r"Estimating relative pose: (\d+)%",
        ],
        "rotation_averaging": [
            r"Running rotation averaging",
        ],
        "track_establishment": [
            r"Running track establishment",
            r"Establishing tracks (\d+) / (\d+)",
        ],
        "global_positioning": [
            r"Running global positioning",
        ],
        "bundle_adjustment": [
            r"Running bundle adjustment",
            r"Global bundle adjustment iteration (\d+) / (\d+)",
        ],
        "retriangulation": [
            r"Running retriangulation",
            r"Triangulating image (\d+) / (\d+)",
        ],
        "completed": [
            r"Reconstruction done in ([\d.]+) seconds",
        ],
    }
    
    # Progress extraction patterns
    PROGRESS_PATTERNS = [
        # Feature extraction: "Processed image X of Y"
        (r"Processed image (\d+) of (\d+)", "feature_extraction"),
        # Loading images: "Loading Images X / Y"
        (r"Loading Images (\d+) / (\d+)", "loading"),
        # Relative pose: "Estimating relative pose: X%"
        (r"Estimating relative pose: (\d+)%", "relative_pose"),
        # Track establishment: "Establishing tracks X / Y"
        (r"Establishing tracks (\d+) / (\d+)", "track_establishment"),
        # Triangulation: "Triangulating image X / Y"
        (r"Triangulating image (\d+) / (\d+)", "retriangulation"),
        # Bundle adjustment iteration: "Global bundle adjustment iteration X / Y"
        (r"Global bundle adjustment iteration (\d+) / (\d+)", "bundle_adjustment"),
        # Image pair loading: "Loading Image Pair X / Y"
        (r"Loading Image Pair (\d+) / (\d+)", "loading_pairs"),
        # Initializing pairs: "Initializing pairs X / Y"
        (r"Initializing pairs (\d+) / (\d+)", "initializing_pairs"),
        # Establishing pairs: "Establishing pairs X / Y"
        (r"Establishing pairs (\d+) / (\d+)", "establishing_pairs"),
    ]
    
    def __init__(self):
        self.current_stage: Optional[str] = None
        self.stages: Dict[str, StageInfo] = {}
        self.last_progress: float = 0.0
        
    def parse_line(self, line: str) -> Optional[ParsedProgress]:
        """Parse a single log line.
        
        Args:
            line: Log line to parse
            
        Returns:
            ParsedProgress if progress info found, else None
        """
        line = line.strip()
        if not line:
            return None
        
        # Check for stage transitions
        new_stage = self._detect_stage(line)
        if new_stage and new_stage != self.current_stage:
            # End previous stage
            if self.current_stage and self.current_stage in self.stages:
                self.stages[self.current_stage].end_time = datetime.now()
            
            # Start new stage
            self.current_stage = new_stage
            self.stages[new_stage] = StageInfo(
                name=new_stage,
                start_time=datetime.now()
            )
        
        # Extract progress
        progress = self._extract_progress(line)
        if progress:
            self.last_progress = progress.progress
            return progress
        
        # Check for completion
        completion_match = re.search(r"Reconstruction done in ([\d.]+) seconds", line)
        if completion_match:
            elapsed = float(completion_match.group(1))
            return ParsedProgress(
                stage="completed",
                progress=100.0,
                message=f"Completed in {elapsed:.1f} seconds"
            )
        
        return None
    
    def _detect_stage(self, line: str) -> Optional[str]:
        """Detect current processing stage from log line."""
        for stage, patterns in self.STAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, line):
                    return stage
        return None
    
    def _extract_progress(self, line: str) -> Optional[ParsedProgress]:
        """Extract progress information from log line."""
        for pattern, stage in self.PROGRESS_PATTERNS:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()
                
                if len(groups) == 1:
                    # Percentage pattern (e.g., "X%")
                    progress = float(groups[0])
                    return ParsedProgress(
                        stage=stage,
                        progress=progress,
                        message=line
                    )
                elif len(groups) == 2:
                    # Current/Total pattern (e.g., "X / Y")
                    current = int(groups[0])
                    total = int(groups[1])
                    progress = (current / total) * 100 if total > 0 else 0
                    return ParsedProgress(
                        stage=stage,
                        progress=progress,
                        current=current,
                        total=total,
                        message=line
                    )
        
        return None
    
    def get_stage_times(self) -> Dict[str, float]:
        """Get elapsed time for each stage.
        
        Returns:
            Dict of stage name to elapsed seconds
        """
        times = {}
        for name, info in self.stages.items():
            if info.start_time:
                end = info.end_time or datetime.now()
                elapsed = (end - info.start_time).total_seconds()
                times[name] = elapsed
        return times
    
    def get_overall_progress(self) -> float:
        """Calculate overall progress based on stages completed.
        
        Returns:
            Progress percentage (0-100)
        """
        # Define stage weights (approximate time proportions)
        stage_weights = {
            "loading": 5,
            "feature_extraction": 15,
            "matching": 15,
            "preprocessing": 5,
            "view_graph_calibration": 2,
            "relative_pose_estimation": 10,
            "rotation_averaging": 5,
            "track_establishment": 8,
            "global_positioning": 15,
            "bundle_adjustment": 15,
            "retriangulation": 5,
        }
        
        total_weight = sum(stage_weights.values())
        completed_weight = 0
        
        for stage, info in self.stages.items():
            if info.end_time and stage in stage_weights:
                completed_weight += stage_weights[stage]
        
        # Add partial progress for current stage
        if self.current_stage and self.current_stage in stage_weights:
            stage_weight = stage_weights[self.current_stage]
            completed_weight += (self.last_progress / 100) * stage_weight
        
        return (completed_weight / total_weight) * 100
