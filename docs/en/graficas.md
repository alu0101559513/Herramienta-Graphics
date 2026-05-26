# Plots screen

The plots screen allows viewing, filtering, downloading, and regenerating all plots generated during an analysis.

From this section you can work with both:

- SAES plots.
- Evolution plots.

![Plots screen](/images/graficas.png)

---

## SAES plots

SAES plots include classic statistical visualizations such as:

- Boxplot.
- Violin Plot.
- Histograms.
- Critical Distance Diagram.

## Evolution plots

Evolution plots allow analyzing how a metric changes during algorithm executions.

These plots can display:

- Mean.
- Median.
- Standard deviation.
- Minimum and maximum values.

::: tip
Statistical layers can be enabled or disabled from the configuration panel.
:::

## Download all plots

If plots are available, the following button will appear:

**Download all**

This button automatically generates a ZIP file containing:

- SAES plots.
- Evolution plots.

## Filter system

![SAES filters](/images/filtros_saes.png)

### Filter by algorithm

Allows displaying only plots belonging to specific algorithms.

You can select:

- One algorithm.
- Multiple algorithms.
- All algorithms.

### Filter by plot type

Allows displaying only specific plot types.

Examples:

- Evolution.
- Boxplot.
- Violin.
- Histogram.
- Critical Distance.

### Filter by format

Allows filtering by file extension.

Examples:

- PNG.
- EPS.
- SVG.
- JPG.
- JPEG.

### Filter by metric

Allows displaying only plots related to specific metrics.

For example:

- Accuracy.
- Hypervolume.
- Fitness.

## Filter by instance

Allows displaying only plots associated with specific instances or problems.

## Search bar

The search bar allows locating plots by typing:

- Filename.
- Metric name.
- Instance name.
- Plot type.
- Format.

## Evolution options

The screen includes a dedicated panel for configuring evolution plots.

![Evolution filters](/images/filtros_evolucion.png)

### Statistical layers

You can enable or disable:

- Mean.
- Median.
- Standard deviation.
- Min/Max.

### Grid

The Grid option adds or removes the background grid from plots.

### Group by instance

Generates separate plots grouped by detected instance.

### Group by metric

Generates independent plots for each metric.

## Apply changes

After modifying filters or evolution options, you must click:

**Apply**

The application will automatically regenerate the required plots.

## Visual configuration

This section allows customizing the visual presentation of plots on screen.

![Visualization filters](/images/filtros_visualizacion.png)

### Number of columns

You can choose:

- 1 column.
- 2 columns.
- 3 columns.
- 4 columns.

### Number of visible rows

Controls how many rows are displayed simultaneously.

### Image size

You can adjust visual density:

| Option | Description |
|---|---|
| Low | Compact plots |
| Medium | Balanced size |
| High | Larger visual size |

### Image fit

There are two main modes:

| Mode | Description |
|---|---|
| Contain | The full image is always visible |
| Cover | The image completely fills the available space |

### Show metadata

The metadata option allows displaying:

- Plot type.
- Metric.
- Instance.
- X column.
- Format.
- Filename.

<video src="/videos/graficas.mp4" controls muted loop playsinline class="docs-video"></video>