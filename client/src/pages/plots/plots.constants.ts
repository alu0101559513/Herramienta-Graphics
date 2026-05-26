import type {
  AnalysisModule,
  EvolutionStatistic,
} from '../../features/analysis/analysis.types';
import type { PlotType, SaesPlotType } from './plots-types';

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

export const SAES_PLOT_TYPES: SaesPlotType[] = [
  'boxplot',
  'violin',
  'histogram',
  'critical_distance',
];

export const ALL_PLOT_TYPES: PlotType[] = [
  'evolution',
  'boxplot',
  'violin',
  'histogram',
  'critical_distance',
];

export const EVOLUTION_STATISTICS: EvolutionStatistic[] = [
  'std',
  'median',
  'mean',
  'min_max',
];
