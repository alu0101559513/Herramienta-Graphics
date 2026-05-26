import type { AnalysisModule } from '../../features/analysis/analysis.types';
import type { PendingAction } from './analysis-detail.types';

export const SUCCESS_MESSAGE_DURATION_MS = 4500;

export const RESULT_CATEGORIES = {
  saesPlots: 'saes_plots',
  reports: 'saes_reports',
  notebooks: 'notebooks',
  evolutionPlots: 'evolution_plots',
} as const;

/**
 * Normalizes the raw analysis status into a display-friendly bucket.
 *
 * @param status Raw analysis status.
 * @returns Normalized status name.
 */
export function getNormalizedStatus(status?: string | null) {
  const normalized = (status ?? '').toLowerCase();

  if (normalized === 'created' || normalized === 'dataset_uploaded') return 'created';

  if (
    normalized.includes('completed') ||
    normalized.includes('done') ||
    normalized.includes('success') ||
    normalized.includes('finished')
  ) {
    return 'completed';
  }

  if (
    normalized.includes('processing') ||
    normalized.includes('running') ||
    normalized.includes('pending')
  ) {
    return 'running';
  }

  if (normalized.includes('error') || normalized.includes('failed')) {
    return 'error';
  }

  return 'unknown';
}

/**
 * Returns the translation key for an analysis status.
 *
 * @param status Raw analysis status.
 * @returns i18n key for the status label.
 */
export function getStatusTranslationKey(status?: string | null) {
  const normalized = getNormalizedStatus(status);

  switch (normalized) {
    case 'created':
      return 'analysis.status.created';
    case 'completed':
      return 'analysis.status.completed';
    case 'running':
      return 'analysis.status.running';
    case 'error':
      return 'analysis.status.error';
    default:
      return 'analysis.status.unknown';
  }
}

/**
 * Returns the CSS class used to render a status badge.
 *
 * @param status Raw analysis status.
 * @returns Badge class name.
 */
export function getStatusBadgeClass(status?: string | null) {
  const normalized = (status ?? '').toLowerCase();

  if (normalized === 'created') return 'pages-status-badge pages-status-created';

  if (normalized === 'dataset_uploaded') {
    return 'pages-status-badge pages-status-dataset';
  }

  if (
    normalized.includes('completed') ||
    normalized.includes('done') ||
    normalized.includes('success') ||
    normalized.includes('finished')
  ) {
    return 'pages-status-badge pages-status-completed';
  }

  if (
    normalized.includes('processing') ||
    normalized.includes('running') ||
    normalized.includes('pending')
  ) {
    return 'pages-status-badge pages-status-running';
  }

  if (normalized.includes('error') || normalized.includes('failed')) {
    return 'pages-status-badge pages-status-error';
  }

  return 'pages-status-badge pages-status-default';
}

/**
 * Checks whether a file is a LaTeX artifact.
 *
 * @param fileName File name.
 * @returns True when the file ends in .tex.
 */
export function isTex(fileName: string) {
  return fileName.toLowerCase().endsWith('.tex');
}

/**
 * Checks whether a file is a Jupyter notebook.
 *
 * @param fileName File name.
 * @returns True when the file ends in .ipynb.
 */
export function isNotebook(fileName: string) {
  return fileName.toLowerCase().endsWith('.ipynb');
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
 * Checks whether a file belongs to the plot artifact family.
 *
 * @param fileName File name.
 * @returns True for plot-friendly extensions.
 */
export function isPlotArtifact(fileName: string) {
  const lower = fileName.toLowerCase();

  return (
    lower.endsWith('.png') ||
    lower.endsWith('.jpg') ||
    lower.endsWith('.jpeg') ||
    lower.endsWith('.webp') ||
    lower.endsWith('.svg') ||
    lower.endsWith('.eps') ||
    lower.endsWith('.pdf')
  );
}

/**
 * Checks whether a file is part of a report artifact set.
 *
 * @param fileName File name.
 * @returns True for report-renderable files.
 */
export function isReportArtifact(fileName: string) {
  return isTex(fileName) || isPreviewableImage(fileName);
}

/**
 * Returns the label used for a pending action.
 *
 * @param action Pending action identifier.
 * @param t Translation helper.
 * @returns Localized action label.
 */
export function getPendingActionLabel(
  action: PendingAction,
  t: (key: string, options?: Record<string, unknown>) => string,
) {
  switch (action) {
    case 'plots':
      return t('analysis.results.categories.plots');
    case 'saes_reports':
      return t('analysis.modules.saes_reports');
    case 'notebooks':
      return t('analysis.modules.notebooks');
    default:
      return action;
  }
}

/**
 * Returns the help text shown for a pending action.
 *
 * @param action Pending action identifier.
 * @param missingPlotModules Modules still missing for plots.
 * @param t Translation helper.
 * @returns Localized description for the pending action.
 */
export function getPendingActionDescription(
  action: PendingAction,
  missingPlotModules: AnalysisModule[],
  t: (key: string, options?: Record<string, unknown>) => string,
) {
  switch (action) {
    case 'plots':
      if (
        missingPlotModules.includes('saes_plots') &&
        missingPlotModules.includes('evolution_plots')
      ) {
        return t('analysis.detail.moduleDescriptions.allPlots', {
          defaultValue:
            'Genera las gráficas SAES y las curvas de evolución disponibles para este dataset.',
        });
      }

      if (missingPlotModules.includes('saes_plots')) {
        return t('analysis.detail.moduleDescriptions.saes_plots', {
          defaultValue:
            'Genera boxplot, violin, histogramas y distancia crítica con SAES.',
        });
      }

      return t('analysis.detail.moduleDescriptions.evolution_plots', {
        defaultValue:
          'Genera curvas de evolución con media, mínimo, máximo y dispersión usando Matplotlib.',
      });

    case 'saes_reports':
      return t('analysis.detail.moduleDescriptions.saes_reports', {
        defaultValue: 'Genera tablas estadísticas SAES.',
      });

    case 'notebooks':
      return t('analysis.detail.moduleDescriptions.notebooks', {
        defaultValue: 'Genera un notebook Jupyter reproducible.',
      });

    default:
      return '';
  }
}

/**
 * Returns the action label used on the pending action button.
 *
 * @param action Pending action identifier.
 * @param t Translation helper.
 * @returns Localized button label.
 */
export function getPendingActionButtonLabel(
  action: PendingAction,
  t: (key: string, options?: Record<string, unknown>) => string,
) {
  if (action === 'plots') {
    return t('analysis.detail.results.createPlots');
  }

  return `${t('common.create')} ${getPendingActionLabel(action, t)}`;
}

/**
 * Resolves the backend modules needed for a pending action.
 *
 * @param action Pending action identifier.
 * @param missingPlotModules Missing plot modules.
 * @returns Module list to request.
 */
export function resolveModulesForPendingAction(
  action: PendingAction,
  missingPlotModules: AnalysisModule[],
): AnalysisModule[] {
  switch (action) {
    case 'plots':
      return missingPlotModules;

    case 'saes_reports':
      return ['saes_reports'];

    case 'notebooks':
      return ['notebooks'];

    default:
      return [];
  }
}
