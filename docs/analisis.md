# Pantalla de análisis

La sección de análisis es el núcleo principal de la aplicación. Desde aquí puedes crear, gestionar y ejecutar todos los análisis disponibles.

![Análisis](/images/analisis.png)
---
## Tabla de análisis

La tabla principal muestra todos los análisis disponibles.

Cada fila contiene:

- Nombre del análisis.
- Fecha de actualización.
- Estado.
- Acciones rápidas.

## Estados de análisis

Los análisis pueden encontrarse en distintos estados:

| Estado | Descripción |
|---|---|
| Creado | Análisis creado pero no ejecutado |
| En ejecución | Análisis en ejecución |
| Completado | Análisis completado correctamente |
| Error | Error durante la ejecución |

## Acciones disponibles

Cada análisis dispone de tres acciones:

### Abrir análisis

Permite acceder al detalle completo del análisis.

Desde ahí podrás:

- Consultar resultados.
- Ver gráficas.
- Descargar archivos.


### Editar análisis

Permite modificar el nombre.

![Editar Análisis](/images/editar_analisis.png)


### Eliminar análisis

Elimina completamente el análisis y sus resultados asociados.

![Eliminar Análisis](/images/eliminar_analisis.png)
---

## Filtros y búsqueda

La sección incluye un sistema avanzado de búsqueda y filtrado.

Puedes:

- Buscar por nombre.
- Buscar por descripción.
- Filtrar por estado.
- Ordenar resultados.

![Filtros Análisis](/images/filtros_analisis.png)

## Crear un nuevo análisis

Para crear un análisis pulsa el botón:

**Nuevo análisis**

![Modal Análisis](/images/modal_analisis.png)

## Datos básicos

La primera sección permite introducir:

| Campo | Descripción |
|---|---|
| Nombre | Nombre identificativo del análisis |
| Descripción | Descripción opcional |

## Subir dataset CSV

La aplicación trabaja principalmente con datasets CSV.

Para subir un dataset:

1. Pulsa la zona de subida.
2. Selecciona un fichero `.csv`.
3. La aplicación detectará automáticamente las capacidades disponibles.

![Modal Análisis](/images/dataset-analisis.png)

## Detección automática del dataset

Tras subir el CSV, la aplicación analiza automáticamente:

- Métricas detectadas.
- Algoritmos.
- Instancias.
- Columnas de evolución.
- Columnas fitness.
- Número de ejecuciones.

Existen distintos formatos válidos 

#### 1. Formato SAES
Este formato permite generar:

- SAES Plots
- SAES Reports
- Notebooks

##### Columnas requeridas

| Columna | Tipo de dato | Descripción |
|---|---|---|
| Algorithm | string | Nombre del algoritmo |
| Instance | string | Problema, dataset o instancia |
| MetricName | string | Nombre de la métrica evaluada |
| ExecutionId | integer | Identificador de ejecución independiente |
| MetricValue | float | Valor numérico de la métrica |

##### Ejemplo
```csv
Algorithm,Instance,MetricName,ExecutionId,MetricValue
GA,I1,fitness,1,0.45
GA,I1,fitness,2,0.39
PSO,I1,fitness,1,0.51
PSO,I1,fitness,2,0.47
```

#### 2. Formato Evolution

Este formato permite generar:

- Evolution Plots

##### Columnas requeridas

| Columna | Tipo de dato | Descripción |
|---|---|---|
| Algorithm | string | Nombre del algoritmo |
| MetricValue | float | Fitness o valor de la métrica |
| Generation / Time / Evaluations | integer o float | Eje X de evolución |


##### Ejemplo

```csv
Algorithm,ExecutionId,Generation,MetricValue
GA,1,0,100
GA,1,1,80
GA,1,2,65
GA,1,3,50
PSO,1,0,110
PSO,1,1,90
PSO,1,2,70
PSO,1,3,55
```

#### 3. Formato combinado SAES + Evolution

También es posible combinar ambos formatos en un único CSV.

##### Columnas recomendadas

