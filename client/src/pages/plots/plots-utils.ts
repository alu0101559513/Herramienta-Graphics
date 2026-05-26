import { SAES_PLOT_TYPES } from './plots.constants';
import { DEFAULT_EVOLUTION_OPTIONS } from '../../features/analysis/analysis.constants';
import type {
  AnalysisModule,
  EvolutionAnalyzeOptions,
  EvolutionMetadata,
  EvolutionStatistic,
} from '../../features/analysis/analysis.types';
import type {
  ImageFit,
  ImageHeight,
  PlotItem,
  PlotType,
  SaesPlotType,
} from './plots-types';

/**
 * Checks whether a value is a plain object record.
 *
 * @param value Candidate value.
 * @returns True when the value is an object record.
 */
export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/**
 * Checks whether a file can be previewed as an image.
 *
 * @param fileName File name.
 * @returns True for previewable image extensions.
 */
export function isPreviewableImage(fileName: string) {
  const lower = fileName.toLowerCase();

  return (
    lower.endsWith('.png') ||
    lower.endsWith('.jpg') ||
    lower.endsWith('.jpeg') ||
    lower.endsWith('.webp') ||
    lower.endsWith('.svg')
  );
}

/**
 * Checks whether a file is a supported plot artifact.
 *
 * @param fileName File name.
 * @returns True for supported plot extensions.
 */
export function isSupportedPlotFile(fileName: string) {
  const lower = fileName.toLowerCase();

  return (
    lower.endsWith('.png') ||
    lower.endsWith('.jpg') ||
    lower.endsWith('.jpeg') ||
    lower.endsWith('.webp') ||
    lower.endsWith('.svg') ||
    lower.endsWith('.pdf') ||
    lower.endsWith('.eps')
  );
}

/**
 * Returns the lowercased file extension.
 *
 * @param fileName File name.
 * @returns File extension or an empty string.
 */
export function getFileExtension(fileName: string) {
  const parts = fileName.toLowerCase().split('.');
  return parts.length > 1 ? parts[parts.length - 1] : '';
}

/**
 * Normalizes a token extracted from a plot file name.
 *
 * @param value Raw token value.
 * @returns Cleaned token or null.
 */
export function cleanToken(value: string | null | undefined) {
  if (!value) return null;

  const cleaned = value
    .replace(/^convergence[_-]/i, '')
    .replace(/[_-]convergence$/i, '')
    .replace(/^evolution[_-]/i, '')
    .replace(/[_-]evolution$/i, '')
    .replace(/^progress[_-]/i, '')
    .replace(/[_-]progress$/i, '')
    .replace(/^line[_-]/i, '')
    .replace(/[_-]line$/i, '')
    .replace(/[_-]+/g, ' ')
    .trim();

  return cleaned || null;
}

/**
 * Returns the display label for an evolution statistic.
 *
 * @param statistic Evolution statistic identifier.
 * @returns Human-readable label.
 */
export function getEvolutionStatisticLabel(statistic: EvolutionStatistic) {
  switch (statistic) {
    case 'std':
      return 'Desviación';
    case 'median':
      return 'Mediana';
    case 'mean':
      return 'Media';
    case 'min_max':
      return 'Min / Max';
  }
}

/**
 * Extracts the enabled evolution statistics from the form options.
 *
 * @param options Evolution analysis options.
 * @returns Enabled statistics.
 */
export function getEvolutionStatisticsFromOptions(
  options: EvolutionAnalyzeOptions,
): EvolutionStatistic[] {
  const result: EvolutionStatistic[] = [];

  if (options.showStd) result.push('std');
  if (options.showMedian) result.push('median');
  if (options.showAverage) result.push('mean');
  if (options.showMinMax) result.push('min_max');

  return result;
}

/**
 * Extracts the enabled evolution statistics from persisted metadata.
 *
 * @param metadata Evolution metadata.
 * @returns Enabled statistics.
 */
export function getEvolutionStatisticsFromMetadata(
  metadata?: EvolutionMetadata | null,
): EvolutionStatistic[] {
  if (!metadata) {
    return getEvolutionStatisticsFromOptions(DEFAULT_EVOLUTION_OPTIONS);
  }

  const result: EvolutionStatistic[] = [];

  if (metadata.show_std !== false) result.push('std');
  if (metadata.show_median !== false) result.push('median');
  if (metadata.show_average !== false) result.push('mean');
  if (metadata.show_min_max !== false) result.push('min_max');

  return result.length > 0
    ? result
    : getEvolutionStatisticsFromOptions(DEFAULT_EVOLUTION_OPTIONS);
}

