# Optimización conservadora de rendimiento Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reducir tiempos de entrada y rerenderizado sin alterar scoring, NLP, Isolation Forest, umbrales, dictámenes ni persistencia.

**Architecture:** Las vistas consultarán únicamente el lote activo, las listas reutilizables se cachearán y las representaciones extensas se paginarán en bloques de 50. El enrutador y Expedientes cargarán trabajo pesado bajo demanda, manteniendo las interfaces públicas existentes.

**Tech Stack:** Python 3, Streamlit 1.60, SQLAlchemy 2, MySQL/MariaDB, Pandas, Plotly, NetworkX, unittest.

## Global Constraints

- MySQL/MariaDB es la única base operativa.
- No modificar fórmulas ni umbrales del pipeline.
- No modificar ingesta, estados de revisión ni significado de campos persistidos.
- Gráficos y métricas usan el lote completo; solo tablas y tarjetas se paginan.
- Tamaño fijo de página: 50 registros.
- No añadir dependencias.

---

### Task 1: Utilidad pura de paginación

**Files:**
- Create: `utilidades/paginacion.py`
- Create: `tests/test_rendimiento_vistas.py`

**Interfaces:**
- Produces: `paginar_dataframe(df: pd.DataFrame, pagina: int, tamano: int = 50) -> tuple[pd.DataFrame, int, int]` que retorna subconjunto, página normalizada y total de páginas.

- [ ] **Step 1: Escribir pruebas fallidas de límites y preservación**

```python
class PaginacionTest(unittest.TestCase):
    def test_limita_cada_pagina_a_cincuenta(self):
        df = pd.DataFrame({"id": range(125), "valor": range(125)})
        pagina, actual, total = paginar_dataframe(df, 2)
        self.assertEqual(len(pagina), 50)
        self.assertEqual((actual, total), (2, 3))
        self.assertEqual(pagina["id"].tolist(), list(range(50, 100)))

    def test_normaliza_pagina_fuera_de_rango(self):
        df = pd.DataFrame({"id": range(51)})
        pagina, actual, total = paginar_dataframe(df, 99)
        self.assertEqual((actual, total), (2, 2))
        self.assertEqual(pagina["id"].tolist(), [50])

    def test_no_altera_dataframe_original(self):
        df = pd.DataFrame({"valor": range(80)})
        suma = df["valor"].sum()
        paginar_dataframe(df, 1)
        self.assertEqual(len(df), 80)
        self.assertEqual(df["valor"].sum(), suma)
```

- [ ] **Step 2: Ejecutar pruebas y confirmar fallo por módulo inexistente**

Run: `python -m unittest tests.test_rendimiento_vistas.PaginacionTest -v`
Expected: FAIL con `ModuleNotFoundError: utilidades.paginacion`.

- [ ] **Step 3: Implementar la función pura mínima**

Validar `tamano >= 1`, calcular `max(1, ceil(len(df)/tamano))`, limitar `pagina` al rango y devolver `df.iloc[inicio:fin].copy()`.

- [ ] **Step 4: Ejecutar pruebas y confirmar verde**

Run: `python -m unittest tests.test_rendimiento_vistas.PaginacionTest -v`
Expected: 3 tests PASS.

### Task 2: Consultar Dashboard por lote activo

**Files:**
- Modify: `vistas/vista_panel_principal.py:21-135`
- Modify: `tests/test_rendimiento_vistas.py`
- Modify: `utilidades/gestor_lotes.py:1-65`

**Interfaces:**
- Consumes: `renderizar_selector_lote_global(...) -> int | None`.
- Produces: `_cargar_datos_dashboard(lote_id: int) -> pd.DataFrame`.

- [ ] **Step 1: Añadir prueba fallida de consulta parametrizada**

Analizar el AST/fuente de `_cargar_datos_dashboard` y afirmar que su firma contiene `lote_id`, el SQL contiene `WHERE c.id_carga = :lote` y la ejecución recibe `{"lote": lote_id}`.

- [ ] **Step 2: Ejecutar la prueba y observar que falla porque la función no acepta lote**

Run: `python -m unittest tests.test_rendimiento_vistas.DashboardQueryTest -v`
Expected: FAIL en la firma o cláusula `WHERE`.

- [ ] **Step 3: Mover el selector antes de la carga y filtrar desde MySQL**

Eliminar la consulta duplicada de lotes en `_cargar_datos_dashboard`, agregar `WHERE c.id_carga = :lote`, pasar el parámetro y conservar todas las columnas actuales. Cachear en `gestor_lotes.py` una función `_cargar_lotes()` con TTL de 30 segundos.

- [ ] **Step 4: Verificar prueba y compilación**

Run: `python -m unittest tests.test_rendimiento_vistas.DashboardQueryTest -v`
Expected: PASS.

### Task 3: Paginar Matriz y Casos sin alterar gráficos

**Files:**
- Modify: `vistas/vista_panel_principal.py:299-430`
- Modify: `tests/test_rendimiento_vistas.py`

**Interfaces:**
- Consumes: `paginar_dataframe` de Task 1.
- Produces: dos selectores numéricos independientes con claves `pagina_matriz` y `pagina_casos`.

- [ ] **Step 1: Añadir prueba fallida del límite de renderizado**

Probar una función auxiliar pura `_preparar_paginas_dashboard(df_filtrado, pagina_matriz, pagina_casos)` o verificar que ambos subconjuntos devueltos contengan como máximo 50 registros y que el DataFrame de entrada conserve 125.

- [ ] **Step 2: Ejecutar y confirmar fallo por auxiliar inexistente**

Run: `python -m unittest tests.test_rendimiento_vistas.DashboardPaginationTest -v`
Expected: FAIL por importación ausente.

