import { createAsyncThunk } from '@reduxjs/toolkit';
import JSZip from 'jszip';
import { AUTH_TOKEN_STORAGE_KEY } from '../auth/auth.thunks';
import { mapAnalysisBackendErrorToI18nKey } from './analysis.error';
import type {
  AnalysisItem,
  AnalysisModule,
  AnalyzeAnalysisPayload,
  DatasetCapabilities,
  EvolutionMetadata,
  EvolutionMetadataByXColumn,
  MetricDirection,
  PlotExportFormat,
} from './analysis.types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

export type ReanalyzeAnalysisPayload = {
  analysisId: string;
  selectedAlgorithms: string[];
  modules?: AnalysisModule[];
  selectedPlotTypes?: string[];

  evolutionTitle?: string;
  evolutionXAxisColumns?: string[];
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
};

type AnalysisExecutionResponse = {
  analysis_id: string;
  modules: AnalysisModule[];
  status: string;
  metrics_direction: Record<string, MetricDirection>;
  plot_export_formats: PlotExportFormat[];
  selected_algorithms_last_run: string[];
  selected_plot_types_last_run?: string[];
  current_run_key: string;
  outputs: Record<string, unknown>;
  error?: string | null;
};

type AnalysisRunSummary = {
  selected_algorithms: string[];
  modules: AnalysisModule[];
  categories: Record<string, string[]>;
};
/**
 * Returns the configured backend base URL.
 *
 * @returns API base URL.
 */
function getApiBaseUrl(): string {
  if (!API_BASE_URL) {
    throw new Error('Missing VITE_API_BASE_URL environment variable');
  }

  return API_BASE_URL;
}
/**
 * Reads the stored auth token from local storage.
 *
 * @returns Persisted bearer token.
 */
function getStoredToken(): string {
  const token = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);

  if (!token) {
    throw new Error('No stored session');
  }

  return token;
}
/**
 * Builds JSON request headers with an optional bearer token.
 *
 * @param token Optional bearer token.
 * @returns Fetch headers for JSON requests.
 */
function buildJsonHeaders(token?: string): HeadersInit {
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}
/**
 * Builds authorization headers when a token is available.
 *
 * @param token Optional bearer token.
 * @returns Authorization header object or an empty object.
 */
function buildAuthHeaders(token?: string): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}
/**
 * Checks whether a value is an object record.
 *
 * @param value Candidate value.
 * @returns True when the value is an object.
 */
function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
/**
 * Extracts a string identifier from multiple backend shapes.
 *
 * @param value Candidate identifier value.
 * @returns String id or an empty string.
 */
function extractId(value: unknown): string {
  if (typeof value === 'string') return value;
  if (!isObject(value)) return '';

  if (typeof value.$oid === 'string') return value.$oid;
  if (typeof value.id === 'string') return value.id;
  if (typeof value._id === 'string') return value._id;

  return '';
}
/**
 * Normalizes a raw value into a string array.
 *
 * @param raw Raw backend value.
 * @returns String array.
 */
function normalizeStringArray(raw: unknown): string[] {
  return Array.isArray(raw)
    ? raw.filter((value): value is string => typeof value === 'string')
    : [];
}
/**
 * Normalizes a raw value into a string record.
 *
 * @param raw Raw backend value.
 * @returns String key-value record.
 */
function normalizeStringRecord(raw: unknown): Record<string, string> {
  if (!isObject(raw)) return {};

  return Object.fromEntries(
    Object.entries(raw).filter((entry): entry is [string, string] => {
      return typeof entry[1] === 'string';
    }),
  );
}
/**
 * Normalizes a raw category map into arrays of file names.
 *
 * @param raw Raw backend value.
 * @returns Files grouped by category.
 */
function normalizeFilesByCategory(raw: unknown): Record<string, string[]> {
  if (!isObject(raw)) return {};

  const result: Record<string, string[]> = {};

  for (const [key, value] of Object.entries(raw)) {
    result[key] = normalizeStringArray(value);
  }

  return result;
}
/**
 * Filters and normalizes module identifiers from raw backend data.
 *
 * @param raw Raw backend value.
 * @returns Known analysis modules.
 */
