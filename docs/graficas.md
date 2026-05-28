# Pantalla de gráficas

La pantalla de gráficas permite visualizar, filtrar, descargar y regenerar todas las gráficas generadas durante un análisis. 

Desde esta sección puedes trabajar tanto con:

- Gráficas SAES.
- Gráficas de evolución.


![Pantalla gráficas](/images/graficas.png)
---


## Gráficas SAES

Las gráficas SAES incluyen visualizaciones estadísticas clásicas como:

- Boxplot.
- Violin Plot.
- Histogramas.
- Critical Distance Diagram.


## Gráficas de evolución

Las gráficas de evolución permiten analizar cómo cambia una métrica durante las ejecuciones del algoritmo.

Estas gráficas pueden mostrar:

- Media.
- Mediana.
- Desviación estándar.
- Mínimos y máximos.

::: tip
Las capas estadísticas pueden activarse o desactivarse desde el panel de configuración.
:::


## Descargar todas las gráficas

Si existen gráficas disponibles, aparecerá el botón:

**Descargar todo**

Este botón genera automáticamente un archivo ZIP con:

- Gráficas SAES.
- Gráficas de evolución.


## Sistema de filtros

![Filtros SAES](/images/filtros_saes.png)

### Filtrar por algoritmo

Permite mostrar únicamente las gráficas pertenecientes a algoritmos concretos.

Puedes seleccionar:

- Un algoritmo.
- Varios algoritmos.
- Todos los algoritmos.


### Filtrar por tipo de gráfica

Permite visualizar únicamente determinados tipos de gráficas.

Ejemplos:

- Evolution.
- Boxplot.
- Violin.
- Histogram.
- Critical Distance.


### Filtrar por formato

Permite filtrar por extensión de archivo.

Ejemplos:

- PNG.
- EPS.
- SVG.
- JPG.
- JPEG

### Filtrar por métrica

Permite visualizar únicamente gráficas relacionadas con métricas específicas.

Por ejemplo:

- Accuracy.
- Hypervolume.
- Fitness.


## Filtrar por instancia

Permite mostrar únicamente gráficas asociadas a determinadas instancias o problemas.


## Buscador

La barra de búsqueda permite localizar gráficas escribiendo:

- Nombre del archivo.
- Nombre de la métrica.
- Nombre de la instancia.
- Tipo de gráfica.
- Formato.


## Opciones de evolución

La pantalla incluye un panel específico para configurar las gráficas de evolución.

![Filtros evolución](/images/filtros_evolucion.png)

### Capas estadísticas

Puedes activar o desactivar:

- Media.
- Mediana.
- Desviación estándar.
- Min/Max.


### Grid

La opción Grid añade o elimina la rejilla de las gráficas.

### Agrupar por instancia

Genera gráficas separadas según la instancia detectada.

### Agrupar por métrica

Genera gráficas independientes para cada métrica.

## Aplicar cambios

Después de modificar filtros u opciones de evolución, debes pulsar:

**Aplicar**

La aplicación regenerará automáticamente las gráficas necesarias.


## Configuración visual

Esta sección permite personalizar la presentación visual de las gráficas en la pantalla.

![Filtros Visualización](/images/filtros_visualizacion.png)

### Número de columnas

Puedes elegir:

- 1 columna.
- 2 columnas.
- 3 columnas.
- 4 columnas.


### Número de filas visibles

Permite controlar cuántas filas se muestran simultáneamente.

### Tamaño de imagen

Puedes ajustar la densidad visual:

| Opción | Descripción |
|---|---|
| Baja | Gráficas compactas |
| Media | Tamaño equilibrado |
| Alta | Mayor tamaño visual |


### Ajuste de imagen

Existen dos modos principales:

| Modo | Descripción |
|---|---|
| Contain | La imagen completa siempre es visible |
| Cover | La imagen rellena completamente el espacio |


### Mostrar metadatos

La opción de metadatos permite mostrar:

- Tipo de gráfica.
- Métrica.
- Instancia.
- Columna X.
- Formato.
- Nombre del archivo.

<video src="/videos/graficas.mp4" controls muted loop playsinline class="docs-video"></video>

### Comparación de dos algoritmos

<video src="/videos/ejemplo_graficas.mp4" controls muted loop playsinline class="docs-video"></video>