/**
 * Applies statistic toggles to the evolution options.
 *
 * @param options Current evolution options.
 * @param statistics Selected evolution statistics.
 * @returns Updated evolution options.
 */
export function applyEvolutionStatisticsToOptions(
  options: EvolutionAnalyzeOptions,
  statistics: EvolutionStatistic[],
): EvolutionAnalyzeOptions {
  return {
    ...options,
    showStd: statistics.includes('std'),
    showMedian: statistics.includes('median'),
    showAverage: statistics.includes('mean'),
    showMinMax: statistics.includes('min_max'),
  };
}

/**
 * Parses metadata from an evolution plot file name.
 *
 * @param fileName Plot file name.
 * @returns Parsed plot metadata.
 */
export function parseEvolutionPlotInfo(
  fileName: string,
): Omit<PlotItem, 'category' | 'extension'> {
  const base = fileName.replace(/\.(png|jpg|jpeg|webp|svg|pdf|eps)$/i, '');
  const withoutPrefix = base.replace(/^(convergence|evolution|progress|line)[_-]/i, '');
  const withoutSuffix = withoutPrefix.replace(
    /[_-](convergence|evolution|progress|line)$/i,
    '',
  );

  const parts = withoutSuffix.split(/[_-]/).filter(Boolean);

  const metric = parts.length > 0 ? cleanToken(parts[0]) : cleanToken(base);
  const xColumn = parts.length > 2 ? cleanToken(parts[parts.length - 1]) : null;
  const instance =
    parts.length > 2
      ? cleanToken(parts.slice(1, -1).join('_'))
      : parts.length > 1
      ? cleanToken(parts.slice(1).join('_'))
      : null;

  return {
    fileName,
    type: 'evolution',
    metric,
    instance,
    xColumn,
  };
}

/**
 * Parses metadata from a SAES plot file name.
 *
 * @param fileName Plot file name.
 * @returns Parsed plot metadata or null when unsupported.
 */
export function parseSaesPlotInfo(
  fileName: string,
): Omit<PlotItem, 'category' | 'extension'> | null {
  const base = fileName.replace(/\.(png|jpg|jpeg|webp|svg|pdf|eps)$/i, '');

  if (base.endsWith('_critical_distance')) {
    return {
      fileName,
      type: 'critical_distance',
      metric: cleanToken(base.replace(/_critical_distance$/i, '')),
      instance: null,
      xColumn: null,
    };
  }

  for (const type of ['boxplot', 'violin', 'histogram'] as const) {
    if (!base.endsWith(`_${type}`)) continue;

    const withoutType = base.slice(0, -(type.length + 1));
    const lastUnderscore = withoutType.lastIndexOf('_');

    return {
      fileName,
      type,
      metric:
        lastUnderscore === -1
          ? cleanToken(withoutType)
          : cleanToken(withoutType.slice(0, lastUnderscore)),
      instance:
        lastUnderscore === -1 ? null : cleanToken(withoutType.slice(lastUnderscore + 1)),
      xColumn: null,
    };
  }

  return null;
}

/**
 * Parses plot metadata from a file name and category.
 *
 * @param category Plot category.
 * @param fileName Plot file name.
 * @returns Parsed plot metadata or null when unsupported.
 */
export function parsePlotInfo(
  category: string,
  fileName: string,
): Omit<PlotItem, 'category' | 'extension'> | null {
  if (category === 'evolution_plots') return parseEvolutionPlotInfo(fileName);

  const saesPlotInfo = parseSaesPlotInfo(fileName);
  if (saesPlotInfo) return saesPlotInfo;

  const lower = fileName.toLowerCase();

  if (
    lower.includes('convergence') ||
    lower.includes('evolution') ||
    lower.includes('progress') ||
    lower.includes('line')
  ) {
    return parseEvolutionPlotInfo(fileName);
  }

  return null;
}

/**
 * Returns the translation key for a plot type label.
 *
 * @param type Plot type identifier.
 * @returns Translation key for the plot type.
 */
export function getPlotTypeLabel(type: PlotType) {
  switch (type) {
    case 'evolution':
      return 'analysis.plots.plotType.evolution';
    case 'boxplot':
      return 'analysis.plots.plotType.boxplot';
    case 'violin':
      return 'analysis.plots.plotType.violin';
    case 'histogram':
      return 'analysis.plots.plotType.histogram';
    case 'critical_distance':
      return 'analysis.plots.plotType.criticalDistance';
    default:
      return 'analysis.plots.plotType.unknown';
  }
}

