"""Future analysis boundary. No AI model, cloud API or fake metrics in v0.1.0."""
from pathlib import Path
from typing import Protocol

class RecordingAnalyzer(Protocol):
    """Read finalized metadata/segments; write separate artifacts under output_dir.
    Implementations must not modify input video or block the recorder loop.
    Register/run plugins explicitly in a future worker, never at import time.
    """
    name: str
    async def analyze(self, metadata_path: Path, output_dir: Path) -> list[Path]: ...
