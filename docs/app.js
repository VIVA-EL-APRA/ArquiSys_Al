const requestEl = document.getElementById("request");
const diagramTypeEl = document.getElementById("diagramType");
const outputFormatEl = document.getElementById("outputFormat");
const plantumlServerEl = document.getElementById("plantumlServer");
const generateBtn = document.getElementById("generateBtn");

const analysisEl = document.getElementById("analysis");
const questionsEl = document.getElementById("questions");
const outputEl = document.getElementById("output");

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "loose",
  theme: "base",
  themeVariables: {
    fontFamily: "Segoe UI, Arial, sans-serif",
    textColor: "#0f172a",
    primaryColor: "#d8f4ef",
    primaryTextColor: "#1f2933",
    primaryBorderColor: "#0e7490",
    lineColor: "#1f2933",
    noteTextColor: "#0f172a",
    actorTextColor: "#0f172a",
    labelTextColor: "#0f172a",
  },
});

generateBtn.addEventListener("click", runPipeline);

runPipeline();

function runPipeline() {
  const request = requestEl.value.trim();
  if (!request) {
    analysisEl.innerHTML = "<div class='error'>Escribe una solicitud antes de generar.</div>";
    questionsEl.innerHTML = "";
    outputEl.innerHTML = "";
    return;
  }

  const analysis = analyzeRequest(request, diagramTypeEl.value, outputFormatEl.value);
  renderAnalysis(analysis);

  if (!analysis.readyForArchitect) {
    renderQuestions(analysis);
    outputEl.innerHTML = "";
    return;
  }

  questionsEl.innerHTML = "";
  renderOutput(analysis);
}

function renderAnalysis(analysis) {
  analysisEl.innerHTML = `
    <h2>Resultado del analisis</h2>
    <div class="grid">
      <div class="metric"><div class="title">Tipo detectado</div><div class="value">${escapeHtml(analysis.diagramType)}</div></div>
      <div class="metric"><div class="title">Formato</div><div class="value">${escapeHtml(analysis.diagramFormat)}</div></div>
      <div class="metric"><div class="title">Estado</div><div class="value">${analysis.readyForArchitect ? "Listo" : "Falta contexto"}</div></div>
      <div class="metric"><div class="title">Actores/Participantes</div><div class="value">${analysis.actors.length + analysis.participants.length}</div></div>
    </div>
  `;
}

function renderQuestions(analysis) {
  const questions = analysis.clarifyingQuestions || [];
  if (!questions.length) {
    questionsEl.innerHTML = "";
    return;
  }

  questionsEl.innerHTML = `
    <div class="hint">
      <h3>Preguntas del analista</h3>
      <ul>${questions.map((q) => `<li>${escapeHtml(q)}</li>`).join("")}</ul>
      <p>Completa la solicitud con esos datos y vuelve a generar.</p>
    </div>
  `;
}

function renderOutput(analysis) {
  outputEl.innerHTML = "<h2>Salida</h2>";

  if (analysis.diagramType === "doc_package") {
    const sections = generatePackage(analysis);
    sections.forEach((section, index) => renderSection(section, index));
    return;
  }

  const section = generateSingleSection(analysis.diagramType, analysis.diagramFormat, analysis);
  renderSection(section, 0);
}

function renderSection(section, index) {
  const sectionCard = document.createElement("article");
  sectionCard.className = "section-card";
  sectionCard.innerHTML = `<h3>${escapeHtml(section.title)}</h3>`;

  const host = document.createElement("div");
  host.className = "diagram-host";
  sectionCard.appendChild(host);

  if (section.format === "mermaid") {
    const pre = document.createElement("pre");
    pre.className = "mermaid";
    pre.textContent = section.code;
    host.appendChild(pre);

    mermaid
      .run({ nodes: [pre] })
      .catch((error) => {
        host.innerHTML = `<div class='error'>Error Mermaid: ${escapeHtml(String(error))}</div>`;
      });
  } else {
    const img = document.createElement("img");
    img.className = "plantuml-preview";
    img.alt = section.title;
    img.src = buildPlantUmlImageUrl(section.code, plantumlServerEl.value.trim());
    img.onerror = () => {
      host.innerHTML = "<div class='error'>No se pudo renderizar PlantUML. Revisa servidor o conexion.</div>";
    };
    host.appendChild(img);
  }

  const codeBlock = document.createElement("pre");
  codeBlock.textContent = section.code;
  sectionCard.appendChild(codeBlock);
  outputEl.appendChild(sectionCard);
}