/**
 * Returns the CSS height class for a plot image.
 *
 * @param imageHeight Desired image height preset.
 * @returns Tailwind height class.
 */
export function getImageHeightClass(imageHeight: ImageHeight) {
  switch (imageHeight) {
    case 'sm':
      return 'h-[260px]';
    case 'md':
      return 'h-[360px]';
    case 'lg':
      return 'h-[500px]';
  }
}

/**
 * Returns the CSS fit class for a plot image.
 *
 * @param imageFit Desired image fit mode.
 * @returns Tailwind fit class.
 */
export function getImageFitClass(imageFit: ImageFit) {
  return imageFit === 'cover' ? 'object-cover' : 'object-contain';
}

/**
 * Deduplicates, trims and sorts a string list.
 *
 * @param values Candidate values.
 * @returns Normalized values.
 */
export function normalizeValues(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean))).sort(
    (a, b) => a.localeCompare(b),
  );
}

/**
 * Deduplicates and sorts plot types.
 *
 * @param values Candidate plot types.
 * @returns Normalized plot types.
 */
export function normalizePlotTypes(values: PlotType[]) {
  return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b));
}

/**
 * Deduplicates and sorts evolution statistics.
 *
 * @param values Candidate statistics.
 * @returns Normalized statistics.
 */
export function normalizeEvolutionStatistics(values: EvolutionStatistic[]) {
  return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b));
}

/**
 * Filters the plot types down to the SAES-specific subset.
 *
 * @param values Candidate plot types.
 * @returns SAES plot types only.
 */
export function normalizeSaesPlotTypes(values: PlotType[]) {
  return values.filter((value): value is SaesPlotType =>
    SAES_PLOT_TYPES.includes(value as SaesPlotType),
  );
}

/**
 * Compares two string arrays as unordered sets.
 *
 * @param a First array.
 * @param b Second array.
 * @returns True when both arrays contain the same values.
 */
export function arraysEqualAsSet(a: string[], b: string[]) {
  const aa = normalizeValues(a);
  const bb = normalizeValues(b);

  return aa.length === bb.length && aa.every((value, index) => value === bb[index]);
}

/**
 * Compares two plot type arrays as unordered sets.
 *
 * @param a First array.
 * @param b Second array.
 * @returns True when both arrays contain the same values.
 */
export function plotTypeArraysEqualAsSet(a: PlotType[], b: PlotType[]) {
  const aa = normalizePlotTypes(a);
  const bb = normalizePlotTypes(b);

  return aa.length === bb.length && aa.every((value, index) => value === bb[index]);
}

/**
 * Compares two evolution statistic arrays as unordered sets.
 *
 * @param a First array.
 * @param b Second array.
 * @returns True when both arrays contain the same values.
 */
export function evolutionStatisticArraysEqualAsSet(
  a: EvolutionStatistic[],
  b: EvolutionStatistic[],
) {
  const aa = normalizeEvolutionStatistics(a);
  const bb = normalizeEvolutionStatistics(b);

  return aa.length === bb.length && aa.every((value, index) => value === bb[index]);
}

/**
 * Builds a stable run key from the selected algorithms.
 *
 * @param selectedAlgorithms Selected algorithms.
 * @param allAlgorithms Complete algorithm list.
 * @returns Stable run key.
 */
export function buildAlgorithmRunKey(
  selectedAlgorithms: string[],
  allAlgorithms: string[],
) {
  const cleanedSelected = normalizeValues(selectedAlgorithms);
  const cleanedAll = normalizeValues(allAlgorithms);

  if (cleanedSelected.length === 0 || arraysEqualAsSet(cleanedSelected, cleanedAll)) {
    return 'all';
  }

  return cleanedSelected
    .map((value) => value.toLowerCase().replace(/\s+/g, '_').replace(/[\\/]/g, '_'))
    .join('__');
}

/**
 * Stringifies a value with stable key ordering.
 *
 * @param value Value to stringify.
 * @returns Stable JSON string.
 */
