import type { AnalysisModule, EvolutionAnalyzeOptions } from './analysis.types';
export const MODULES: AnalysisModule[] = [
  'saes_plots',
  'saes_reports',
  'notebooks',
  'evolution_plots',
];

export const SAES_HEADERS = [
  'algorithm',
  'instance',
  'metricname',
  'executionid',
  'metricvalue',
];

export const DEFAULT_EVOLUTION_OPTIONS: EvolutionAnalyzeOptions = {
  title: 'Curva de Convergencia - {metric} - {instance} - {x_column}',
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

export const EVOLUTION_X_COLUMNS = [
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

export const EVOLUTION_FITNESS_COLUMNS = [
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

export const EVOLUTION_RUN_COLUMNS = [
  'run',
  'seed',
  'executionid',
  'execution_id',
  'execution',
  'rep',
  'replicate',
  'repetition',
];

export const INSTANCE_COLUMNS = ['instance', 'problem', 'problema', 'benchmark', 'case'];
