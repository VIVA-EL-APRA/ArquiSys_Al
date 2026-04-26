from arquisys_ai.agents.analyst_agent import AnalystAgent
from arquisys_ai.core.models import DiagramFormat, DiagramStandard, DiagramType


def test_analyst_extracts_use_case_context() -> None:
    agent = AnalystAgent(use_llm=False)

    text = (
        "Necesito un diagrama UML de casos de uso en Mermaid. "
        "Actores: Cliente, Administrador. "
        "Casos de uso: Iniciar sesion, Registrar pedido"
    )
    result = agent.analyze(text)

    assert result.ready_for_architect is True
    assert result.diagram_type == DiagramType.USE_CASE
    assert result.standard == DiagramStandard.UML
    assert result.diagram_format == DiagramFormat.MERMAID
    assert result.actors == ["Cliente", "Administrador"]
    assert result.use_cases == ["Iniciar sesion", "Registrar pedido"]


def test_analyst_requests_missing_context() -> None:
    agent = AnalystAgent(use_llm=False)

    result = agent.analyze("Quiero un diagrama de casos de uso.")

    assert result.ready_for_architect is False
    assert "actors" in result.missing_info
    assert "use_cases" in result.missing_info
    assert len(result.clarifying_questions) >= 2


def test_analyst_keeps_class_attributes_grouped() -> None:
    agent = AnalystAgent(use_llm=False)

    text = (
        "Necesito un diagrama UML de clases en Mermaid. "
        "Clases: Usuario(id, nombre), Pedido(id, total), Producto(id, precio)"
    )
    result = agent.analyze(text)

    assert result.ready_for_architect is True
    assert result.diagram_type == DiagramType.CLASS
    assert result.classes == [
        "Usuario(id, nombre)",
        "Pedido(id, total)",
        "Producto(id, precio)",
    ]


def test_analyst_extracts_sequence_context() -> None:
    agent = AnalystAgent(use_llm=False)

    text = (
        "Necesito un diagrama de secuencia UML en Mermaid. "
        "Participantes: Cliente, API, Base de Datos. "
        "Interacciones: Cliente->>API: Crear pedido, API->>Base de Datos: Guardar pedido"
    )
    result = agent.analyze(text)

    assert result.ready_for_architect is True
    assert result.diagram_type == DiagramType.SEQUENCE
    assert result.diagram_format == DiagramFormat.MERMAID
    assert result.participants == ["Cliente", "API", "Base de Datos"]
    assert len(result.sequence_steps) == 2


def test_analyst_detects_qa_request_as_text_output() -> None:
    agent = AnalystAgent(use_llm=False)

    result = agent.analyze("Quiero QA automatico. Casos de uso: Comprar producto")

    assert result.diagram_type == DiagramType.QA_TESTS
    assert result.diagram_format == DiagramFormat.TEXT
    assert result.ready_for_architect is True


def test_analyst_requests_stack_for_scaffolding() -> None:
    agent = AnalystAgent(use_llm=False)

    result = agent.analyze("Quiero scaffolding para pedidos. Casos de uso: Registrar pedido")

    assert result.diagram_type == DiagramType.SCAFFOLDING
    assert result.diagram_format == DiagramFormat.TEXT
    assert result.ready_for_architect is False
    assert "stack" in result.missing_info


def test_analyst_infers_er_type_from_context_labels() -> None:
    agent = AnalystAgent(use_llm=False)

    result = agent.analyze("Entidades ER: Usuario(id), Pedido(id). Relaciones ER: Usuario->Pedido: realiza")

    assert result.diagram_type == DiagramType.ER
    assert result.standard == DiagramStandard.ER
    assert result.ready_for_architect is True


def test_analyst_detects_doc_package_and_infers_missing_context() -> None:
    agent = AnalystAgent(use_llm=False)

    request = (
        "Genera el paquete de documentacion visual completo (Casos de uso, Secuencia, BPMN y Entidad-Relacion) "
        "para el modulo de checkout y pago de un e-commerce de ropa. "
        "El flujo va desde revisar carrito hasta aprobar pago y notificar al almacen. "
        "Incluye manejo de tarjeta sin fondos y falta de stock."
    )
    result = agent.analyze(request)

    assert result.diagram_type == DiagramType.DOC_PACKAGE
    assert result.diagram_format == DiagramFormat.MERMAID
    assert result.ready_for_architect is True
    assert len(result.participants) >= 2
    assert len(result.sequence_steps) >= 2
    assert len(result.entities) >= 2
