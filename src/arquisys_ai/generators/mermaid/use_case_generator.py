from __future__ import annotations

from arquisys_ai.core.models import AnalystResult
from arquisys_ai.utils.text import mermaid_safe_label, normalize_text, to_identifier


def _dedupe(items: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for item in items:
        clean = item.strip()
        if not clean:
            continue
        key = normalize_text(clean)
        if key in seen:
            continue
        seen.add(key)
        unique.append(clean)
    return unique


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


def generate_use_case_mermaid(analysis: AnalystResult) -> str:
    actors = _dedupe(analysis.actors or ["Usuario"])
    use_cases = _dedupe(analysis.use_cases or analysis.flow_steps or ["Accion principal"])

    lines: list[str] = ["flowchart LR"]
    actor_ids: dict[str, str] = {}

    for idx, actor in enumerate(actors, start=1):
        actor_id = f"A{idx}"
        actor_ids[actor] = actor_id
        actor_label = mermaid_safe_label(actor)
        lines.append(f'    {actor_id}["Actor {actor_label}"]')

    lines.append("")
    lines.append(f'    subgraph SYS["{_pick_system_title(analysis)}"]')
    lines.append("        direction TB")

    use_case_ids: dict[str, str] = {}
    category_by_id: dict[str, str] = {}
    text_by_id: dict[str, str] = {}

    for idx, use_case in enumerate(use_cases, start=1):
        base_id = to_identifier(use_case, fallback_prefix=f"UC{idx}")
        use_case_id = f"UC{idx}{base_id[:6]}"
        use_case_ids[use_case] = use_case_id
        category = _use_case_category(use_case)
        category_by_id[use_case_id] = category
        text_by_id[use_case_id] = use_case
        label = mermaid_safe_label(use_case)
        lines.append(f'        {use_case_id}(["{label}"])')

    lines.append("    end")
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
        lines.append(f"    {prev_id} -. include .-> {next_id}")

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
            lines.append(f"    {actor_id} --> {target}")

    if error_ids:
        payment_anchor = payment_ids[0] if payment_ids else (main_ids[-1] if main_ids else list(use_case_ids.values())[0])
        inventory_anchor = inventory_ids[0] if inventory_ids else payment_anchor

        for error_id in error_ids:
            error_label = normalize_text(text_by_id.get(error_id, ""))
            anchor = inventory_anchor if "stock" in error_label else payment_anchor
            lines.append(f"    {anchor} -. extend .-> {error_id}")

    return "\n".join(lines)
