"""
Automatic hidden-message detection and extraction.

    image = load_image_input(data, limits)          # Stage A
    events = run_auto_extraction(image, limits=...)  # Stages B-F
    result = collect_result(events)

See pipeline.py for the stage order and adapters.py for the supported
formats.
"""

from backend.app.services.auto_extract.adapters import (
    ExtractionAdapter,
    ExtractionContext,
    default_adapters,
)
from backend.app.services.auto_extract.image_input import load_image_input
from backend.app.services.auto_extract.pipeline import (
    STAGES,
    collect_result,
    run_auto_extraction,
)
from backend.app.services.auto_extract.types import (
    AutoExtractInputError,
    ImageInput,
    Limits,
    RecordedConfig,
    Validation,
)

__all__ = [
    "AutoExtractInputError",
    "ExtractionAdapter",
    "ExtractionContext",
    "ImageInput",
    "Limits",
    "RecordedConfig",
    "STAGES",
    "Validation",
    "collect_result",
    "default_adapters",
    "load_image_input",
    "run_auto_extraction",
]