function generatePackage(analysis) {
  const titles = {
    use_case: "Casos de Uso (UML)",
    sequence: "Secuencia (UML)",
    flow: "Flujo de Proceso (BPMN-like)",
    er: "Entidad-Relacion (ER)",
  };

  const sections = [];
  for (const target of analysis.packageTargets) {
    sections.push(generateSingleSection(target, analysis.diagramFormat, analysis, titles[target] || target));
  }
  return sections;
}

function generateSingleSection(diagramType, format, analysis, titleOverride = "") {
  const titleByType = {
    use_case: "Diagrama de Casos de Uso",
    sequence: "Diagrama de Secuencia",
    flow: "Diagrama de Flujo",
    er: "Diagrama Entidad-Relacion",
  };

  const title = titleOverride || titleByType[diagramType] || diagramType;
  let code = "";

  if (format === "plantuml") {
    if (diagramType === "use_case") code = generateUseCasePlantUml(analysis);
    if (diagramType === "sequence") code = generateSequencePlantUml(analysis);
    if (diagramType === "flow") code = generateFlowPlantUml(analysis);
    if (diagramType === "er") code = generateErPlantUml(analysis);
  } else {
    if (diagramType === "use_case") code = generateUseCaseMermaid(analysis);
    if (diagramType === "sequence") code = generateSequenceMermaid(analysis);
    if (diagramType === "flow") code = generateFlowMermaid(analysis);
    if (diagramType === "er") code = generateErMermaid(analysis);
  }

  return { title, format, code };
}

function analyzeRequest(request, selectedType, selectedFormat) {
  const normalized = normalizeText(request);
  const packageTargets = inferPackageTargets(normalized);

  let diagramType = inferDiagramType(normalized, selectedType, packageTargets);
  const diagramFormat = inferFormat(normalized, selectedFormat);

  let actors = extractListAfterLabels(request, ["Actores", "Actor", "Usuarios"]);
  let useCases = extractListAfterLabels(request, ["Casos de uso", "Acciones", "Funciones"]);
  let flowSteps = extractListAfterLabels(request, ["Pasos", "Flujo", "Proceso", "Actividades"]);
  const participantsRaw = extractListAfterLabels(request, ["Participantes", "Intervinientes"]);
  const interactions = extractListAfterLabels(request, ["Interacciones", "Mensajes", "Mensajes de secuencia"]);
  let entities = extractListAfterLabels(request, ["Entidades ER", "Entidades", "Tablas"]);
  let relationships = extractListAfterLabels(request, ["Relaciones ER", "Relaciones", "Cardinalidades"]);

  if (!actors.length) actors = inferActorsFromContext(normalized);
  if (!flowSteps.length) flowSteps = inferFlowStepsFromContext(normalized);
  if (!useCases.length) useCases = flowSteps.slice();

  let participants = participantsRaw.length ? participantsRaw : inferParticipantsFromContext(actors, normalized);
  let sequenceSteps = interactions.length
    ? interactions
    : inferSequenceStepsFromContext(participants, flowSteps, normalized);

  if (!entities.length) entities = inferEntitiesFromContext(normalized);
  if (!relationships.length) relationships = inferRelationshipsFromEntities(entities);

  if (diagramType === "doc_package" && packageTargets.length === 0) {
    diagramType = "doc_package";
  }

  const analysis = {
    rawRequest: request,
    diagramType,
    diagramFormat,
    packageTargets: packageTargets.length ? packageTargets : ["use_case", "sequence", "flow", "er"],
    actors,
    useCases,
    flowSteps,
    participants,
    sequenceSteps,
    entities,
    relationships,
    missingInfo: [],
    clarifyingQuestions: [],
    readyForArchitect: false,
  };

  analysis.missingInfo = detectMissingInfo(analysis);
  analysis.clarifyingQuestions = buildClarifyingQuestions(analysis.missingInfo);
  analysis.readyForArchitect = analysis.missingInfo.length === 0;
  return analysis;
}

