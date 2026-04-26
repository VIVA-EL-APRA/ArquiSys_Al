from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DiagramStandard(str, Enum):
    UML = "uml"
    BPMN = "bpmn"
    ER = "er"
    C4 = "c4"


class DiagramType(str, Enum):
    DOC_PACKAGE = "doc_package"
    USE_CASE = "use_case"
    CLASS = "class"
    FLOW = "flow"
    SEQUENCE = "sequence"
    ER = "er"
    C4_CONTEXT = "c4_context"
    C4_CONTAINER = "c4_container"
    QA_TESTS = "qa_tests"
    SCAFFOLDING = "scaffolding"


class DiagramFormat(str, Enum):
    MERMAID = "mermaid"
    PLANTUML = "plantuml"
    TEXT = "text"


@dataclass
class AnalystResult:
    raw_request: str
    summary: str = ""
    standard: DiagramStandard | None = None
    diagram_type: DiagramType | None = None
    diagram_format: DiagramFormat = DiagramFormat.MERMAID
    actors: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    flow_steps: list[str] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    sequence_steps: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    c4_people: list[str] = field(default_factory=list)
    c4_systems: list[str] = field(default_factory=list)
    c4_containers: list[str] = field(default_factory=list)
    c4_relations: list[str] = field(default_factory=list)
    stack: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    missing_info: list[str] = field(default_factory=list)
    clarifying_questions: list[str] = field(default_factory=list)
    ready_for_architect: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_request": self.raw_request,
            "summary": self.summary,
            "standard": self.standard.value if self.standard else None,
            "diagram_type": self.diagram_type.value if self.diagram_type else None,
            "diagram_format": self.diagram_format.value,
            "actors": self.actors,
            "use_cases": self.use_cases,
            "classes": self.classes,
            "flow_steps": self.flow_steps,
            "participants": self.participants,
            "sequence_steps": self.sequence_steps,
            "entities": self.entities,
            "relationships": self.relationships,
            "c4_people": self.c4_people,
            "c4_systems": self.c4_systems,
            "c4_containers": self.c4_containers,
            "c4_relations": self.c4_relations,
            "stack": self.stack,
            "constraints": self.constraints,
            "missing_info": self.missing_info,
            "clarifying_questions": self.clarifying_questions,
            "ready_for_architect": self.ready_for_architect,
        }


@dataclass
class ArchitectResult:
    diagram_type: DiagramType
    diagram_format: DiagramFormat
    code: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagram_type": self.diagram_type.value,
            "diagram_format": self.diagram_format.value,
            "warnings": self.warnings,
            "code": self.code,
        }


@dataclass
class PipelineResult:
    analysis: AnalystResult
    architecture: ArchitectResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis": self.analysis.to_dict(),
            "architecture": self.architecture.to_dict() if self.architecture else None,
        }
