from __future__ import annotations

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.generators.plantuml.common import dedupe, make_unique_id, quote_label
from arquisys_ai.utils.text import normalize_text


def _actor_category(actor: str) -> str:
    normalized = normalize_text(actor)
    if any(token in normalized for token in ["cliente", "usuario", "user", "comprador"]):
        return "primary"
    if any(token in normalized for token in ["pasarela", "pago", "payment", "banco", "tarjeta"]):
        return "payment"
    if any(token in normalized for token in ["inventario", "stock"]):
        return "inventory"
    if any(token in normalized for token in ["almacen", "warehouse", "despacho", "logistica"]):
        return "warehouse"
    return "external"


def _use_case_category(use_case: str) -> str:
    normalized = normalize_text(use_case)
    if any(token in normalized for token in ["manejar", "error", "rechaz", "sin fondos", "insuficiente", "fallo", "falla"]):
        return "error"
    if any(token in normalized for token in ["stock", "inventario"]):
        return "inventory"
    if any(token in normalized for token in ["pago", "tarjeta", "cobro", "autorizacion"]):
        return "payment"
    if any(token in normalized for token in ["almacen", "despacho", "envio", "notificar"]):
        return "warehouse"
    return "checkout"


def _pick_system_title(analysis: AnalystResult) -> str:
    normalized = normalize_text(analysis.raw_request)
    if any(token in normalized for token in ["checkout", "ecommerce", "e-commerce", "carrito", "pago"]):
        return "Sistema E-commerce"
    return "Sistema"


def generate_use_case_plantuml(analysis: AnalystResult) -> str:
    actors = dedupe(analysis.actors or ["Usuario"])
    use_cases = dedupe(analysis.use_cases or analysis.flow_steps or ["Accion principal"])

    lines: list[str] = ["@startuml", "left to right direction"]

    used_ids: set[str] = set()
    actor_ids: dict[str, str] = {}
    for idx, actor in enumerate(actors, start=1):
        actor_id = make_unique_id(actor, f"A{idx}", used_ids)
        actor_ids[actor] = actor_id
        lines.append(f'actor "{quote_label(actor)}" as {actor_id}')

    lines.append("")
    lines.append(f'package "{_pick_system_title(analysis)}" {{')

    use_case_ids: dict[str, str] = {}
    category_by_id: dict[str, str] = {}
    text_by_id: dict[str, str] = {}

    for idx, use_case in enumerate(use_cases, start=1):
        use_case_id = make_unique_id(use_case, f"UC{idx}", used_ids)
        use_case_ids[use_case] = use_case_id
        category_by_id[use_case_id] = _use_case_category(use_case)
        text_by_id[use_case_id] = use_case
        lines.append(f'  usecase "{quote_label(use_case)}" as {use_case_id}')

    lines.append("}")
    lines.append("")

    main_ids = [
        use_case_ids[item]
        for item in use_cases
        if _use_case_category(item) != "error"
    ]
    if not main_ids:
        main_ids = list(use_case_ids.values())

    payment_ids = [node_id for node_id in use_case_ids.values() if category_by_id[node_id] == "payment"]
    inventory_ids = [node_id for node_id in use_case_ids.values() if category_by_id[node_id] == "inventory"]
    warehouse_ids = [node_id for node_id in use_case_ids.values() if category_by_id[node_id] == "warehouse"]
    error_ids = [node_id for node_id in use_case_ids.values() if category_by_id[node_id] == "error"]

    for prev_id, next_id in zip(main_ids, main_ids[1:]):
        lines.append(f"{prev_id} .> {next_id} : <<include>>")

    for actor in actors:
        actor_id = actor_ids[actor]
        actor_kind = _actor_category(actor)

        if actor_kind == "primary":
            targets = main_ids[:2] if len(main_ids) >= 2 else main_ids
        elif actor_kind == "payment":
            targets = payment_ids
        elif actor_kind == "inventory":
            targets = inventory_ids
        elif actor_kind == "warehouse":
            targets = warehouse_ids
        else:
            targets = main_ids[:1]

        if not targets:
            targets = main_ids[:1]

        for target in targets:
            lines.append(f"{actor_id} --> {target}")

    if error_ids:
        payment_anchor = payment_ids[0] if payment_ids else (main_ids[-1] if main_ids else list(use_case_ids.values())[0])
        inventory_anchor = inventory_ids[0] if inventory_ids else payment_anchor
        for error_id in error_ids:
            error_label = normalize_text(text_by_id.get(error_id, ""))
            anchor = inventory_anchor if "stock" in error_label else payment_anchor
            lines.append(f"{anchor} .> {error_id} : <<extend>>")

    lines.append("@enduml")
    return "\n".join(lines)
