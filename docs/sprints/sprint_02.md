# Sprint 02 - Agente Arquitecto + cierre tecnico Sprint 1

## Objetivo

Construir el Agente Arquitecto y dejar operativo el flujo completo con el Agente Analista para no generar diagramas sin contexto suficiente.

## Alcance implementado

1. Agente Analista
- Clasifica tipo de salida: casos de uso, clases, flujo, secuencia, ER, C4, QA automatico y scaffolding.
- Detecta estandar objetivo: UML/BPMN/ER/C4.
- Detecta formato objetivo: Mermaid/PlantUML/Text.
- Extrae contexto clave por dominio (actores, casos de uso, clases, pasos, participantes, entidades, relaciones, stack).
- Si falta informacion, entrega preguntas de aclaracion.

2. Agente Arquitecto
- Recibe contexto estructurado aprobado por el Analista.
- Genera Mermaid para:
  - Casos de uso (flowchart LR)
  - Clases (classDiagram)
  - Flujo (flowchart TD)
  - Secuencia (sequenceDiagram)
  - ER (erDiagram)
  - C4 Context y C4 Container
- Genera artefactos textuales para:
  - QA automatico (escenarios base Gherkin)
  - Scaffolding inicial (estructura + stubs)
- Soporta modo paquete de documentacion en una sola corrida cuando la solicitud incluye multiples tipos.
- Soporta salida PlantUML nativa para UML, ER y C4 simplificado.

3. Orquestacion
- Pipeline local analista -> arquitecto.
- Se detiene cuando no hay contexto suficiente.

4. Calidad
- Tests unitarios para analista y arquitecto.
- Tests de integracion del flujo principal.
- Interfaz web local para validar entradas completas e incompletas.
- Demo web estatica en `docs/` lista para publicacion en GitHub Pages.

## Criterios de aceptacion

- El sistema no genera diagrama si falta contexto obligatorio.
- Para solicitudes completas, se genera Mermaid valido por tipo o texto estructurado cuando corresponde.
- Se pueden ejecutar pruebas locales para validar regresiones.
- Existe una UI en Streamlit para pruebas funcionales del flujo Sprint 2.

## Nota sobre enfoque agentico

- El comportamiento agentico en este sprint es deliberativo y orientado a meta: primero entender contexto, luego construir el diagrama.
- No se entrena un modelo desde cero; se aplica orquestacion de agentes y reglas de dominio sobre componentes preentrenados.
- La generacion de Mermaid y artefactos en Sprint 2 es local y determinista, sin depender de copiar codigo externo.

## Pendientes para Sprint 3

- Implementar Agente Validador formal UML/BPMN.
- Integrar bucle de correccion Arquitecto <-> Validador.
- Endurecer validacion automatica de sintaxis por formato antes de entregar salida final.
