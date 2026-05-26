import {
  EVOLUTION_FITNESS_COLUMNS,
  EVOLUTION_RUN_COLUMNS,
  EVOLUTION_X_COLUMNS,
  INSTANCE_COLUMNS,
  SAES_HEADERS,
} from '../features/analysis/analysis.constants';
import type {
  DatasetCapability,
  MetricDirection,
} from '../features/analysis/analysis.types';

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
 * Parses a CSV line while preserving quoted commas and escaped quotes.
 *
 * @param line Raw CSV line.
 * @returns Parsed cell values.
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
 * @returns Lowercase ASCII-like token.
 */
export function normalizeHeader(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]/g, '');
}

/**
 * Finds the first header that matches one of the candidates.
 *
 * @param headers Normalized headers.
 * @param candidates Candidate names.
 * @returns Matching header or null.
 */
function findHeader(headers: string[], candidates: string[]): string | null {
  return headers.find((header) => candidates.includes(header)) ?? null;
}

/**
 * Finds the index of the first header that matches one of the candidates.
 *
 * @param headers Normalized headers.
 * @param candidates Candidate names.
 * @returns Matching index or -1.
 */
function findHeaderIndex(headers: string[], candidates: string[]): number {
  return headers.findIndex((header) => candidates.includes(header));
}

/**
 * Checks whether a dataset contains the required SAES columns.
 *
 * @param headers Normalized headers.
 * @returns True when the dataset looks like SAES data.
 */
function hasSaesColumns(headers: string[]): boolean {
  return SAES_HEADERS.every((header) => headers.includes(header));
}

/**
 * Deduplicates and sorts a list of strings using Spanish collation.
 *
 * @param values Candidate values.
 * @returns Sorted unique values.
 */
export function uniqueSorted(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean))).sort((a, b) =>
    a.localeCompare(b, 'es'),
  );
}

/**
 * Inspects an uploaded CSV and derives dataset capabilities.
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
      algorithms: [],
      instances: [],
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

  const algorithmIndex = findHeaderIndex(headers, ['algorithm', 'algoritmo']);
  const instanceIndex = findHeaderIndex(headers, INSTANCE_COLUMNS);
  const metricIndex = headers.indexOf('metricname');

  const detectedXColumns = originalHeaders.filter((_header, index) =>
    EVOLUTION_X_COLUMNS.includes(headers[index]),
  );

  const metrics = new Set<string>();
  const algorithms = new Set<string>();
  const instances = new Set<string>();

  for (let index = 1; index < lines.length; index += 1) {
    const cells = parseCsvLine(lines[index]);

    const metric = metricIndex !== -1 ? cells[metricIndex]?.trim() : '';
    const algorithm = algorithmIndex !== -1 ? cells[algorithmIndex]?.trim() : '';
    const instance = instanceIndex !== -1 ? cells[instanceIndex]?.trim() : '';

    if (metric) metrics.add(metric);
    if (algorithm) algorithms.add(algorithm);
    if (instance) instances.add(instance);
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
    algorithms: uniqueSorted(Array.from(algorithms)),
    instances: uniqueSorted(Array.from(instances)),
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
 * @returns Metric directions or null when the file shape does not match.
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
