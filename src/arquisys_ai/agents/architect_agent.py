from __future__ import annotations

from dataclasses import replace
from collections.abc import Callable

from arquisys_ai.core.models import AnalystResult, ArchitectResult, DiagramFormat, DiagramType
from arquisys_ai.generators.mermaid.c4_container_generator import generate_c4_container_mermaid
from arquisys_ai.generators.mermaid.c4_context_generator import generate_c4_context_mermaid
from arquisys_ai.generators.mermaid.class_generator import generate_class_mermaid
from arquisys_ai.generators.mermaid.er_generator import generate_er_mermaid
from arquisys_ai.generators.mermaid.flow_generator import generate_flow_mermaid
from arquisys_ai.generators.mermaid.sequence_generator import generate_sequence_mermaid
from arquisys_ai.generators.mermaid.use_case_generator import generate_use_case_mermaid
from arquisys_ai.generators.plantuml.c4_container_generator import generate_c4_container_plantuml
from arquisys_ai.generators.plantuml.c4_context_generator import generate_c4_context_plantuml
from arquisys_ai.generators.plantuml.class_generator import generate_class_plantuml
from arquisys_ai.generators.plantuml.er_generator import generate_er_plantuml
from arquisys_ai.generators.plantuml.flow_generator import generate_flow_plantuml
from arquisys_ai.generators.plantuml.sequence_generator import generate_sequence_plantuml
from arquisys_ai.generators.plantuml.use_case_generator import generate_use_case_plantuml
from arquisys_ai.generators.text.qa_generator import generate_qa_test_cases
from arquisys_ai.generators.text.scaffolding_generator import generate_scaffolding_plan
from arquisys_ai.utils.text import normalize_text


