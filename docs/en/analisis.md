# Analysis screen

The analysis section is the core of the application. From here you can create, manage, and execute all available analyses.

![Analysis](/images/analisis.png)

---

## Analysis table

The main table displays all available analyses.

Each row contains:

- Analysis name.
- Update date.
- Status.
- Quick actions.

## Analysis statuses

Analyses can be in different states:

| Status | Description |
|---|---|
| Created | Analysis created but not executed |
| Running | Analysis currently running |
| Completed | Analysis completed successfully |
| Error | Error during execution |

## Available actions

Each analysis provides three actions:

### Open analysis

Allows access to the complete analysis detail screen.

From there you can:

- Inspect results.
- View plots.
- Download generated files.

### Edit analysis

Allows modifying the analysis name.

![Edit Analysis](/images/editar_analisis.png)

### Delete analysis

Completely removes the analysis and all associated results.

![Delete Analysis](/images/eliminar_analisis.png)

---

## Filters and search

The section includes an advanced filtering and search system.

You can:

- Search by name.
- Search by description.
- Filter by status.
- Sort results.

![Analysis Filters](/images/filtros_analisis.png)

## Create a new analysis

To create a new analysis press the button:

**New analysis**

![Analysis Modal](/images/modal_analisis.png)

## Basic information

The first section allows entering:

| Field | Description |
|---|---|
| Name | Analysis identifier name |
| Description | Optional description |

## Upload CSV dataset

The application mainly works with CSV datasets.

To upload a dataset:

1. Click the upload area.
2. Select a `.csv` file.
3. The application will automatically detect the available capabilities.

![Analysis Dataset](/images/dataset-analisis.png)

## Automatic dataset detection

After uploading the CSV, the application automatically analyzes:

- Detected metrics.
- Algorithms.
- Instances.
- Evolution columns.
- Fitness columns.
- Number of executions.

Several valid dataset formats are supported.

#### 1. SAES format

This format enables:

- SAES Plots
- SAES Reports
- Notebooks

##### Required columns

| Column | Data type | Description |
|---|---|---|
| Algorithm | string | Algorithm name |
| Instance | string | Problem, dataset, or instance |
| MetricName | string | Evaluated metric name |
| ExecutionId | integer | Independent execution identifier |
| MetricValue | float | Numeric metric value |

##### Example

```csv
Algorithm,Instance,MetricName,ExecutionId,MetricValue
GA,I1,fitness,1,0.45
GA,I1,fitness,2,0.39
PSO,I1,fitness,1,0.51
PSO,I1,fitness,2,0.47
```

#### 2. Evolution format

This format enables:

- Evolution Plots

##### Required columns

| Column | Data type | Description |
|---|---|---|
| Algorithm | string | Algorithm name |
| MetricValue | float | Fitness or metric value |
| Generation / Time / Evaluations | integer or float | Evolution X axis |

##### Example

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

#### 3. Combined SAES + Evolution format

Both formats can also be combined into a single CSV.

##### Recommended columns

| Column | Data type | Description |
|---|---|---|
| Algorithm | string | Algorithm name |
| Instance | string | Problem or instance |
| MetricName | string | Metric name |
| ExecutionId | integer | Execution identifier |
| Generation | integer or float | Generation or iteration |
| MetricValue | float | Fitness or metric value |

##### Example

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

## Detected compatibility

The application automatically detects whether the dataset supports:

| Module | Compatibility |
|---|---|
| SAES Plots | Yes / No |
| SAES Reports | Yes / No |
| Evolution Plots | Yes / No |
| Notebooks | Yes / No |

## Available modules

The user can activate different analysis modules if they are available for the uploaded dataset.

![Analysis Modules](/images/modulos_analisis.png)

### SAES Plots

Generates statistical plots using the SAES tool.

Includes:

- Boxplots.
- Violin plots.
- Histograms.
- Critical Distance plots.

### SAES Reports

Generates automatic statistical reports.

Includes tests such as:

- Friedman.
- Wilcoxon.
- Rankings.
- Statistical comparisons.

### Evolution Plots

Generates evolution and convergence plots.

Allows visualization of:

- Temporal evolution.
- Fitness.
- Generations.
- Evaluations.

### Notebooks

Generates ready-to-use interactive notebooks.

The notebooks include:

- Embedded dataset.
- Prepared code.
- Automatic plot generation.
- SAES reports.
- Reproducible results.

## Metrics configuration

The application allows defining whether a metric should:

- Be maximized.
- Be minimized.

#### Optional metrics CSV

It is also possible to upload an optional CSV file to automatically define whether each metric should be maximized or minimized.

##### Required columns

| Column | Data type | Description |
|---|---|---|
| MetricName | string | Metric name |
| Maximize | boolean | Indicates whether the metric should be maximized |

##### Example

```csv
MetricName,Maximize
accuracy,True
loss,False
fitness,True
error,False
```

If this file is provided, the application will automatically use these configurations during the analysis.

![Analysis Metrics CSV](/images/metricas.png)

## Export formats

Plots can be exported in different formats:

- PNG
- SVG
- EPS
- JPG
- JPEG

## Evolution plot configuration

When the dataset supports evolution, an advanced configuration section becomes available.

### X axis configuration

You can select different columns as the X axis:

- Generations.
- Time.
- Evaluations.
- Other detected columns.

### Label configuration

It is possible to customize:

- Plot title.
- X axis label.
- Y axis label.

### Visual options

Plots allow enabling or disabling:

| Option | Description |
|---|---|
| Grid | Background grid |
| Average | Average line |
| Median | Median line |
| Min/Max | Minimum and maximum limits |
| Standard deviation | Standard deviation band |

### Grouping

Plots can be automatically grouped:

- By instance.
- By metric.

## Run analysis

Once everything is configured:

1. Press **Create and run**.
2. The application will automatically start the pipeline.

<video src="/videos/crear_analisis.mp4" controls muted loop playsinline class="docs-video"></video>