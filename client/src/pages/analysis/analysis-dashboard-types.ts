export type CreationStep =
  | 'idle'
  | 'creating'
  | 'uploading_dataset'
  | 'running_analysis'
  | 'finished'
  | 'error';

export type StatusFilter = 'all' | 'created' | 'completed' | 'running' | 'error';

export type SortOption = 'date_desc' | 'date_asc' | 'name_asc' | 'name_desc';

export type DatasetCapability = {
  headers: string[];
  originalHeaders: string[];
  hasSaes: boolean;
  hasEvolution: boolean;
  metrics: string[];
  detectedXColumns: string[];
  detectedFitnessColumn: string | null;
  detectedRunColumn: string | null;
  detectedAlgorithmColumn: string | null;
  detectedInstanceColumn: string | null;
  rowCount: number;
};

export type EvolutionOptions = {
  title: string;
  xColumns: string[];
  xLabelsByColumn: Record<string, string>;
  yLabelsByMetric: Record<string, string>;

  showGrid: boolean;
  showMinMax: boolean;
  showStd: boolean;
  showAverage: boolean;
  showMedian: boolean;

  groupByInstance: boolean;
  groupByMetric: boolean;
};
