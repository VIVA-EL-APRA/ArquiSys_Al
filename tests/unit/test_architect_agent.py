from arquisys_ai.agents.architect_agent import ArchitectAgent
from arquisys_ai.core.models import AnalystResult, DiagramFormat, DiagramStandard, DiagramType


def test_architect_generates_use_case_mermaid() -> None:
    agent = ArchitectAgent()
    analysis = AnalystResult(
        raw_request="",
        summary="",
        standard=DiagramStandard.UML,
        diagram_type=DiagramType.USE_CASE,
        diagram_format=DiagramFormat.MERMAID,
        actors=["Cliente"],
        use_cases=["Comprar producto"],
        missing_info=[],
        ready_for_architect=True,
    )

    result = agent.build(analysis)

    assert result.diagram_format == DiagramFormat.MERMAID
    assert "flowchart LR" in result.code
    assert "subgraph SYS" in result.code
    assert "Cliente" in result.code
    assert "Comprar producto" in result.code


def test_architect_requires_ready_analysis() -> None:
    agent = ArchitectAgent()
    analysis = AnalystResult(
        raw_request="",
        diagram_type=DiagramType.CLASS,
        missing_info=["classes"],
        ready_for_architect=False,
    )

    try:
        agent.build(analysis)
    except ValueError as exc:
        assert "Missing info" in str(exc)
    else:
        raise AssertionError("Expected ValueError when analysis is incomplete")


def test_architect_generates_valid_class_member_syntax() -> None:
    agent = ArchitectAgent()
    analysis = AnalystResult(
        raw_request="",
        summary="",
        standard=DiagramStandard.UML,
        diagram_type=DiagramType.CLASS,
        diagram_format=DiagramFormat.MERMAID,
        classes=["Usuario(id, nombre)", "Pedido(id, total)"],
        missing_info=[],
        ready_for_architect=True,
    )

    result = agent.build(analysis)

    assert "classDiagram" in result.code
    assert "+id string" in result.code
    assert "+nombre string" in result.code
    assert "+id: string" not in result.code


def test_architect_generates_sequence_mermaid() -> None:
    agent = ArchitectAgent()
    analysis = AnalystResult(
        raw_request="",
        summary="",
        standard=DiagramStandard.UML,
        diagram_type=DiagramType.SEQUENCE,
        diagram_format=DiagramFormat.MERMAID,
        participants=["Cliente", "API"],
        sequence_steps=["Cliente->>API: Crear pedido", "API-->>Cliente: Confirmar"],
        missing_info=[],
        ready_for_architect=True,
    )

    result = agent.build(analysis)

    assert result.diagram_format == DiagramFormat.MERMAID
    assert "sequenceDiagram" in result.code
    assert "Crear pedido" in result.code


def test_architect_generates_er_mermaid() -> None:
    agent = ArchitectAgent()
    analysis = AnalystResult(
        raw_request="",
        summary="",
        standard=DiagramStandard.ER,
        diagram_type=DiagramType.ER,
        diagram_format=DiagramFormat.MERMAID,
        entities=["Usuario(id, nombre)", "Pedido(id, total)"],
        relationships=["Usuario->Pedido: realiza"],
        missing_info=[],
        ready_for_architect=True,
    )

    result = agent.build(analysis)

    assert "erDiagram" in result.code
    assert "USUARIO" in result.code
    assert "PEDIDO" in result.code


def test_architect_generates_text_for_qa_artifact() -> None:
    agent = ArchitectAgent()
    analysis = AnalystResult(
        raw_request="",
        summary="",
        diagram_type=DiagramType.QA_TESTS,
        diagram_format=DiagramFormat.TEXT,
        use_cases=["Comprar producto"],
        missing_info=[],
        ready_for_architect=True,
    )

    result = agent.build(analysis)

    assert result.diagram_format == DiagramFormat.TEXT
    assert "QA Automatico" in result.code
    assert "Scenario" in result.code


def test_architect_generates_text_for_scaffolding() -> None:
    agent = ArchitectAgent()
    analysis = AnalystResult(
        raw_request="",
        summary="",
        diagram_type=DiagramType.SCAFFOLDING,
        diagram_format=DiagramFormat.TEXT,
        use_cases=["Registrar pedido"],
        stack=["FastAPI", "React"],
        missing_info=[],
        ready_for_architect=True,
    )

    result = agent.build(analysis)

    assert result.diagram_format == DiagramFormat.TEXT
    assert "Scaffolding Base" in result.code
    assert "/api/registrar-pedido" in result.code


