import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PrivateLayout from '../../components/PrivateLayout';
import '../../styles/pages.css';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  clearAnalysisError,
  clearAnalysisSuccessMessage,
  setSelectedAnalysis,
} from '../../features/analysis/analysis.slice';
import {
  selectAnalysisError,
  selectAnalysisFiles,
  selectAnalysisIsLoading,
  selectAnalysisSuccessMessage,
  selectSelectedAnalysis,
} from '../../features/analysis/analysis.selectors';
import {
  downloadAnalysisCategoryZip,
  downloadAnalysisFile,
  getAnalysis,
  listAnalysisFiles,
  reanalyzeAnalysis,
} from '../../features/analysis/analysis.thunks';
import type { AnalysisModule } from '../../features/analysis/analysis.types';
import type { PendingAction } from './analysis-detail.types';
import {
  RESULT_CATEGORIES,
  SUCCESS_MESSAGE_DURATION_MS,
  getStatusBadgeClass,
  getStatusTranslationKey,
  isNotebook,
  isPlotArtifact,
  isPreviewableImage,
  isReportArtifact,
  isTex,
} from './analysis-detail.utils';

function SectionShell({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`pages-analysis-shell ${className}`}>{children}</section>;
}

function StatCard({
  label,
  value,
  icon,
  tone = 'blue',
}: {
  label: string;
  value: string | number;
  icon: string;
  tone?: 'blue' | 'violet' | 'amber' | 'emerald' | 'pink' | 'cyan';
}) {
  const toneClasses = {
    blue: 'pages-stat-card-icon-blue',
    violet: 'pages-stat-card-icon-violet',
    amber: 'pages-stat-card-icon-amber',
    emerald: 'pages-stat-card-icon-emerald',
    pink: 'pages-stat-card-icon-pink',
    cyan: 'pages-stat-card-icon-cyan',
  }[tone];

  return (
    <article className="pages-stat-card">
      <div className={`pages-stat-card-icon ${toneClasses}`}>
        <span className="material-symbols-outlined text-[22px]">{icon}</span>
      </div>

      <p className="pages-stat-label">{label}</p>
      <p className="pages-stat-value">{value}</p>
    </article>
  );
}

