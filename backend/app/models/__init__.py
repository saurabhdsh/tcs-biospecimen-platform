from app.models.audit import AuditEvent
from app.models.custody import Custodian, CustodyAssignment, CustodyEvent
from app.models.environmental import EnvironmentalEvent, EvidenceAttachment
from app.models.exception import ExceptionCase, ExceptionResolution, ExceptionStatusHistory
from app.models.inventory import InventoryTransaction, SampleStorageAssignment, StorageLocation
from app.models.label import LabelPrintEvent, SampleLabel
from app.models.lineage import LineageRelationship, QuantityTransaction
from app.models.manifest import Manifest, ManifestFile, ManifestRow, ManifestValidationError
from app.models.report import ReportRun
from app.models.sample import Sample, SampleAlias, SampleIdentifier, SampleIdSequence
from app.models.shipment import Shipment, ShipmentSample
from app.models.traceability import Evidence, Requirement, TestCase, TestExecution
from app.models.user import Role, User, UserRole

__all__ = [
    "AuditEvent",
    "Custodian",
    "CustodyAssignment",
    "CustodyEvent",
    "EnvironmentalEvent",
    "Evidence",
    "EvidenceAttachment",
    "ExceptionCase",
    "ExceptionResolution",
    "ExceptionStatusHistory",
    "InventoryTransaction",
    "LabelPrintEvent",
    "LineageRelationship",
    "Manifest",
    "ManifestFile",
    "ManifestRow",
    "ManifestValidationError",
    "QuantityTransaction",
    "ReportRun",
    "Requirement",
    "Role",
    "Sample",
    "SampleAlias",
    "SampleIdentifier",
    "SampleIdSequence",
    "SampleLabel",
    "SampleStorageAssignment",
    "Shipment",
    "ShipmentSample",
    "StorageLocation",
    "TestCase",
    "TestExecution",
    "User",
    "UserRole",
]


def load_all_models() -> None:
    return None