function detectMissingInfo(analysis) {
  const missing = [];
  if (!analysis.diagramType || analysis.diagramType === "auto") {
    missing.push("diagram_type");
    return missing;
  }

  const ensureForType = (type) => {
    if (type === "use_case") {
      if (!analysis.actors.length) missing.push("actors");
      if (!analysis.useCases.length) missing.push("use_cases");
    }
    if (type === "sequence") {
      if (analysis.participants.length < 2) missing.push("participants");
      if (!analysis.sequenceSteps.length) missing.push("sequence_steps");
    }
    if (type === "flow") {
      if (analysis.flowSteps.length < 2) missing.push("flow_steps");
    }
    if (type === "er") {
      if (!analysis.entities.length) missing.push("entities");
    }
  };

  if (analysis.diagramType === "doc_package") {
    analysis.packageTargets.forEach(ensureForType);
  } else {
    ensureForType(analysis.diagramType);
  }

  return dedupeBy(missing, (value) => value);
}

function buildClarifyingQuestions(missingInfo) {
  const map = {
    diagram_type: "Que salida necesitas: casos de uso, secuencia, flujo/BPMN, ER o paquete completo?",
    actors: "Quienes son los actores principales?",
    use_cases: "Que casos de uso o acciones principales quieres modelar?",
    participants: "Que participantes intervienen en la secuencia (minimo dos)?",
    sequence_steps: "Que mensajes o interacciones quieres en secuencia?",
    flow_steps: "Cuales son los pasos del flujo en orden?",
    entities: "Que entidades/tablas incluye el modelo ER?",
  };
  return missingInfo.map((item) => map[item]).filter(Boolean);
}

function inferDiagramType(normalized, selectedType, packageTargets) {
  if (selectedType && selectedType !== "auto") return selectedType;
  if (isPackageRequest(normalized, packageTargets)) return "doc_package";
  if (containsAny(normalized, ["caso de uso", "casos de uso", "use case"])) return "use_case";
  if (containsAny(normalized, ["secuencia", "sequence"])) return "sequence";
  if (containsAny(normalized, ["bpmn", "flujo", "workflow", "proceso"])) return "flow";
  if (containsAny(normalized, ["entidad relacion", "entity relationship", "diagrama er", "erd"])) return "er";
  return "auto";
}

function inferFormat(normalized, selectedFormat) {
  if (selectedFormat && selectedFormat !== "auto") return selectedFormat;
  if (normalized.includes("plantuml")) return "plantuml";
  return "mermaid";
}

function inferPackageTargets(normalized) {
  const targets = [];
  if (containsAny(normalized, ["caso de uso", "casos de uso", "use case"])) targets.push("use_case");
  if (containsAny(normalized, ["secuencia", "sequence"])) targets.push("sequence");
  if (containsAny(normalized, ["bpmn", "flujo", "workflow", "proceso"])) targets.push("flow");
  if (containsAny(normalized, ["entidad relacion", "entity relationship", "diagrama er", "erd"])) targets.push("er");
  return dedupeBy(targets, (value) => value);
}

function isPackageRequest(normalized, packageTargets) {
  const explicit = containsAny(normalized, [
    "paquete de documentacion",
    "documentacion visual completo",
    "documentacion completa",
    "set completo de diagramas",
    "todos los diagramas",
  ]);
  return explicit || packageTargets.length >= 3;
}

function inferActorsFromContext(normalized) {
  const actors = [];
  if (containsAny(normalized, ["usuario", "cliente", "comprador"])) actors.push("Usuario");
  if (containsAny(normalized, ["pasarela", "pago", "gateway"])) actors.push("Pasarela de Pagos");
  if (containsAny(normalized, ["inventario", "stock"])) actors.push("Sistema de Inventario");
  if (containsAny(normalized, ["almacen", "warehouse"])) actors.push("Almacen");
  return dedupeBy(actors, (item) => normalizeText(item));
}

function inferFlowStepsFromContext(normalized) {
  const steps = [];
  if (containsAny(normalized, ["carrito"])) steps.push("Revisar carrito");
  if (containsAny(normalized, ["checkout"])) steps.push("Iniciar checkout");
  if (containsAny(normalized, ["stock", "inventario"])) steps.push("Validar stock disponible");
  if (containsAny(normalized, ["pago", "pasarela", "tarjeta"])) steps.push("Solicitar autorizacion de pago");
  if (containsAny(normalized, ["aprobado", "aprueba el pago"])) steps.push("Confirmar pago aprobado");
  if (containsAny(normalized, ["notifica al almacen", "notificar al almacen", "almacen"])) steps.push("Notificar al almacen");
  if (containsAny(normalized, ["sin fondos", "tarjeta sin fondos"])) steps.push("Manejar pago rechazado por fondos");
  if (containsAny(normalized, ["falta de stock", "stock insuficiente"])) steps.push("Manejar falta de stock");
  return dedupeBy(steps, (item) => normalizeText(item));
}

