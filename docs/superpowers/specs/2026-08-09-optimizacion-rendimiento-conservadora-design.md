# Diseño de optimización conservadora de rendimiento

## Objetivo

Reducir el tiempo de entrada y de interacción de las ventanas de AUI Intelligence sin modificar la lógica funcional que calcula características, reglas normativas, NLP, Isolation Forest, puntajes, niveles de riesgo, estados de revisión o métricas.

## Restricciones invariables

- MySQL/MariaDB continúa siendo la única base de datos operativa.
- No se modifican las fórmulas ni los umbrales del pipeline.
- No se modifica la ingesta ni el significado de los campos persistidos.
- Los gráficos y métricas continúan usando el conjunto completo del lote activo.
- La paginación afecta únicamente la cantidad de filas o tarjetas renderizadas.
- Cada página contiene hasta 50 registros.
- Todos los registros siguen siendo accesibles mediante paginación y filtros.

## Arquitectura propuesta

### Consultas por lote

El selector global determina primero `lote_activo_id`. Dashboard e Inteligencia Ejecutiva pasan ese identificador a consultas parametrizadas, de modo que MySQL devuelva solamente las operaciones necesarias. La selección de lotes se cachea brevemente y la invalidación existente mediante `st.cache_data.clear()` conserva la coherencia después de cargas, eliminaciones, decisiones y cambios de configuración.

### Paginación de presentación

La Matriz de resultados y Casos para revisión trabajan sobre el DataFrame ya filtrado. Cada sección mantiene una página independiente, calcula el total de páginas con tamaño fijo de 50 y corta el DataFrame con `iloc`. Los indicadores y gráficos siguen recibiendo el DataFrame completo filtrado; únicamente las dos representaciones extensas reciben el subconjunto de la página.

Cuando un filtro reduce el número de páginas, la página activa se normaliza al rango válido. Un lote o filtro sin registros conserva el mensaje informativo existente.

### Carga diferida

El enrutador importa cada vista solamente cuando se solicita. Así, abrir Centro de control no carga anticipadamente sklearn, NLP, NetworkX, PDF o módulos de ingesta. Los nombres públicos de las funciones de vista se conservan.

### Expedientes

Las consultas de expedientes se cachean por lote e identificador. El mapa de relaciones se limita al lote activo además del RUC seleccionado. La disposición del grafo se cachea a partir de esos datos. La explicación proporcional evita importar SHAP cuando no se proporciona simultáneamente un modelo y un escalador; cuando ambos existen, el comportamiento SHAP actual permanece disponible.

### Límites y seguridad

No se introducen escrituras nuevas. Las consultas siguen parametrizadas. Los errores de MySQL conservan el tratamiento actual de cada vista. La optimización no cambia permisos, sesiones ni auditoría.

## Flujo de datos

1. Streamlit restaura la sesión y resuelve la vista activa.
2. Solo se importa el módulo de la vista solicitada.
3. El selector global obtiene su lista cacheada y entrega `lote_activo_id`.
4. La vista consulta MySQL usando el lote como parámetro.
5. Se calculan indicadores y gráficos sobre el lote completo.
6. Los filtros producen el conjunto visible.
7. Matriz y Casos renderizan como máximo 50 registros por página.

## Estrategia de pruebas

- Pruebas unitarias de la función de paginación: colección vacía, primera página, última página incompleta y normalización de página fuera de rango.
- Pruebas de construcción de consultas para comprobar que el lote activo forma parte de los parámetros y que no se recupera el histórico completo.
- Prueba de regresión que confirma que paginar no altera conteos, sumas ni DataFrame completo usado por gráficos.
- Prueba de explicabilidad que confirma que el camino proporcional no importa SHAP sin modelo y escalador.
- Prueba del grafo que confirma el aislamiento por lote en la consulta.
- Compilación de todos los módulos y ejecución de la suite existente.

## Criterios de aceptación

- Ninguna tabla extensa crea más de 50 filas o tarjetas en una ejecución.
- Cambiar de página no recalcula ni modifica el scoring.
- Dashboard no consulta convocatorias de lotes distintos al activo.
- Expedientes no incluye relaciones de otros lotes.
- Entrar a una vista liviana no importa módulos exclusivos de ingesta o auditoría.
- Las pruebas existentes del pipeline conservan exactamente sus resultados.
