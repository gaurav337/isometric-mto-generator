from abc import ABC, abstractmethod
from typing import Any
from app.config import Settings

class ExtractionError(Exception):
    pass

class VisionExtractor(ABC):
    @abstractmethod
    def extract(self, image_b64: str) -> dict[str, Any]:
        """
        Sends the base64-encoded image to the vision model and returns the parsed JSON dict
        matching the LLMOutputSchema structure.
        
        Raises:
            ExtractionError: if extraction fails or returns invalid JSON.
        """
        pass

    @property
    @abstractmethod
    def source(self) -> str:
        """Returns the source identifier (e.g. 'nvidia', 'gemini', 'mock')"""
        pass

class ChainExtractor(VisionExtractor):
    def __init__(self, extractors: list[VisionExtractor]):
        self.extractors = extractors
        self._active_extractor = None

    @property
    def source(self) -> str:
        if self._active_extractor:
            return self._active_extractor.source
        return "chain"

    def extract(self, image_b64: str) -> dict[str, Any]:
        last_error = None
        for extractor in self.extractors:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Attempting extraction using provider: {extractor.source}")
            try:
                result = extractor.extract(image_b64)
                self._active_extractor = extractor
                return result
            except Exception as e:
                logger.warning(f"Provider {extractor.source} failed: {e}")
                last_error = e
        
        # If all failed
        raise ExtractionError(f"All extraction providers failed. Last error: {last_error}")


def get_active_provider_name(settings: Settings) -> str:
    if settings.nvidia_api_key and settings.nvidia_api_key.strip():
        return "nvidia"
    elif settings.gemini_api_key and settings.gemini_api_key.strip():
        return "gemini"
    elif settings.openrouter_api_key and settings.openrouter_api_key.strip():
        return "openrouter"
    else:
        return "mock"

def get_extractor(settings: Settings) -> VisionExtractor:
    """
    Factory function to select and instantiate the appropriate extractor.
    Dynamically falls back to mock if no keys are provided.
    Returns a ChainExtractor if multiple keys are configured.
    """
    from app.services.nvidia_extractor import NvidiaExtractor
    from app.services.gemini_extractor import GeminiExtractor
    from app.services.openrouter_extractor import OpenRouterExtractor
    from app.services.mock_extractor import MockExtractor
    
    extractors = []
    if settings.nvidia_api_key and settings.nvidia_api_key.strip():
        extractors.append(NvidiaExtractor(settings))
    if settings.gemini_api_key and settings.gemini_api_key.strip():
        extractors.append(GeminiExtractor(settings))
    if settings.openrouter_api_key and settings.openrouter_api_key.strip():
        extractors.append(OpenRouterExtractor(settings))
        
    if not extractors:
        return MockExtractor()
        
    if len(extractors) == 1:
        return extractors[0]
        
    return ChainExtractor(extractors)


