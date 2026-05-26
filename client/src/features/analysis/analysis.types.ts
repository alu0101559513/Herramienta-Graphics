export type AnalysisModule =
  | 'saes_plots'
  | 'saes_reports'
  | 'notebooks'
  | 'evolution_plots';

export type MetricDirection = 'maximize' | 'minimize';

export type PlotExportFormat = 'png' | 'eps' | 'svg' | 'jpg' | 'jpeg';

export type EvolutionXAxisColumn = string;

export type EvolutionStatistic = 'std' | 'median' | 'mean' | 'min_max';
export interface EvolutionAnalyzeOptions {
  title: string;
  xColumns: EvolutionXAxisColumn[];
  xLabelsByColumn: Record<string, string>;
  yLabelsByMetric: Record<string, string>;

  showGrid: boolean;
  showMinMax: boolean;
  showStd: boolean;
  showAverage: boolean;
  showMedian: boolean;

  groupByInstance: boolean;
  groupByMetric: boolean;
}

export interface DatasetCapability {
  headers: string[];
  originalHeaders: string[];
  hasSaes: boolean;
  hasEvolution: boolean;
  metrics: string[];
  algorithms: string[];
  instances: string[];
  detectedXColumns: string[];
  detectedFitnessColumn: string | null;
  detectedRunColumn: string | null;
  detectedAlgorithmColumn: string | null;
  detectedInstanceColumn: string | null;
  rowCount: number;
}

export interface DatasetCapabilities {
  saes_plots: boolean;
  saes_reports: boolean;
  notebooks: boolean;
  evolution_plots: boolean;
}

export interface EvolutionMetadataByXColumn {
  metrics?: string[];
  algorithms?: string[];
  instances?: string[];
  run_count?: number | null;
  x_min?: number | null;
  x_max?: number | null;
}

export interface EvolutionMetadata {
  runs?: number | null;
  run_count?: number | null;

  x_min?: number | null;
  x_max?: number | null;

  generation_min?: number | null;
  generation_max?: number | null;
  time_min?: number | null;
  time_max?: number | null;

  y_min?: number | null;
  y_max?: number | null;
  point_count?: number | null;

  x_columns?: string[];
  metrics?: string[];
  algorithms?: string[];
  instances?: string[];
  by_x_column?: Record<string, EvolutionMetadataByXColumn>;

  x_label?: string | null;
  y_label?: string | null;
  x_labels_by_column?: Record<string, string>;
  y_labels_by_metric?: Record<string, string>;
  title?: string | null;

  show_grid?: boolean;
  show_min_max?: boolean;
  show_std?: boolean;
  show_average?: boolean;
  show_median?: boolean;
  group_by_instance?: boolean;
  group_by_metric?: boolean;
}

export interface AnalysisItem {
  id: string;
  name: string;
  description: string;
  status: string;

  created_at?: string;
  updated_at?: string;

  algorithms?: string[];
  problems?: string[];
  metrics?: string[];
  num_runs?: number | null;

  enabled_modules?: AnalysisModule[];
  dataset_capabilities?: DatasetCapabilities;

  metrics_direction?: Record<string, MetricDirection>;
  plot_export_formats?: PlotExportFormat[];

  evolution_metadata?: EvolutionMetadata;

  outputs?: Record<string, unknown>;
  error?: string | null;

  raw_dataset_file_id?: string | null;
  raw_dataset_filename?: string | null;
  normalized_dataset_file_id?: string | null;
  filtered_dataset_file_ids?: Record<string, string>;

  metrics_config_file_id?: string | null;

  selected_algorithms_last_run?: string[];
  current_run_key?: string;
}

export interface AnalyzeAnalysisPayload {
  analysisId: string;
  modules: AnalysisModule[];
  metricsDirection?: Record<string, MetricDirection>;
  metricsFile?: File | null;
  plotExportFormats?: PlotExportFormat[];

  evolutionTitle?: string;
  evolutionXAxisColumns?: EvolutionXAxisColumn[];
  evolutionXLabelsByColumn?: Record<string, string>;
  evolutionYLabelsByMetric?: Record<string, string>;

  evolutionSelectedAlgorithms?: string[];
  evolutionSelectedMetrics?: string[];
  evolutionSelectedInstances?: string[];

  evolutionShowGrid?: boolean;
  evolutionShowMinMax?: boolean;
  evolutionShowStd?: boolean;
  evolutionShowAverage?: boolean;
  evolutionShowMedian?: boolean;

  evolutionGroupByInstance?: boolean;
  evolutionGroupByMetric?: boolean;
}

export interface AnalysisState {
  analyses: AnalysisItem[];
  selectedAnalysis: AnalysisItem | null;

  createAnalysisForm: {
    name: string;
    description: string;
  };

  datasetFile: File | null;
  metricsFile: File | null;

  analyzeForm: {
    modules: AnalysisModule[];
    metricsDirection: Record<string, MetricDirection>;
    plotExportFormats: PlotExportFormat[];
    evolutionOptions: EvolutionAnalyzeOptions;
  };

  reanalyzeForm: {
    modules: AnalysisModule[];
    selectedAlgorithms: string[];
  };

  filesByCategory: Record<string, string[]>;
  currentRunKey: string;

  isLoading: boolean;
  error: string | null;
  successMessage: string | null;
}