function inferParticipantsFromContext(actors, normalized) {
  const participants = [...actors];
  if (!participants.length) participants.push("Usuario", "Sistema Checkout");
  if (!participants.some((item) => normalizeText(item).includes("checkout"))) {
    participants.splice(1, 0, "Sistema Checkout");
  }
  if (participants.length < 2) participants.push("Sistema");
  return dedupeBy(participants, (item) => normalizeText(item));
}

function inferSequenceStepsFromContext(participants, flowSteps, normalized) {
  const p = participants.slice();
  if (p.length < 2) p.push("Sistema Checkout");
  const user = p[0];
  const checkout = p.find((item) => normalizeText(item).includes("checkout")) || p[1];
  const payment = p.find((item) => containsAny(normalizeText(item), ["pasarela", "pago"])) || "Pasarela de Pagos";
  const inventory = p.find((item) => containsAny(normalizeText(item), ["inventario", "stock"])) || "Sistema de Inventario";
  const warehouse = p.find((item) => normalizeText(item).includes("almacen")) || "Almacen";

  const steps = [
    `${user}->>${checkout}: Revisar carrito e iniciar checkout`,
    `${checkout}->>${inventory}: Validar stock`,
    `${inventory}-->>${checkout}: Stock confirmado`,
    `${checkout}->>${payment}: Autorizar pago`,
    `${payment}-->>${checkout}: Pago aprobado`,
    `${checkout}->>${warehouse}: Notificar preparacion`,
    `${checkout}-->>${user}: Confirmar pedido`,
  ];

  if (containsAny(normalized, ["sin fondos", "tarjeta sin fondos"])) {
    steps.push(`${payment}-->>${checkout}: Tarjeta sin fondos`);
    steps.push(`${checkout}-->>${user}: Informar rechazo de pago`);
  }
  if (containsAny(normalized, ["falta de stock", "stock insuficiente"])) {
    steps.push(`${inventory}-->>${checkout}: Stock insuficiente`);
    steps.push(`${checkout}-->>${user}: Informar falta de stock`);
  }

  if (!flowSteps.length) return steps;
  return dedupeBy(steps, (item) => item.toLowerCase());
}

function inferEntitiesFromContext(normalized) {
  const entities = [];
  if (containsAny(normalized, ["usuario", "cliente"])) entities.push("Usuario(id, email)");
  if (normalized.includes("carrito")) entities.push("Carrito(id, estado)");
  if (containsAny(normalized, ["pedido", "checkout"])) entities.push("Pedido(id, estado, total)");
  if (normalized.includes("pago")) entities.push("Pago(id, estado, monto)");
  if (containsAny(normalized, ["inventario", "stock"])) entities.push("Inventario(id, stockDisponible)");
  if (normalized.includes("almacen")) entities.push("NotificacionAlmacen(id, estado)");
  if (entities.length < 2) entities.push("Pedido(id)", "Pago(id)");
  return dedupeBy(entities, (item) => normalizeText(item));
}

function inferRelationshipsFromEntities(entities) {
  const names = entities.map((entry) => entry.split("(")[0].trim());
  const by = (text) => names.find((name) => normalizeText(name) === normalizeText(text));
  const relationships = [];

  if (by("Usuario") && by("Carrito")) relationships.push("Usuario->Carrito: posee");
  if (by("Carrito") && by("Pedido")) relationships.push("Carrito->Pedido: genera");
  if (by("Pedido") && by("Pago")) relationships.push("Pedido->Pago: registra");
  if (by("Pedido") && by("NotificacionAlmacen")) relationships.push("Pedido->NotificacionAlmacen: notifica");

  if (!relationships.length && names.length >= 2) relationships.push(`${names[0]}->${names[1]}: relacion`);
  return relationships;
}