function ParameterPanel({
  title,
  items,
  emptyText,
  tone = 'blue',
}: {
  title: string;
  items?: string[] | null;
  emptyText: string;
  tone?: 'blue' | 'violet';
}) {
  const { t } = useTranslation();
  const safeItems = items ?? [];
  const [expanded, setExpanded] = useState(false);

  const collapsedLimit = 24;
  const visibleItems = expanded ? safeItems : safeItems.slice(0, collapsedLimit);
  const hasOverflow = safeItems.length > collapsedLimit;

  const panelTone =
    tone === 'violet'
      ? 'pages-detail-parameter-panel-violet'
      : 'pages-detail-parameter-panel-blue';

  const chipTone =
    tone === 'violet'
      ? 'pages-detail-parameter-chip-violet'
      : 'pages-detail-parameter-chip-blue';

  const listHeightClass =
    safeItems.length <= 8
      ? 'max-h-[120px]'
      : safeItems.length <= 18
      ? 'max-h-[180px]'
      : expanded
      ? 'max-h-[420px]'
      : 'max-h-[240px]';

  return (
    <div className={`flex h-full flex-col rounded-[28px] border p-6 ${panelTone}`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-xl font-black tracking-tight text-[var(--text-primary)]">
            {title}
          </h3>
          <p className="mt-1 text-sm text-[var(--text-muted)]">{safeItems.length}</p>
        </div>

        {hasOverflow ? (
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className="pages-pill-btn inline-flex shrink-0 items-center gap-2 px-3 py-2 text-xs font-semibold"
          >
            <span className="material-symbols-outlined text-[16px]">
              {expanded ? 'expand_less' : 'expand_more'}
            </span>
            {expanded ? t('analysis.detail.showLess') : t('analysis.detail.showMore')}
          </button>
        ) : null}
      </div>

      {safeItems.length === 0 ? (
        <div className="flex min-h-[120px] flex-1 items-center justify-center rounded-2xl border border-dashed border-[var(--border)] bg-white/60 px-4 text-center">
          <p className="text-sm text-[var(--text-muted)]">{emptyText}</p>
        </div>
      ) : (
        <div
          className={`overflow-y-auto rounded-2xl border border-white/70 bg-white/55 p-4 shadow-inner ${listHeightClass}`}
        >
          <div className="flex flex-wrap gap-2">
            {visibleItems.map((item) => (
              <span
                key={item}
                title={item}
                className={`max-w-full truncate rounded-full border px-3 py-2 text-sm font-semibold ${chipTone}`}
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ResultCard({
  title,
  count,
  description,
  icon,
  accent,
  primaryAction,
  secondaryAction,
}: {
  title: string;
  count: number;
  description: string;
  icon: string;
  accent: 'blue' | 'violet' | 'amber';
  primaryAction?: ReactNode;
  secondaryAction?: ReactNode;
}) {
  const accentClasses = {
    blue: 'pages-result-card-blue',
    violet: 'pages-result-card-violet',
    amber: 'pages-result-card-amber',
  }[accent];

  return (
    <article
      className={`pages-result-card flex h-full flex-col p-6 transition-all duration-200 hover:-translate-y-1 hover:shadow-md ${accentClasses}`}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="pages-result-icon inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl">
            <span className="material-symbols-outlined text-[22px]">{icon}</span>
          </div>

          <div>
            <h3 className="text-lg font-black text-[var(--text-primary)]">{title}</h3>
            <p className="mt-1 text-sm leading-6 text-[var(--text-secondary)]">
              {description}
            </p>
          </div>
        </div>

        <span className="pages-result-count-badge shrink-0 rounded-full px-3 py-1 text-xs font-bold text-[var(--text-primary)]">
          {count}
        </span>
      </div>

      {(primaryAction || secondaryAction) && (
        <div className="mt-auto flex flex-wrap gap-2 pt-4">
          {primaryAction}
          {secondaryAction}
        </div>
      )}
    </article>
  );
}

function FileList({
  title,
  files,
  category,
  onDownload,
  tone = 'slate',
}: {
  title: string;
  files: string[];
  category: string;
  onDownload: (category: string, fileName: string) => void;
  tone?: 'slate' | 'violet' | 'amber';
}) {
  const { t } = useTranslation();

  if (files.length === 0) return null;

  const titleTone =
    tone === 'violet'
      ? 'text-violet-600'
      : tone === 'amber'
      ? 'text-amber-600'
      : 'text-[var(--text-primary)]';

  const itemTone =
    tone === 'violet'
      ? 'border-violet-100 bg-violet-50/35'
      : tone === 'amber'
      ? 'border-amber-100 bg-amber-50/35'
      : 'border-[var(--border)] bg-[var(--surface)]';

  return (
    <div>
      <h3 className={`mb-3 text-lg font-black ${titleTone}`}>{title}</h3>

      <div className="space-y-3">
        {files.map((fileName) => (
          <div
            key={fileName}
            className={`flex flex-col gap-3 rounded-2xl border px-4 py-4 md:flex-row md:items-center md:justify-between ${itemTone}`}
          >
            <div className="min-w-0">
              <p
                className="truncate text-sm font-semibold text-[var(--text-primary)]"
                title={fileName}
              >
                {fileName}
              </p>
            </div>

            <button
              type="button"
              onClick={() => onDownload(category, fileName)}
              className="pages-pill-btn inline-flex shrink-0 items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold"
            >
              <span className="material-symbols-outlined text-[18px]">download</span>
              {t('common.download')}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AnalysisDetailPage() {
  const { t } = useTranslation();
  const { analysisId } = useParams();
  const dispatch = useAppDispatch();

  const selectedAnalysis = useAppSelector(selectSelectedAnalysis);
  const files = useAppSelector(selectAnalysisFiles);
  const isLoading = useAppSelector(selectAnalysisIsLoading);
  const error = useAppSelector(selectAnalysisError);
  const successMessage = useAppSelector(selectAnalysisSuccessMessage);

  const [runningActions, setRunningActions] = useState<PendingAction[]>([]);

  useEffect(() => {
    if (!analysisId) return;

    const load = async () => {
      dispatch(clearAnalysisError());
      dispatch(clearAnalysisSuccessMessage());

      const analysisResult = await dispatch(getAnalysis(analysisId));

      if (getAnalysis.fulfilled.match(analysisResult)) {
        dispatch(setSelectedAnalysis(analysisResult.payload));
        await dispatch(listAnalysisFiles({ analysisId }));
      }
    };

    void load();
  }, [analysisId, dispatch]);

  useEffect(() => {
    if (!successMessage) return;

    const timeoutId = window.setTimeout(() => {
      dispatch(clearAnalysisSuccessMessage());
    }, SUCCESS_MESSAGE_DURATION_MS);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [dispatch, successMessage]);

  const moduleSet = useMemo(() => {
    const modules = (selectedAnalysis as unknown as { modules?: AnalysisModule[] } | null)
      ?.modules;

    return new Set(modules || selectedAnalysis?.enabled_modules || []);
  }, [selectedAnalysis]);

  const hasSaesCapability =
    Boolean(selectedAnalysis?.dataset_capabilities?.saes_plots) ||
    Boolean(selectedAnalysis?.dataset_capabilities?.saes_reports) ||
    Boolean(selectedAnalysis?.dataset_capabilities?.notebooks) ||
    moduleSet.has('saes_plots') ||
    moduleSet.has('saes_reports') ||
    moduleSet.has('notebooks') ||
    Boolean(selectedAnalysis?.metrics?.length);

  const hasEvolutionCapability =
    Boolean(selectedAnalysis?.dataset_capabilities?.evolution_plots) ||
    moduleSet.has('evolution_plots') ||
    Boolean(files.evolution_plots?.length);

  const saesPlotCategory =
    files[RESULT_CATEGORIES.saesPlots]?.length > 0 ? RESULT_CATEGORIES.saesPlots : null;

  const evolutionPlotCategory =
    files[RESULT_CATEGORIES.evolutionPlots]?.length > 0
      ? RESULT_CATEGORIES.evolutionPlots
      : null;

  const reportCategory =
    files[RESULT_CATEGORIES.reports]?.length > 0 ? RESULT_CATEGORIES.reports : null;

  const notebookCategory =
    files[RESULT_CATEGORIES.notebooks]?.length > 0 ? RESULT_CATEGORIES.notebooks : null;

  const saesPlotFiles = useMemo(() => {
    return saesPlotCategory ? (files[saesPlotCategory] || []).filter(isPlotArtifact) : [];
  }, [files, saesPlotCategory]);

  const evolutionPlotFiles = useMemo(() => {
    return evolutionPlotCategory
      ? (files[evolutionPlotCategory] || []).filter(isPlotArtifact)
      : [];
  }, [files, evolutionPlotCategory]);

  const allPlotFiles = useMemo(() => {
    return Array.from(new Set([...saesPlotFiles, ...evolutionPlotFiles]));
  }, [saesPlotFiles, evolutionPlotFiles]);

  const previewablePlotFiles = useMemo(() => {
    return allPlotFiles.filter(isPreviewableImage);
  }, [allPlotFiles]);

  const reportFiles = useMemo(() => {
    return reportCategory ? (files[reportCategory] || []).filter(isReportArtifact) : [];
  }, [files, reportCategory]);

  const notebookFiles = useMemo(() => {
    return notebookCategory ? (files[notebookCategory] || []).filter(isNotebook) : [];
  }, [files, notebookCategory]);

  const reportTexFiles = useMemo(
    () => reportFiles.filter((fileName) => isTex(fileName)),
    [reportFiles],
  );

  const reportImageFiles = useMemo(
    () => reportFiles.filter((fileName) => isPreviewableImage(fileName)),
    [reportFiles],
  );

  const notebookIpynbFiles = useMemo(
    () => notebookFiles.filter((fileName) => isNotebook(fileName)),
    [notebookFiles],
  );

  const firstNotebookFile = notebookFiles[0] || null;

  const hasSaesPlots = saesPlotFiles.length > 0;
  const hasEvolutionPlots = evolutionPlotFiles.length > 0;
  const hasAnyPlots = hasSaesPlots || hasEvolutionPlots;
  const hasReports = reportFiles.length > 0;
  const hasNotebooks = notebookFiles.length > 0;

  const missingPlotModules = useMemo(() => {
    const modules: AnalysisModule[] = [];

    if (hasSaesCapability && !hasSaesPlots) {
      modules.push('saes_plots');
    }

    if (hasEvolutionCapability && !hasEvolutionPlots) {
      modules.push('evolution_plots');
    }

    return modules;
  }, [hasSaesCapability, hasEvolutionCapability, hasSaesPlots, hasEvolutionPlots]);

  const pendingActions = useMemo(() => {
    const pending: PendingAction[] = [];

    if (missingPlotModules.length > 0) pending.push('plots');
    if (hasSaesCapability && !hasReports) pending.push('saes_reports');
    if (hasSaesCapability && !hasNotebooks) pending.push('notebooks');

    return pending;
  }, [missingPlotModules, hasSaesCapability, hasReports, hasNotebooks]);

  const getPendingActionLabel = (action: PendingAction) => {
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
  };

  const getPendingActionDescription = (action: PendingAction) => {
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
  };

  const getPendingActionButtonLabel = (action: PendingAction) => {
    if (action === 'plots') {
      return t('analysis.detail.results.createPlots');
    }

    return `${t('common.create')} ${getPendingActionLabel(action)}`;
  };

  const resolveModulesForPendingAction = (action: PendingAction): AnalysisModule[] => {
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
  };

  const handleGeneratePendingAction = async (action: PendingAction) => {
    if (!analysisId || !selectedAnalysis) return;
    if (!selectedAnalysis.normalized_dataset_file_id) return;
    if (runningActions.includes(action)) return;

    const modules = resolveModulesForPendingAction(action);

    if (modules.length === 0) return;

    setRunningActions((prev) => [...prev, action]);

    try {
      const selectedAlgorithms =
        selectedAnalysis.selected_algorithms_last_run &&
        selectedAnalysis.selected_algorithms_last_run.length > 0
          ? selectedAnalysis.selected_algorithms_last_run
          : selectedAnalysis.algorithms || [];

      const result = await dispatch(
        reanalyzeAnalysis({
          analysisId,
          modules,
          selectedAlgorithms,
        }),
      );

      if (reanalyzeAnalysis.fulfilled.match(result)) {
        const analysisResult = await dispatch(getAnalysis(analysisId));

        if (getAnalysis.fulfilled.match(analysisResult)) {
          dispatch(setSelectedAnalysis(analysisResult.payload));
        }

        await dispatch(listAnalysisFiles({ analysisId }));
      }
    } finally {
      setRunningActions((prev) => prev.filter((item) => item !== action));
    }
  };

  const handleDownloadFile = (category: string, fileName: string) => {
    if (!analysisId) return;

    void dispatch(
      downloadAnalysisFile({
        analysisId,
        category,
        fileName,
        openInNewTab: false,
      }),
    );
  };

  const handleDownloadCategory = (category: string) => {
    if (!analysisId) return;

    void dispatch(
      downloadAnalysisCategoryZip({
        analysisId,
        category,
      }),
    );
  };

  const handleDownloadAllPlots = () => {
    if (saesPlotCategory && hasSaesPlots) {
      handleDownloadCategory(saesPlotCategory);
    }

    if (evolutionPlotCategory && hasEvolutionPlots) {
      handleDownloadCategory(evolutionPlotCategory);
    }
  };

  return (
    <PrivateLayout>
      <main className="min-h-screen bg-[var(--app-bg)] px-3 py-5 sm:px-4 md:px-6 xl:px-8 2xl:px-10">
        <div className="mx-auto w-full max-w-[2200px]">
          <div className="mb-6">
            <Link to="/analysis" className="pages-back-link">
              <span className="material-symbols-outlined text-[18px]">arrow_back</span>
              {t('common.back')}
            </Link>
          </div>

          <section className="pages-hero-card pages-hero-card-analysis 2xl:p-10">
            <div className="flex flex-col gap-8 2xl:grid 2xl:grid-cols-[minmax(0,1.25fr)_minmax(560px,0.75fr)] 2xl:items-center">
              <div className="min-w-0">
                <div className="mb-4 flex flex-wrap items-center gap-3">
                  <span className={getStatusBadgeClass(selectedAnalysis?.status)}>
                    <span className="h-2 w-2 rounded-full bg-current opacity-70" />
                    {t(getStatusTranslationKey(selectedAnalysis?.status))}
                  </span>
                </div>

                <h1 className="max-w-[18ch] text-4xl font-black tracking-tight text-[var(--text-primary)] md:text-6xl 2xl:text-7xl">
                  {selectedAnalysis?.name || t('analysis.detail.fallbackName')}
                </h1>

                {selectedAnalysis?.description ? (
                  <p className="mt-5 max-w-4xl text-[15px] leading-7 text-[var(--text-secondary)] md:text-base">
                    {selectedAnalysis.description}
                  </p>
                ) : null}
                {selectedAnalysis?.raw_dataset_filename ? (
                  <div className="mt-5 inline-flex max-w-full items-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--surface-strong)] px-4 py-3 text-sm text-[var(--text-secondary)] shadow-sm">
                    <span className="material-symbols-outlined text-[18px] text-[var(--brand)]">
                      description
                    </span>
                    <span className="font-black text-[var(--text-primary)]">CSV:</span>
                    <span className="truncate">
                      {selectedAnalysis.raw_dataset_filename}
                    </span>
                  </div>
                ) : null}
              </div>

              <div className="grid w-full grid-cols-2 gap-4 sm:grid-cols-3">
                <StatCard
                  label={t('analysis.detail.stats.runs')}
                  value={selectedAnalysis?.num_runs ?? '-'}
                  icon="laps"
                  tone="blue"
                />
                <StatCard
                  label={t('analysis.detail.stats.plots')}
                  value={allPlotFiles.length}
                  icon="bar_chart"
                  tone="violet"
                />
                <StatCard
                  label={t('analysis.detail.stats.reports')}
                  value={reportFiles.length}
                  icon="table_chart"
                  tone="amber"
                />
                <StatCard
                  label={t('analysis.detail.stats.notebooks')}
                  value={notebookFiles.length}
                  icon="menu_book"
                  tone="pink"
                />
                <StatCard
                  label={t('analysis.detail.stats.metrics')}
                  value={selectedAnalysis?.metrics?.length ?? 0}
                  icon="tune"
                  tone="cyan"
                />
                <StatCard
                  label={t('analysis.detail.stats.instances')}
                  value={selectedAnalysis?.problems?.length ?? 0}
                  icon="dataset"
                  tone="emerald"
                />
              </div>
            </div>
          </section>

          {error ? (
            <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-100 px-5 py-4 text-sm font-medium text-rose-700 shadow-sm">
              {t(error, { defaultValue: error })}
            </div>
          ) : null}

          {successMessage ? (
            <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-100 px-5 py-4 text-sm font-medium text-emerald-700 shadow-sm">
              {t(successMessage, { defaultValue: successMessage })}
            </div>
          ) : null}

          <SectionShell className="pages-surface-section">
            <div className="grid grid-cols-1 gap-8">
              <div className="grid grid-cols-1 gap-8 xl:grid-cols-2">
                <ParameterPanel
                  title={t('analysis.detail.parameters.metricsTitle')}
                  items={selectedAnalysis?.metrics}
                  emptyText={t('analysis.detail.parameters.noMetrics')}
                  tone="blue"
                />

                <ParameterPanel
                  title={t('analysis.detail.parameters.instancesTitle')}
                  items={selectedAnalysis?.problems}
                  emptyText={t('analysis.detail.parameters.noInstances')}
                  tone="violet"
                />
              </div>

              <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                <ResultCard
                  title={t('analysis.results.categories.plots')}
                  count={allPlotFiles.length}
                  icon="insights"
                  accent="blue"
                  description={
                    hasAnyPlots
                      ? t('analysis.detail.results.plotsPreviewable', {
                          total: allPlotFiles.length,
                          previewable: previewablePlotFiles.length,
                        })
                      : hasSaesCapability || hasEvolutionCapability
                      ? t('analysis.detail.results.noPlots')
                      : t('analysis.detail.results.notAvailableForDataset')
                  }
                  primaryAction={
                    hasAnyPlots ? (
                      <Link
                        to={`/analysis/${analysisId}/plots`}
                        className="pages-action-btn-primary px-5 py-3 text-sm font-semibold"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          insights
                        </span>
                        {t('analysis.results.categories.plots')}
                      </Link>
                    ) : undefined
                  }
                  secondaryAction={
                    hasAnyPlots ? (
                      <button
                        type="button"
                        onClick={handleDownloadAllPlots}
                        className="pages-action-btn-secondary px-5 py-3 text-sm font-semibold"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          folder_zip
                        </span>
                        {t('analysis.results.downloadAll')}
                      </button>
                    ) : undefined
                  }
                />

                <ResultCard
                  title={t('analysis.detail.stats.reports')}
                  count={reportFiles.length}
                  icon="table_chart"
                  accent="violet"
                  description={
                    hasReports
                      ? t('analysis.detail.results.reportsFallback')
                      : hasSaesCapability
                      ? t('analysis.detail.results.noReports')
                      : t('analysis.detail.results.notAvailableWithoutSaes')
                  }
                  primaryAction={
                    hasReports ? (
                      <Link
                        to={`/analysis/${analysisId}/reports`}
                        className="pages-action-btn-primary px-5 py-3 text-sm font-semibold"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          table_chart
                        </span>
                        {t('analysis.results.categories.reports')}
                      </Link>
                    ) : undefined
                  }
                  secondaryAction={
                    hasReports && reportCategory ? (
                      <button
                        type="button"
                        onClick={() => handleDownloadCategory(reportCategory)}
                        className="pages-action-btn-secondary px-5 py-3 text-sm font-semibold"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          folder_zip
                        </span>
                        {t('analysis.results.downloadAll')}
                      </button>
                    ) : undefined
                  }
                />

                <ResultCard
                  title={t('analysis.detail.stats.notebooks')}
                  count={notebookFiles.length}
                  icon="menu_book"
                  accent="amber"
                  description={
                    hasNotebooks
                      ? t('analysis.detail.results.notebooksDescription')
                      : hasSaesCapability
                      ? t('analysis.detail.results.noNotebooks')
                      : t('analysis.detail.results.notAvailableWithoutSaes')
                  }
                  primaryAction={
                    firstNotebookFile && notebookCategory ? (
                      <button
                        type="button"
                        onClick={() =>
                          handleDownloadFile(notebookCategory, firstNotebookFile)
                        }
                        className="pages-action-btn-primary px-5 py-3 text-sm font-semibold"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          download
                        </span>
                        {t('common.download')}
                      </button>
                    ) : undefined
                  }
                />
              </div>
            </div>
          </SectionShell>

          {(reportImageFiles.length > 0 ||
            reportTexFiles.length > 0 ||
            notebookIpynbFiles.length > 0) && (
            <SectionShell className="mt-8 bg-gradient-to-br from-white via-violet-50/10 to-amber-50/10 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800">
              <div className="space-y-8">
                <div>
                  <h2 className="text-2xl font-black tracking-tight text-[var(--text-primary)]">
                    {t('analysis.detail.files.title')}
                  </h2>
                </div>

                <FileList
                  title={t('analysis.detail.files.renderedReports')}
                  files={reportImageFiles}
                  category={reportCategory || RESULT_CATEGORIES.reports}
                  onDownload={handleDownloadFile}
                  tone="amber"
                />

                <FileList
                  title={t('analysis.detail.files.latexReports')}
                  files={reportTexFiles}
                  category={reportCategory || RESULT_CATEGORIES.reports}
                  onDownload={handleDownloadFile}
                  tone="violet"
                />

                <FileList
                  title={t('analysis.detail.files.jupyterNotebooks')}
                  files={notebookIpynbFiles}
                  category={notebookCategory || RESULT_CATEGORIES.notebooks}
                  onDownload={handleDownloadFile}
                  tone="amber"
                />
              </div>
            </SectionShell>
          )}

          {pendingActions.length > 0 && (
            <SectionShell className="mt-8 pages-detail-pending-shell">
              <div className="mb-5">
                <h2 className="text-2xl font-black tracking-tight text-[var(--text-primary)]">
                  {t('analysis.detail.results.pendingTitle')}
                </h2>
              </div>

              <div className="space-y-4">
                {pendingActions.map((action) => {
                  const isRunning = runningActions.includes(action);
                  const actionLabel = getPendingActionLabel(action);

                  return (
                    <div
                      key={action}
                      className="pages-detail-pending-card flex flex-col gap-4 rounded-[24px] p-5 shadow-sm md:flex-row md:items-center md:justify-between"
                    >
                      <div className="min-w-0">
                        <h3 className="text-base font-black text-[var(--text-primary)]">
                          {actionLabel}
                        </h3>
                        <p className="mt-1 text-sm text-[var(--text-secondary)]">
                          {getPendingActionDescription(action)}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() => void handleGeneratePendingAction(action)}
                        disabled={isLoading || isRunning}
                        className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full bg-[var(--brand)] px-5 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:scale-[1.02] hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          {isRunning ? 'sync' : 'play_arrow'}
                        </span>
                        {isRunning
                          ? t('analysis.loading')
                          : getPendingActionButtonLabel(action)}
                      </button>
                    </div>
                  );
                })}
              </div>
            </SectionShell>
          )}
        </div>
      </main>
    </PrivateLayout>
  );
}