function normalizeModules(raw: unknown): AnalysisModule[] {
  return normalizeStringArray(raw).filter(
    (value): value is AnalysisModule =>
      value === 'saes_plots' ||
      value === 'saes_reports' ||
      value === 'notebooks' ||
      value === 'evolution_plots',
  );
}
/**
 * Normalizes a raw list of plot export formats.
 *
 * @param raw Raw backend value.
 * @returns Supported export formats, defaulting to png.
 */
function normalizePlotExportFormats(raw: unknown): PlotExportFormat[] {
  const values = Array.isArray(raw) ? raw : typeof raw === 'string' ? raw.split(',') : [];
  const formats = values
    .map((value) => String(value).trim().toLowerCase())
    .filter(
      (value): value is PlotExportFormat =>
        value === 'png' ||
        value === 'eps' ||
        value === 'svg' ||
        value === 'jpg' ||
        value === 'jpeg',
    );

  return formats.length > 0 ? Array.from(new Set(formats)) : ['png'];
}
/**
 * Normalizes a raw metrics direction object.
 *
 * @param raw Raw backend value.
 * @returns Valid metric direction map.
 */
function normalizeMetricsDirection(raw: unknown): Record<string, MetricDirection> {
  if (!isObject(raw)) return {};

  const result: Record<string, MetricDirection> = {};

  for (const [key, value] of Object.entries(raw)) {
    if (value === 'maximize' || value === 'minimize') {
      result[key] = value;
    }
  }

  return result;
}
/**
 * Normalizes backend dataset capability flags.
 *
 * @param raw Raw backend value.
 * @returns Capability flags with booleans.
 */
function normalizeDatasetCapabilities(raw: unknown): DatasetCapabilities {
  const source = isObject(raw) ? raw : {};

  return {
    saes_plots: Boolean(source.saes_plots),
    saes_reports: Boolean(source.saes_reports),
    notebooks: Boolean(source.notebooks),
    evolution_plots: Boolean(source.evolution_plots),
  };
}
/**
 * Normalizes evolution metadata for a single X column.
 *
 * @param raw Raw backend value.
 * @returns Metadata summary for one X column.
 */
function normalizeEvolutionMetadataByXColumn(raw: unknown): EvolutionMetadataByXColumn {
  const source = isObject(raw) ? raw : {};

  return {
    metrics: normalizeStringArray(source.metrics),
    algorithms: normalizeStringArray(source.algorithms),
    instances: normalizeStringArray(source.instances),
    run_count: typeof source.run_count === 'number' ? source.run_count : null,
    x_min: typeof source.x_min === 'number' ? source.x_min : null,
    x_max: typeof source.x_max === 'number' ? source.x_max : null,
  };
}
/**
 * Normalizes the per-X-column evolution metadata map.
 *
 * @param raw Raw backend value.
 * @returns Metadata indexed by X column.
 */
function normalizeEvolutionMetadataByXColumnRecord(
  raw: unknown,
): Record<string, EvolutionMetadataByXColumn> {
  if (!isObject(raw)) return {};

  const result: Record<string, EvolutionMetadataByXColumn> = {};

  for (const [key, value] of Object.entries(raw)) {
    result[key] = normalizeEvolutionMetadataByXColumn(value);
  }

  return result;
}
/**
 * Normalizes the global evolution metadata payload.
 *
 * @param raw Raw backend value.
 * @returns Structured evolution metadata.
 */
