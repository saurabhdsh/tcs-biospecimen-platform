"""Future integration adapters. Replace with enterprise connectors when required."""

from abc import ABC, abstractmethod


class ColdChainAdapter(ABC):
    """Future: enterprise cold-chain / CMMS temperature stream integration."""

    @abstractmethod
    def fetch_latest_reading(self, device_id: str) -> dict:
        raise NotImplementedError


class CarrierAdapter(ABC):
    """Future: carrier / logistics shipment tracking integration."""

    @abstractmethod
    def get_tracking(self, tracking_number: str) -> dict:
        raise NotImplementedError


class CTMSAdapter(ABC):
    """Future: CTMS study/subject linkage."""

    @abstractmethod
    def lookup_study(self, study_id: str) -> dict:
        raise NotImplementedError
