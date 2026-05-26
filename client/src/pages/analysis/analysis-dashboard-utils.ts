import type {
  AnalysisModule,
  MetricDirection,
} from '../../features/analysis/analysis.types';
import type {
  CreationStep,
  DatasetCapability,
  EvolutionOptions,
  StatusFilter,
} from './analysis-dashboard-types';

export const MODULES: AnalysisModule[] = [
  'saes_plots',
  'saes_reports',
  'notebooks',
  'evolution_plots',
];

export const DEFAULT_EVOLUTION_OPTIONS: EvolutionOptions = {
  title: 'Curva de Convergencia',
  xColumns: [],
  xLabelsByColumn: {},
  yLabelsByMetric: {},

  showGrid: true,
  showMinMax: true,
  showStd: true,
  showAverage: true,
  showMedian: true,

  groupByInstance: true,
  groupByMetric: true,
};

const SAES_HEADERS = [
  'algorithm',
  'instance',
  'metricname',
  'executionid',
  'metricvalue',
];

const EVOLUTION_X_COLUMNS = [
  'time',
  'times',
  'tiempo',
  'timestamp',
  'elapsed',
  'elapsedtime',
  'elapsed_time',
  'evaluation',
  'evaluations',
  'evaluacion',
  'evaluaciones',
  'eval',
  'evals',
  'functionevaluation',
  'functionevaluations',
  'function_evaluation',
  'function_evaluations',
  'fe',
  'budget',
  'iteration',
  'iterations',
  'iteracion',
  'iteraciones',
  'generation',
  'generations',
  'generacion',
  'generaciones',
  'step',
  'steps',
  'epoch',
  'x',
];

const EVOLUTION_FITNESS_COLUMNS = [
  'metricvalue',
  'metric_value',
  'fitness',
  'bestfitness',
  'best_fitness',
  'best',
  'bestvalue',
  'best_value',
  'objectivevalue',
  'objective_value',
  'objective',
  'value',
  'valor',
  'score',
  'cost',
  'loss',
];

const EVOLUTION_RUN_COLUMNS = [
  'run',
  'seed',
  'executionid',
  'execution_id',
  'execution',
  'rep',
  'replicate',
  'repetition',
];

const INSTANCE_COLUMNS = ['instance', 'problem', 'problema', 'benchmark', 'case'];

/**
 * Returns the progress percentage for a given creation step.
 *
 * @param step Current creation workflow step.
 * @returns Progress percentage for the UI progress bar.
 */
export function getCreationProgress(step: CreationStep): number {
  switch (step) {
    case 'creating':
      return 25;
    case 'uploading_dataset':
      return 55;
    case 'running_analysis':
      return 85;
    case 'finished':
    case 'error':
      return 100;
    default:
      return 0;
  }
}

/**
 * Returns the i18n key associated with a creation step.
 *
 * @param step Current creation workflow step.
 * @returns Translation key for the status message.
 */
export function getCreationMessageKey(step: CreationStep): string {
  switch (step) {
    case 'creating':
      return 'analysis.dashboard.creation.creating';
    case 'uploading_dataset':
      return 'analysis.dashboard.creation.uploadingDataset';
    case 'running_analysis':
      return 'analysis.dashboard.creation.running';
    case 'finished':
      return 'analysis.dashboard.creation.finished';
    case 'error':
      return 'analysis.dashboard.creation.error';
    default:
      return 'analysis.dashboard.creation.ready';
  }
}

/**
 * Formats an ISO date string for display in Spanish locale.
 *
 * @param value Date string to format.
 * @returns Formatted date or a fallback dash.
 */