- [ ] **Step 3: Implementar paginación independiente**

Ordenar una vez por `puntaje_riesgo`, paginar esa copia para Matriz y Casos, renderizar controles `st.number_input` entre 1 y el total y mostrar `Página X de Y`. Mantener `df_filtrado` completo en métricas y Plotly.

- [ ] **Step 4: Ejecutar pruebas**

Run: `python -m unittest tests.test_rendimiento_vistas.DashboardPaginationTest -v`
Expected: PASS y ningún subconjunto supera 50.

### Task 4: Carga diferida de vistas

**Files:**
- Modify: `ejecutor.py:18-30,256-267`
- Modify: `tests/test_rendimiento_vistas.py`

**Interfaces:**
- Produces: `renderizar_vista(vista: str) -> None` con imports locales por rama.

- [ ] **Step 1: Añadir prueba fallida de imports diferidos**

Inspeccionar AST y comprobar que `ejecutor.py` no contiene imports de `vistas.vista_carga_datos`, `vista_detalle_auditoria` ni `vista_estadisticas_globales` a nivel de módulo.

- [ ] **Step 2: Ejecutar y confirmar fallo por imports ansiosos actuales**

Run: `python -m unittest tests.test_rendimiento_vistas.LazyImportsTest -v`
Expected: FAIL listando módulos importados globalmente.

- [ ] **Step 3: Sustituir imports globales por resolución local**

Dentro de `renderizar_vista`, importar únicamente la función correspondiente a la clave solicitada. Mantener el fallback al Dashboard y los mismos identificadores de rutas.

- [ ] **Step 4: Ejecutar prueba y compilación**

Run: `python -m unittest tests.test_rendimiento_vistas.LazyImportsTest -v`
Expected: PASS.

### Task 5: Expedientes cacheados y grafo aislado por lote

**Files:**
- Modify: `vistas/vista_detalle_auditoria.py:19-270`
- Modify: `tests/test_rendimiento_vistas.py`

**Interfaces:**
- Produces: `_cargar_expedientes_lote(lote_id: int) -> pd.DataFrame`, `_cargar_caso(lote_id: int, id_convocatoria: int) -> dict | None`, `_cargar_relaciones(lote_id: int, ruc: str) -> pd.DataFrame` cacheadas 30 segundos.

- [ ] **Step 1: Añadir prueba fallida del aislamiento del grafo**

Comprobar que la consulta de relaciones incluye `c.id_carga = :lote` y parámetros `lote` y `ruc`.

- [ ] **Step 2: Ejecutar y confirmar fallo porque la consulta actual solo filtra RUC**

Run: `python -m unittest tests.test_rendimiento_vistas.ExpedienteQueryTest -v`
Expected: FAIL por ausencia de `id_carga`.

- [ ] **Step 3: Extraer y cachear consultas de solo lectura**

Crear las tres funciones con `@st.cache_data(ttl=30, show_spinner=False)`. Mantener exactamente las columnas consumidas por la vista. Pasar `lote_id` a relaciones y construir el grafo solo con ese DataFrame.

- [ ] **Step 4: Ejecutar prueba y compilación**

Run: `python -m unittest tests.test_rendimiento_vistas.ExpedienteQueryTest -v`
Expected: PASS.

### Task 6: Evitar importación innecesaria de SHAP

**Files:**
- Modify: `modulos_ia/explicabilidad_ia.py:10-48`
- Modify: `tests/test_rendimiento_vistas.py`

**Interfaces:**
- Conserva: `calcular_explicabilidad_caso(row_data: dict, scaler=None, model=None) -> pd.DataFrame`.

- [ ] **Step 1: Añadir prueba fallida que bloquee importación SHAP en modo proporcional**

Parchear `builtins.__import__` para fallar si recibe `shap`, llamar sin modelo/escalador y afirmar que devuelve cuatro factores con suma aproximada de 100.

- [ ] **Step 2: Ejecutar y confirmar que falla porque actualmente intenta importar SHAP**

Run: `python -m unittest tests.test_rendimiento_vistas.ExplicabilidadTest -v`
Expected: FAIL indicando importación de `shap`.

- [ ] **Step 3: Importar SHAP solo dentro de la rama con modelo y escalador**

Evaluar primero `if model is not None and scaler is not None`; únicamente entonces importar SHAP. Mantener sin cambios las fórmulas proporcionales y el cálculo SHAP existente.

- [ ] **Step 4: Ejecutar prueba**

Run: `python -m unittest tests.test_rendimiento_vistas.ExplicabilidadTest -v`
Expected: PASS.

### Task 7: Regresión completa y evidencia de rendimiento estructural

**Files:**
- Modify: `README.md` solo si necesita documentar paginación.

**Interfaces:** Ninguna nueva.

- [ ] **Step 1: Ejecutar suite completa**

Run: `python -m unittest discover -s tests -v`
Expected: pruebas existentes de scoring y nuevas pruebas de rendimiento PASS.

- [ ] **Step 2: Compilar todos los módulos**

Run: `python -m compileall -q base_datos utilidades vistas modulos_ia ejecutor.py`
Expected: exit code 0.

- [ ] **Step 3: Verificar invariantes por búsqueda**

Confirmar que no cambiaron archivos de `modulos_ia/extractor_caracteristicas.py`, `modulos_ia/modelo_aislamiento.py` ni la función `_persistir_resultados`; confirmar que cada render extenso usa un DataFrame paginado y que las consultas del Dashboard y grafo contienen `id_carga`.

- [ ] **Step 4: Revisar diff final**

Comprobar que no hay cambios en fórmulas, umbrales, escrituras SQL ni estados de revisión. Documentar cualquier limitación de medición que dependa del servidor MySQL en ejecución.