function generateUseCaseMermaid(a) {
  const actors = a.actors.length ? a.actors : ["Usuario"];
  const useCases = a.useCases.length ? a.useCases : ["Accion principal"];
  const lines = ["flowchart LR"];

  const actorIds = actors.map((actor, i) => `A${i + 1}`);
  actorIds.forEach((id, i) => lines.push(`    ${id}["Actor ${safeLabel(actors[i])}"]`));
  lines.push("", '    subgraph SYS["Sistema E-commerce"]', "        direction TB");

  const useCaseIds = useCases.map((item, i) => `UC${i + 1}`);
  useCaseIds.forEach((id, i) => lines.push(`        ${id}(["${safeLabel(useCases[i])}"])`));
  lines.push("    end", "");

  for (let i = 0; i < useCaseIds.length - 1; i += 1) {
    lines.push(`    ${useCaseIds[i]} -. include .-> ${useCaseIds[i + 1]}`);
  }

  actorIds.forEach((actorId) => {
    useCaseIds.slice(0, Math.min(2, useCaseIds.length)).forEach((caseId) => {
      lines.push(`    ${actorId} --> ${caseId}`);
    });
  });

  return lines.join("\n");
}

function generateSequenceMermaid(a) {
  const participants = a.participants.length ? a.participants : ["Usuario", "Sistema"];
  const steps = a.sequenceSteps.length ? a.sequenceSteps : ["Usuario->>Sistema: Solicitud", "Sistema-->>Usuario: Respuesta"];

  const ids = participants.map((name, i) => `${toIdentifier(name, `P${i + 1}`)}${i + 1}`);
  const map = new Map(participants.map((name, i) => [normalizeText(name), ids[i]]));
  const lines = ["sequenceDiagram"];

  participants.forEach((participant, i) => {
    lines.push(`    participant ${ids[i]} as "${safeLabel(participant)}"`);
  });

  steps.forEach((step) => {
    const parsed = parseInteraction(step);
    if (!parsed) {
      lines.push(`    ${ids[0]}->>${ids[1]}: ${safeLabel(step)}`);
      return;
    }
    const sender = map.get(normalizeText(parsed.sender)) || ids[0];
    const receiver = map.get(normalizeText(parsed.receiver)) || ids[1];
    lines.push(`    ${sender}${parsed.arrow}${receiver}: ${safeLabel(parsed.message)}`);
  });

  return lines.join("\n");
}

function generateFlowMermaid(a) {
  const steps = a.flowSteps.length ? a.flowSteps : ["Inicio", "Proceso", "Fin"];
  const normalized = steps.map((step) => normalizeText(step));
  const looksCheckout = normalized.some((s) => s.includes("stock") || s.includes("inventario")) && normalized.some((s) => s.includes("pago"));

  if (looksCheckout) {
    const start = pickStep(steps, ["carrito", "checkout"], "Iniciar checkout");
    const stock = pickStep(steps, ["stock", "inventario"], "Validar stock");
    const pay = pickStep(steps, ["pago", "autoriz"], "Procesar pago");
    const notify = pickStep(steps, ["almacen", "notificar"], "Notificar al almacen");
    const stockErr = pickStep(steps, ["falta de stock", "stock insuficiente"], "Manejar falta de stock");
    const payErr = pickStep(steps, ["sin fondos", "rechaz"], "Manejar pago rechazado");
    return [
      "flowchart TD",
      '    S(["Inicio"])',
      `    A["${safeLabel(start)}"]`,
      `    B["${safeLabel(stock)}"]`,
      '    D1{"Stock disponible?"}',
      `    C["${safeLabel(pay)}"]`,
      '    D2{"Pago aprobado?"}',
      `    N["${safeLabel(notify)}"]`,
      `    E1["${safeLabel(stockErr)}"]`,
      `    E2["${safeLabel(payErr)}"]`,
      '    OK(["Fin exitoso"])',
      '    FAIL(["Fin con incidencia"])',
      "    S --> A --> B --> D1",
      "    D1 -- Si --> C",
      "    D1 -- No --> E1 --> FAIL",
      "    C --> D2",
      "    D2 -- Si --> N --> OK",
      "    D2 -- No --> E2 --> FAIL",
    ].join("\n");
  }

  const lines = ["flowchart TD"];
  steps.forEach((step, i) => lines.push(`    N${i + 1}["${safeLabel(step)}"]`));
  for (let i = 0; i < steps.length - 1; i += 1) lines.push(`    N${i + 1} --> N${i + 2}`);
  return lines.join("\n");
}