function normalizeEvolutionMetadata(raw: unknown): EvolutionMetadata {
  const source = isObject(raw) ? raw : {};

  return {
    runs: typeof source.runs === 'number' ? source.runs : null,
    run_count: typeof source.run_count === 'number' ? source.run_count : null,

    x_min: typeof source.x_min === 'number' ? source.x_min : null,
    x_max: typeof source.x_max === 'number' ? source.x_max : null,

    generation_min:
      typeof source.generation_min === 'number' ? source.generation_min : null,
    generation_max:
      typeof source.generation_max === 'number' ? source.generation_max : null,
    time_min: typeof source.time_min === 'number' ? source.time_min : null,
    time_max: typeof source.time_max === 'number' ? source.time_max : null,

    y_min: typeof source.y_min === 'number' ? source.y_min : null,
    y_max: typeof source.y_max === 'number' ? source.y_max : null,
    point_count: typeof source.point_count === 'number' ? source.point_count : null,

    x_columns: normalizeStringArray(source.x_columns),
    metrics: normalizeStringArray(source.metrics),
    algorithms: normalizeStringArray(source.algorithms),
    instances: normalizeStringArray(source.instances),
    by_x_column: normalizeEvolutionMetadataByXColumnRecord(source.by_x_column),

    x_label: typeof source.x_label === 'string' ? source.x_label : null,
    y_label: typeof source.y_label === 'string' ? source.y_label : null,
    x_labels_by_column: normalizeStringRecord(source.x_labels_by_column),
    y_labels_by_metric: normalizeStringRecord(source.y_labels_by_metric),
    title: typeof source.title === 'string' ? source.title : null,

    show_grid: typeof source.show_grid === 'boolean' ? source.show_grid : undefined,
    show_min_max:
      typeof source.show_min_max === 'boolean' ? source.show_min_max : undefined,
    show_std: typeof source.show_std === 'boolean' ? source.show_std : undefined,
    show_average:
      typeof source.show_average === 'boolean' ? source.show_average : undefined,
    show_median: typeof source.show_median === 'boolean' ? source.show_median : undefined,
    group_by_instance:
      typeof source.group_by_instance === 'boolean'
        ? source.group_by_instance
        : undefined,
    group_by_metric:
      typeof source.group_by_metric === 'boolean' ? source.group_by_metric : undefined,
  };
}
/**
 * Normalizes an analysis payload from the backend.
 *
 * @param raw Raw backend value.
 * @returns Client-ready analysis item.
 */
function normalizeAnalysisItem(raw: unknown): AnalysisItem {
  const item = isObject(raw) ? raw : {};

  return {
    id: extractId(item.id) || extractId(item._id),
    name: typeof item.name === 'string' ? item.name : '',
    description: typeof item.description === 'string' ? item.description : '',
    status: typeof item.status === 'string' ? item.status : '',

    created_at: typeof item.created_at === 'string' ? item.created_at : undefined,
    updated_at: typeof item.updated_at === 'string' ? item.updated_at : undefined,

    algorithms: normalizeStringArray(item.algorithms),
    problems: normalizeStringArray(item.problems),
    metrics: normalizeStringArray(item.metrics),
    num_runs: typeof item.num_runs === 'number' ? item.num_runs : null,

    enabled_modules: normalizeModules(item.enabled_modules),
    dataset_capabilities: normalizeDatasetCapabilities(item.dataset_capabilities),

    metrics_direction: normalizeMetricsDirection(item.metrics_direction),
    plot_export_formats: normalizePlotExportFormats(item.plot_export_formats),

    evolution_metadata: normalizeEvolutionMetadata(item.evolution_metadata),

    outputs: isObject(item.outputs) ? item.outputs : undefined,
    error: typeof item.error === 'string' ? item.error : null,

    raw_dataset_file_id: extractId(item.raw_dataset_file_id) || null,
    raw_dataset_filename:
      typeof item.raw_dataset_filename === 'string' ? item.raw_dataset_filename : null,
    normalized_dataset_file_id: extractId(item.normalized_dataset_file_id) || null,
    filtered_dataset_file_ids: normalizeStringRecord(item.filtered_dataset_file_ids),

    metrics_config_file_id: extractId(item.metrics_config_file_id) || null,

    selected_algorithms_last_run: normalizeStringArray(item.selected_algorithms_last_run),
    current_run_key:
      typeof item.current_run_key === 'string' ? item.current_run_key : 'all',
  };
}
/**
 * Extracts a string error message from various backend error response shapes.
 * @param response Fetch response object from a failed request.
 * @returns Extracted error message or a default fallback.
 */
async function extractBackendErrorMessage(response: Response): Promise<string> {
  try {
    const data: unknown = await response.json();

    if (isObject(data) && 'detail' in data) {
      const detail = data.detail;

      if (typeof detail === 'string') return detail;

      if (Array.isArray(detail) && detail.length > 0) {
        const firstError = detail[0];

        if (isObject(firstError) && typeof firstError.msg === 'string') {
          return firstError.msg;
        }
      }
    }

    if (isObject(data) && typeof data.message === 'string') {
      return data.message;
    }

    return 'Unknown error';
  } catch {
    return 'Unknown error';
  }
}
/**
 * Appends the run key query parameter when needed.
 *
 * @param url Base URL.
 * @param runKey Optional run key.
 * @returns URL with the run key query string.
 */
