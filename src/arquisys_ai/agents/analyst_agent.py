from __future__ import annotations

import json
from pathlib import Path

from arquisys_ai.config.settings import get_settings
from arquisys_ai.core.models import AnalystResult, DiagramFormat, DiagramStandard, DiagramType
from arquisys_ai.services.llm_client import LLMClient, NullLLMClient
from arquisys_ai.utils.text import extract_list_after_labels, extract_numbered_steps, normalize_text


_PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "core" / "prompts" / "analyst" / "system_prompt.txt"
)


class AnalystAgent:
    def __init__(self, llm_client: LLMClient | None = None, use_llm: bool | None = None):
        settings = get_settings()
        self._llm_client = llm_client or NullLLMClient()
        self._use_llm = settings.use_llm_for_analyst if use_llm is None else use_llm

    def analyze(self, user_request: str) -> AnalystResult:
        result = self._heuristic_analysis(user_request)

        if self._use_llm and result.missing_info:
            llm_result = self._try_llm_completion(user_request)
            if llm_result is not None:
                result = self._merge(result, llm_result)

        result.missing_info = self._detect_missing_info(result)
        result.clarifying_questions = self._build_clarifying_questions(result.missing_info)
        result.ready_for_architect = not result.missing_info
        return result

    def _heuristic_analysis(self, user_request: str) -> AnalystResult:
        normalized = normalize_text(user_request)
        diagram_type = self._infer_diagram_type(normalized)
        package_targets = self._infer_package_targets(normalized)

        actors = extract_list_after_labels(user_request, ["Actores", "Actor", "Usuarios"])
        use_cases = extract_list_after_labels(
            user_request,
            ["Casos de uso", "Funciones", "Acciones", "Historias"],
        )
        classes = extract_list_after_labels(user_request, ["Clases", "Entidades", "Objetos"])

        flow_steps = extract_list_after_labels(
            user_request,
            ["Pasos", "Flujo", "Actividades", "Proceso", "Flujo principal", "Flujos alternativos"],
        )
        if not flow_steps:
            flow_steps = extract_numbered_steps(user_request)

        participants = extract_list_after_labels(
            user_request,
            ["Participantes", "Intervinientes", "Lifelines", "Participantes de secuencia"],
        )
        sequence_steps = extract_list_after_labels(
            user_request,
            ["Interacciones", "Mensajes", "Mensajes de secuencia", "Secuencia"],
        )
        if diagram_type == DiagramType.SEQUENCE and not sequence_steps:
            sequence_steps = extract_numbered_steps(user_request)

        entities = extract_list_after_labels(
            user_request,
            ["Entidades ER", "Entidades", "Tablas", "Entitys", "Entities"],
        )
        relationships = extract_list_after_labels(
            user_request,
            ["Relaciones ER", "Relaciones", "Cardinalidades"],
        )

        c4_people = extract_list_after_labels(
            user_request,
            ["Personas C4", "Personas", "Actores C4", "Usuarios C4"],
        )
        c4_systems = extract_list_after_labels(
            user_request,
            ["Sistemas C4", "Sistemas", "Sistema objetivo", "Aplicaciones"],
        )
        c4_containers = extract_list_after_labels(
            user_request,
            ["Contenedores", "Containers", "Componentes de despliegue"],
        )
        c4_relations = extract_list_after_labels(
            user_request,
            ["Relaciones C4", "Conexiones C4", "Interacciones C4"],
        )

        stack = extract_list_after_labels(
            user_request,
            ["Stack", "Tech Stack", "Tecnologias", "Frameworks", "Plataforma"],
        )

        if not actors:
            actors = self._infer_actors_from_context(normalized)

        package_mode = diagram_type == DiagramType.DOC_PACKAGE

        flow_expected = diagram_type in {DiagramType.FLOW, DiagramType.SEQUENCE} or (
            package_mode and any(target in package_targets for target in {DiagramType.USE_CASE, DiagramType.SEQUENCE, DiagramType.FLOW})
        )
        if not flow_steps and flow_expected:
            flow_steps = self._infer_flow_steps_from_context(normalized)

        use_case_expected = diagram_type in {DiagramType.USE_CASE, DiagramType.QA_TESTS, DiagramType.SCAFFOLDING} or (
            package_mode and DiagramType.USE_CASE in package_targets
        )
        if not use_cases and use_case_expected:
            use_cases = self._infer_use_cases_from_context(flow_steps, normalized)

        sequence_expected = diagram_type == DiagramType.SEQUENCE or (
            package_mode and DiagramType.SEQUENCE in package_targets
        )
        if sequence_expected and not participants:
            participants = self._infer_default_participants(actors, normalized)
        if sequence_expected and not sequence_steps:
            sequence_steps = self._infer_sequence_steps_from_context(participants, flow_steps, use_cases, normalized)

        er_expected = diagram_type == DiagramType.ER or (package_mode and DiagramType.ER in package_targets)
        if er_expected and not entities:
            entities = self._infer_entities_from_context(normalized)
        if er_expected and not relationships:
            relationships = self._infer_relationships_from_entities(entities)

        c4_context_expected = diagram_type == DiagramType.C4_CONTEXT or (
            package_mode and DiagramType.C4_CONTEXT in package_targets
        )
        c4_container_expected = diagram_type == DiagramType.C4_CONTAINER or (
            package_mode and DiagramType.C4_CONTAINER in package_targets
        )
        if (c4_context_expected or c4_container_expected) and not c4_people:
            c4_people = actors or ["Usuario"]
        if (c4_context_expected or c4_container_expected) and not c4_systems:
            c4_systems = self._infer_c4_systems_from_context(normalized)
        if c4_container_expected and not c4_containers:
            c4_containers = self._infer_c4_containers_from_context(stack)
        if (c4_context_expected or c4_container_expected) and not c4_relations:
            c4_relations = self._infer_c4_relations(c4_people, c4_systems, c4_containers)

        if diagram_type is None:
            if c4_containers:
                diagram_type = DiagramType.C4_CONTAINER
            elif c4_people or c4_systems:
                diagram_type = DiagramType.C4_CONTEXT
            elif entities:
                diagram_type = DiagramType.ER
            elif participants and sequence_steps:
                diagram_type = DiagramType.SEQUENCE
            elif classes:
                diagram_type = DiagramType.CLASS
            elif actors and use_cases:
                diagram_type = DiagramType.USE_CASE
            elif flow_steps:
                diagram_type = DiagramType.FLOW

        if diagram_type == DiagramType.SEQUENCE and not participants:
            participants = actors

        if diagram_type == DiagramType.ER and not entities:
            entities = classes

        standard = self._infer_standard(normalized, diagram_type)
        diagram_format = self._infer_format(normalized, diagram_type)

        summary = user_request.strip().split("\n", maxsplit=1)[0][:260]

        result = AnalystResult(
            raw_request=user_request,
            summary=summary,
            standard=standard,
            diagram_type=diagram_type,
            diagram_format=diagram_format,
            actors=actors,
            use_cases=use_cases,
            classes=classes,
            flow_steps=flow_steps,
            participants=participants,
            sequence_steps=sequence_steps,
            entities=entities,
            relationships=relationships,
            c4_people=c4_people,
            c4_systems=c4_systems,
            c4_containers=c4_containers,
            c4_relations=c4_relations,
            stack=stack,
        )
        result.missing_info = self._detect_missing_info(result)
        result.clarifying_questions = self._build_clarifying_questions(result.missing_info)
        result.ready_for_architect = not result.missing_info
        return result

    @staticmethod
    def _contains_any(text: str, tokens: list[str]) -> bool:
        return any(token in text for token in tokens)

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        for item in items:
            value = item.strip()
            if not value:
                continue
            key = normalize_text(value)
            if key in seen:
                continue
            seen.add(key)
            output.append(value)
        return output

    @staticmethod
    def _infer_package_targets(normalized_text: str) -> list[DiagramType]:
        targets: list[DiagramType] = []

        if AnalystAgent._contains_any(normalized_text, ["caso de uso", "casos de uso", "use case"]):
            targets.append(DiagramType.USE_CASE)
        if AnalystAgent._contains_any(normalized_text, ["diagrama de secuencia", "sequence diagram", "secuencia"]):
            targets.append(DiagramType.SEQUENCE)
        if AnalystAgent._contains_any(normalized_text, ["bpmn", "diagrama de flujo", "workflow", "proceso"]):
            targets.append(DiagramType.FLOW)
        if AnalystAgent._contains_any(
            normalized_text,
            ["entity relationship", "entidad relacion", "entidad-relacion", "diagrama er", "erd"],
        ):
            targets.append(DiagramType.ER)
        if AnalystAgent._contains_any(normalized_text, ["diagrama de clase", "diagrama de clases", "class diagram"]):
            targets.append(DiagramType.CLASS)
        if AnalystAgent._contains_any(normalized_text, ["c4 context", "c4 contexto", "contexto c4"]):
            targets.append(DiagramType.C4_CONTEXT)
        if AnalystAgent._contains_any(normalized_text, ["c4 container", "c4 contenedor", "c4 contenedores"]):
            targets.append(DiagramType.C4_CONTAINER)

        deduped: list[DiagramType] = []
        seen: set[DiagramType] = set()
        for target in targets:
            if target in seen:
                continue
            seen.add(target)
            deduped.append(target)
        return deduped

    @staticmethod
    def _is_package_request(normalized_text: str, targets: list[DiagramType]) -> bool:
        if not targets:
            return False

        explicit_package = AnalystAgent._contains_any(
            normalized_text,
            [
                "tipo de salida: paquete",
                "paquete de documentacion",
                "documentacion visual completo",
                "documentacion completa",
                "set completo de diagramas",
                "todos los diagramas",
                "todo lo que es diagramacion",
            ],
        )
        return explicit_package and len(targets) >= 2 or len(targets) >= 3

    @staticmethod
    def _infer_actors_from_context(normalized_text: str) -> list[str]:
        actors: list[str] = []
        if AnalystAgent._contains_any(normalized_text, ["usuario", "cliente", "buyer", "comprador"]):
            actors.append("Usuario")
        if AnalystAgent._contains_any(normalized_text, ["pasarela de pagos", "pasarela de pago", "gateway de pago"]):
            actors.append("Pasarela de Pagos")
        if AnalystAgent._contains_any(normalized_text, ["inventario", "sistema de inventario", "stock"]):
            actors.append("Sistema de Inventario")
        if AnalystAgent._contains_any(normalized_text, ["almacen", "warehouse"]):
            actors.append("Almacen")

        if not actors and AnalystAgent._contains_any(normalized_text, ["e-commerce", "ecommerce", "checkout"]):
            actors = ["Usuario", "Pasarela de Pagos"]

        return AnalystAgent._dedupe(actors)

    @staticmethod
    def _infer_default_participants(actors: list[str], normalized_text: str) -> list[str]:
        participants = list(actors)
        if not participants:
            participants = AnalystAgent._infer_actors_from_context(normalized_text)

        if not participants:
            participants = ["Usuario"]

        has_checkout = any("checkout" in normalize_text(item) for item in participants)
        if not has_checkout:
            participants.insert(1 if participants else 0, "Sistema Checkout")

        if len(participants) < 2:
            participants.append("Sistema")

        return AnalystAgent._dedupe(participants)

    @staticmethod
    def _infer_flow_steps_from_context(normalized_text: str) -> list[str]:
        steps: list[str] = []

        if AnalystAgent._contains_any(normalized_text, ["carrito", "revisa su carrito"]):
            steps.append("Revisar carrito")
        if "checkout" in normalized_text:
            steps.append("Iniciar checkout")
        if AnalystAgent._contains_any(normalized_text, ["stock", "inventario"]):
            steps.append("Validar stock disponible")
        if "pago" in normalized_text:
            steps.append("Solicitar autorizacion de pago")
        if AnalystAgent._contains_any(normalized_text, ["aprueba el pago", "pago aprobado", "aprobado"]):
            steps.append("Confirmar pago aprobado")
        if AnalystAgent._contains_any(normalized_text, ["notifica al almacen", "notificar al almacen", "almacen"]):
            steps.append("Notificar al almacen")
        if AnalystAgent._contains_any(normalized_text, ["sin fondos", "tarjeta sin fondos"]):
            steps.append("Manejar pago rechazado por fondos")
        if AnalystAgent._contains_any(normalized_text, ["falta de stock", "stock insuficiente"]):
            steps.append("Manejar falta de stock")

        if len(steps) < 2 and "pedido" in normalized_text:
            steps.extend(["Crear pedido", "Procesar pago", "Confirmar pedido"])

        return AnalystAgent._dedupe(steps)

    @staticmethod
    def _infer_use_cases_from_context(flow_steps: list[str], normalized_text: str) -> list[str]:
        if flow_steps:
            return AnalystAgent._dedupe([step for step in flow_steps])

        use_cases: list[str] = []
        if "carrito" in normalized_text:
            use_cases.append("Revisar carrito")
        if "checkout" in normalized_text:
            use_cases.append("Completar checkout")
        if "pago" in normalized_text:
            use_cases.append("Procesar pago")
        if "inventario" in normalized_text or "stock" in normalized_text:
            use_cases.append("Validar stock")
        if "almacen" in normalized_text:
            use_cases.append("Notificar al almacen")
        if "sin fondos" in normalized_text:
            use_cases.append("Gestionar tarjeta sin fondos")
        if "falta de stock" in normalized_text or "stock insuficiente" in normalized_text:
            use_cases.append("Gestionar falta de stock")

        return AnalystAgent._dedupe(use_cases)

    @staticmethod
    def _infer_sequence_steps_from_context(
        participants: list[str],
        flow_steps: list[str],
        use_cases: list[str],
        normalized_text: str,
    ) -> list[str]:
        if len(participants) < 2:
            participants = ["Usuario", "Sistema Checkout"]

        user = participants[0]
        checkout = next((item for item in participants if "checkout" in normalize_text(item)), participants[1])
        payment = next((item for item in participants if "pasarela" in normalize_text(item) or "pago" in normalize_text(item)), "Pasarela de Pagos")
        inventory = next((item for item in participants if "inventario" in normalize_text(item) or "stock" in normalize_text(item)), "Sistema de Inventario")
        warehouse = next((item for item in participants if "almacen" in normalize_text(item)), "Almacen")

        steps: list[str] = [
            f"{user}->>{checkout}: Revisar carrito e iniciar checkout",
            f"{checkout}->>{inventory}: Validar stock",
            f"{inventory}-->>{checkout}: Stock confirmado",
            f"{checkout}->>{payment}: Autorizar pago",
            f"{payment}-->>{checkout}: Pago aprobado",
            f"{checkout}->>{warehouse}: Notificar preparacion",
            f"{checkout}-->>{user}: Confirmar pedido",
        ]

        if AnalystAgent._contains_any(normalized_text, ["sin fondos", "tarjeta sin fondos"]):
            steps.extend(
                [
                    f"{payment}-->>{checkout}: Tarjeta sin fondos",
                    f"{checkout}-->>{user}: Informar rechazo de pago",
                ]
            )
        if AnalystAgent._contains_any(normalized_text, ["falta de stock", "stock insuficiente"]):
            steps.extend(
                [
                    f"{inventory}-->>{checkout}: Stock insuficiente",
                    f"{checkout}-->>{user}: Informar falta de stock",
                ]
            )

        if not steps and (flow_steps or use_cases):
            source = participants[0]
            target = participants[1]
            for item in flow_steps or use_cases:
                steps.append(f"{source}->>{target}: {item}")

        return AnalystAgent._dedupe(steps)

    @staticmethod
    def _infer_entities_from_context(normalized_text: str) -> list[str]:
        entities: list[str] = []

        if AnalystAgent._contains_any(normalized_text, ["usuario", "cliente"]):
            entities.append("Usuario(id, email)")
        if "carrito" in normalized_text:
            entities.append("Carrito(id, estado)")
        if AnalystAgent._contains_any(normalized_text, ["checkout", "pedido", "ecommerce", "e-commerce"]):
            entities.append("Pedido(id, estado, total)")
        if "pago" in normalized_text:
            entities.append("Pago(id, estado, monto)")
            entities.append("TransaccionPago(id, estado, referencia)")
        if AnalystAgent._contains_any(normalized_text, ["producto", "ropa"]):
            entities.append("Producto(id, sku, nombre)")
        if AnalystAgent._contains_any(normalized_text, ["inventario", "stock"]):
            entities.append("Inventario(id, stockDisponible)")
        if "almacen" in normalized_text:
            entities.append("NotificacionAlmacen(id, estado, fechaEnvio)")

        if len(entities) < 2:
            entities.extend(["Usuario(id)", "Pedido(id)", "Pago(id)"])

        return AnalystAgent._dedupe(entities)

    @staticmethod
    def _infer_relationships_from_entities(entities: list[str]) -> list[str]:
        names = [entity.split("(", maxsplit=1)[0].strip() for entity in entities]
        by_key = {normalize_text(name): name for name in names}
        relationships: list[str] = []

        def get(key: str) -> str | None:
            return by_key.get(normalize_text(key))

        usuario = get("Usuario")
        carrito = get("Carrito")
        pedido = get("Pedido")
        pago = get("Pago")
        transaccion = get("TransaccionPago")
        producto = get("Producto")
        inventario = get("Inventario")
        notificacion = get("NotificacionAlmacen")

        if usuario and carrito:
            relationships.append(f"{usuario}-> {carrito}: posee")
        if carrito and pedido:
            relationships.append(f"{carrito}-> {pedido}: genera")
        if pedido and pago:
            relationships.append(f"{pedido}-> {pago}: registra")
        if pago and transaccion:
            relationships.append(f"{pago}-> {transaccion}: confirma")
        if pedido and producto:
            relationships.append(f"{pedido}-> {producto}: contiene")
        if producto and inventario:
            relationships.append(f"{producto}-> {inventario}: actualiza")
        if pedido and notificacion:
            relationships.append(f"{pedido}-> {notificacion}: notifica")

        if not relationships and len(names) >= 2:
            relationships.append(f"{names[0]}-> {names[1]}: relacion")

        return AnalystAgent._dedupe(relationships)

    @staticmethod
    def _infer_c4_systems_from_context(normalized_text: str) -> list[str]:
        systems: list[str] = []
        if AnalystAgent._contains_any(normalized_text, ["ecommerce", "e-commerce", "checkout"]):
            systems.append("Plataforma Ecommerce")
        if AnalystAgent._contains_any(normalized_text, ["pasarela de pago", "pasarela de pagos", "gateway de pago"]):
            systems.append("Pasarela de Pagos")
        if AnalystAgent._contains_any(normalized_text, ["inventario", "stock"]):
            systems.append("Sistema de Inventario")
        if "almacen" in normalized_text:
            systems.append("Sistema de Almacen")
        if not systems:
            systems.append("Sistema Principal")
        return AnalystAgent._dedupe(systems)

    @staticmethod
    def _infer_c4_containers_from_context(stack: list[str]) -> list[str]:
        if stack:
            first = stack[0]
            second = stack[1] if len(stack) > 1 else "PostgreSQL"
            return [f"Web App({first})", f"API({first})", f"Base de Datos({second})"]
        return ["Web App(React)", "API(FastAPI)", "Base de Datos(PostgreSQL)"]

    @staticmethod
    def _infer_c4_relations(c4_people: list[str], c4_systems: list[str], c4_containers: list[str]) -> list[str]:
        relations: list[str] = []
        if c4_people and c4_systems:
            relations.append(f"{c4_people[0]}-> {c4_systems[0]}: Usa")
        if c4_systems and len(c4_systems) > 1:
            relations.append(f"{c4_systems[0]}-> {c4_systems[1]}: Integra")
        if c4_containers and len(c4_containers) > 1:
            left = c4_containers[0].split("(", maxsplit=1)[0].strip()
            right = c4_containers[1].split("(", maxsplit=1)[0].strip()
            relations.append(f"{left}-> {right}: Consume")
        return AnalystAgent._dedupe(relations)

    @staticmethod
    def _infer_diagram_type(normalized_text: str) -> DiagramType | None:
        if "tipo de salida: paquete" in normalized_text or "tipo de salida: paquete documentacion" in normalized_text:
            return DiagramType.DOC_PACKAGE
        if "tipo de salida: scaffolding" in normalized_text:
            return DiagramType.SCAFFOLDING
        if "tipo de salida: qa automatico" in normalized_text or "tipo de salida: qa automatica" in normalized_text:
            return DiagramType.QA_TESTS
        if "tipo de salida: c4 contenedores" in normalized_text:
            return DiagramType.C4_CONTAINER
        if "tipo de salida: c4 contexto" in normalized_text:
            return DiagramType.C4_CONTEXT
        if "tipo de salida: er" in normalized_text:
            return DiagramType.ER
        if "tipo de salida: secuencia" in normalized_text:
            return DiagramType.SEQUENCE
        if "tipo de salida: casos de uso" in normalized_text:
            return DiagramType.USE_CASE
        if "tipo de salida: clases" in normalized_text:
            return DiagramType.CLASS
        if "tipo de salida: flujo" in normalized_text:
            return DiagramType.FLOW

        package_targets = AnalystAgent._infer_package_targets(normalized_text)
        if AnalystAgent._is_package_request(normalized_text, package_targets):
            return DiagramType.DOC_PACKAGE

        if any(token in normalized_text for token in ["scaffolding", "codigo base", "esqueleto", "boilerplate", "scaffold"]):
            return DiagramType.SCAFFOLDING

        if any(
            token in normalized_text
            for token in [
                "qa automatic",
                "qa automatica",
                "casos de prueba",
                "escenarios de prueba",
                "gherkin",
                "pruebas qa",
            ]
        ):
            return DiagramType.QA_TESTS

        if any(token in normalized_text for token in ["c4 container", "c4 contenedor", "c4 contenedores"]):
            return DiagramType.C4_CONTAINER

        if any(token in normalized_text for token in ["c4 context", "c4 contexto", "contexto c4"]):
            return DiagramType.C4_CONTEXT

        if any(token in normalized_text for token in ["entity relationship", "entidad relacion", "er diagram", "diagrama er", "erd"]):
            return DiagramType.ER

        if any(token in normalized_text for token in ["diagrama de secuencia", "sequence diagram", "secuencia"]):
            return DiagramType.SEQUENCE

        if any(token in normalized_text for token in ["caso de uso", "casos de uso", "use case"]):
            return DiagramType.USE_CASE

        if any(token in normalized_text for token in ["diagrama de clase", "diagrama de clases", "class diagram"]):
            return DiagramType.CLASS
        if "clases" in normalized_text and "diagrama" in normalized_text:
            return DiagramType.CLASS

        if any(token in normalized_text for token in ["diagrama de flujo", "workflow", "flujo", "proceso"]):
            return DiagramType.FLOW

        return None

    @staticmethod
    def _infer_standard(normalized_text: str, diagram_type: DiagramType | None) -> DiagramStandard | None:
        if "bpmn" in normalized_text:
            return DiagramStandard.BPMN
        if "estandar: c4" in normalized_text or "c4" in normalized_text:
            return DiagramStandard.C4
        if "estandar: er" in normalized_text or any(
            token in normalized_text for token in ["entity relationship", "entidad relacion", "erd", "er diagram", "diagrama er"]
        ):
            return DiagramStandard.ER
        if "uml" in normalized_text:
            return DiagramStandard.UML

        if diagram_type in {
            DiagramType.USE_CASE,
            DiagramType.CLASS,
            DiagramType.FLOW,
            DiagramType.SEQUENCE,
        }:
            return DiagramStandard.UML
        if diagram_type == DiagramType.ER:
            return DiagramStandard.ER
        if diagram_type in {DiagramType.C4_CONTEXT, DiagramType.C4_CONTAINER}:
            return DiagramStandard.C4

        return None

    @staticmethod
    def _infer_format(normalized_text: str, diagram_type: DiagramType | None) -> DiagramFormat:
        if diagram_type in {DiagramType.QA_TESTS, DiagramType.SCAFFOLDING}:
            return DiagramFormat.TEXT
        if "plantuml" in normalized_text:
            return DiagramFormat.PLANTUML
        if any(token in normalized_text for token in ["texto", "markdown", "text output"]):
            return DiagramFormat.TEXT
        return DiagramFormat.MERMAID

    def _try_llm_completion(self, user_request: str) -> AnalystResult | None:
        system_prompt = _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else ""
        user_prompt = (
            "Extrae el contexto del siguiente pedido y devuelve JSON puro con esta forma: "
            "{summary, standard, diagram_type, diagram_format, actors, use_cases, classes, flow_steps, "
            "participants, sequence_steps, entities, relationships, c4_people, c4_systems, c4_containers, "
            "c4_relations, stack}. No agregues texto fuera del JSON.\n\n"
            f"Pedido:\n{user_request}"
        )
        llm_raw = self._llm_client.complete(system_prompt, user_prompt, temperature=0.0).strip()
        if not llm_raw:
            return None

        json_start = llm_raw.find("{")
        json_end = llm_raw.rfind("}")
        if json_start < 0 or json_end <= json_start:
            return None

        payload = llm_raw[json_start : json_end + 1]
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None

        return AnalystResult(
            raw_request=user_request,
            summary=str(data.get("summary", "")).strip(),
            standard=self._to_standard(data.get("standard")),
            diagram_type=self._to_type(data.get("diagram_type")),
            diagram_format=self._to_format(data.get("diagram_format")),
            actors=self._to_list(data.get("actors")),
            use_cases=self._to_list(data.get("use_cases")),
            classes=self._to_list(data.get("classes")),
            flow_steps=self._to_list(data.get("flow_steps")),
            participants=self._to_list(data.get("participants")),
            sequence_steps=self._to_list(data.get("sequence_steps")),
            entities=self._to_list(data.get("entities")),
            relationships=self._to_list(data.get("relationships")),
            c4_people=self._to_list(data.get("c4_people")),
            c4_systems=self._to_list(data.get("c4_systems")),
            c4_containers=self._to_list(data.get("c4_containers")),
            c4_relations=self._to_list(data.get("c4_relations")),
            stack=self._to_list(data.get("stack")),
        )

    @staticmethod
    def _merge(base: AnalystResult, llm_result: AnalystResult) -> AnalystResult:
        return AnalystResult(
            raw_request=base.raw_request,
            summary=llm_result.summary or base.summary,
            standard=llm_result.standard or base.standard,
            diagram_type=llm_result.diagram_type or base.diagram_type,
            diagram_format=llm_result.diagram_format or base.diagram_format,
            actors=llm_result.actors or base.actors,
            use_cases=llm_result.use_cases or base.use_cases,
            classes=llm_result.classes or base.classes,
            flow_steps=llm_result.flow_steps or base.flow_steps,
            participants=llm_result.participants or base.participants,
            sequence_steps=llm_result.sequence_steps or base.sequence_steps,
            entities=llm_result.entities or base.entities,
            relationships=llm_result.relationships or base.relationships,
            c4_people=llm_result.c4_people or base.c4_people,
            c4_systems=llm_result.c4_systems or base.c4_systems,
            c4_containers=llm_result.c4_containers or base.c4_containers,
            c4_relations=llm_result.c4_relations or base.c4_relations,
            stack=llm_result.stack or base.stack,
            constraints=base.constraints,
        )

    @staticmethod
    def _detect_missing_info(result: AnalystResult) -> list[str]:
        missing: list[str] = []

        if result.diagram_type is None:
            missing.append("diagram_type")
            return missing

        if result.diagram_type == DiagramType.DOC_PACKAGE:
            targets = AnalystAgent._infer_package_targets(normalize_text(result.raw_request))
            if not targets:
                missing.append("diagram_type")
                return missing

            if DiagramType.USE_CASE in targets and not (result.use_cases or result.flow_steps):
                missing.append("use_cases")

            if DiagramType.SEQUENCE in targets:
                if len(result.participants) < 2:
                    missing.append("participants")
                if not (result.sequence_steps or result.flow_steps or result.use_cases):
                    missing.append("sequence_steps")

            if DiagramType.FLOW in targets and len(result.flow_steps) < 2:
                missing.append("flow_steps")

            if DiagramType.ER in targets and not result.entities:
                missing.append("entities")

            if DiagramType.C4_CONTEXT in targets:
                if not result.c4_people:
                    missing.append("c4_people")
                if not result.c4_systems:
                    missing.append("c4_systems")

            if DiagramType.C4_CONTAINER in targets:
                if not result.c4_systems:
                    missing.append("c4_systems")
                if not result.c4_containers:
                    missing.append("c4_containers")

            if DiagramType.QA_TESTS in targets and not (result.use_cases or result.flow_steps or result.sequence_steps):
                missing.append("qa_scope")

            if DiagramType.SCAFFOLDING in targets:
                if not any([result.use_cases, result.flow_steps, result.sequence_steps, result.classes, result.entities]):
                    missing.append("scaffolding_scope")
                if not result.stack:
                    missing.append("stack")

            return AnalystAgent._dedupe(missing)

        if result.diagram_type == DiagramType.USE_CASE:
            if not result.actors:
                missing.append("actors")
            if not result.use_cases:
                missing.append("use_cases")

        elif result.diagram_type == DiagramType.CLASS:
            if not result.classes:
                missing.append("classes")

        elif result.diagram_type == DiagramType.FLOW:
            if len(result.flow_steps) < 2:
                missing.append("flow_steps")

        elif result.diagram_type == DiagramType.SEQUENCE:
            if len(result.participants) < 2:
                missing.append("participants")
            if not result.sequence_steps and not result.flow_steps and not result.use_cases:
                missing.append("sequence_steps")

        elif result.diagram_type == DiagramType.ER:
            if not result.entities:
                missing.append("entities")

        elif result.diagram_type == DiagramType.C4_CONTEXT:
            if not result.c4_people:
                missing.append("c4_people")
            if not result.c4_systems:
                missing.append("c4_systems")

        elif result.diagram_type == DiagramType.C4_CONTAINER:
            if not result.c4_systems:
                missing.append("c4_systems")
            if not result.c4_containers:
                missing.append("c4_containers")

        elif result.diagram_type == DiagramType.QA_TESTS:
            if not result.use_cases and not result.flow_steps and not result.sequence_steps:
                missing.append("qa_scope")

        elif result.diagram_type == DiagramType.SCAFFOLDING:
            if not any([result.use_cases, result.flow_steps, result.sequence_steps, result.classes, result.entities]):
                missing.append("scaffolding_scope")
            if not result.stack:
                missing.append("stack")

        if result.diagram_type in {
            DiagramType.USE_CASE,
            DiagramType.CLASS,
            DiagramType.FLOW,
            DiagramType.SEQUENCE,
            DiagramType.ER,
            DiagramType.C4_CONTEXT,
            DiagramType.C4_CONTAINER,
        } and result.standard is None:
            missing.append("standard")

        return missing

    @staticmethod
    def _build_clarifying_questions(missing_info: list[str]) -> list[str]:
        question_map = {
            "diagram_type": "Que salida necesitas: diagrama unico (casos de uso, clases, flujo, secuencia, ER, C4) o paquete de documentacion?",
            "actors": "Quienes son los actores principales que interactuan con el sistema?",
            "use_cases": "Que acciones o casos de uso quieres modelar?",
            "classes": "Que clases o entidades principales deben aparecer?",
            "flow_steps": "Cuales son los pasos del proceso en orden?",
            "participants": "Que participantes intervienen en la secuencia (minimo dos)?",
            "sequence_steps": "Que mensajes o interacciones deben aparecer en la secuencia?",
            "entities": "Que entidades o tablas incluye tu modelo ER?",
            "c4_people": "Que personas o roles externos intervienen en el sistema (C4 Context)?",
            "c4_systems": "Que sistemas o plataformas deben aparecer en el diagrama C4?",
            "c4_containers": "Que contenedores internos quieres en C4 Container (API, Web, DB, Worker)?",
            "qa_scope": "Que casos de uso o pasos de flujo debo convertir en escenarios de prueba?",
            "scaffolding_scope": "Que funcionalidad base quieres scaffoldear (casos de uso, flujos o entidades)?",
            "stack": "Que stack tecnologico debo usar para generar scaffolding (por ejemplo FastAPI, React, PostgreSQL)?",
            "standard": "Debo usar UML, BPMN, ER o C4?",
        }
        return [question_map[key] for key in missing_info if key in question_map]

    @staticmethod
    def _to_list(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        return []

    @staticmethod
    def _to_standard(value: object) -> DiagramStandard | None:
        if not isinstance(value, str):
            return None
        token = value.strip().lower()
        if token == DiagramStandard.UML.value:
            return DiagramStandard.UML
        if token == DiagramStandard.BPMN.value:
            return DiagramStandard.BPMN
        if token == DiagramStandard.ER.value:
            return DiagramStandard.ER
        if token == DiagramStandard.C4.value:
            return DiagramStandard.C4
        return None

    @staticmethod
    def _to_type(value: object) -> DiagramType | None:
        if not isinstance(value, str):
            return None
        token = value.strip().lower()
        if token == DiagramType.DOC_PACKAGE.value:
            return DiagramType.DOC_PACKAGE
        if token == DiagramType.USE_CASE.value:
            return DiagramType.USE_CASE
        if token == DiagramType.CLASS.value:
            return DiagramType.CLASS
        if token == DiagramType.FLOW.value:
            return DiagramType.FLOW
        if token == DiagramType.SEQUENCE.value:
            return DiagramType.SEQUENCE
        if token == DiagramType.ER.value:
            return DiagramType.ER
        if token == DiagramType.C4_CONTEXT.value:
            return DiagramType.C4_CONTEXT
        if token == DiagramType.C4_CONTAINER.value:
            return DiagramType.C4_CONTAINER
        if token == DiagramType.QA_TESTS.value:
            return DiagramType.QA_TESTS
        if token == DiagramType.SCAFFOLDING.value:
            return DiagramType.SCAFFOLDING
        return None

    @staticmethod
    def _to_format(value: object) -> DiagramFormat:
        if not isinstance(value, str):
            return DiagramFormat.MERMAID
        token = value.strip().lower()
        if token == DiagramFormat.PLANTUML.value:
            return DiagramFormat.PLANTUML
        if token == DiagramFormat.TEXT.value:
            return DiagramFormat.TEXT
        return DiagramFormat.MERMAID