function generateErMermaid(a) {
  const entities = a.entities.length ? a.entities : ["Entidad(id)"];
  const lines = ["erDiagram"];
  const idByName = new Map();

  entities.forEach((entry, i) => {
    const parsed = parseEntity(entry);
    const id = toIdentifier(parsed.name, `E${i + 1}`).toUpperCase();
    idByName.set(normalizeText(parsed.name), id);
    lines.push(`    ${id} {`);
    if (parsed.attrs.length) {
      parsed.attrs.forEach((attr) => lines.push(`        string ${toIdentifier(attr, "field").replace(/^./, (c) => c.toLowerCase())}`));
    } else {
      lines.push("        string id");
    }
    lines.push("    }");
  });

  const rels = a.relationships.length ? a.relationships : ["Entidad->Entidad: relacion"];
  let added = 0;
  rels.forEach((rel) => {
    const parsed = parseRelationship(rel);
    if (!parsed) return;
    const left = idByName.get(normalizeText(parsed.left));
    const right = idByName.get(normalizeText(parsed.right));
    if (!left || !right) return;
    lines.push(`    ${left} ||--o{ ${right} : ${safeLabel(parsed.label)}`);
    added += 1;
  });

  if (!added && entities.length >= 2) {
    const first = idByName.get(normalizeText(parseEntity(entities[0]).name));
    const second = idByName.get(normalizeText(parseEntity(entities[1]).name));
    if (first && second) lines.push(`    ${first} ||--o{ ${second} : relacion`);
  }

  return lines.join("\n");
}

function generateUseCasePlantUml(a) {
  const actors = a.actors.length ? a.actors : ["Usuario"];
  const useCases = a.useCases.length ? a.useCases : ["Accion principal"];
  const lines = ["@startuml", "left to right direction"];

  const actorIds = actors.map((name, i) => `${toIdentifier(name, `A${i + 1}`)}${i + 1}`);
  actorIds.forEach((id, i) => lines.push(`actor "${safeLabel(actors[i])}" as ${id}`));

  lines.push("", 'package "Sistema E-commerce" {');
  const ucIds = useCases.map((name, i) => `${toIdentifier(name, `UC${i + 1}`)}${i + 1}`);
  ucIds.forEach((id, i) => lines.push(`  usecase "${safeLabel(useCases[i])}" as ${id}`));
  lines.push("}", "");

  for (let i = 0; i < ucIds.length - 1; i += 1) lines.push(`${ucIds[i]} .> ${ucIds[i + 1]} : <<include>>`);
  actorIds.forEach((actorId) => ucIds.slice(0, Math.min(2, ucIds.length)).forEach((ucId) => lines.push(`${actorId} --> ${ucId}`)));
  lines.push("@enduml");
  return lines.join("\n");
}

function generateSequencePlantUml(a) {
  const participants = a.participants.length ? a.participants : ["Usuario", "Sistema"];
  const steps = a.sequenceSteps.length ? a.sequenceSteps : ["Usuario->>Sistema: Solicitud", "Sistema-->>Usuario: Respuesta"];

  const ids = participants.map((name, i) => `${toIdentifier(name, `P${i + 1}`)}${i + 1}`);
  const map = new Map(participants.map((name, i) => [normalizeText(name), ids[i]]));
  const lines = ["@startuml"];

  participants.forEach((participant, i) => {
    const kind = i === 0 ? "actor" : "participant";
    lines.push(`${kind} "${safeLabel(participant)}" as ${ids[i]}`);
  });

  steps.forEach((step) => {
    const parsed = parseInteraction(step);
    if (!parsed) {
      lines.push(`${ids[0]} -> ${ids[1]} : ${safeLabel(step)}`);
      return;
    }
    const sender = map.get(normalizeText(parsed.sender)) || ids[0];
    const receiver = map.get(normalizeText(parsed.receiver)) || ids[1];
    const arrow = parsed.arrow === "-->>" ? "-->" : "->";
    lines.push(`${sender} ${arrow} ${receiver} : ${safeLabel(parsed.message)}`);
  });

  lines.push("@enduml");
  return lines.join("\n");
}

