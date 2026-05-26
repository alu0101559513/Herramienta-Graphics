# Detalle de un análisis

La pantalla de detalle permite consultar toda la información de un análisis concreto y acceder a los resultados generados.

![Detalles Análisis](/images/analisis-detail.png)


## Información principal

En la parte superior de la pantalla se muestra la información general del análisis.

Esta zona incluye:

- Estado del análisis.
- Nombre del análisis.
- Descripción.
- Nombre del CSV utilizado.
- Número de ejecuciones.
- Número de gráficas.
- Número de reportes.
- Número de notebooks.
- Número de métricas.
- Número de instancias.

---



## Métricas e instancias

La página muestra dos paneles principales:

- Métricas detectadas.
- Instancias detectadas.

Estos paneles permiten comprobar rápidamente qué elementos del dataset se han reconocido.

![Métricas e instancias](/images/m_instancias_analisis.png)
---

## Resultados disponibles

La sección de resultados resume los módulos generados.

![Resultados disponibles](/images/modulos_disponibles.png)

Los resultados se agrupan en:

- Gráficas.
- Reportes.
- Notebooks.

## Gráficas

La tarjeta de gráficas permite acceder a todas las visualizaciones generadas.

Desde esta tarjeta puedes:

- Abrir la pantalla de gráficas.
- Descargar todas las gráficas disponibles.
- Ver cuántas gráficas se han generado.


Las gráficas pueden incluir:

- Gráficas SAES.
- Curvas de evolución.


## Reportes

La tarjeta de reportes permite acceder a los resultados estadísticos generados.

Desde esta tarjeta puedes:

- Abrir la pantalla de reportes.
- Descargar todos los reportes.

Los reportes están disponibles cuando el análisis tiene compatibilidad con SAES.


## Notebooks

La tarjeta de notebooks permite descargar el notebook generado para el análisis.

El notebook puede incluir:

- Dataset incorporado.
- Configuración de métricas.
- Código para reproducir gráficas.
- Código para generar reportes.


## Módulos pendientes

Si el análisis tiene módulos disponibles que todavía no se han generado, aparecerá una sección de módulos pendientes.

Desde esta sección puedes crear:

- Gráficas pendientes.
- Reportes SAES.
- Notebooks.

::: warning
Al generar módulos pendientes, la aplicación reutiliza el dataset y la configuración del análisis.
:::

![Módulos pendientes](/images/resultados_pendientes.png)