from __future__ import annotations

import html
import json
import os
import sys
import urllib.request
import zlib
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arquisys_ai.graph.workflow import ArquiSysWorkflow  # noqa: E402


st.set_page_config(page_title="ArquiSys AI Studio", layout="wide")


def inject_styles() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --bg-0: #f6f8f4;
  --bg-1: #e8f4ef;
  --bg-2: #fff7ea;
  --ink: #1f2933;
  --muted: #5d6b79;
  --card: rgba(255, 255, 255, 0.9);
  --line: rgba(14, 116, 144, 0.22);
  --primary: #0e7490;
  --ok: #0f766e;
  --warn: #b45309;
}

.stApp {
  background:
    radial-gradient(1200px 700px at 10% -20%, rgba(14, 116, 144, 0.16), transparent 60%),
    radial-gradient(800px 550px at 90% 0%, rgba(245, 158, 11, 0.2), transparent 55%),
    linear-gradient(155deg, var(--bg-0) 0%, var(--bg-1) 45%, var(--bg-2) 100%);
  color: var(--ink);
}

html, body, [class*="css"] {
  font-family: "Sora", "Segoe UI", sans-serif;
}

.stApp,
.stApp p,
.stApp span,
.stApp div,
.stApp label,
.stApp li,
.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4,
.stApp h5,
.stApp h6,
.stMarkdown,
div[data-testid="stSidebar"] * {
  color: var(--ink) !important;
}

.stTextInput input,
.stTextArea textarea,
div[data-baseweb="select"] > div,
div[data-baseweb="select"] input {
  color: #1f2933 !important;
  background-color: rgba(255, 255, 255, 0.96) !important;
}

code,
pre,
.stCode {
  color: #0f172a !important;
}

.hero {
  border: 1px solid var(--line);
  border-radius: 20px;
  background: linear-gradient(130deg, rgba(255, 255, 255, 0.94), rgba(255, 255, 255, 0.72));
  padding: 1.35rem 1.2rem;
  box-shadow: 0 14px 40px rgba(14, 116, 144, 0.12);
  animation: rise 520ms ease-out;
}

.hero-badge {
  display: inline-block;
  margin-bottom: 0.5rem;
  padding: 0.22rem 0.7rem;
  font-size: 0.74rem;
  font-weight: 700;
  border-radius: 999px;
  border: 1px solid rgba(14, 116, 144, 0.35);
  color: var(--primary);
  background: rgba(14, 116, 144, 0.08);
}

.hero h1 {
  margin: 0 0 0.45rem 0;
  font-size: clamp(1.45rem, 2.6vw, 2.15rem);
}

.hero p {
  margin: 0;
  color: var(--muted);
  font-size: 0.97rem;
  line-height: 1.48;
}

.stat-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 0.8rem 0.9rem;
  background: var(--card);
  backdrop-filter: blur(7px);
  box-shadow: 0 8px 24px rgba(31, 41, 51, 0.08);
  animation: rise 500ms ease-out;
}