function stableStringify(value: unknown): string {
  const normalize = (input: unknown): unknown => {
    if (input === undefined || input === null) return null;
    if (Array.isArray(input)) return input.map(normalize);

    if (typeof input === 'object') {
      const source = input as Record<string, unknown>;
      const result: Record<string, unknown> = {};

      Object.keys(source)
        .sort()
        .forEach((key) => {
          result[key] = normalize(source[key]);
        });

      return result;
    }

    return input;
  };

  return JSON.stringify(normalize(value));
}

/**
 * Normalizes a string record into a stable sorted object.
 *
 * @param value Source string record.
 * @returns Sorted and trimmed record.
 */
function stableStringRecord(value: Record<string, string> = {}) {
  return Object.fromEntries(
    Object.entries(value)
      .map(([key, item]) => [key.trim(), String(item ?? '').trim()])
      .filter(([key, item]) => key && item)
      .sort(([a], [b]) => a.localeCompare(b)),
  );
}

/**
 * Builds a stable signature object for evolution options.
 *
 * @param options Evolution options.
 * @param selectedAlgorithms Selected algorithms.
 * @param selectedMetrics Selected metrics.
 * @param selectedInstances Selected instances.
 * @returns Stable signature object.
 */
export function buildEvolutionOptionsSignature(
  options: EvolutionAnalyzeOptions,
  selectedAlgorithms: string[] = [],
  selectedMetrics: string[] = [],
  selectedInstances: string[] = [],
) {
  return {
    title: (options.title || '').trim() || null,
    x_columns: normalizeValues(options.xColumns),
    x_label: null,
    y_label: null,
    x_labels_by_column: stableStringRecord(options.xLabelsByColumn),
    y_labels_by_metric: stableStringRecord(options.yLabelsByMetric),
    selected_algorithms: normalizeValues(selectedAlgorithms),
    selected_metrics: normalizeValues(selectedMetrics),
    selected_instances: normalizeValues(selectedInstances),
    show_grid: Boolean(options.showGrid),
    show_min_max: Boolean(options.showMinMax),
    show_std: Boolean(options.showStd),
    show_average: Boolean(options.showAverage),
    show_median: Boolean(options.showMedian),
    group_by_instance: Boolean(options.groupByInstance),
    group_by_metric: Boolean(options.groupByMetric),
  };
}

/**
 * Checks whether stored outputs match a given evolution options signature.
 *
 * @param outputs Stored run outputs.
 * @param options Evolution options.
 * @param selectedAlgorithms Selected algorithms.
 * @param selectedMetrics Selected metrics.
 * @param selectedInstances Selected instances.
 * @returns True when the signature matches.
 */
function evolutionOptionsMatchSignature(
  outputs: Record<string, unknown> | null,
  options: EvolutionAnalyzeOptions,
  selectedAlgorithms: string[] = [],
  selectedMetrics: string[] = [],
  selectedInstances: string[] = [],
) {
  if (!outputs) return false;

  const storedSignature = outputs.evolution_options_signature;

  if (typeof storedSignature !== 'string' || !storedSignature.trim()) {
    return false;
  }

  try {
    const parsed = JSON.parse(storedSignature);
    const expected = buildEvolutionOptionsSignature(
      options,
      selectedAlgorithms,
      selectedMetrics,
      selectedInstances,
    );

    return stableStringify(parsed) === stableStringify(expected);
  } catch {
    return false;
  }
}

/**
 * Builds a cache key for the current selection state.
 *
 * @param selectedAlgorithms Selected algorithms.
 * @param selectedPlotTypes Selected plot types.
 * @param evolutionOptions Evolution options.
 * @param selectedMetrics Selected metrics.
 * @param selectedInstances Selected instances.
 * @returns Stable selection signature.
 */
export function buildSelectionSignature(
  selectedAlgorithms: string[],
  selectedPlotTypes: PlotType[],
  evolutionOptions: EvolutionAnalyzeOptions,
  selectedMetrics: string[] = [],
  selectedInstances: string[] = [],
) {
  const algorithmsKey = normalizeValues(selectedAlgorithms).join('||');
  const normalizedPlotTypes = normalizePlotTypes(selectedPlotTypes);
  const plotTypesKey = normalizedPlotTypes.join('||') || 'all_plot_types';

  const evolutionKey =
    normalizedPlotTypes.length === 0 || normalizedPlotTypes.includes('evolution')
      ? stableStringify(
          buildEvolutionOptionsSignature(
            evolutionOptions,
            selectedAlgorithms,
            selectedMetrics,
            selectedInstances,
          ),
        )
      : 'no_evolution';

  return `${algorithmsKey}::${plotTypesKey}::${evolutionKey}`;
}

