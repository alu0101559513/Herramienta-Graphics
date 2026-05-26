import type { RootState } from '../../app/store';

export const selectAnalyses = (state: RootState) => state.analysis.analyses;
export const selectSelectedAnalysis = (state: RootState) =>
  state.analysis.selectedAnalysis;
export const selectAnalysisIsLoading = (state: RootState) => state.analysis.isLoading;
export const selectAnalysisError = (state: RootState) => state.analysis.error;
export const selectAnalysisSuccessMessage = (state: RootState) =>
  state.analysis.successMessage;
export const selectAnalysisFiles = (state: RootState) => state.analysis.filesByCategory;
export const selectAnalysisDatasetFile = (state: RootState) => state.analysis.datasetFile;
export const selectAnalysisMetricsFile = (state: RootState) => state.analysis.metricsFile;
export const selectAnalysisForm = (state: RootState) => state.analysis.createAnalysisForm;
export const selectAnalyzeForm = (state: RootState) => state.analysis.analyzeForm;
export const selectEvolutionAnalyzeOptions = (state: RootState) =>
  state.analysis.analyzeForm.evolutionOptions;
export const selectReanalyzeForm = (state: RootState) => state.analysis.reanalyzeForm;
export const selectReanalyzeSelectedAlgorithms = (state: RootState) =>
  state.analysis.reanalyzeForm.selectedAlgorithms;
export const selectReanalyzeModules = (state: RootState) =>
  state.analysis.reanalyzeForm.modules;
export const selectCurrentRunKey = (state: RootState) => state.analysis.currentRunKey;