function generateFlowPlantUml(a) {
  const steps = a.flowSteps.length ? a.flowSteps : ["Inicio", "Proceso", "Fin"];
  const normalized = steps.map((step) => normalizeText(step));
  const looksCheckout = normalized.some((s) => s.includes("stock") || s.includes("inventario")) && normalized.some((s) => s.includes("pago"));

  if (looksCheckout) {
    const start = pickStep(steps, ["carrito", "checkout"], "Iniciar checkout");
    const stock = pickStep(steps, ["stock", "inventario"], "Validar stock");
    const pay = pickStep(steps, ["pago", "autoriz"], "Procesar pago");
    const notify = pickStep(steps, ["almacen", "notificar"], "Notificar al almacen");
    const stockErr = pickStep(steps, ["falta de stock", "stock insuficiente"], "Manejar falta de stock");
    const payErr = pickStep(steps, ["sin fondos", "rechaz"], "Manejar pago rechazado");
    return [
      "@startuml",
      "start",
      `:${safeLabel(start)};`,
      `:${safeLabel(stock)};`,
      "if (Stock disponible?) then (Si)",
      `  :${safeLabel(pay)};`,
      "  if (Pago aprobado?) then (Si)",
      `    :${safeLabel(notify)};`,
      "    stop",
      "  else (No)",
      `    :${safeLabel(payErr)};`,
      "    stop",
      "  endif",
      "else (No)",
      `  :${safeLabel(stockErr)};`,
      "  stop",
      "endif",
      "@enduml",
    ].join("\n");
  }

  const lines = ["@startuml", "start"];
  steps.forEach((step) => lines.push(`:${safeLabel(step)};`));
  lines.push("stop", "@enduml");
  return lines.join("\n");
}

function generateErPlantUml(a) {
  const entities = a.entities.length ? a.entities : ["Entidad(id)"];
  const lines = ["@startuml", "hide circle"];
  const idByName = new Map();

  entities.forEach((entry, i) => {
    const parsed = parseEntity(entry);
    const id = `${toIdentifier(parsed.name, `E${i + 1}`)}${i + 1}`;
    idByName.set(normalizeText(parsed.name), id);
    lines.push(`entity "${safeLabel(parsed.name)}" as ${id} {`);
    if (parsed.attrs.length) {
      parsed.attrs.forEach((attr, idx) => {
        const field = `${toIdentifier(attr, "field")}`.replace(/^./, (c) => c.toLowerCase());
        lines.push(`${idx === 0 ? "  *" : "  "} ${field} : string`);
      });
    } else {
      lines.push("  * id : string");
    }
    lines.push("}");
  });

  const rels = a.relationships.length ? a.relationships : ["Entidad->Entidad: relacion"];
  let added = 0;
  rels.forEach((rel) => {
    const parsed = parseRelationship(rel);
    if (!parsed) return;
    const left = idByName.get(normalizeText(parsed.left));
    const right = idByName.get(normalizeText(parsed.right));
    if (!left || !right) return;
    lines.push(`${left} ||--o{ ${right} : ${safeLabel(parsed.label)}`);
    added += 1;
  });

  if (!added && entities.length >= 2) {
    const first = idByName.get(normalizeText(parseEntity(entities[0]).name));
    const second = idByName.get(normalizeText(parseEntity(entities[1]).name));
    if (first && second) lines.push(`${first} ||--o{ ${second} : relacion`);
  }

  lines.push("@enduml");
  return lines.join("\n");
}

