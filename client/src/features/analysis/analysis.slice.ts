import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import { DEFAULT_EVOLUTION_OPTIONS } from './analysis.constants';
import { analysisInitialState } from './analysis.state';
import {
  analyzeAnalysis,
  createAnalysis,
  deleteAnalysis,
  getAnalysis,
  listAnalyses,
  listAnalysisFiles,
  reanalyzeAnalysis,
  updateAnalysis,
  uploadAnalysisDataset,
} from './analysis.thunks';
import type {
  AnalysisItem,
  AnalysisModule,
  EvolutionAnalyzeOptions,
  MetricDirection,
  PlotExportFormat,
} from './analysis.types';

/**
 * Removes duplicate string items while preserving insertion order.
 *
 * @typeParam T String literal union for the list values.
 * @param items Source list.
 * @returns Deduplicated list.
 */
function uniqueItems<T extends string>(items: T[]): T[] {
  return Array.from(new Set(items));
}

/**
 * Toggles a string item inside a list.
 *
 * @typeParam T String literal union for the list values.
 * @param items Current list.
 * @param item Value to toggle.
 * @returns Updated list.
 */
function toggleItem<T extends string>(items: T[], item: T): T[] {
  return items.includes(item)
    ? items.filter((value) => value !== item)
    : [...items, item];
}

/**
 * Checks whether a value is a plain object record.
 *
 * @param value Candidate value.
 * @returns True when the value is an object record.
 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/**
 * Normalizes a raw value into a string array.
 *
 * @param raw Raw value from the backend.
 * @returns String array.
 */
function normalizeStringArray(raw: unknown): string[] {
  return Array.isArray(raw)
    ? raw.filter((value): value is string => typeof value === 'string')
    : [];
}

/**
 * Normalizes a category-to-files map, dropping empty buckets.
 *
 * @param raw Raw files map.
 * @returns Normalized category map.
 */
function normalizeFilesByCategory(raw: unknown): Record<string, string[]> {
  if (!isRecord(raw)) return {};

  const result: Record<string, string[]> = {};

  for (const [key, value] of Object.entries(raw)) {
    const files = normalizeStringArray(value);

    if (files.length > 0) {
      result[key] = files;
    }
  }

  return result;
}

/**
 * Extracts the generated files for the current run from backend outputs.
 *
 * @param outputs Raw outputs payload.
 * @param runKey Optional run key.
 * @returns Files grouped by category.
 */
function getFilesFromOutputs(
  outputs: Record<string, unknown> | undefined | null,
  runKey?: string,
): Record<string, string[]> {
  if (!outputs) return {};

  const direct = normalizeFilesByCategory(outputs);

  if (Object.keys(direct).length > 0) {
    return direct;
  }

  const resolvedRunKey = runKey || 'all';
  const analysisRuns = isRecord(outputs.analysis_runs) ? outputs.analysis_runs : null;
  const runOutputs =
    analysisRuns && isRecord(analysisRuns[resolvedRunKey])
      ? analysisRuns[resolvedRunKey]
      : null;

  if (runOutputs) {
    return normalizeFilesByCategory(runOutputs);
  }

  return {};
}

/**
 * Normalizes export formats and falls back to png when empty.
 *
 * @param formats Raw export format list.
 * @returns Supported unique formats.
 */
function normalizeFormats(formats?: PlotExportFormat[] | null): PlotExportFormat[] {
  const valid = (formats || []).filter(
    (format): format is PlotExportFormat =>
      format === 'png' ||
      format === 'eps' ||
      format === 'svg' ||
      format === 'jpg' ||
      format === 'jpeg',
  );

  const unique = uniqueItems(valid);
  return unique.length > 0 ? unique : ['png'];
}

/**
 * Checks whether the analysis outputs already contain generated files.
 *
 * @param outputs Raw outputs payload.
 * @returns True when at least one generated file exists.
 */