export function formatRelativeDate(value?: string) {
  if (!value) return '-';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return '-';

  return new Intl.DateTimeFormat('es-ES', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

/**
 * Converts a date string into a sortable timestamp.
 *
 * @param value Date string to convert.
 * @returns Milliseconds since epoch or 0 when invalid.
 */
export function getAnalysisTimestamp(value?: string) {
  if (!value) return 0;

  const timestamp = new Date(value).getTime();

  return Number.isNaN(timestamp) ? 0 : timestamp;
}

/**
 * Normalizes backend status values into dashboard buckets.
 *
 * @param status Raw analysis status.
 * @returns Normalized status bucket.
 */
export function getNormalizedStatus(status?: string) {
  const normalized = (status ?? '').toLowerCase();

  if (normalized === 'created' || normalized === 'dataset_uploaded') return 'created';

  if (
    normalized.includes('completed') ||
    normalized.includes('done') ||
    normalized.includes('success') ||
    normalized.includes('finished')
  ) {
    return 'completed';
  }

  if (normalized.includes('running') || normalized.includes('pending')) {
    return 'running';
  }

  if (normalized.includes('failed') || normalized.includes('error')) {
    return 'error';
  }

  return 'other';
}

/**
 * Checks whether a status matches the active dashboard filter.
 *
 * @param status Raw analysis status.
 * @param filter Active filter value.
 * @returns True when the item should be shown.
 */
export function matchesStatusFilter(status?: string, filter?: StatusFilter) {
  if (!filter || filter === 'all') return true;

  return getNormalizedStatus(status) === filter;
}

/**
 * Returns the CSS class used to style a status badge.
 *
 * @param status Raw analysis status.
 * @returns Tailwind-compatible badge class.
 */
export function getStatusBadgeClass(status?: string) {
  const normalized = (status ?? '').toLowerCase();

  if (normalized === 'created') {
    return 'pages-status-badge pages-status-created';
  }

  if (normalized === 'dataset_uploaded' || normalized.includes('uploaded')) {
    return 'pages-status-badge pages-status-dataset';
  }

  if (
    normalized.includes('completed') ||
    normalized.includes('done') ||
    normalized.includes('success') ||
    normalized.includes('finished')
  ) {
    return 'pages-status-badge pages-status-completed';
  }

  if (normalized.includes('running') || normalized.includes('pending')) {
    return 'pages-status-badge pages-status-running';
  }

  if (normalized.includes('failed') || normalized.includes('error')) {
    return 'pages-status-badge pages-status-error';
  }

  return 'pages-status-badge pages-status-default';
}

/**
 * Returns the i18n key for a status label.
 *
 * @param status Raw analysis status.
 * @returns Translation key or null when unknown.
 */
export function getStatusLabelKey(status?: string) {
  const normalized = (status ?? '').toLowerCase();

  if (normalized === 'created') return 'analysis.status.created';

  if (normalized === 'dataset_uploaded' || normalized.includes('uploaded')) {
    return 'analysis.status.datasetUploaded';
  }

  if (
    normalized.includes('completed') ||
    normalized.includes('done') ||
    normalized.includes('success') ||
    normalized.includes('finished')
  ) {
    return 'analysis.status.completed';
  }

  if (normalized.includes('running') || normalized.includes('pending')) {
    return 'analysis.status.running';
  }

  if (normalized.includes('failed') || normalized.includes('error')) {
    return 'analysis.status.error';
  }

  return null;
}

/**
 * Parses a CSV row while preserving quoted values.
 *
 * @param line Raw CSV line.
 * @returns Parsed column values.
 */
export function parseCsvLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];

    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }

  result.push(current.trim());

  return result;
}

/**
 * Normalizes a CSV header for resilient matching.
 *
 * @param value Raw header value.
 * @returns Lowercase ASCII-like header token.
 */
export function normalizeHeader(value: string) {
  return value
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]/g, '');
}

/**
 * Finds the first normalized header that matches one of the candidates.
 *
 * @param headers Normalized headers.
 * @param candidates Accepted names.
 * @returns Matching header or null.
 */
export function findHeader(headers: string[], candidates: string[]) {
  return headers.find((header) => candidates.includes(header)) ?? null;
}

/**
 * Checks whether a dataset contains the required SAES columns.
 *
 * @param headers Normalized headers.
 * @returns True when the dataset looks like a SAES export.
 */
export function hasSaesColumns(headers: string[]) {
  return SAES_HEADERS.every((header) => headers.includes(header));
}

/**
 * Deduplicates and sorts a list of strings using Spanish collation.
 *
 * @param values Candidate values.
 * @returns Sorted unique values.
 */