function normalizeText(text) {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function containsAny(text, tokens) {
  return tokens.some((token) => text.includes(token));
}

function extractListAfterLabels(text, labels) {
  for (const label of labels) {
    const regex = new RegExp(`(?:^|[\\n\\r]|\\.\\s*)${escapeRegex(label)}\\s*:\\s*([^\\n\\r\\.]+)`, "i");
    const match = text.match(regex);
    if (match && match[1]) return splitCsvItems(match[1]);
  }
  return [];
}

function splitCsvItems(raw) {
  const separators = new Set([",", ";", "|", "/"]);
  const items = [];
  let token = "";
  let depthParen = 0;
  let depthBracket = 0;
  let depthBrace = 0;

  for (const char of raw) {
    if (char === "(") depthParen += 1;
    if (char === ")") depthParen = Math.max(0, depthParen - 1);
    if (char === "[") depthBracket += 1;
    if (char === "]") depthBracket = Math.max(0, depthBracket - 1);
    if (char === "{") depthBrace += 1;
    if (char === "}") depthBrace = Math.max(0, depthBrace - 1);

    const shouldSplit = separators.has(char) && depthParen === 0 && depthBracket === 0 && depthBrace === 0;
    if (shouldSplit) {
      const clean = token.trim().replace(/^[\s.:-]+|[\s.:-]+$/g, "");
      if (clean) items.push(clean);
      token = "";
      continue;
    }
    token += char;
  }

  const last = token.trim().replace(/^[\s.:-]+|[\s.:-]+$/g, "");
  if (last) items.push(last);
  return items;
}

function parseInteraction(text) {
  const match = text.match(/^\s*(.+?)\s*(->>|-->>|->|-->)\s*(.+?)\s*:\s*(.+)\s*$/);
  if (!match) return null;
  return {
    sender: match[1].trim(),
    arrow: match[2].trim(),
    receiver: match[3].trim(),
    message: match[4].trim(),
  };
}

function parseEntity(entry) {
  const match = entry.match(/^\s*([^(]+?)\s*(?:\(([^)]*)\))?\s*$/);
  if (!match) return { name: entry.trim(), attrs: [] };
  const attrs = match[2] ? match[2].split(",").map((item) => item.trim()).filter(Boolean) : [];
  return { name: match[1].trim(), attrs };
}

function parseRelationship(entry) {
  const match = entry.match(/^\s*(.+?)\s*(?:->|-->)\s*(.+?)(?:\s*:\s*(.+))?\s*$/);
  if (!match) return null;
  return { left: match[1].trim(), right: match[2].trim(), label: (match[3] || "relacion").trim() };
}

function pickStep(steps, tokens, fallback) {
  for (const step of steps) {
    const normalized = normalizeText(step);
    if (tokens.some((token) => normalized.includes(token))) return step;
  }
  return fallback;
}

function toIdentifier(text, fallback = "N") {
  const normalized = text.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const parts = normalized.split(/[^A-Za-z0-9]+/).filter(Boolean);
  if (!parts.length) return fallback;
  let id = parts.map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join("");
  if (/^[0-9]/.test(id)) id = `${fallback}${id}`;
  return id;
}

function safeLabel(text) {
  return text
    .replace(/"/g, "'")
    .replace(/\s+/g, " ")
    .replace(/[\[\]{}<>]/g, "")
    .trim();
}

function dedupeBy(items, keyFn) {
  const seen = new Set();
  const output = [];
  items.forEach((item) => {
    const key = keyFn(item);
    if (seen.has(key)) return;
    seen.add(key);
    output.push(item);
  });
  return output;
}

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function normalizePlantUmlServer(rawServer) {
  let base = (rawServer || "https://www.plantuml.com/plantuml").trim().replace(/\/+$/, "");
  const lower = base.toLowerCase();
  for (const suffix of ["/png", "/svg", "/txt", "/uml", "/img"]) {
    if (lower.endsWith(suffix)) {
      base = base.slice(0, -suffix.length);
      break;
    }
  }
  if (!base.toLowerCase().endsWith("/plantuml")) base = `${base}/plantuml`;
  return base;
}

function encode6bit(value) {
  if (value < 10) return String.fromCharCode(48 + value);
  value -= 10;
  if (value < 26) return String.fromCharCode(65 + value);
  value -= 26;
  if (value < 26) return String.fromCharCode(97 + value);
  value -= 26;
  if (value === 0) return "-";
  if (value === 1) return "_";
  return "?";
}

function append3bytes(b1, b2, b3) {
  const c1 = b1 >> 2;
  const c2 = ((b1 & 0x3) << 4) | (b2 >> 4);
  const c3 = ((b2 & 0xf) << 2) | (b3 >> 6);
  const c4 = b3 & 0x3f;
  return [c1, c2, c3, c4].map((item) => encode6bit(item & 0x3f)).join("");
}

function plantumlEncode(text) {
  const compressed = window.pako.deflateRaw(new TextEncoder().encode(text), { level: 9 });
  let encoded = "";
  for (let i = 0; i < compressed.length; i += 3) {
    const b1 = compressed[i];
    const b2 = i + 1 < compressed.length ? compressed[i + 1] : 0;
    const b3 = i + 2 < compressed.length ? compressed[i + 2] : 0;
    encoded += append3bytes(b1, b2, b3);
  }
  return encoded;
}

function buildPlantUmlImageUrl(code, serverBase) {
  const encoded = plantumlEncode(code);
  const base = normalizePlantUmlServer(serverBase);
  return `${base}/png/${encoded}`;
}