function hasGeneratedOutputs(outputs?: Record<string, unknown> | null): boolean {
  if (!outputs) return false;

  const directFiles = getFilesFromOutputs(outputs);
  if (Object.values(directFiles).some((files) => files.length > 0)) return true;

  const analysisRuns = isRecord(outputs.analysis_runs) ? outputs.analysis_runs : null;

  if (!analysisRuns) return false;

  return Object.values(analysisRuns).some((runOutputs) => {
    const files = normalizeFilesByCategory(runOutputs);
    return Object.values(files).some((items) => items.length > 0);
  });
}

/**
 * Seeds the evolution form options from analysis metadata.
 *
 * @param current Current form options.
 * @param analysis Analysis item containing metadata.
 * @returns Hydrated evolution options.
 */
function hydrateEvolutionOptionsFromAnalysis(
  current: EvolutionAnalyzeOptions,
  analysis: AnalysisItem,
): EvolutionAnalyzeOptions {
  const metadata = analysis.evolution_metadata || {};

  return {
    ...current,
    title: metadata.title ?? current.title,
    xColumns:
      metadata.x_columns && metadata.x_columns.length > 0
        ? [...metadata.x_columns]
        : current.xColumns,
    xLabelsByColumn: {
      ...current.xLabelsByColumn,
      ...(metadata.x_labels_by_column || {}),
    },
    yLabelsByMetric: {
      ...current.yLabelsByMetric,
      ...(metadata.y_labels_by_metric || {}),
    },
    showGrid:
      typeof metadata.show_grid === 'boolean' ? metadata.show_grid : current.showGrid,
    showMinMax:
      typeof metadata.show_min_max === 'boolean'
        ? metadata.show_min_max
        : current.showMinMax,
    showStd: typeof metadata.show_std === 'boolean' ? metadata.show_std : current.showStd,
    showAverage:
      typeof metadata.show_average === 'boolean'
        ? metadata.show_average
        : current.showAverage,
    showMedian:
      typeof metadata.show_median === 'boolean'
        ? metadata.show_median
        : current.showMedian,
    groupByInstance:
      typeof metadata.group_by_instance === 'boolean'
        ? metadata.group_by_instance
        : current.groupByInstance,
    groupByMetric:
      typeof metadata.group_by_metric === 'boolean'
        ? metadata.group_by_metric
        : current.groupByMetric,
  };
}

/**
 * Synchronizes form state from the selected analysis.
 *
 * @param state Analysis slice state.
 * @param analysis Selected analysis item.
 */
function hydrateFormsFromAnalysis(
  state: typeof analysisInitialState,
  analysis: AnalysisItem,
) {
  state.analyzeForm.metricsDirection = {
    ...(analysis.metrics_direction || {}),
  };

  state.analyzeForm.plotExportFormats = normalizeFormats(analysis.plot_export_formats);

  state.analyzeForm.evolutionOptions = hydrateEvolutionOptionsFromAnalysis(
    state.analyzeForm.evolutionOptions,
    analysis,
  );

  state.reanalyzeForm.modules =
    analysis.enabled_modules && analysis.enabled_modules.length > 0
      ? [...analysis.enabled_modules]
      : [];

  state.reanalyzeForm.selectedAlgorithms =
    analysis.selected_algorithms_last_run &&
    analysis.selected_algorithms_last_run.length > 0
      ? [...analysis.selected_algorithms_last_run]
      : [...(analysis.algorithms || [])];

  state.currentRunKey = analysis.current_run_key || 'all';
}

/**
 * Resets the selected analysis slice state to its initial values.
 *
 * @param state Analysis slice state.
 */
function resetSelectedAnalysisState(state: typeof analysisInitialState) {
  state.selectedAnalysis = null;
  state.filesByCategory = {};
  state.analyzeForm = {
    modules: [],
    metricsDirection: {},
    plotExportFormats: ['png'],
    evolutionOptions: {
      ...DEFAULT_EVOLUTION_OPTIONS,
    },
  };
  state.reanalyzeForm = {
    modules: [],
    selectedAlgorithms: [],
  };
  state.currentRunKey = 'all';
}

/**
 * Applies the execution response to the slice state.
 *
 * @param state Analysis slice state.
 * @param payload Normalized execution response.
 */
