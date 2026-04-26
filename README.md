# ArquiSys AI

ArquiSys AI es un sistema agentico para convertir requerimientos funcionales en diagramas tecnicos.

En esta base se implementan Sprint 1 y Sprint 2:
- Agente Analista: entiende la intencion del usuario y detecta contexto faltante.
- Agente Arquitecto: genera diagramas y artefactos tecnicos a partir del contexto aprobado.

## Estado actual

- Soporte de salidas para: UML (casos de uso, clases, flujo, secuencia), ER y C4 (contexto, contenedores).
- Soporte de paquete automatico de documentacion visual en una sola solicitud (multidiagrama).
- Soporte adicional de artefactos: QA automatico (Gherkin base) y scaffolding inicial.
- Formatos de salida: Mermaid, PlantUML y texto estructurado (segun tipo de salida).
- Pipeline analista -> arquitecto listo para pruebas locales.
- Interfaz web local para probar todo el alcance de Sprint 2 ampliado.

## Enfoque IA agentica

- El sistema es agentico porque persigue una meta con autonomia parcial: entender la solicitud, pedir contexto faltante y luego generar el diagrama.
- No requiere entrenar un modelo desde cero para esta etapa; usa reglas + orquestacion de agentes sobre modelos ya preentrenados (opcional LLM para Analista).
- No depende de "jalar codigo" de internet para generar diagramas: la generacion actual usa logica local del proyecto.

## Estructura

```
src/arquisys_ai/
  agents/
  config/
  core/
  generators/
  graph/
  services/
  utils/
tests/
docs/
scripts/
```

## Instalacion

```bash
py -m pip install -e .[dev,ui]
```

## Probar por consola

```bash
py scripts/run_local.py --request "Necesito un diagrama UML de casos de uso en Mermaid. Actores: Cliente, Admin. Casos de uso: Iniciar sesion, Comprar producto"
py -m pytest
```

## Probar con interfaz web

```bash
py -m streamlit run scripts/ui_app.py
```

## GitHub Pages

- Se incluye una demo web estatica en `docs/` (sin backend) para GitHub Pages.
- El workflow `.github/workflows/pages.yml` publica automaticamente `docs/` al hacer push a `main`.
- La demo web soporta render de Mermaid y PlantUML (via servidor PlantUML).

Si necesitas usar servidor PlantUML propio en la demo, cambia el campo "Servidor PlantUML" en la pagina.

La interfaz permite:
- escribir solicitudes libres,
- completar contexto guiado (actores, casos de uso, secuencia, ER, C4, stack),
- visualizar preguntas del Analista cuando falta contexto,
- renderizar Mermaid cuando corresponde y mostrar artefactos textuales para QA/scaffolding,
- generar paquetes completos (casos de uso + secuencia + flujo/BPMN + ER) desde el mismo contexto.

## Variables de entorno

Revisa `.env.example` para habilitar proveedor LLM opcional.