class ArchitectAgent:
    def __init__(self):
        self._mermaid_generators: dict[DiagramType, Callable[[AnalystResult], str]] = {
            DiagramType.USE_CASE: generate_use_case_mermaid,
            DiagramType.CLASS: generate_class_mermaid,
            DiagramType.FLOW: generate_flow_mermaid,
            DiagramType.SEQUENCE: generate_sequence_mermaid,
            DiagramType.ER: generate_er_mermaid,
            DiagramType.C4_CONTEXT: generate_c4_context_mermaid,
            DiagramType.C4_CONTAINER: generate_c4_container_mermaid,
        }
        self._text_generators: dict[DiagramType, Callable[[AnalystResult], str]] = {
            DiagramType.QA_TESTS: generate_qa_test_cases,
            DiagramType.SCAFFOLDING: generate_scaffolding_plan,
        }
        self._plantuml_generators: dict[DiagramType, Callable[[AnalystResult], str]] = {
            DiagramType.USE_CASE: generate_use_case_plantuml,
            DiagramType.CLASS: generate_class_plantuml,
            DiagramType.FLOW: generate_flow_plantuml,
            DiagramType.SEQUENCE: generate_sequence_plantuml,
            DiagramType.ER: generate_er_plantuml,
            DiagramType.C4_CONTEXT: generate_c4_context_plantuml,
            DiagramType.C4_CONTAINER: generate_c4_container_plantuml,
        }

    def build(self, analysis: AnalystResult) -> ArchitectResult:
        if analysis.diagram_type is None:
            raise ValueError("diagram_type is required before building a diagram")

        if analysis.missing_info:
            missing = ", ".join(analysis.missing_info)
            raise ValueError(f"Cannot build diagram. Missing info: {missing}")

        warnings: list[str] = []

        if analysis.diagram_type == DiagramType.DOC_PACKAGE:
            code = self._build_doc_package(analysis)
            return ArchitectResult(
                diagram_type=analysis.diagram_type,
                diagram_format=DiagramFormat.TEXT,
                code=code,
                warnings=warnings,
            )

        if analysis.diagram_type in self._text_generators:
            if analysis.diagram_format != DiagramFormat.TEXT:
                warnings.append("Output for this request is textual. Returning text artifact.")
            generator = self._text_generators[analysis.diagram_type]
            code = generator(analysis)
            return ArchitectResult(
                diagram_type=analysis.diagram_type,
                diagram_format=DiagramFormat.TEXT,
                code=code,
                warnings=warnings,
            )

        output_format = analysis.diagram_format

        if output_format == DiagramFormat.TEXT:
            warnings.append("Text output requested for a diagram. Returning Mermaid output instead.")
            output_format = DiagramFormat.MERMAID

        if output_format not in {DiagramFormat.MERMAID, DiagramFormat.PLANTUML}:
            raise ValueError(f"Unsupported diagram format: {output_format.value}")

        generator = (
            self._plantuml_generators.get(analysis.diagram_type)
            if output_format == DiagramFormat.PLANTUML
            else self._mermaid_generators.get(analysis.diagram_type)
        )
        if generator is None:
            raise ValueError(
                f"Unsupported diagram type for {output_format.value}: {analysis.diagram_type.value}"
            )

        code = generator(analysis)
        return ArchitectResult(
            diagram_type=analysis.diagram_type,
            diagram_format=output_format,
            code=code,
            warnings=warnings,
        )

    @staticmethod
    def _contains_any(text: str, tokens: list[str]) -> bool:
        return any(token in text for token in tokens)

    @staticmethod
    def _infer_package_targets(normalized_text: str) -> list[DiagramType]:
        targets: list[DiagramType] = []

        if ArchitectAgent._contains_any(normalized_text, ["caso de uso", "casos de uso", "use case"]):
            targets.append(DiagramType.USE_CASE)
        if ArchitectAgent._contains_any(normalized_text, ["diagrama de secuencia", "sequence diagram", "secuencia"]):
            targets.append(DiagramType.SEQUENCE)
        if ArchitectAgent._contains_any(normalized_text, ["bpmn", "diagrama de flujo", "workflow", "proceso"]):
            targets.append(DiagramType.FLOW)
        if ArchitectAgent._contains_any(
            normalized_text,
            ["entity relationship", "entidad relacion", "entidad-relacion", "diagrama er", "erd"],
        ):
            targets.append(DiagramType.ER)
        if ArchitectAgent._contains_any(normalized_text, ["diagrama de clase", "diagrama de clases", "class diagram"]):
            targets.append(DiagramType.CLASS)
        if ArchitectAgent._contains_any(normalized_text, ["c4 context", "c4 contexto", "contexto c4"]):
            targets.append(DiagramType.C4_CONTEXT)
        if ArchitectAgent._contains_any(normalized_text, ["c4 container", "c4 contenedor", "c4 contenedores"]):
            targets.append(DiagramType.C4_CONTAINER)
        if ArchitectAgent._contains_any(normalized_text, ["qa automatic", "qa automatica", "casos de prueba", "gherkin"]):
            targets.append(DiagramType.QA_TESTS)
        if ArchitectAgent._contains_any(normalized_text, ["scaffolding", "codigo base", "boilerplate", "scaffold"]):
            targets.append(DiagramType.SCAFFOLDING)

        deduped: list[DiagramType] = []
        seen: set[DiagramType] = set()
        for target in targets:
            if target in seen:
                continue
            seen.add(target)
            deduped.append(target)

        if deduped:
            return deduped
        return [DiagramType.USE_CASE, DiagramType.SEQUENCE, DiagramType.FLOW, DiagramType.ER]

    def _build_doc_package(self, analysis: AnalystResult) -> str:
        normalized = normalize_text(analysis.raw_request)
        targets = self._infer_package_targets(normalized)
        preferred_format = analysis.diagram_format
        if preferred_format not in {DiagramFormat.MERMAID, DiagramFormat.PLANTUML}:
            preferred_format = DiagramFormat.MERMAID

        generator_map = self._plantuml_generators if preferred_format == DiagramFormat.PLANTUML else self._mermaid_generators
        fence = "plantuml" if preferred_format == DiagramFormat.PLANTUML else "mermaid"

        section_title = {
            DiagramType.USE_CASE: "Casos de Uso (UML)",
            DiagramType.CLASS: "Clases (UML)",
            DiagramType.FLOW: "Flujo de Proceso (BPMN-like)",
            DiagramType.SEQUENCE: "Secuencia (UML)",
            DiagramType.ER: "Entidad-Relacion (ER)",
            DiagramType.C4_CONTEXT: "C4 Context",
            DiagramType.C4_CONTAINER: "C4 Container",
            DiagramType.QA_TESTS: "QA Automatico",
            DiagramType.SCAFFOLDING: "Scaffolding Base",
        }

        lines: list[str] = [
            "# Paquete de Documentacion Visual",
            "",
            "Este paquete fue generado automaticamente por el Agente Arquitecto a partir del contexto entregado.",
            "",
        ]

        for target in targets:
            title = section_title.get(target, target.value)
            lines.append(f"## {title}")

            if target in generator_map:
                target_analysis = replace(
                    analysis,
                    diagram_type=target,
                    diagram_format=preferred_format,
                    missing_info=[],
                    ready_for_architect=True,
                )
                code = generator_map[target](target_analysis)
                lines.extend([f"```{fence}", code, "```", ""])
                continue

            if target in self._text_generators:
                target_analysis = replace(
                    analysis,
                    diagram_type=target,
                    diagram_format=DiagramFormat.TEXT,
                    missing_info=[],
                    ready_for_architect=True,
                )
                artifact = self._text_generators[target](target_analysis)
                lines.extend([artifact, ""])
                continue

            lines.extend(["No hay generador disponible para esta salida.", ""])

        return "\n".join(lines).strip()