function patchAnalysisAfterExecution(
  state: typeof analysisInitialState,
  payload: {
    analysis_id: string;
    modules: AnalysisModule[];
    status: string;
    metrics_direction: Record<string, MetricDirection>;
    plot_export_formats: PlotExportFormat[];
    selected_algorithms_last_run: string[];
    current_run_key: string;
    outputs: Record<string, unknown>;
    error?: string | null;
  },
) {
  const runKey = payload.current_run_key || 'all';
  const hasOutputs = hasGeneratedOutputs(payload.outputs);
  const isFailed = payload.status === 'failed' || payload.status === 'error';

  state.isLoading = false;
  state.currentRunKey = runKey;
  state.filesByCategory = getFilesFromOutputs(payload.outputs, runKey);

  state.successMessage =
    isFailed && hasOutputs
      ? 'analysis.messages.analysisPartialExecuted'
      : 'analysis.messages.analysisExecuted';

  state.error =
    isFailed && !hasOutputs ? payload.error || 'analysis.backend.unknownError' : null;

  const patch: Partial<AnalysisItem> = {
    status: payload.status,
    enabled_modules: payload.modules,
    metrics_direction: payload.metrics_direction,
    plot_export_formats: payload.plot_export_formats,
    selected_algorithms_last_run: payload.selected_algorithms_last_run,
    current_run_key: runKey,
    error: payload.error ?? null,
    outputs: payload.outputs,
  };

  if (state.selectedAnalysis?.id === payload.analysis_id) {
    state.selectedAnalysis = {
      ...state.selectedAnalysis,
      ...patch,
    };

    hydrateFormsFromAnalysis(state, state.selectedAnalysis);
  }

  state.analyses = state.analyses.map((analysis) =>
    analysis.id === payload.analysis_id ? { ...analysis, ...patch } : analysis,
  );
}