export function uniqueSorted(values: string[]) {
  return Array.from(new Set(values.filter(Boolean))).sort((a, b) =>
    a.localeCompare(b, 'es'),
  );
}

/**
 * Inspects an uploaded CSV to detect dataset capabilities and metadata.
 *
 * @param file CSV file selected by the user.
 * @returns Detected dataset capability summary.
 */
export async function inspectDataset(file: File): Promise<DatasetCapability> {
  const text = await file.text();

  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length < 2) {
    return {
      headers: [],
      originalHeaders: [],
      hasSaes: false,
      hasEvolution: false,
      metrics: [],
      detectedXColumns: [],
      detectedFitnessColumn: null,
      detectedRunColumn: null,
      detectedAlgorithmColumn: null,
      detectedInstanceColumn: null,
      rowCount: 0,
    };
  }

  const originalHeaders = parseCsvLine(lines[0]);
  const headers = originalHeaders.map(normalizeHeader);

  const algorithmColumn = findHeader(headers, ['algorithm', 'algoritmo']);
  const instanceColumn = findHeader(headers, INSTANCE_COLUMNS);
  const fitnessColumn = findHeader(headers, EVOLUTION_FITNESS_COLUMNS);
  const runColumn = findHeader(headers, EVOLUTION_RUN_COLUMNS);

  const metricIndex = headers.indexOf('metricname');

  const detectedXColumns = originalHeaders.filter((_header, index) =>
    EVOLUTION_X_COLUMNS.includes(headers[index]),
  );

  const metrics = new Set<string>();

  for (let index = 1; index < lines.length; index += 1) {
    const cells = parseCsvLine(lines[index]);
    const metric = metricIndex !== -1 ? cells[metricIndex]?.trim() : '';

    if (metric) metrics.add(metric);
  }

  if (!metrics.size && fitnessColumn) {
    metrics.add(fitnessColumn);
  }

  return {
    headers,
    originalHeaders,
    hasSaes: hasSaesColumns(headers),
    hasEvolution: Boolean(
      algorithmColumn && detectedXColumns.length > 0 && fitnessColumn,
    ),
    metrics: uniqueSorted(Array.from(metrics)),
    detectedXColumns,
    detectedFitnessColumn: fitnessColumn,
    detectedRunColumn: runColumn,
    detectedAlgorithmColumn: algorithmColumn,
    detectedInstanceColumn: instanceColumn,
    rowCount: Math.max(0, lines.length - 1),
  };
}

/**
 * Extracts metric optimization directions from a metrics CSV file.
 *
 * @param file Metrics CSV file.
 * @returns Metric directions or null when the file does not match the expected shape.
 */
export async function extractMetricDirectionsFromMetricsCsv(
  file: File,
): Promise<Record<string, MetricDirection> | null> {
  const text = await file.text();

  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length < 2) return null;

  const headers = parseCsvLine(lines[0]).map(normalizeHeader);
  const metricNameIndex = headers.indexOf('metricname');
  const maximizeIndex = headers.indexOf('maximize');

  if (metricNameIndex === -1 || maximizeIndex === -1) return null;

  const result: Record<string, MetricDirection> = {};

  for (let index = 1; index < lines.length; index += 1) {
    const cells = parseCsvLine(lines[index]);
    const metric = cells[metricNameIndex]?.trim();
    const maximize = cells[maximizeIndex]?.trim().toLowerCase();

    if (!metric) continue;
    if (maximize !== 'true' && maximize !== 'false') continue;

    result[metric] = maximize === 'true' ? 'maximize' : 'minimize';
  }

  return Object.keys(result).length ? result : null;
}

/**
 * Returns the human-readable label for an analysis module.
 *
 * @param module Analysis module identifier.
 * @returns Localized label used in the UI.
 */
export function getModuleLabel(module: AnalysisModule) {
  switch (module) {
    case 'saes_plots':
      return 'Gráficas SAES';
    case 'saes_reports':
      return 'Reportes SAES';
    case 'notebooks':
      return 'Notebook';
    case 'evolution_plots':
      return 'Gráficas de evolución';
    default:
      return module;
  }
}