/**
 * Resolves backend modules required for the selected plot types.
 *
 * @param selectedPlotTypes Selected plot types.
 * @param hasSaesCapability Whether SAES plots are supported.
 * @param hasEvolutionCapability Whether evolution plots are supported.
 * @returns Backend modules to request.
 */
export function getModulesForPlotTypes(
  selectedPlotTypes: PlotType[],
  hasSaesCapability: boolean,
  hasEvolutionCapability: boolean,
): AnalysisModule[] {
  if (selectedPlotTypes.length === 0) {
    return [
      ...(hasSaesCapability ? (['saes_plots'] as AnalysisModule[]) : []),
      ...(hasEvolutionCapability ? (['evolution_plots'] as AnalysisModule[]) : []),
    ];
  }

  const modules = new Set<AnalysisModule>();

  if (hasEvolutionCapability && selectedPlotTypes.includes('evolution')) {
    modules.add('evolution_plots');
  }

  if (
    hasSaesCapability &&
    selectedPlotTypes.some((type) => SAES_PLOT_TYPES.includes(type as SaesPlotType))
  ) {
    modules.add('saes_plots');
  }

  return Array.from(modules);
}

/**
 * Resolves the run-specific outputs from a backend payload.
 *
 * @param outputs Raw outputs payload.
 * @param runKey Run key to resolve.
 * @returns Run-specific outputs or null.
 */
export function getRunOutputs(
  outputs: unknown,
  runKey: string,
): Record<string, unknown> | null {
  if (!isRecord(outputs)) return null;

  const analysisRuns = isRecord(outputs.analysis_runs) ? outputs.analysis_runs : null;

  if (analysisRuns && isRecord(analysisRuns[runKey])) {
    return analysisRuns[runKey] as Record<string, unknown>;
  }

  return outputs;
}

/**
 * Checks whether a value looks like a category-to-files map.
 *
 * @param value Candidate value.
 * @returns True when the value is a non-empty object.
 */
export function hasFileMap(value: unknown) {
  return isRecord(value) && Object.keys(value).length > 0;
}

/**
 * Normalizes the X column list from evolution metadata.
 *
 * @param value Candidate metadata value.
 * @returns List of X columns.
 */
export function normalizeMetadataXColumns(value: unknown) {
  if (!isRecord(value)) return [];

  return Array.isArray(value.x_columns)
    ? value.x_columns.filter((item): item is string => typeof item === 'string')
    : [];
}

/**
 * Checks whether stored outputs match the current evolution options.
 *
 * @param outputs Stored run outputs.
 * @param options Evolution options.
 * @param selectedAlgorithms Selected algorithms.
 * @param selectedMetrics Selected metrics.
 * @param selectedInstances Selected instances.
 * @returns True when the metadata matches.
 */
export function evolutionOptionsMatchMetadata(
  outputs: Record<string, unknown> | null,
  options: EvolutionAnalyzeOptions,
  selectedAlgorithms: string[] = [],
  selectedMetrics: string[] = [],
  selectedInstances: string[] = [],
) {
  if (!outputs) return false;

  const metadata = isRecord(outputs.evolution_metadata)
    ? (outputs.evolution_metadata as EvolutionMetadata)
    : null;

  if (
    evolutionOptionsMatchSignature(
      outputs,
      options,
      selectedAlgorithms,
      selectedMetrics,
      selectedInstances,
    )
  ) {
    return true;
  }

  if (
    normalizeValues(selectedAlgorithms).length > 0 ||
    normalizeValues(selectedMetrics).length > 0 ||
    normalizeValues(selectedInstances).length > 0
  ) {
    return false;
  }

  if (!metadata) return false;

  const metadataXColumns = normalizeMetadataXColumns(metadata);
  const metadataStatistics = getEvolutionStatisticsFromMetadata(metadata);
  const optionsStatistics = getEvolutionStatisticsFromOptions(options);

  const xColumnsMatch =
    options.xColumns.length === 0 || arraysEqualAsSet(metadataXColumns, options.xColumns);

  const statisticsMatch = evolutionStatisticArraysEqualAsSet(
    metadataStatistics,
    optionsStatistics,
  );

  const showGridMatch =
    typeof metadata.show_grid !== 'boolean' || metadata.show_grid === options.showGrid;

  const groupByInstanceMatch =
    typeof metadata.group_by_instance !== 'boolean' ||
    metadata.group_by_instance === options.groupByInstance;

  const groupByMetricMatch =
    typeof metadata.group_by_metric !== 'boolean' ||
    metadata.group_by_metric === options.groupByMetric;

  const titleMatch =
    typeof metadata.title !== 'string' ||
    metadata.title === options.title ||
    options.title.trim().length === 0;

  return (
    xColumnsMatch &&
    statisticsMatch &&
    showGridMatch &&
    groupByInstanceMatch &&
    groupByMetricMatch &&
    titleMatch
  );
}

