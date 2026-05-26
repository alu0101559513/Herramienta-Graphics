import { DEFAULT_EVOLUTION_OPTIONS } from './analysis.constants';
import type { AnalysisState } from './analysis.types';

export const analysisInitialState: AnalysisState = {
  analyses: [],
  selectedAnalysis: null,

  createAnalysisForm: {
    name: '',
    description: '',
  },

  datasetFile: null,
  metricsFile: null,

  analyzeForm: {
    modules: [],
    metricsDirection: {},
    plotExportFormats: ['png'],
    evolutionOptions: {
      ...DEFAULT_EVOLUTION_OPTIONS,
    },
  },

  reanalyzeForm: {
    modules: [],
    selectedAlgorithms: [],
  },

  filesByCategory: {},
  currentRunKey: 'all',

  isLoading: false,
  error: null,
  successMessage: null,
};