const analysisSlice = createSlice({
  name: 'analysis',
  initialState: analysisInitialState,
  reducers: {
    setCreateAnalysisField: (
      state,
      action: PayloadAction<{
        field: keyof typeof state.createAnalysisForm;
        value: string;
      }>,
    ) => {
      state.createAnalysisForm[action.payload.field] = action.payload.value;
    },

    setDatasetFile: (state, action: PayloadAction<File | null>) => {
      state.datasetFile = action.payload;
    },

    setMetricsFile: (state, action: PayloadAction<File | null>) => {
      state.metricsFile = action.payload;
    },

    toggleModule: (state, action: PayloadAction<AnalysisModule>) => {
      state.analyzeForm.modules = toggleItem(state.analyzeForm.modules, action.payload);
    },

    setAnalyzeModules: (state, action: PayloadAction<AnalysisModule[]>) => {
      state.analyzeForm.modules = uniqueItems(action.payload);
    },

    setMetricDirection: (
      state,
      action: PayloadAction<{
        metric: string;
        direction: MetricDirection;
      }>,
    ) => {
      state.analyzeForm.metricsDirection[action.payload.metric] =
        action.payload.direction;
    },

    togglePlotExportFormat: (state, action: PayloadAction<PlotExportFormat>) => {
      state.analyzeForm.plotExportFormats = normalizeFormats(
        toggleItem(state.analyzeForm.plotExportFormats, action.payload),
      );
    },

    setPlotExportFormats: (state, action: PayloadAction<PlotExportFormat[]>) => {
      state.analyzeForm.plotExportFormats = normalizeFormats(action.payload);
    },

    setEvolutionOptions: (
      state,
      action: PayloadAction<Partial<EvolutionAnalyzeOptions>>,
    ) => {
      state.analyzeForm.evolutionOptions = {
        ...state.analyzeForm.evolutionOptions,
        ...action.payload,
      };
    },

    setEvolutionXColumns: (state, action: PayloadAction<string[]>) => {
      state.analyzeForm.evolutionOptions.xColumns = uniqueItems(
        action.payload.filter((value) => value.trim()),
      );
    },

    toggleEvolutionXColumn: (state, action: PayloadAction<string>) => {
      state.analyzeForm.evolutionOptions.xColumns = toggleItem(
        state.analyzeForm.evolutionOptions.xColumns,
        action.payload,
      );
    },

    setEvolutionXLabelForColumn: (
      state,
      action: PayloadAction<{
        column: string;
        label: string;
      }>,
    ) => {
      state.analyzeForm.evolutionOptions.xLabelsByColumn[action.payload.column] =
        action.payload.label;
    },

    setEvolutionYLabelForMetric: (
      state,
      action: PayloadAction<{
        metric: string;
        label: string;
      }>,
    ) => {
      state.analyzeForm.evolutionOptions.yLabelsByMetric[action.payload.metric] =
        action.payload.label;
    },

    resetEvolutionOptions: (state) => {
      state.analyzeForm.evolutionOptions = {
        ...DEFAULT_EVOLUTION_OPTIONS,
      };
    },

    setReanalyzeModules: (state, action: PayloadAction<AnalysisModule[]>) => {
      state.reanalyzeForm.modules = uniqueItems(action.payload);
    },

    toggleReanalyzeModule: (state, action: PayloadAction<AnalysisModule>) => {
      state.reanalyzeForm.modules = toggleItem(
        state.reanalyzeForm.modules,
        action.payload,
      );
    },

    setSelectedAlgorithmsForReanalysis: (state, action: PayloadAction<string[]>) => {
      state.reanalyzeForm.selectedAlgorithms = uniqueItems(action.payload);
    },

    toggleSelectedAlgorithmForReanalysis: (state, action: PayloadAction<string>) => {
      state.reanalyzeForm.selectedAlgorithms = toggleItem(
        state.reanalyzeForm.selectedAlgorithms,
        action.payload,
      );
    },

    clearSelectedAlgorithmsForReanalysis: (state) => {
      state.reanalyzeForm.selectedAlgorithms = [];
    },

    setCurrentRunKey: (state, action: PayloadAction<string>) => {
      state.currentRunKey = action.payload || 'all';
    },

    setSelectedAnalysis: (state, action: PayloadAction<AnalysisItem | null>) => {
      state.selectedAnalysis =
        action.payload && action.payload.id ? action.payload : null;

      if (state.selectedAnalysis) {
        hydrateFormsFromAnalysis(state, state.selectedAnalysis);
      }
    },

    clearAnalysisError: (state) => {
      state.error = null;
    },

    clearAnalysisSuccessMessage: (state) => {
      state.successMessage = null;
    },

    resetAnalysisState: (state) => {
      state.analyses = [];
      state.selectedAnalysis = null;
      state.createAnalysisForm = {
        name: '',
        description: '',
      };
      state.datasetFile = null;
      state.metricsFile = null;
      state.analyzeForm = {
        modules: [],
        metricsDirection: {},
        plotExportFormats: ['png'],
        evolutionOptions: {
          ...DEFAULT_EVOLUTION_OPTIONS,
        },
      };
      state.reanalyzeForm = {
        modules: [],
        selectedAlgorithms: [],
      };
      state.filesByCategory = {};
      state.currentRunKey = 'all';
      state.isLoading = false;
      state.error = null;
      state.successMessage = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(listAnalyses.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(listAnalyses.fulfilled, (state, action) => {
        state.isLoading = false;
        state.analyses = action.payload.filter((item) => Boolean(item.id));
      })
      .addCase(listAnalyses.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload ?? 'analysis.backend.unknownError';
      })

      .addCase(createAnalysis.pending, (state) => {
        state.isLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(createAnalysis.fulfilled, (state, action) => {
        state.isLoading = false;
        state.analyses.push(action.payload);
        state.createAnalysisForm = {
          name: '',
          description: '',
        };
        state.successMessage = 'analysis.messages.analysisCreated';
      })
      .addCase(createAnalysis.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload ?? 'analysis.backend.unknownError';
      })

      .addCase(getAnalysis.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(getAnalysis.fulfilled, (state, action) => {
        state.isLoading = false;
        state.selectedAnalysis = action.payload.id ? action.payload : null;

        if (state.selectedAnalysis) {
          hydrateFormsFromAnalysis(state, state.selectedAnalysis);
          state.filesByCategory = getFilesFromOutputs(
            state.selectedAnalysis.outputs,
            state.selectedAnalysis.current_run_key || state.currentRunKey,
          );
        }
      })
      .addCase(getAnalysis.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload ?? 'analysis.backend.unknownError';
      })

      .addCase(updateAnalysis.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(updateAnalysis.fulfilled, (state, action) => {
        state.isLoading = false;

        state.analyses = state.analyses.map((analysis) =>
          analysis.id === action.payload.id ? action.payload : analysis,
        );

        if (state.selectedAnalysis?.id === action.payload.id) {
          state.selectedAnalysis = action.payload;
          hydrateFormsFromAnalysis(state, action.payload);
          state.filesByCategory = getFilesFromOutputs(
            action.payload.outputs,
            action.payload.current_run_key || state.currentRunKey,
          );
        }

        state.successMessage = 'analysis.messages.analysisUpdated';
      })
      .addCase(updateAnalysis.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload ?? 'analysis.backend.unknownError';
      })

      .addCase(deleteAnalysis.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(deleteAnalysis.fulfilled, (state, action) => {
        state.isLoading = false;
        state.analyses = state.analyses.filter(
          (analysis) => analysis.id !== action.payload.analysisId,
        );

        if (state.selectedAnalysis?.id === action.payload.analysisId) {
          resetSelectedAnalysisState(state);
        }

        state.successMessage = 'analysis.messages.analysisDeleted';
      })
      .addCase(deleteAnalysis.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload ?? 'analysis.backend.unknownError';
      })

      .addCase(uploadAnalysisDataset.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(uploadAnalysisDataset.fulfilled, (state) => {
        state.isLoading = false;
        state.datasetFile = null;
        state.reanalyzeForm.selectedAlgorithms = [];
        state.filesByCategory = {};
        state.currentRunKey = 'all';
        state.successMessage = 'analysis.messages.datasetUploaded';
      })
      .addCase(uploadAnalysisDataset.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload ?? 'analysis.backend.unknownError';
      })

      .addCase(analyzeAnalysis.pending, (state) => {
        state.isLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(analyzeAnalysis.fulfilled, (state, action) => {
        patchAnalysisAfterExecution(state, action.payload);
      })
      .addCase(analyzeAnalysis.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload ?? 'analysis.backend.unknownError';
      })

      .addCase(reanalyzeAnalysis.pending, (state) => {
        state.isLoading = true;
        state.error = null;
        state.successMessage = null;
      })
      .addCase(reanalyzeAnalysis.fulfilled, (state, action) => {
        patchAnalysisAfterExecution(state, action.payload);

        state.reanalyzeForm.modules = action.payload.modules;
        state.reanalyzeForm.selectedAlgorithms =
          action.payload.selected_algorithms_last_run;
      })
      .addCase(reanalyzeAnalysis.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload ?? 'analysis.backend.unknownError';
      })

      .addCase(listAnalysisFiles.pending, (state) => {
        state.error = null;
      })
      .addCase(listAnalysisFiles.fulfilled, (state, action) => {
        state.filesByCategory = action.payload.files;
        state.currentRunKey = action.payload.runKey;
      })
      .addCase(listAnalysisFiles.rejected, (state, action) => {
        state.error = action.payload ?? 'analysis.backend.unknownError';
      });
  },
});

export const {
  setCreateAnalysisField,
  setDatasetFile,
  setMetricsFile,
  toggleModule,
  setAnalyzeModules,
  setMetricDirection,
  togglePlotExportFormat,
  setPlotExportFormats,
  setEvolutionOptions,
  setEvolutionXColumns,
  toggleEvolutionXColumn,
  setEvolutionXLabelForColumn,
  setEvolutionYLabelForMetric,
  resetEvolutionOptions,
  setReanalyzeModules,
  toggleReanalyzeModule,
  setSelectedAlgorithmsForReanalysis,
  toggleSelectedAlgorithmForReanalysis,
  clearSelectedAlgorithmsForReanalysis,
  setCurrentRunKey,
  setSelectedAnalysis,
  clearAnalysisError,
  clearAnalysisSuccessMessage,
  resetAnalysisState,
} = analysisSlice.actions;

export const analysisReducer = analysisSlice.reducer;