/**
 * Checks whether the current selection was already generated.
 *
 * @param outputs Stored analysis outputs.
 * @param runKey Run key.
 * @param selectedPlotTypes Selected plot types.
 * @param evolutionOptions Evolution options.
 * @param selectedAlgorithms Selected algorithms.
 * @param selectedMetrics Selected metrics.
 * @param selectedInstances Selected instances.
 * @returns True when the selection is already available.
 */
export function selectionAlreadyGenerated(
  outputs: unknown,
  runKey: string,
  selectedPlotTypes: PlotType[],
  evolutionOptions: EvolutionAnalyzeOptions,
  selectedAlgorithms: string[] = [],
  selectedMetrics: string[] = [],
  selectedInstances: string[] = [],
) {
  const runOutputs = getRunOutputs(outputs, runKey);

  if (!runOutputs) return false;

  const needsEvolution =
    selectedPlotTypes.length === 0 || selectedPlotTypes.includes('evolution');

  const needsSaes =
    selectedPlotTypes.length === 0 ||
    selectedPlotTypes.some((type) => SAES_PLOT_TYPES.includes(type as SaesPlotType));

  const evolutionOk =
    !needsEvolution ||
    (hasFileMap(runOutputs.evolution_plots) &&
      evolutionOptionsMatchMetadata(
        runOutputs,
        evolutionOptions,
        selectedAlgorithms,
        selectedMetrics,
        selectedInstances,
      ));

  const generatedPlotTypes = Array.isArray(runOutputs.generated_plot_types)
    ? runOutputs.generated_plot_types.filter(
        (item): item is string => typeof item === 'string',
      )
    : [];

  const selectedSaesTypes = normalizeSaesPlotTypes(selectedPlotTypes);

  const saesOk =
    !needsSaes ||
    (hasFileMap(runOutputs.saes_plots) &&
      (selectedSaesTypes.length === 0 ||
        selectedSaesTypes.every((type) => generatedPlotTypes.includes(type))));

  return evolutionOk && saesOk;
}

/**
 * Builds evolution form options from stored metadata.
 *
 * @param metadata Evolution metadata.
 * @returns Form-ready evolution options.
 */
export function getEvolutionOptionsFromMetadata(
  metadata?: EvolutionMetadata | null,
): EvolutionAnalyzeOptions {
  return {
    ...DEFAULT_EVOLUTION_OPTIONS,
    title: metadata?.title || DEFAULT_EVOLUTION_OPTIONS.title,
    xColumns: metadata?.x_columns || [],
    xLabelsByColumn: metadata?.x_labels_by_column || {},
    yLabelsByMetric: metadata?.y_labels_by_metric || {},
    showGrid:
      typeof metadata?.show_grid === 'boolean'
        ? metadata.show_grid
        : DEFAULT_EVOLUTION_OPTIONS.showGrid,
    showMinMax:
      typeof metadata?.show_min_max === 'boolean'
        ? metadata.show_min_max
        : DEFAULT_EVOLUTION_OPTIONS.showMinMax,
    showStd:
      typeof metadata?.show_std === 'boolean'
        ? metadata.show_std
        : DEFAULT_EVOLUTION_OPTIONS.showStd,
    showAverage:
      typeof metadata?.show_average === 'boolean'
        ? metadata.show_average
        : DEFAULT_EVOLUTION_OPTIONS.showAverage,
    showMedian:
      typeof metadata?.show_median === 'boolean'
        ? metadata.show_median
        : DEFAULT_EVOLUTION_OPTIONS.showMedian,
    groupByInstance:
      typeof metadata?.group_by_instance === 'boolean'
        ? metadata.group_by_instance
        : DEFAULT_EVOLUTION_OPTIONS.groupByInstance,
    groupByMetric:
      typeof metadata?.group_by_metric === 'boolean'
        ? metadata.group_by_metric
        : DEFAULT_EVOLUTION_OPTIONS.groupByMetric,
  };
}
