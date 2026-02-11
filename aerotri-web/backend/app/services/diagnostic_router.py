"""Diagnostic router for intelligent failure diagnosis routing.

This module implements the DiagnosticRouter which intelligently routes task failures
to appropriate diagnostic levels based on error characteristics and failure patterns.

Diagnostic Levels:
- L1_NONE: No diagnosis for trivial failures (e.g., user cancellation)
- L2_QUICK: Quick diagnosis (10s) for important but common failures
- L3_DEEP: Deep diagnosis (60s) for critical or recurring failures
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DiagnosticLevel(Enum):
    """Diagnostic level classification.

    Levels determine the depth and duration of diagnostic analysis:
    - L1_NONE: Skip diagnosis for trivial failures
    - L2_QUICK: Quick diagnosis for important failures (10s timeout)
    - L3_DEEP: Deep diagnosis for critical failures (60s timeout)
    """
    L1_NONE = "none"      # 普通失败：不诊断
    L2_QUICK = "quick"    # 重要失败：快速诊断(10s)
    L3_DEEP = "deep"      # 关键失败：深度诊断(60s)


class DiagnosticRouter:
    """Intelligent diagnostic router for task failures.

    Analyzes failure patterns and error characteristics to determine the
    appropriate diagnostic level, then routes to the corresponding diagnostic
    implementation.

    Routing Rules:
    1. User-initiated cancellations → L1_NONE (no diagnosis)
    2. Resource errors (CUDA OOM, disk full) → L2_QUICK (quick diagnosis)
    3. Unknown/critical errors → L3_DEEP (deep diagnosis)
    4. Recurring failures (>3 attempts) → L3_DEEP (deep diagnosis)
    5. Default → L2_QUICK (quick diagnosis)

    Example:
        ```python
        router = DiagnosticRouter()

        # Route and diagnose a failure
        result = await router.diagnose(
            block_id=123,
            task_type="sfm",
            error_message="CUDA out of memory",
            stage="bundle_adjustment",
            failure_count=1
        )

        # Or get routing decision only
        level = router.route_failure(
            error_message="Task cancelled by user",
            failure_count=0
        )
        # Returns DiagnosticLevel.L1_NONE
        ```
    """

    # Error patterns for automatic classification
    # Format: {pattern: (level, reason)}
    ERROR_PATTERNS: Dict[str, tuple] = {
        # L1_NONE patterns - User-initiated or trivial failures
        "cancelled": (DiagnosticLevel.L1_NONE, "User cancelled task"),
        "keyboard interrupt": (DiagnosticLevel.L1_NONE, "Manual interruption"),
        "task was cancelled": (DiagnosticLevel.L1_NONE, "Task cancellation"),

        # L2_QUICK patterns - Important but common resource/permission issues
        "cuda out of memory": (DiagnosticLevel.L2_QUICK, "GPU memory issue"),
        "out of memory": (DiagnosticLevel.L2_QUICK, "Memory allocation failed"),
        "permission denied": (DiagnosticLevel.L2_QUICK, "File permission issue"),
        "no space left": (DiagnosticLevel.L2_QUICK, "Disk space issue"),
        "file not found": (DiagnosticLevel.L2_QUICK, "Missing file or path"),
        "cannot connect": (DiagnosticLevel.L2_QUICK, "Network connection issue"),

        # L3_DEEP patterns - Critical or complex failures
        "unknown error": (DiagnosticLevel.L3_DEEP, "Unknown critical error"),
        "assertion failed": (DiagnosticLevel.L3_DEEP, "Internal assertion error"),
        "segmentation fault": (DiagnosticLevel.L3_DEEP, "Program crash"),
        "killed": (DiagnosticLevel.L3_DEEP, "Process terminated unexpectedly"),
    }

    def __init__(self):
        """Initialize the diagnostic router."""
        self._failure_history: Dict[int, int] = {}

    def route_failure(
        self,
        error_message: str,
        failure_count: int = 0,
        stage: Optional[str] = None
    ) -> DiagnosticLevel:
        """Determine diagnostic level based on error characteristics.

        Applies routing rules to classify the failure and determine the
        appropriate diagnostic level.

        Args:
            error_message: Error message or exception string
            failure_count: Number of times this task has failed (0-indexed)
            stage: Processing stage where failure occurred (optional)

        Returns:
            DiagnosticLevel: The appropriate diagnostic level

        Example:
            ```python
            router = DiagnosticRouter()

            # User cancellation - no diagnosis
            level = router.route_failure("Task cancelled by user", 0)
            # Returns DiagnosticLevel.L1_NONE

            # CUDA OOM - quick diagnosis
            level = router.route_failure("CUDA out of memory", 1)
            # Returns DiagnosticLevel.L2_QUICK

            # Unknown error on 4th attempt - deep diagnosis
            level = router.route_failure("Unknown error during mapping", 4)
            # Returns DiagnosticLevel.L3_DEEP
            ```
        """
        error_lower = error_message.lower().strip()

        # Rule 1: Check for recurring failures (>3 attempts)
        if failure_count > 3:
            logger.info(
                f"Recurring failure detected (count={failure_count}), "
                f"routing to L3_DEEP diagnosis"
            )
            return DiagnosticLevel.L3_DEEP

        # Rule 2: Match against known error patterns
        for pattern, (level, reason) in self.ERROR_PATTERNS.items():
            if pattern in error_lower:
                logger.debug(
                    f"Error pattern matched: '{pattern}' → {level.value} "
                    f"({reason})"
                )
                return level

        # Rule 3: Default to L2_QUICK for unknown errors
        logger.debug(
            f"No specific pattern matched, routing to default L2_QUICK diagnosis"
        )
        return DiagnosticLevel.L2_QUICK

    async def diagnose(
        self,
        block_id: int,
        task_type: str,
        error_message: str,
        failure_count: int = 0,
        stage: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute diagnostic process based on routed level.

        Routes the failure to the appropriate diagnostic implementation
        based on the error characteristics and returns diagnostic results.

        Args:
            block_id: Block ID that failed
            task_type: Type of task (e.g., "sfm", "openmvs", "3dgs", "tiles")
            error_message: Error message or exception string
            failure_count: Number of times this task has failed
            stage: Processing stage where failure occurred
            context: Additional context for diagnosis (optional)

        Returns:
            Dictionary with diagnostic results, or None if L1_NONE:
            ```python
            {
                "level": "quick" | "deep",
                "block_id": 123,
                "task_type": "sfm",
                "diagnosis": "Analysis result",
                "suggestions": ["fix1", "fix2"],
                "severity": "warning" | "error",
                "timestamp": "2025-01-01T12:00:00Z"
            }
            ```

        Example:
            ```python
            router = DiagnosticRouter()
            result = await router.diagnose(
                block_id=123,
                task_type="sfm",
                error_message="CUDA out of memory",
                failure_count=1,
                stage="bundle_adjustment"
            )

            if result:
                print(f"Diagnosis: {result['diagnosis']}")
                print(f"Severity: {result['severity']}")
            ```
        """
        # Step 1: Route to diagnostic level
        level = self.route_failure(error_message, failure_count, stage)

        logger.info(
            f"Routing block {block_id} failure to {level.value} diagnosis "
            f"(task_type={task_type}, stage={stage})"
        )

        # Step 2: Execute diagnosis based on level
        if level == DiagnosticLevel.L1_NONE:
            logger.debug(
                f"L1_NONE diagnosis for block {block_id}: skipping analysis"
            )
            return None

        elif level == DiagnosticLevel.L2_QUICK:
            logger.debug(
                f"L2_QUICK diagnosis for block {block_id}: running quick analysis"
            )
            # TODO: Implement quick diagnosis (10s timeout)
            # For now, return placeholder
            return {
                "level": "quick",
                "block_id": block_id,
                "task_type": task_type,
                "diagnosis": "Quick diagnosis not yet implemented",
                "suggestions": [],
                "severity": "info",
                "timestamp": None,  # Will be set by actual implementation
            }

        elif level == DiagnosticLevel.L3_DEEP:
            logger.debug(
                f"L3_DEEP diagnosis for block {block_id}: running deep analysis"
            )
            # TODO: Implement deep diagnosis (60s timeout)
            # For now, return placeholder
            return {
                "level": "deep",
                "block_id": block_id,
                "task_type": task_type,
                "diagnosis": "Deep diagnosis not yet implemented",
                "suggestions": [],
                "severity": "info",
                "timestamp": None,  # Will be set by actual implementation
            }

        # Should never reach here
        logger.warning(f"Unexpected diagnostic level: {level}")
        return None

    def track_failure(self, block_id: int) -> int:
        """Track failure count for a block.

        Maintains an internal counter of failure attempts per block to support
        recurring failure detection.

        Args:
            block_id: Block ID that failed

        Returns:
            Current failure count (after incrementing)

        Example:
            ```python
            router = DiagnosticRouter()

            # First failure
            count1 = router.track_failure(123)  # Returns 1

            # Second failure
            count2 = router.track_failure(123)  # Returns 2
            ```
        """
        self._failure_history[block_id] = self._failure_history.get(block_id, 0) + 1
        return self._failure_history[block_id]

    def reset_failure_count(self, block_id: int) -> None:
        """Reset failure count for a block (e.g., after successful retry).

        Args:
            block_id: Block ID to reset

        Example:
            ```python
            router = DiagnosticRouter()
            router.track_failure(123)  # count = 1
            router.reset_failure_count(123)  # count = 0
            ```
        """
        if block_id in self._failure_history:
            del self._failure_history[block_id]
            logger.debug(f"Reset failure count for block {block_id}")

    def get_failure_count(self, block_id: int) -> int:
        """Get current failure count for a block.

        Args:
            block_id: Block ID to query

        Returns:
            Current failure count (0 if no failures tracked)

        Example:
            ```python
            router = DiagnosticRouter()
            count = router.get_failure_count(123)  # Returns 0
            ```
        """
        return self._failure_history.get(block_id, 0)


# Singleton instance for global use
diagnostic_router = DiagnosticRouter()
