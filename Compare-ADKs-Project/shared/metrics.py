"""Metrics collection for ADK pipeline comparison."""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RunMetrics:
    framework: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    llm_calls: int = 0
    tool_calls: int = 0
    report_word_count: int = 0
    status: str = "pending"
    error: Optional[str] = None
    output_preview: str = ""

    def finish(self, output: str = ""):
        self.end_time = time.time()
        self.status = "success"
        if output:
            self.output_preview = output[:500]
            self.report_word_count = len(output.split())

    def fail(self, error: str):
        self.end_time = time.time()
        self.status = "error"
        self.error = error

    @property
    def elapsed_seconds(self) -> float:
        if self.end_time:
            return round(self.end_time - self.start_time, 2)
        return round(time.time() - self.start_time, 2)
