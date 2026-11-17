# Historial de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado semántico.

## [0.1.0] - 2026-11-17
### Agregado
- Backend en FastAPI con ciclo diario: datos públicos de MEXC → variables → pronóstico del MLP → propuesta del LLM local → validación → riesgo → simulación Paper → registro.
- Cliente de Ollama solo para localhost, con salida JSON validada (acción, símbolo, fecha de vela y justificación).
- Simulador Paper: 50,000 USDT, sin apalancamiento ni ventas en corto, precisión y mínimo del par, deslizamiento configurable.
- Controles de riesgo en configuración: exposición máxima, pérdida diaria máxima y antigüedad máxima del dato.
- SQLite para velas, decisiones, órdenes, patrimonio, errores y estado; una sola decisión por vela.
- API protegida con `X-API-Key` y documentación automática en `/docs`.
- Interfaz en Vue 3 + Vite + TypeScript con botones de iniciar, pausar, detener y revisar vela.
- 23 pruebas automatizadas, incluidos los 9 errores provocados del protocolo.