function withRunKey(url: string, runKey?: string): string {
  if (!runKey) return url;

  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}run_key=${encodeURIComponent(runKey)}`;
}
/**
 * Appends a cache-busting timestamp to a URL.
 *
 * @param url Base URL.
 * @returns URL with a timestamp query parameter.
 */
function withCacheBust(url: string): string {
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}_t=${Date.now()}`;
}
/**
 * Normalizes the execution response returned by the backend.
 *
 * @param raw Raw backend value.
 * @returns Execution response ready for the store.
 */
function normalizeExecutionResponse(raw: unknown): AnalysisExecutionResponse {
  const item = isObject(raw) ? raw : {};

  return {
    analysis_id: typeof item.analysis_id === 'string' ? item.analysis_id : '',
    modules: normalizeModules(item.modules),
    status: typeof item.status === 'string' ? item.status : '',
    metrics_direction: normalizeMetricsDirection(item.metrics_direction),
    plot_export_formats: normalizePlotExportFormats(item.plot_export_formats),
    selected_algorithms_last_run: normalizeStringArray(item.selected_algorithms_last_run),
    selected_plot_types_last_run: normalizeStringArray(item.selected_plot_types_last_run),
    current_run_key:
      typeof item.current_run_key === 'string' ? item.current_run_key : 'all',
    outputs: isObject(item.outputs) ? item.outputs : {},
    error: typeof item.error === 'string' ? item.error : null,
  };
}
/**
 * Normalizes a run summary payload.
 *
 * @param raw Raw backend value.
 * @returns Normalized run summary.
 */
function normalizeAnalysisRunSummary(raw: unknown): AnalysisRunSummary {
  const item = isObject(raw) ? raw : {};
  const categoriesRaw = isObject(item.categories) ? item.categories : {};
  const categories: Record<string, string[]> = {};

  for (const [runKey, runData] of Object.entries(categoriesRaw)) {
    categories[runKey] = normalizeStringArray(runData);
  }

  return {
    selected_algorithms: normalizeStringArray(item.selected_algorithms),
    modules: normalizeModules(item.modules),
    categories,
  };
}
/**
 * Appends evolution JSON fields to a multipart form.
 *
 * @param formData Multipart form to extend.
 * @param payload Evolution-related payload values.
 */
function appendEvolutionJsonFields(
  body: Record<string, unknown>,
  payload: ReanalyzeAnalysisPayload,
): void {
  if (payload.evolutionTitle !== undefined) body.evolution_title = payload.evolutionTitle;
  if (payload.evolutionXAxisColumns !== undefined)
    body.evolution_x_columns = payload.evolutionXAxisColumns;
  if (payload.evolutionXLabelsByColumn !== undefined) {
    body.evolution_x_labels_by_column = payload.evolutionXLabelsByColumn;
  }
  if (payload.evolutionYLabelsByMetric !== undefined) {
    body.evolution_y_labels_by_metric = payload.evolutionYLabelsByMetric;
  }

  if (payload.evolutionSelectedAlgorithms !== undefined) {
    body.evolution_selected_algorithms = payload.evolutionSelectedAlgorithms;
  }
  if (payload.evolutionSelectedMetrics !== undefined) {
    body.evolution_selected_metrics = payload.evolutionSelectedMetrics;
  }
  if (payload.evolutionSelectedInstances !== undefined) {
    body.evolution_selected_instances = payload.evolutionSelectedInstances;
  }

  if (payload.evolutionShowGrid !== undefined)
    body.evolution_show_grid = payload.evolutionShowGrid;
  if (payload.evolutionShowMinMax !== undefined)
    body.evolution_show_min_max = payload.evolutionShowMinMax;
  if (payload.evolutionShowStd !== undefined)
    body.evolution_show_std = payload.evolutionShowStd;
  if (payload.evolutionShowAverage !== undefined)
    body.evolution_show_average = payload.evolutionShowAverage;
  if (payload.evolutionShowMedian !== undefined)
    body.evolution_show_median = payload.evolutionShowMedian;
  if (payload.evolutionGroupByInstance !== undefined) {
    body.evolution_group_by_instance = payload.evolutionGroupByInstance;
  }
  if (payload.evolutionGroupByMetric !== undefined) {
    body.evolution_group_by_metric = payload.evolutionGroupByMetric;
  }
}
/**
 * Appends evolution form fields to a multipart form.
 *
 * @param formData Multipart form to extend.
 * @param payload Evolution-related payload values.
 */