/**
 * Returns the short description shown for an analysis module.
 *
 * @param module Analysis module identifier.
 * @returns Descriptive copy for the module card.
 */
export function getModuleDescription(module: AnalysisModule) {
  switch (module) {
    case 'saes_plots':
      return 'Boxplot, violin, histogramas y distancia crítica generados con SAES.';
    case 'saes_reports':
      return 'Tablas estadísticas SAES en LaTeX y previsualización JSON.';
    case 'notebooks':
      return 'Notebook Jupyter reproducible con datos, reportes y gráficas.';
    case 'evolution_plots':
      return 'Curvas de convergencia configurables con media, mediana, min/max y desviación estándar.';
    default:
      return '';
  }
}

/**
 * Checks whether a module belongs to the SAES feature set.
 *
 * @param module Analysis module identifier.
 * @returns True for SAES modules.
 */
export function isSaesModule(module: AnalysisModule) {
  return module === 'saes_plots' || module === 'saes_reports' || module === 'notebooks';
}

/**
 * Checks whether a module belongs to the evolution feature set.
 *
 * @param module Analysis module identifier.
 * @returns True for evolution plots.
 */
export function isEvolutionModule(module: AnalysisModule) {
  return module === 'evolution_plots';
}

/**
 * Explains why a module cannot be enabled for the current dataset.
 *
 * @param module Analysis module identifier.
 * @param capability Detected dataset capability summary.
 * @returns Human-readable disable reason or null.
 */
export function getModuleDisabledReason(
  module: AnalysisModule,
  capability: DatasetCapability | null,
) {
  if (!capability) return 'Sube un CSV para detectar los módulos disponibles.';

  if (isSaesModule(module) && !capability.hasSaes) {
    return 'Deshabilitado: el CSV no tiene el formato SAES requerido.';
  }

  if (isEvolutionModule(module) && !capability.hasEvolution) {
    return 'Deshabilitado: el CSV no tiene columnas de evolución suficientes.';
  }

  return null;
}

/**
 * Checks whether a module is enabled for the detected dataset.
 *
 * @param module Analysis module identifier.
 * @param capability Detected dataset capability summary.
 * @returns True when the module can be used.
 */
export function isModuleEnabled(
  module: AnalysisModule,
  capability: DatasetCapability | null,
) {
  return getModuleDisabledReason(module, capability) === null;
}

/**
 * Filters out modules that are not supported by the current dataset.
 *
 * @param modules Selected modules.
 * @param capability Detected dataset capability summary.
 * @returns Supported modules only.
 */
export function normalizeSelectedModulesForCapability(
  modules: AnalysisModule[],
  capability: DatasetCapability | null,
): AnalysisModule[] {
  if (!capability) return [];

  return modules.filter((module) => isModuleEnabled(module, capability));
}

/**
 * Builds the default module list for the detected dataset.
 *
 * @param capability Detected dataset capability summary.
 * @returns Default modules available to the user.
 */
export function getDefaultModulesForCapability(
  capability: DatasetCapability | null,
): AnalysisModule[] {
  if (!capability) return [];

  const modules: AnalysisModule[] = [];

  if (capability.hasSaes) modules.push('saes_plots');
  if (capability.hasEvolution) modules.push('evolution_plots');

  return modules;
}

/**
 * Adds or removes a string from a selection list.
 *
 * @param values Current values.
 * @param value Value to toggle.
 * @returns Updated selection list.
 */
export function toggleString(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

/**
 * Builds a default label map where each X column maps to itself.
 *
 * @param columns X-axis columns.
 * @returns Default X labels keyed by column name.
 */
export function buildDefaultXLabels(columns: string[]): Record<string, string> {
  return Object.fromEntries(columns.map((column) => [column, column]));
}

/**
 * Builds a default label map for metrics.
 *
 * @param metrics Metric names.
 * @returns Default Y labels keyed by metric name.
 */
export function buildDefaultYLabels(metrics: string[]): Record<string, string> {
  return Object.fromEntries(metrics.map((metric) => [metric, metric || 'Fitness']));
}
