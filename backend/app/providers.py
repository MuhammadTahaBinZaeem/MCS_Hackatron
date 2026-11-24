from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ProviderStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"


@dataclass(frozen=True)
class ProviderUnavailable:
    status: ProviderStatus = ProviderStatus.NOT_CONFIGURED


class TextProvider(Protocol):
    def classify(self, value: str) -> ProviderUnavailable: ...
    def compare(self, value: str, candidates: list[str]) -> ProviderUnavailable: ...
    def summarize(self, aggregates: dict) -> ProviderUnavailable: ...


class VisionProvider(Protocol):
    def analyze(self, image: bytes) -> ProviderUnavailable: ...


class StorageProvider(Protocol):
    def save(self, value: bytes) -> ProviderUnavailable: ...
    def read(self, key: str) -> ProviderUnavailable: ...
    def delete(self, key: str) -> ProviderUnavailable: ...


class EmailProvider(Protocol):
    def send(self, recipient: str, message: str) -> ProviderUnavailable: ...


class DisabledProviders:
    def classify(self, value: str) -> ProviderUnavailable: return ProviderUnavailable()
    def compare(self, value: str, candidates: list[str]) -> ProviderUnavailable: return ProviderUnavailable()
    def summarize(self, aggregates: dict) -> ProviderUnavailable: return ProviderUnavailable()
    def analyze(self, image: bytes) -> ProviderUnavailable: return ProviderUnavailable()
    def save(self, value: bytes) -> ProviderUnavailable: return ProviderUnavailable()
    def read(self, key: str) -> ProviderUnavailable: return ProviderUnavailable()
    def delete(self, key: str) -> ProviderUnavailable: return ProviderUnavailable()
    def send(self, recipient: str, message: str) -> ProviderUnavailable: return ProviderUnavailable()