function appendEvolutionFormFields(
  formData: FormData,
  payload: AnalyzeAnalysisPayload,
): void {
  if (payload.evolutionTitle !== undefined)
    formData.append('evolution_title', payload.evolutionTitle);
  if (payload.evolutionXAxisColumns !== undefined) {
    formData.append('evolution_x_columns', JSON.stringify(payload.evolutionXAxisColumns));
  }
  if (payload.evolutionXLabelsByColumn !== undefined) {
    formData.append(
      'evolution_x_labels_by_column',
      JSON.stringify(payload.evolutionXLabelsByColumn),
    );
  }
  if (payload.evolutionYLabelsByMetric !== undefined) {
    formData.append(
      'evolution_y_labels_by_metric',
      JSON.stringify(payload.evolutionYLabelsByMetric),
    );
  }

  if (payload.evolutionSelectedAlgorithms !== undefined) {
    formData.append(
      'evolution_selected_algorithms',
      JSON.stringify(payload.evolutionSelectedAlgorithms),
    );
  }
  if (payload.evolutionSelectedMetrics !== undefined) {
    formData.append(
      'evolution_selected_metrics',
      JSON.stringify(payload.evolutionSelectedMetrics),
    );
  }
  if (payload.evolutionSelectedInstances !== undefined) {
    formData.append(
      'evolution_selected_instances',
      JSON.stringify(payload.evolutionSelectedInstances),
    );
  }

  if (payload.evolutionShowGrid !== undefined)
    formData.append('evolution_show_grid', String(payload.evolutionShowGrid));
  if (payload.evolutionShowMinMax !== undefined)
    formData.append('evolution_show_min_max', String(payload.evolutionShowMinMax));
  if (payload.evolutionShowStd !== undefined)
    formData.append('evolution_show_std', String(payload.evolutionShowStd));
  if (payload.evolutionShowAverage !== undefined)
    formData.append('evolution_show_average', String(payload.evolutionShowAverage));
  if (payload.evolutionShowMedian !== undefined)
    formData.append('evolution_show_median', String(payload.evolutionShowMedian));
  if (payload.evolutionGroupByInstance !== undefined) {
    formData.append(
      'evolution_group_by_instance',
      String(payload.evolutionGroupByInstance),
    );
  }
  if (payload.evolutionGroupByMetric !== undefined) {
    formData.append('evolution_group_by_metric', String(payload.evolutionGroupByMetric));
  }
}

/**
 * Fetches the current user's analyses.
 *
 * @returns List of analyses normalized for the store.
 */
export const listAnalyses = createAsyncThunk<
  AnalysisItem[],
  void,
  { rejectValue: string }
