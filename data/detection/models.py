"""Typed, JSON-serializable models for deterministic rule results."""

from dataclasses import asdict, dataclass, field
import json
from typing import Any, Dict, List, Mapping, Optional


@dataclass
class Evidence:
    """A reference to one source record supporting a rule evaluation."""

    source_dataset: str
    record_type: str
    record_id: str
    role: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable evidence dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Evidence":
        """Create evidence from a serialized dictionary."""
        return cls(
            source_dataset=str(data["source_dataset"]),
            record_type=str(data["record_type"]),
            record_id=str(data["record_id"]),
            role=str(data["role"]),
            details=dict(data.get("details", {})),
        )


@dataclass
class RuleResult:
    """The standardized output of one deterministic rule evaluation."""

    rule_id: str
    rule_name: str
    detection_category: str
    triggered: bool
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    account_id: Optional[str] = None
    employee_id: Optional[str] = None
    customer_id: Optional[str] = None
    transaction_ids: List[str] = field(default_factory=list)
    access_event_ids: List[str] = field(default_factory=list)
    profile_change_ids: List[str] = field(default_factory=list)
    scenario_id: Optional[str] = None
    explanation: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    thresholds: Dict[str, Any] = field(default_factory=dict)
    detection_timestamp: Optional[str] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    evidence: List[Evidence] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return the result, including evidence, as a JSON-ready dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize the result to JSON."""
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RuleResult":
        """Create a result from a serialized dictionary."""
        values = dict(data)
        values["evidence"] = [
            Evidence.from_dict(item) for item in values.get("evidence", [])
        ]
        return cls(**values)

    @classmethod
    def from_json(cls, value: str) -> "RuleResult":
        """Deserialize a result from JSON."""
        return cls.from_dict(json.loads(value))