def test_architect_generates_c4_context_mermaid() -> None:
    agent = ArchitectAgent()
    analysis = AnalystResult(
        raw_request="",
        summary="",
        standard=DiagramStandard.C4,
        diagram_type=DiagramType.C4_CONTEXT,
        diagram_format=DiagramFormat.MERMAID,
        c4_people=["Cliente"],
        c4_systems=["Plataforma Ecommerce"],
        c4_relations=["Cliente->Plataforma Ecommerce: Usa"],
        missing_info=[],
        ready_for_architect=True,
    )

    result = agent.build(analysis)

    assert result.diagram_format == DiagramFormat.MERMAID
    assert "flowchart LR" in result.code
    assert "Persona Cliente" in result.code


def test_architect_respects_plantuml_format_for_use_case() -> None:
    agent = ArchitectAgent()
    analysis = AnalystResult(
        raw_request="Necesito un diagrama de casos de uso en PlantUML",
        summary="",
        standard=DiagramStandard.UML,
        diagram_type=DiagramType.USE_CASE,
        diagram_format=DiagramFormat.PLANTUML,
        actors=["Cliente", "Pasarela"],
        use_cases=["Revisar carrito", "Pagar"],
        missing_info=[],
        ready_for_architect=True,
    )

    result = agent.build(analysis)

    assert result.diagram_format == DiagramFormat.PLANTUML
    assert "@startuml" in result.code
    assert "usecase" in result.code
    assert "@enduml" in result.code


def test_architect_generates_documentation_package() -> None:
    agent = ArchitectAgent()
    analysis = AnalystResult(
        raw_request=(
            "Genera el paquete de documentacion visual completo con Casos de uso, Secuencia, BPMN y Entidad-Relacion "
            "para checkout"
        ),
        summary="",
        diagram_type=DiagramType.DOC_PACKAGE,
        diagram_format=DiagramFormat.TEXT,
        actors=["Usuario", "Pasarela de Pagos", "Sistema de Inventario", "Almacen"],
        use_cases=["Revisar carrito", "Procesar pago", "Notificar al almacen"],
        flow_steps=["Revisar carrito", "Validar stock", "Procesar pago", "Notificar al almacen"],
        participants=["Usuario", "Sistema Checkout", "Pasarela de Pagos", "Sistema de Inventario", "Almacen"],
        sequence_steps=["Usuario->>Sistema Checkout: Iniciar checkout"],
        entities=["Usuario(id)", "Pedido(id)", "Pago(id)"],
        relationships=["Usuario->Pedido: crea"],
        missing_info=[],
        ready_for_architect=True,
    )

    result = agent.build(analysis)

    assert result.diagram_format == DiagramFormat.TEXT
    assert "Paquete de Documentacion Visual" in result.code
    assert "Casos de Uso (UML)" in result.code
    assert "Secuencia (UML)" in result.code
    assert "Entidad-Relacion (ER)" in result.code


def test_architect_generates_documentation_package_in_plantuml() -> None:
    agent = ArchitectAgent()
    analysis = AnalystResult(
        raw_request="Genera paquete completo en PlantUML con casos de uso y secuencia y ER",
        summary="",
        diagram_type=DiagramType.DOC_PACKAGE,
        diagram_format=DiagramFormat.PLANTUML,
        actors=["Usuario", "Pasarela"],
        use_cases=["Revisar carrito", "Pagar"],
        flow_steps=["Revisar carrito", "Pagar"],
        participants=["Usuario", "Sistema Checkout", "Pasarela"],
        sequence_steps=["Usuario->>Sistema Checkout: Iniciar", "Sistema Checkout->>Pasarela: Cobrar"],
        entities=["Usuario(id)", "Pago(id)"],
        relationships=["Usuario->Pago: realiza"],
        missing_info=[],
        ready_for_architect=True,
    )

    result = agent.build(analysis)

    assert result.diagram_format == DiagramFormat.TEXT
    assert "```plantuml" in result.code
    assert "@startuml" in result.code