>('analysis/listAnalyses', async (_, thunkApi) => {
  try {
    const token = getStoredToken();
    const response = await fetch(`${getApiBaseUrl()}/analyses/`, {
      method: 'GET',
      headers: buildAuthHeaders(token),
    });
    if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
    const data = (await response.json()) as unknown;
    return Array.isArray(data) ? data.map(normalizeAnalysisItem) : [];
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Creates a new analysis record.
 *
 * @returns Newly created analysis item.
 */
export const createAnalysis = createAsyncThunk<
  AnalysisItem,
  { name: string; description: string },
  { rejectValue: string }
>('analysis/createAnalysis', async (payload, thunkApi) => {
  try {
    const token = getStoredToken();
    const response = await fetch(`${getApiBaseUrl()}/analyses/`, {
      method: 'POST',
      headers: buildJsonHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
    return normalizeAnalysisItem(await response.json());
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Fetches a single analysis by id.
 *
 * @returns Normalized analysis item.
 */
export const getAnalysis = createAsyncThunk<
  AnalysisItem,
  string,
  { rejectValue: string }
>('analysis/getAnalysis', async (analysisId, thunkApi) => {
  try {
    const token = getStoredToken();
    const response = await fetch(`${getApiBaseUrl()}/analyses/${analysisId}`, {
      method: 'GET',
      headers: buildAuthHeaders(token),
    });
    if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
    return normalizeAnalysisItem(await response.json());
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Updates an analysis name and description.
 *
 * @returns Updated analysis item.
 */
export const updateAnalysis = createAsyncThunk<
  AnalysisItem,
  { analysisId: string; name: string; description: string },
  { rejectValue: string }
>('analysis/updateAnalysis', async ({ analysisId, name, description }, thunkApi) => {
  try {
    const token = getStoredToken();
    const response = await fetch(`${getApiBaseUrl()}/analyses/${analysisId}`, {
      method: 'PATCH',
      headers: buildJsonHeaders(token),
      body: JSON.stringify({ name, description }),
    });
    if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
    return normalizeAnalysisItem(await response.json());
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Deletes an analysis.
 *
 * @returns Analysis id and confirmation message.
 */
export const deleteAnalysis = createAsyncThunk<
  { message: string; analysisId: string },
  string,
  { rejectValue: string }
>('analysis/deleteAnalysis', async (analysisId, thunkApi) => {
  try {
    const token = getStoredToken();
    const response = await fetch(`${getApiBaseUrl()}/analyses/${analysisId}`, {
      method: 'DELETE',
      headers: buildAuthHeaders(token),
    });
    if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
    return { message: 'analysis.messages.analysisDeleted', analysisId };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Uploads a CSV dataset for an analysis.
 *
 * @returns Upload confirmation payload.
 */
export const uploadAnalysisDataset = createAsyncThunk<
  { message: string; analysisId: string },
  { analysisId: string; file: File },
  { rejectValue: string }
>('analysis/uploadAnalysisDataset', async ({ analysisId, file }, thunkApi) => {
  try {
    const token = getStoredToken();
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(
      `${getApiBaseUrl()}/analyses/${analysisId}/upload-dataset`,
      {
        method: 'POST',
        headers: buildAuthHeaders(token),
        body: formData,
      },
    );
    if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
    return { message: 'analysis.messages.datasetUploaded', analysisId };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Executes the selected analysis modules.
 *
 * @returns Analysis execution response.
 */
export const analyzeAnalysis = createAsyncThunk<
  AnalysisExecutionResponse,
  AnalyzeAnalysisPayload,
  { rejectValue: string }
>('analysis/analyzeAnalysis', async (payload, thunkApi) => {
  try {
    const token = getStoredToken();
    const formData = new FormData();

    formData.append('modules', JSON.stringify(payload.modules));

    if (payload.metricsDirection && Object.keys(payload.metricsDirection).length > 0) {
      formData.append('metrics_direction', JSON.stringify(payload.metricsDirection));
    }
    if (payload.metricsFile) formData.append('metrics_file', payload.metricsFile);
    if (payload.plotExportFormats && payload.plotExportFormats.length > 0) {
      formData.append('plot_export_formats', JSON.stringify(payload.plotExportFormats));
    }

    appendEvolutionFormFields(formData, payload);

    const response = await fetch(
      `${getApiBaseUrl()}/analyses/${payload.analysisId}/analyze`,
      {
        method: 'POST',
        headers: buildAuthHeaders(token),
        body: formData,
      },
    );
    if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
    return normalizeExecutionResponse(await response.json());
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Re-runs selected modules for an analysis.
 *
 * @returns Reanalysis response.
 */
export const reanalyzeAnalysis = createAsyncThunk<
  AnalysisExecutionResponse,
  ReanalyzeAnalysisPayload,
  { rejectValue: string }
>('analysis/reanalyzeAnalysis', async (payload, thunkApi) => {
  try {
    const token = getStoredToken();
    const body: Record<string, unknown> = {
      selected_algorithms: payload.selectedAlgorithms,
    };

    if (payload.modules && payload.modules.length > 0) body.modules = payload.modules;
    if (payload.selectedPlotTypes && payload.selectedPlotTypes.length > 0) {
      body.selected_plot_types = payload.selectedPlotTypes;
    }

    appendEvolutionJsonFields(body, payload);

    const response = await fetch(
      `${getApiBaseUrl()}/analyses/${payload.analysisId}/reanalyze`,
      {
        method: 'POST',
        headers: buildJsonHeaders(token),
        body: JSON.stringify(body),
      },
    );
    if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
    return normalizeExecutionResponse(await response.json());
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Lists generated files for an analysis run.
 *
 * @returns Files grouped by category.
 */
export const listAnalysisFiles = createAsyncThunk<
  { files: Record<string, string[]>; runKey: string },
  { analysisId: string; runKey?: string },
  { rejectValue: string }
>('analysis/listAnalysisFiles', async ({ analysisId, runKey }, thunkApi) => {
  try {
    const token = getStoredToken();
    const response = await fetch(
      withRunKey(`${getApiBaseUrl()}/analyses/${analysisId}/files`, runKey),
      {
        method: 'GET',
        headers: buildAuthHeaders(token),
      },
    );
    if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
    return {
      files: normalizeFilesByCategory(await response.json()),
      runKey: runKey || 'all',
    };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Lists available analysis runs.
 *
 * @returns Run summaries for the selected analysis.
 */
export const listAnalysisRuns = createAsyncThunk<
  Record<string, AnalysisRunSummary>,
  string,
  { rejectValue: string }
>('analysis/listAnalysisRuns', async (analysisId, thunkApi) => {
  try {
    const token = getStoredToken();
    const response = await fetch(`${getApiBaseUrl()}/analyses/${analysisId}/runs`, {
      method: 'GET',
      headers: buildAuthHeaders(token),
    });
    if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
    const data = (await response.json()) as unknown;
    if (!isObject(data)) return {};

    const result: Record<string, AnalysisRunSummary> = {};
    for (const [runKey, runData] of Object.entries(data))
      result[runKey] = normalizeAnalysisRunSummary(runData);
    return result;
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Resolves a blob URL for a generated analysis file.
 *
 * @returns Blob URL string.
 */
export const getAnalysisFileBlobUrl = createAsyncThunk<
  { category: string; fileName: string; blobUrl: string; runKey: string },
  { analysisId: string; category: string; fileName: string; runKey?: string },
  { rejectValue: string }
>(
  'analysis/getAnalysisFileBlobUrl',
  async ({ analysisId, category, fileName, runKey }, thunkApi) => {
    try {
      const token = getStoredToken();
      const response = await fetch(
        withCacheBust(
          withRunKey(
            `${getApiBaseUrl()}/analyses/${analysisId}/files/${category}/${fileName}`,
            runKey,
          ),
        ),
        { method: 'GET', headers: buildAuthHeaders(token) },
      );
      if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
      const blob = await response.blob();
      return {
        category,
        fileName,
        blobUrl: window.URL.createObjectURL(blob),
        runKey: runKey || 'all',
      };
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
    }
  },
);

/**
 * Downloads a single analysis artifact.
 *
 * @returns Download status message.
 */
export const downloadAnalysisFile = createAsyncThunk<
  void,
  {
    analysisId: string;
    category: string;
    fileName: string;
    openInNewTab?: boolean;
    runKey?: string;
  },
  { rejectValue: string }
>(
  'analysis/downloadAnalysisFile',
  async ({ analysisId, category, fileName, openInNewTab = false, runKey }, thunkApi) => {
    try {
      const token = getStoredToken();
      const response = await fetch(
        withCacheBust(
          withRunKey(
            `${getApiBaseUrl()}/analyses/${analysisId}/files/${category}/${fileName}`,
            runKey,
          ),
        ),
        { method: 'GET', headers: buildAuthHeaders(token) },
      );
      if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);

      if (openInNewTab) {
        window.open(blobUrl, '_blank', 'noopener,noreferrer');
      } else {
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = fileName.split('/').pop() || fileName;
        document.body.appendChild(link);
        link.click();
        link.remove();
      }

      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1500);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
    }
  },
);

/**
 * Downloads all files in an analysis category as a ZIP.
 *
 * @returns Download status message.
 */
export const downloadAnalysisCategoryZip = createAsyncThunk<
  { category: string },
  { analysisId: string; category: string; runKey?: string },
  { rejectValue: string }
>(
  'analysis/downloadAnalysisCategoryZip',
  async ({ analysisId, category, runKey }, thunkApi) => {
    try {
      const token = getStoredToken();
      const response = await fetch(
        withRunKey(
          `${getApiBaseUrl()}/analyses/${encodeURIComponent(
            analysisId,
          )}/files/${encodeURIComponent(category)}/zip`,
          runKey,
        ),
        { method: 'GET', headers: buildAuthHeaders(token) },
      );
      if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const contentDisposition = response.headers.get('content-disposition') ?? '';
      const fileNameMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
      const downloadName = fileNameMatch?.[1] ?? `${category}.zip`;

      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = downloadName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);

      return { category };
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
    }
  },
);

/**
 * Downloads all plot files as a ZIP archive.
 *
 * @returns Download status message.
 */
export const downloadAnalysisPlotsZip = createAsyncThunk<
  void,
  {
    analysisId: string;
    categories: string[];
    filesByCategory: Record<string, string[]>;
    runKey?: string;
  },
  { rejectValue: string }
>(
  'analysis/downloadAnalysisPlotsZip',
  async ({ analysisId, categories, filesByCategory, runKey }, thunkApi) => {
    try {
      const token = getStoredToken();
      const zip = new JSZip();

      for (const category of categories) {
        const fileNames = filesByCategory[category] || [];
        const folder = zip.folder(category) || zip;

        for (const fileName of fileNames) {
          const response = await fetch(
            withCacheBust(
              withRunKey(
                `${getApiBaseUrl()}/analyses/${encodeURIComponent(
                  analysisId,
                )}/files/${encodeURIComponent(category)}/${encodeURIComponent(fileName)}`,
                runKey,
              ),
            ),
            {
              method: 'GET',
              headers: buildAuthHeaders(token),
            },
          );

          if (!response.ok) {
            throw new Error(await extractBackendErrorMessage(response));
          }

          const blob = await response.blob();
          folder.file(fileName.split('/').pop() || fileName, blob);
        }
      }

      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const blobUrl = window.URL.createObjectURL(zipBlob);
      const downloadName = `plots_${runKey || 'all'}.zip`;

      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = downloadName;
      document.body.appendChild(link);
      link.click();
      link.remove();

      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1500);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
    }
  },
);

async function downloadFileFromEndpoint(
  url: string,
  downloadName: string,
): Promise<void> {
  const token = getStoredToken();
  const response = await fetch(url, {
    method: 'GET',
    headers: buildAuthHeaders(token),
  });
  if (!response.ok) throw new Error(await extractBackendErrorMessage(response));
  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = downloadName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => window.URL.revokeObjectURL(blobUrl), 1500);
}

/**
 * Downloads the original uploaded CSV dataset.
 *
 * @returns Download status message.
 */
export const downloadRawDataset = createAsyncThunk<
  void,
  { analysisId: string },
  { rejectValue: string }
>('analysis/downloadRawDataset', async ({ analysisId }, thunkApi) => {
  try {
    await downloadFileFromEndpoint(
      `${getApiBaseUrl()}/analyses/${analysisId}/dataset/raw`,
      'raw_dataset.csv',
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Downloads the normalized CSV dataset.
 *
 * @returns Download status message.
 */
export const downloadNormalizedDataset = createAsyncThunk<
  void,
  { analysisId: string },
  { rejectValue: string }
>('analysis/downloadNormalizedDataset', async ({ analysisId }, thunkApi) => {
  try {
    await downloadFileFromEndpoint(
      `${getApiBaseUrl()}/analyses/${analysisId}/dataset/normalized`,
      'normalized_dataset.csv',
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Downloads a filtered dataset artifact.
 *
 * @returns Download status message.
 */
export const downloadFilteredDataset = createAsyncThunk<
  void,
  { analysisId: string; runKey?: string },
  { rejectValue: string }
>('analysis/downloadFilteredDataset', async ({ analysisId, runKey }, thunkApi) => {
  try {
    await downloadFileFromEndpoint(
      withRunKey(`${getApiBaseUrl()}/analyses/${analysisId}/dataset/filtered`, runKey),
      `filtered_dataset_${runKey || 'current'}.csv`,
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});

/**
 * Downloads the metrics CSV file.
 *
 * @returns Download status message.
 */
export const downloadMetrics = createAsyncThunk<
  void,
  { analysisId: string },
  { rejectValue: string }
>('analysis/downloadMetrics', async ({ analysisId }, thunkApi) => {
  try {
    await downloadFileFromEndpoint(
      `${getApiBaseUrl()}/analyses/${analysisId}/metrics`,
      'metrics.csv',
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return thunkApi.rejectWithValue(mapAnalysisBackendErrorToI18nKey(message));
  }
});
