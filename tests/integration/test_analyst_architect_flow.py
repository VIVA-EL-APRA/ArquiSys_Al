from arquisys_ai.graph.workflow import ArquiSysWorkflow


def test_pipeline_runs_when_context_is_complete() -> None:
    workflow = ArquiSysWorkflow()

    request = (
        "Necesito un diagrama UML de flujo en Mermaid. "
        "Pasos: Recibir pedido, Validar pago, Confirmar compra"
    )
    result = workflow.run(request)

    assert result.analysis.ready_for_architect is True
    assert result.architecture is not None
    assert "flowchart TD" in result.architecture.code


def test_pipeline_stops_when_context_is_missing() -> None:
    workflow = ArquiSysWorkflow()

    result = workflow.run("Hazme un diagrama")

    assert result.analysis.ready_for_architect is False
    assert result.architecture is None


def test_pipeline_generates_sequence_diagram() -> None:
    workflow = ArquiSysWorkflow()

    request = (
        "Necesito un diagrama de secuencia UML en Mermaid. "
        "Participantes: Cliente, API, Base de Datos. "
        "Interacciones: Cliente->>API: Crear pedido, API->>Base de Datos: Guardar pedido"
    )
    result = workflow.run(request)

    assert result.analysis.ready_for_architect is True
    assert result.architecture is not None
    assert "sequenceDiagram" in result.architecture.code


def test_pipeline_generates_qa_artifact() -> None:
    workflow = ArquiSysWorkflow()

    request = "Quiero QA automatico. Casos de uso: Iniciar sesion, Comprar producto"
    result = workflow.run(request)

    assert result.analysis.ready_for_architect is True
    assert result.architecture is not None
    assert result.architecture.diagram_format.value == "text"
    assert "Scenario" in result.architecture.code


def test_pipeline_generates_documentation_package_without_extra_questions() -> None:
    workflow = ArquiSysWorkflow()

    request = (
        "Genera el paquete de documentacion visual completo (Casos de uso, Secuencia, BPMN y Entidad-Relacion) "
        "para checkout y pago de un e-commerce de ropa. "
        "Desde revisar carrito hasta aprobar pago y notificar al almacen, "
        "considerando tarjeta sin fondos y falta de stock."
    )
    result = workflow.run(request)

    assert result.analysis.diagram_type.value == "doc_package"
    assert result.analysis.ready_for_architect is True
    assert result.architecture is not None
    assert result.architecture.diagram_format.value == "text"
    assert "Casos de Uso (UML)" in result.architecture.code
    assert "Secuencia (UML)" in result.architecture.code
    assert "Flujo de Proceso (BPMN-like)" in result.architecture.code
    assert "Entidad-Relacion (ER)" in result.architecture.code


def test_pipeline_generates_plantuml_when_requested() -> None:
    workflow = ArquiSysWorkflow()

    request = (
        "Necesito un diagrama de secuencia UML en PlantUML. "
        "Participantes: Cliente, API, Pasarela. "
        "Interacciones: Cliente->>API: Checkout, API->>Pasarela: Cobrar, Pasarela-->>API: Aprobado"
    )
    result = workflow.run(request)

    assert result.analysis.ready_for_architect is True
    assert result.architecture is not None
    assert result.architecture.diagram_format.value == "plantuml"
    assert "@startuml" in result.architecture.code
