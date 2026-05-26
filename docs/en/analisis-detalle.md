# Analysis detail

The detail screen allows you to inspect all information related to a specific analysis and access the generated results.

![Analysis Details](/images/analisis-detail.png)

## Main information

At the top of the page, the general analysis information is displayed.

This section includes:

- Analysis status.
- Analysis name.
- Description.
- Uploaded CSV filename.
- Number of executions.
- Number of plots.
- Number of reports.
- Number of notebooks.
- Number of metrics.
- Number of instances.

---

## Metrics and instances

The page displays two main panels:

- Detected metrics.
- Detected instances.

These panels allow you to quickly verify which dataset elements have been recognized.

![Metrics and instances](/images/m_instancias_analisis.png)

---

## Available results

The results section summarizes the generated modules.

![Available results](/images/modulos_disponibles.png)

Results are grouped into:

- Plots.
- Reports.
- Notebooks.

## Plots

The plots card provides access to all generated visualizations.

From this card you can:

- Open the plots screen.
- Download all available plots.
- View the total number of generated plots.

Plots may include:

- SAES plots.
- Evolution curves.

## Reports

The reports card provides access to the generated statistical results.

From this card you can:

- Open the reports screen.
- Download all reports.

Reports are available when the analysis supports SAES.

## Notebooks

The notebooks card allows downloading the generated notebook for the analysis.

The notebook may include:

- Embedded dataset.
- Metrics configuration.
- Plot generation code.
- Report generation code.

## Pending modules

If the analysis has available modules that have not yet been generated, a pending modules section will appear.

From this section you can generate:

- Pending plots.
- SAES reports.
- Notebooks.

::: warning
When generating pending modules, the application reuses the dataset and analysis configuration.
:::

![Pending modules](/images/resultados_pendientes.png)