| Columna | Tipo de dato | Descripción |
|---|---|---|
| Algorithm | string | Nombre del algoritmo |
| Instance | string | Problema o instancia |
| MetricName | string | Nombre de la métrica |
| ExecutionId | integer | Identificador de ejecución |
| Generation | integer o float | Generación o iteración |
| MetricValue | float | Valor fitness o métrica |

##### Ejemplo

```csv
Algorithm,Instance,MetricName,ExecutionId,Generation,MetricValue
GA,I1,fitness,1,0,100
GA,I1,fitness,1,1,80
GA,I1,fitness,1,2,65
GA,I1,fitness,2,0,98
GA,I1,fitness,2,1,78
GA,I1,fitness,2,2,60
PSO,I1,fitness,1,0,110
PSO,I1,fitness,1,1,90
PSO,I1,fitness,1,2,70
```

## Compatibilidad detectada

La aplicación detecta automáticamente si el dataset soporta:

| Módulo | Compatibilidad |
|---|---|
| SAES Plots | Sí / No |
| SAES Reports | Sí / No |
| Evolution Plots | Sí / No |
| Notebooks | Sí / No |


## Módulos disponibles

El usuario puede activar distintos módulos de análisis si están disponibles para el fichero adjuntado.

![Módulos Análisis](/images/modulos_analisis.png)

### SAES Plots

Genera gráficas estadísticas mediante la herramienta SAES.

Incluye:

- Boxplots.
- Violin plots.
- Histogramas.
- Critical Distance plots.


### SAES Reports

Genera reportes estadísticos automáticos.

Incluye pruebas como:

- Friedman.
- Wilcoxon.
- Rankings.
- Comparaciones estadísticas.


### Evolution Plots

Genera gráficas de evolución y convergencia.

Permite visualizar:

- Evolución temporal.
- Fitness.
- Generaciones.
- Evaluaciones.

### Notebooks

Genera notebooks interactivos listos para usar.

Los notebooks incluyen:

- Dataset embebido.
- Código preparado.
- Generación automática de gráficas.
- Reportes SAES.
- Reproducción de resultados.


## Configuración de métricas

La aplicación permite definir si una métrica debe:

- Maximizarse.
- Minimizarse.

#### CSV opcional de métricas

También es posible subir un fichero CSV opcional para definir automáticamente si cada métrica debe maximizarse o minimizarse.

##### Columnas requeridas

| Columna | Tipo de dato | Descripción |
|---|---|---|
| MetricName | string | Nombre de la métrica |
| Maximize | boolean | Indica si la métrica debe maximizarse |


##### Ejemplo

```csv
MetricName,Maximize
accuracy,True
loss,False
fitness,True
error,False
```

Si se proporciona este fichero, la aplicación utilizará automáticamente estas configuraciones durante el análisis

![CSV Métricas Análisis](/images/metricas.png)

## Formatos de exportación

Las gráficas pueden exportarse en distintos formatos:

- PNG
- SVG
- EPS
- JPG
- JPEG
## Configuración de gráficas de evolución

Cuando el dataset soporta evolución, aparece una sección avanzada de configuración.

### Configuración del eje X

Puedes seleccionar distintas columnas como eje X:

- Generaciones.
- Tiempo.
- Evaluaciones.
- Otras columnas detectadas.


### Configuración de etiquetas

Es posible personalizar:

- Título de la gráfica.
- Etiqueta del eje X.
- Etiqueta del eje Y.

### Opciones visuales

Las gráficas permiten activar o desactivar:

| Opción | Descripción |
|---|---|
| Grid | Rejilla de fondo |
| Media | Línea media |
| Mediana | Línea mediana |
| Min/Max | Límites mínimo y máximo |
| Desviación estándar | Banda de desviación |

### Agrupaciones

Las gráficas pueden agruparse automáticamente:

- Por instancia.
- Por métrica.


## Ejecutar análisis

Una vez configurado todo:

1. Pulsa **Crear y ejecutar**.
2. La aplicación iniciará el pipeline automáticamente.

<video src="/videos/crear_analisis.mp4" controls muted loop playsinline class="docs-video"></video>