.stat-title {
  margin: 0;
  color: var(--muted);
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.stat-value {
  margin: 0.4rem 0 0;
  font-size: 1.02rem;
  font-weight: 700;
}

.tone-ok { color: var(--ok); }
.tone-warn { color: var(--warn); }

.hint-box {
  border: 1px dashed rgba(180, 83, 9, 0.45);
  border-radius: 14px;
  background: rgba(245, 158, 11, 0.08);
  padding: 0.85rem;
}

@keyframes rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .hero { padding: 1.1rem 0.95rem; border-radius: 16px; }
  .stat-card { border-radius: 13px; padding: 0.72rem; }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_card(title: str, value: str, tone: str = "") -> None:
    tone_class = ""
    if tone == "ok":
        tone_class = "tone-ok"
    elif tone == "warn":
        tone_class = "tone-warn"

    st.markdown(
        f"""
<div class="stat-card">
  <p class="stat-title">{html.escape(title)}</p>
  <p class="stat-value {tone_class}">{html.escape(value)}</p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_mermaid(mermaid_code: str, height: int = 520) -> None:
    mermaid_payload = json.dumps(mermaid_code)
    iframe_html = f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <style>
    html, body {{ margin: 0; padding: 0; background: transparent; font-family: "Sora", "Segoe UI", sans-serif; }}
    .canvas {{
      border: 1px solid rgba(14, 116, 144, 0.28);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.92);
      min-height: 280px;
      padding: 0.75rem;
      box-sizing: border-box;
      overflow: auto;
    }}
    .error {{ color: #b91c1c; font-size: 0.92rem; margin-top: 0.6rem; white-space: pre-wrap; }}
    svg text {{ fill: #0f172a !important; }}
  </style>
</head>
<body>
  <div class=\"canvas\">
    <pre id=\"graph\" class=\"mermaid\"></pre>
    <div id=\"error\" class=\"error\"></div>
  </div>
  <script src=\"https://cdn.jsdelivr.net/npm/mermaid@10.9.5/dist/mermaid.min.js\"></script>
  <script>
    const code = {mermaid_payload};
    const graphEl = document.getElementById("graph");
    const errorEl = document.getElementById("error");
    graphEl.textContent = code;

    try {{
      mermaid.initialize({{
        startOnLoad: false,
        securityLevel: "loose",
        theme: "base",
        themeVariables: {{
          fontFamily: "Sora, Segoe UI, sans-serif",
          textColor: "#0f172a",
          primaryColor: "#d8f4ef",
          primaryTextColor: "#1f2933",
          primaryBorderColor: "#0e7490",
          actorBkg: "#e8f4ff",
          actorBorder: "#0e7490",
          actorTextColor: "#0f172a",
          noteBkgColor: "#fff4db",
          noteTextColor: "#0f172a",
          labelTextColor: "#0f172a",
          lineColor: "#1f2933",
          secondaryColor: "#fff4db",
          tertiaryColor: "#eef6ff"
        }}
      }});
      mermaid.run({{ nodes: [graphEl] }});
    }} catch (err) {{
      errorEl.textContent = "No se pudo renderizar Mermaid. Revisa el codigo en la pestana de salida.\\n" + String(err);
    }}
  </script>
</body>
</html>
    """
    components.html(iframe_html, height=height, scrolling=True)


def _encode6bit(value: int) -> str:
    if value < 10:
        return chr(48 + value)
    value -= 10
    if value < 26:
        return chr(65 + value)
    value -= 26
    if value < 26:
        return chr(97 + value)
    value -= 26
    if value == 0:
        return "-"
    if value == 1:
        return "_"
    return "?"


def _append3bytes(b1: int, b2: int, b3: int) -> str:
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F
    return "".join(_encode6bit(bit & 0x3F) for bit in [c1, c2, c3, c4])


def _plantuml_encode(text: str) -> str:
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(text.encode("utf-8")) + compressor.flush()

    chunks: list[str] = []
    for idx in range(0, len(compressed), 3):
        b1 = compressed[idx]
        b2 = compressed[idx + 1] if idx + 1 < len(compressed) else 0
        b3 = compressed[idx + 2] if idx + 2 < len(compressed) else 0
        chunks.append(_append3bytes(b1, b2, b3))
    return "".join(chunks)


def _normalize_plantuml_server() -> str:
    raw = os.getenv("PLANTUML_SERVER_URL", "https://www.plantuml.com/plantuml").strip().rstrip("/")
    lowered = raw.lower()

    for suffix in ["/png", "/svg", "/txt", "/uml", "/img"]:
        if lowered.endswith(suffix):
            raw = raw[: -len(suffix)]
            lowered = raw.lower()
            break

    if not lowered.endswith("/plantuml"):
        raw = f"{raw}/plantuml"
    return raw


def render_plantuml(plantuml_code: str) -> None:
    encoded = _plantuml_encode(plantuml_code)
    server_base = _normalize_plantuml_server()
    url = f"{server_base}/png/{encoded}"

    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            image_bytes = response.read()
        if not image_bytes:
            raise ValueError("PlantUML image is empty")
        st.image(image_bytes, use_container_width=True)
    except Exception:
        st.warning(
            "No se pudo renderizar PlantUML desde el servidor configurado. "
            "Se muestra el codigo para que puedas renderizarlo manualmente."
        )
        st.code(plantuml_code, language="plantuml")


def extract_fenced_sections(markdown_text: str, fence_name: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_heading = ""
    inside_block = False
    block_lines: list[str] = []
    block_title = ""
    expected_fence = f"```{fence_name.lower()}"

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if not inside_block:
            if stripped.startswith("## "):
                current_heading = stripped[3:].strip()
            elif stripped.startswith("### "):
                current_heading = stripped[4:].strip()

            if stripped.lower().startswith(expected_fence):
                inside_block = True
                block_lines = []
                block_title = current_heading or f"Diagrama {len(sections) + 1}"
            continue

        if stripped.startswith("```"):
            code = "\n".join(block_lines).strip()
            if code:
                sections.append((block_title, code))
            inside_block = False
            block_lines = []
            block_title = ""
            continue

        block_lines.append(line)

    return sections


def extract_mermaid_sections(markdown_text: str) -> list[tuple[str, str]]:
    return extract_fenced_sections(markdown_text, "mermaid")


def extract_plantuml_sections(markdown_text: str) -> list[tuple[str, str]]:
    return extract_fenced_sections(markdown_text, "plantuml")


def compose_request(
    *,
    base_request: str,
    standard: str,
    diagram_type: str,
    output_format: str,
    actors: str,
    use_cases: str,
    classes: str,
    flow_steps: str,
    participants: str,
    interactions: str,
    entities: str,
    relationships: str,
    c4_people: str,
    c4_systems: str,
    c4_containers: str,
    c4_relations: str,
    stack: str,
) -> str:
    parts: list[str] = [base_request.strip()]

    if standard != "Auto":
        parts.append(f"Estandar: {standard}")
    if diagram_type != "Auto":
        parts.append(f"Tipo de salida: {diagram_type}")
    if output_format != "Auto":
        parts.append(f"Formato: {output_format}")

    if actors.strip():
        parts.append(f"Actores: {actors.strip()}")
    if use_cases.strip():
        parts.append(f"Casos de uso: {use_cases.strip()}")
    if classes.strip():
        parts.append(f"Clases: {classes.strip()}")
    if flow_steps.strip():
        parts.append(f"Pasos: {flow_steps.strip()}")
    if participants.strip():
        parts.append(f"Participantes: {participants.strip()}")
    if interactions.strip():
        parts.append(f"Interacciones: {interactions.strip()}")
    if entities.strip():
        parts.append(f"Entidades ER: {entities.strip()}")
    if relationships.strip():
        parts.append(f"Relaciones ER: {relationships.strip()}")
    if c4_people.strip():
        parts.append(f"Personas C4: {c4_people.strip()}")
    if c4_systems.strip():
        parts.append(f"Sistemas C4: {c4_systems.strip()}")
    if c4_containers.strip():
        parts.append(f"Contenedores: {c4_containers.strip()}")
    if c4_relations.strip():
        parts.append(f"Relaciones C4: {c4_relations.strip()}")
    if stack.strip():
        parts.append(f"Stack: {stack.strip()}")

    return "\n".join([part for part in parts if part])


def set_template(template: str) -> None:
    st.session_state["draft_request"] = template


_DIAGRAM_TYPE_OPTIONS = [
    "Seleccionar...",
    "paquete documentacion",
    "casos de uso",
    "clases",
    "flujo",
    "secuencia",
    "ER",
    "C4 contexto",
    "C4 contenedores",
    "QA automatico",
    "Scaffolding",
]

_STANDARD_OPTIONS = ["Seleccionar...", "UML", "BPMN", "ER", "C4"]

_CLARIFICATION_SCHEMA = {
    "diagram_type": {
        "label": "Tipo de salida",
        "widget": "select",
        "options": _DIAGRAM_TYPE_OPTIONS,
        "prefix": "Tipo de salida",
    },
    "standard": {
        "label": "Estandar",
        "widget": "select",
        "options": _STANDARD_OPTIONS,
        "prefix": "Estandar",
    },
    "actors": {"label": "Actores", "widget": "text", "prefix": "Actores"},
    "use_cases": {"label": "Casos de uso", "widget": "text", "prefix": "Casos de uso"},
    "classes": {"label": "Clases", "widget": "text", "prefix": "Clases"},
    "flow_steps": {"label": "Pasos", "widget": "text", "prefix": "Pasos"},
    "participants": {"label": "Participantes", "widget": "text", "prefix": "Participantes"},
    "sequence_steps": {"label": "Interacciones", "widget": "textarea", "prefix": "Interacciones"},
    "entities": {"label": "Entidades ER", "widget": "text", "prefix": "Entidades ER"},
    "relationships": {"label": "Relaciones ER", "widget": "text", "prefix": "Relaciones ER"},
    "c4_people": {"label": "Personas C4", "widget": "text", "prefix": "Personas C4"},
    "c4_systems": {"label": "Sistemas C4", "widget": "text", "prefix": "Sistemas C4"},
    "c4_containers": {"label": "Contenedores", "widget": "text", "prefix": "Contenedores"},
    "c4_relations": {"label": "Relaciones C4", "widget": "textarea", "prefix": "Relaciones C4"},
    "stack": {"label": "Stack", "widget": "text", "prefix": "Stack"},
    "qa_scope": {"label": "Casos de uso o flujo para QA", "widget": "text", "prefix": "Casos de uso"},
    "scaffolding_scope": {
        "label": "Casos de uso o entidades para scaffolding",
        "widget": "text",
        "prefix": "Casos de uso",
    },
}


def render_clarification_form(analysis: dict[str, object]) -> None:
    missing_info = analysis.get("missing_info", [])
    if not isinstance(missing_info, list) or not missing_info:
        return

    st.markdown("### Responder preguntas del Analista")
    st.caption(
        "Completa los datos faltantes aqui y pulsa 'Reintentar'. "
        "Tambien puedes responder en los expanders superiores y volver a generar."
    )

    answers: dict[str, str] = {}
    with st.form("clarification_form", clear_on_submit=False):
        for key in missing_info:
            if not isinstance(key, str):
                continue

            config = _CLARIFICATION_SCHEMA.get(
                key,
                {"label": key.replace("_", " ").title(), "widget": "text", "prefix": key},
            )
            widget = config.get("widget", "text")
            label = str(config.get("label", key))
            field_key = f"clar_{key}"

            if widget == "select":
                options = config.get("options", ["Seleccionar..."])
                choice = st.selectbox(label, options=options, key=field_key)
                answers[key] = "" if choice == "Seleccionar..." else str(choice)
            elif widget == "textarea":
                answers[key] = st.text_area(label, key=field_key, height=92).strip()
            else:
                answers[key] = st.text_input(label, key=field_key).strip()

        submit_answers = st.form_submit_button("Reintentar con respuestas", use_container_width=True)

    if not submit_answers:
        return

    additional_lines: list[str] = []
    for key in missing_info:
        if not isinstance(key, str):
            continue
        value = answers.get(key, "").strip()
        if not value:
            continue
        prefix = str(_CLARIFICATION_SCHEMA.get(key, {}).get("prefix", key))
        additional_lines.append(f"{prefix}: {value}")

    if not additional_lines:
        st.warning("Completa al menos una respuesta antes de reintentar.")
        return

    previous_request = st.session_state.get("last_request", "")
    merged_request = "\n".join([part for part in [str(previous_request).strip(), *additional_lines] if part])

    result = ArquiSysWorkflow().run(merged_request)
    st.session_state["last_request"] = merged_request
    st.session_state["last_result"] = result.to_dict()
    st.rerun()


def app() -> None:
    inject_styles()

    if "draft_request" not in st.session_state:
        st.session_state["draft_request"] = (
            "Necesito un diagrama UML de casos de uso en Mermaid. "
            "Actores: Cliente, Administrador. "
            "Casos de uso: Iniciar sesion, Comprar producto"
        )

    with st.sidebar:
        st.markdown("### Plantillas rapidas")
        if st.button("Caso de uso ecommerce", use_container_width=True):
            set_template(
                "Necesito un diagrama UML de casos de uso en Mermaid. "
                "Actores: Cliente, Administrador. "
                "Casos de uso: Iniciar sesion, Registrar pedido, Pagar pedido"
            )
            st.rerun()

        if st.button("Secuencia compra", use_container_width=True):
            set_template(
                "Necesito un diagrama de secuencia UML en Mermaid. "
                "Participantes: Cliente, API, Base de Datos. "
                "Interacciones: Cliente->>API: Crear pedido, API->>Base de Datos: Guardar pedido, API-->>Cliente: Confirmar"
            )
            st.rerun()

        if st.button("ER basico", use_container_width=True):
            set_template(
                "Necesito un diagrama ER en Mermaid. "
                "Entidades ER: Usuario(id, nombre), Pedido(id, total). "
                "Relaciones ER: Usuario->Pedido: realiza"
            )
            st.rerun()

        if st.button("C4 contexto", use_container_width=True):
            set_template(
                "Necesito un diagrama C4 Context en Mermaid. "
                "Personas C4: Cliente, Operador. "
                "Sistemas C4: Plataforma Ecommerce, Pasarela de Pago"
            )
            st.rerun()

        if st.button("QA automatico", use_container_width=True):
            set_template("Quiero QA automatico. Casos de uso: Iniciar sesion, Comprar producto")
            st.rerun()

        if st.button("Scaffolding", use_container_width=True):
            set_template(
                "Quiero scaffolding para ecommerce. "
                "Casos de uso: Registrar pedido, Pagar pedido. "
                "Stack: FastAPI, PostgreSQL, React"
            )
            st.rerun()

        st.markdown("---")
        st.caption("Sprint 2 ampliado: diagramacion + artefactos QA + scaffolding con dos agentes.")

    st.markdown(
        """
<div class="hero">
  <span class="hero-badge">SPRINT 2 - ALCANCE AMPLIADO</span>
  <h1>ArquiSys AI Studio</h1>
  <p>
    El Analista extrae contexto y el Arquitecto entrega Mermaid o artefactos textuales.
    Puedes generar: UML, Secuencia, ER, C4, QA automatico y scaffolding base.
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    with st.form("workflow_form", clear_on_submit=False):
        base_request = st.text_area(
            "Solicitud principal",
            value=st.session_state.get("draft_request", ""),
            height=170,
            placeholder="Ejemplo: necesito un diagrama de secuencia...",
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            standard = st.selectbox("Estandar", ["Auto", "UML", "BPMN", "ER", "C4"])
        with c2:
            diagram_type = st.selectbox(
                "Tipo de salida",
                [
                    "Auto",
                    "paquete documentacion",
                    "casos de uso",
                    "clases",
                    "flujo",
                    "secuencia",
                    "ER",
                    "C4 contexto",
                    "C4 contenedores",
                    "QA automatico",
                    "Scaffolding",
                ],
            )
        with c3:
            output_format = st.selectbox("Formato", ["Auto", "Mermaid", "PlantUML", "Texto"])

        with st.expander("Contexto funcional"):
            cfa, cfb = st.columns(2)
            with cfa:
                actors = st.text_input("Actores", placeholder="Cliente, Administrador")
                use_cases = st.text_input("Casos de uso", placeholder="Iniciar sesion, Comprar producto")
            with cfb:
                classes = st.text_input("Clases", placeholder="Usuario(id, nombre), Pedido(id, total)")
                flow_steps = st.text_input("Pasos de flujo", placeholder="Recibir pedido, Validar pago, Confirmar compra")

        with st.expander("Secuencia y datos"):
            csa, csb = st.columns(2)
            with csa:
                participants = st.text_input("Participantes", placeholder="Cliente, API, Base de Datos")
                interactions = st.text_input(
                    "Interacciones",
                    placeholder="Cliente->>API: Crear pedido, API->>Base de Datos: Guardar pedido",
                )
            with csb:
                entities = st.text_input("Entidades ER", placeholder="Usuario(id, nombre), Pedido(id, total)")
                relationships = st.text_input("Relaciones ER", placeholder="Usuario->Pedido: realiza")

        with st.expander("C4 y entrega"):
            cca, ccb = st.columns(2)
            with cca:
                c4_people = st.text_input("Personas C4", placeholder="Cliente, Operador")
                c4_systems = st.text_input("Sistemas C4", placeholder="Plataforma Ecommerce, Pasarela de Pago")
                c4_containers = st.text_input("Contenedores", placeholder="Web App(React), API(FastAPI), DB(PostgreSQL)")
            with ccb:
                c4_relations = st.text_input(
                    "Relaciones C4",
                    placeholder="Cliente->Web App: Usa, Web App->API: Consume",
                )
                stack = st.text_input("Stack", placeholder="FastAPI, PostgreSQL, React")

        submitted = st.form_submit_button("Analizar y generar", use_container_width=True)

    if submitted:
        if not base_request.strip():
            st.warning("Escribe una solicitud antes de ejecutar el flujo.")
        else:
            final_request = compose_request(
                base_request=base_request,
                standard=standard,
                diagram_type=diagram_type,
                output_format=output_format,
                actors=actors,
                use_cases=use_cases,
                classes=classes,
                flow_steps=flow_steps,
                participants=participants,
                interactions=interactions,
                entities=entities,
                relationships=relationships,
                c4_people=c4_people,
                c4_systems=c4_systems,
                c4_containers=c4_containers,
                c4_relations=c4_relations,
                stack=stack,
            )
            workflow = ArquiSysWorkflow()
            result = workflow.run(final_request)

            st.session_state["draft_request"] = base_request
            st.session_state["last_request"] = final_request
            st.session_state["last_result"] = result.to_dict()

    last_result = st.session_state.get("last_result")
    if not last_result:
        st.info("Completa la solicitud y pulsa 'Analizar y generar' para iniciar la prueba.")
        return

    analysis = last_result["analysis"]
    architecture = last_result["architecture"]

    st.markdown("### Resultado del flujo")
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        render_card("Tipo detectado", analysis.get("diagram_type") or "Sin definir")
    with r2:
        render_card("Estandar", analysis.get("standard") or "Sin definir")
    with r3:
        render_card("Formato", analysis.get("diagram_format") or "Sin definir")
    with r4:
        ready = bool(analysis.get("ready_for_architect"))
        render_card("Estado", "Listo para Arquitecto" if ready else "Falta contexto", tone="ok" if ready else "warn")

    if architecture is None:
        questions = analysis.get("clarifying_questions", [])
        st.markdown("### Preguntas del Analista")
        if questions:
            st.markdown('<div class="hint-box">', unsafe_allow_html=True)
            for question in questions:
                st.markdown(f"- {question}")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("Aun falta informacion, pero no se generaron preguntas guiadas.")

        raw_request = str(analysis.get("raw_request", ""))
        if "paquete de documentacion" in raw_request.lower() or "documentacion visual" in raw_request.lower():
            st.info(
                "Para solicitudes de paquete completo, el analista intenta inferir y generar todo automaticamente. "
                "Si aun falta contexto, responde aqui y reintenta en un clic."
            )

        render_clarification_form(analysis)

        st.code(st.session_state.get("last_request", ""), language="text")
        return

    output_format = architecture.get("diagram_format", "mermaid")

    if output_format == "mermaid":
        tabs = st.tabs(["Vista previa", "Codigo Mermaid", "JSON"])
        with tabs[0]:
            st.caption("Vista previa usando Mermaid 10.9.5")
            render_mermaid(architecture["code"])
        with tabs[1]:
            st.code(architecture["code"], language="mermaid")
        with tabs[2]:
            st.json(last_result)
    elif output_format == "plantuml":
        tabs = st.tabs(["Vista previa", "Codigo PlantUML", "JSON"])
        with tabs[0]:
            st.info(
                "Vista previa PlantUML usando servidor remoto/local. "
                "Puedes cambiar servidor con la variable PLANTUML_SERVER_URL."
            )
            render_plantuml(architecture["code"])
        with tabs[1]:
            st.code(architecture["code"], language="plantuml")
        with tabs[2]:
            st.json(last_result)
    else:
        text_output = str(architecture.get("code", ""))
        mermaid_sections = extract_mermaid_sections(text_output)
        plantuml_sections = extract_plantuml_sections(text_output)

        if mermaid_sections:
            tabs = st.tabs(["Diagramas", "Salida", "JSON"])
            with tabs[0]:
                options = [f"{idx}. {title}" for idx, (title, _) in enumerate(mermaid_sections, start=1)]
                selected = st.selectbox("Selecciona diagrama", options=options, key="pkg_mermaid_selector")
                selected_index = options.index(selected)
                selected_title, selected_code = mermaid_sections[selected_index]
                st.caption(selected_title)
                render_mermaid(selected_code, height=680)
                st.code(selected_code, language="mermaid")

            with tabs[1]:
                st.code(text_output, language="markdown")
            with tabs[2]:
                st.json(last_result)
        elif plantuml_sections:
            tabs = st.tabs(["Diagramas", "Salida", "JSON"])
            with tabs[0]:
                options = [f"{idx}. {title}" for idx, (title, _) in enumerate(plantuml_sections, start=1)]
                selected = st.selectbox("Selecciona diagrama", options=options, key="pkg_plantuml_selector")
                selected_index = options.index(selected)
                selected_title, selected_code = plantuml_sections[selected_index]
                st.caption(selected_title)
                st.info(
                    "Vista previa PlantUML usando servidor remoto/local. "
                    "Puedes cambiar servidor con la variable PLANTUML_SERVER_URL."
                )
                render_plantuml(selected_code)
                st.code(selected_code, language="plantuml")

            with tabs[1]:
                st.code(text_output, language="markdown")
            with tabs[2]:
                st.json(last_result)
        else:
            tabs = st.tabs(["Salida", "JSON"])
            with tabs[0]:
                st.code(text_output, language="markdown")
            with tabs[1]:
                st.json(last_result)

    warnings = architecture.get("warnings", [])
    if warnings:
        st.warning(" | ".join(warnings))


if __name__ == "__main__":
    app()
