import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PrivateLayout from '../../components/PrivateLayout';
import '../../styles/pages.css';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  clearAnalysisError,
  clearAnalysisSuccessMessage,
  setAnalyzeModules,
  setCreateAnalysisField,
  setDatasetFile,
  setMetricDirection,
  setMetricsFile,
  setPlotExportFormats,
  toggleModule,
  togglePlotExportFormat,
} from '../../features/analysis/analysis.slice';
import {
  selectAnalyses,
  selectAnalysisError,
} from '../../features/analysis/analysis.selectors';
import {
  analyzeAnalysis,
  createAnalysis,
  deleteAnalysis,
  listAnalyses,
  updateAnalysis,
  uploadAnalysisDataset,
} from '../../features/analysis/analysis.thunks';
import type {
  AnalysisModule,
  MetricDirection,
  PlotExportFormat,
} from '../../features/analysis/analysis.types';
import type {
  CreationStep,
  DatasetCapability,
  EvolutionOptions,
  SortOption,
  StatusFilter,
} from './analysis-dashboard-types';
import {
  DEFAULT_EVOLUTION_OPTIONS,
  MODULES,
  buildDefaultXLabels,
  buildDefaultYLabels,
  extractMetricDirectionsFromMetricsCsv,
  formatRelativeDate,
  getAnalysisTimestamp,
  getCreationMessageKey,
  getCreationProgress,
  getDefaultModulesForCapability,
  getModuleDescription,
  getModuleDisabledReason,
  getModuleLabel,
  getNormalizedStatus,
  getStatusBadgeClass,
  getStatusLabelKey,
  inspectDataset,
  isEvolutionModule,
  isModuleEnabled,
  isSaesModule,
  matchesStatusFilter,
  normalizeSelectedModulesForCapability,
  toggleString,
} from './analysis-dashboard-utils';

function Shell({
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
  tone?: 'blue' | 'violet' | 'emerald' | 'amber';
}) {
  const toneClasses = {
    blue: 'pages-stat-card-icon-blue',
    violet: 'pages-stat-card-icon-violet',
    emerald: 'pages-stat-card-icon-emerald',
    amber: 'pages-stat-card-icon-amber',
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

function UploadCard({
  icon,
  title,
  fileName,
  onFileChange,
  onClear,
  accept,
  disabled,
  tone = 'blue',
}: {
  icon: string;
  title: string;
  fileName: string | null;
  onFileChange: (file: File | null) => void | Promise<void>;
  onClear: () => void;
  accept: string;
  disabled: boolean;
  tone?: 'blue' | 'violet';
}) {
  const toneClasses =
    tone === 'violet' ? 'pages-upload-card-violet' : 'pages-upload-card-blue';

  return (
    <div className={`pages-upload-card ${toneClasses}`}>
      <label className={disabled ? 'pages-upload-label disabled' : 'pages-upload-label'}>
        <input
          type="file"
          accept={accept}
          onChange={async (event) => {
            const file = event.target.files?.[0] ?? null;
            await onFileChange(file);
            event.target.value = '';
          }}
          disabled={disabled}
          className="hidden"
        />

        <div className="pages-upload-icon-wrapper">
          <span className="material-symbols-outlined text-3xl text-[var(--brand)]">
            {icon}
          </span>
        </div>

        <p className="pages-upload-title">{fileName ?? title}</p>
      </label>

      {fileName ? (
        <div className="mt-4 flex justify-center">
          <button
            type="button"
            onClick={onClear}
            disabled={disabled}
            className="pages-upload-clear-btn"
            title="Quitar fichero"
            aria-label="Quitar fichero"
          >
            <span className="material-symbols-outlined text-[18px]">delete</span>
          </button>
        </div>
      ) : null}
    </div>
  );
}

function StyledSelect({
  value,
  onChange,
  children,
  className = '',
}: {
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`relative ${className}`}>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="pages-styled-select"
      >
        {children}
      </select>

      <span className="pages-styled-select-icon">
        <span className="material-symbols-outlined text-[20px]">expand_more</span>
      </span>
    </div>
  );
}

function FormField({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-black uppercase tracking-widest text-[var(--text-secondary)]">
        {label}
      </span>

      {children}

      {hint ? (
        <span className="mt-1 block text-xs leading-5 text-[var(--text-muted)]">
          {hint}
        </span>
      ) : null}
    </label>
  );
}

function ToggleOption({
  label,
  description,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      disabled={disabled}
      className={`flex w-full items-start justify-between gap-4 rounded-2xl border px-4 py-3 text-left transition-all ${
        checked
          ? 'border-[var(--brand)] bg-[var(--brand-soft)] text-[var(--brand-strong)]'
          : 'border-[var(--border)] bg-[var(--surface-strong)] text-[var(--text-primary)]'
      } ${disabled ? 'cursor-not-allowed opacity-60' : 'hover:shadow-sm'}`}
    >
      <span>
        <span className="block text-sm font-black">{label}</span>
        {description ? (
          <span className="mt-1 block text-xs leading-5 text-[var(--text-secondary)]">
            {description}
          </span>
        ) : null}
      </span>

      <span className="material-symbols-outlined text-[26px]">
        {checked ? 'toggle_on' : 'toggle_off'}
      </span>
    </button>
  );
}

function ModuleButton({
  module,
  active,
  disabled,
  disabledReason,
  onClick,
}: {
  module: AnalysisModule;
  active: boolean;
  disabled: boolean;
  disabledReason: string | null;
  onClick: () => void;
}) {
  const icon =
    module === 'evolution_plots'
      ? 'monitoring'
      : module === 'saes_reports'
      ? 'table_chart'
      : module === 'notebooks'
      ? 'menu_book'
      : 'bar_chart';

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={disabledReason || getModuleDescription(module)}
      className={`flex w-full flex-col gap-2 rounded-2xl border px-4 py-4 text-left transition-all ${
        active
          ? 'border-[var(--brand)] bg-[var(--brand-soft)] text-[var(--brand-strong)] shadow-sm'
          : 'border-[var(--border)] bg-[var(--surface-strong)] text-[var(--text-primary)]'
      } ${
        disabled ? 'cursor-not-allowed opacity-50' : 'hover:scale-[1.01] hover:shadow-sm'
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="material-symbols-outlined text-[20px]">{icon}</span>
        <span className="text-sm font-black">{getModuleLabel(module)}</span>
      </div>

      <span className="text-xs leading-5 text-[var(--text-secondary)]">
        {disabledReason || getModuleDescription(module)}
      </span>
    </button>
  );
}

function ChipButton({
  label,
  active,
  disabled,
  onClick,
}: {
  label: string;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`rounded-full border px-4 py-2 text-xs font-black transition-all ${
        active
          ? 'border-[var(--brand)] bg-[var(--brand-soft)] text-[var(--brand-strong)]'
          : 'border-[var(--border)] bg-[var(--surface-strong)] text-[var(--text-secondary)]'
      } ${disabled ? 'cursor-not-allowed opacity-60' : 'hover:shadow-sm'}`}
    >
      {label}
    </button>
  );
}

export default function AnalysisDashboardPage() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const analysisState = useAppSelector((state) => state.analysis);
  const analyses = useAppSelector(selectAnalyses);
  const error = useAppSelector(selectAnalysisError);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSubmittingAnalysis, setIsSubmittingAnalysis] = useState(false);
  const [creationStep, setCreationStep] = useState<CreationStep>('idle');
  const [latestCreatedAnalysisId, setLatestCreatedAnalysisId] = useState<string | null>(
    null,
  );
  const [datasetCapability, setDatasetCapability] = useState<DatasetCapability | null>(
    null,
  );
  const [metricsCsvDirections, setMetricsCsvDirections] = useState<Record<
    string,
    MetricDirection
  > | null>(null);
  const [datasetFileName, setDatasetFileName] = useState<string | null>(null);
  const [metricsFileName, setMetricsFileName] = useState<string | null>(null);
  const [evolutionOptions, setEvolutionOptions] = useState<EvolutionOptions>(
    DEFAULT_EVOLUTION_OPTIONS,
  );
  const [submittedAnalysisName, setSubmittedAnalysisName] = useState('');
  const [submittedAnalysisDescription, setSubmittedAnalysisDescription] = useState('');

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortOption, setSortOption] = useState<SortOption>('date_desc');
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);

  const [editingAnalysisId, setEditingAnalysisId] = useState<string | null>(null);
  const [editedName, setEditedName] = useState('');
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [deletingAnalysisId, setDeletingAnalysisId] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const filtersRef = useRef<HTMLDivElement | null>(null);
  const createModalScrollRef = useRef<HTMLDivElement | null>(null);

  const scrollCreateModalTop = () => {
    createModalScrollRef.current?.scrollTo({
      top: 0,
      left: 0,
      behavior: 'auto',
    });
  };

  const waitForPaint = () =>
    new Promise<void>((resolve) => {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => resolve());
      });
    });

  useEffect(() => {
    void dispatch(listAnalyses());
  }, [dispatch]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!filtersRef.current) return;

      if (!filtersRef.current.contains(event.target as Node)) {
        setIsFiltersOpen(false);
      }
    }

    if (isFiltersOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isFiltersOpen]);

  const stats = useMemo(() => {
    const totalAnalyses = analyses.length;
    const completed = analyses.filter(
      (item) => getNormalizedStatus(item.status) === 'completed',
    ).length;
    const withDataset = analyses.filter((item) => item.normalized_dataset_file_id).length;

    return {
      totalAnalyses,
      completed,
      withDataset,
    };
  }, [analyses]);

  const detectedMetrics = datasetCapability?.metrics ?? [];
  const selectedModules = analysisState.analyzeForm.modules;

  const displayedMetricsDirection = useMemo(() => {
    if (metricsCsvDirections) {
      return metricsCsvDirections;
    }

    const manual = analysisState.analyzeForm.metricsDirection || {};
    const filteredManual: Record<string, MetricDirection> = {};

    for (const metric of detectedMetrics) {
      const selected = manual[metric];

      if (selected === 'maximize' || selected === 'minimize') {
        filteredManual[metric] = selected;
      }
    }

    return filteredManual;
  }, [metricsCsvDirections, analysisState.analyzeForm.metricsDirection, detectedMetrics]);

  const filteredAndSortedAnalyses = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();

    const filtered = analyses.filter((analysis) => {
      const matchesSearch =
        normalizedSearch.length === 0 ||
        analysis.name.toLowerCase().includes(normalizedSearch) ||
        (analysis.description ?? '').toLowerCase().includes(normalizedSearch);

      const matchesStatus = matchesStatusFilter(analysis.status, statusFilter);

      return matchesSearch && matchesStatus;
    });

    return [...filtered].sort((a, b) => {
      if (sortOption === 'name_asc') return a.name.localeCompare(b.name, 'es');
      if (sortOption === 'name_desc') return b.name.localeCompare(a.name, 'es');

      const aTimestamp = getAnalysisTimestamp(a.updated_at || a.created_at);
      const bTimestamp = getAnalysisTimestamp(b.updated_at || b.created_at);

      return sortOption === 'date_asc'
        ? aTimestamp - bTimestamp
        : bTimestamp - aTimestamp;
    });
  }, [analyses, searchTerm, statusFilter, sortOption]);

  const hasActiveFilters =
    searchTerm.trim().length > 0 || statusFilter !== 'all' || sortOption !== 'date_desc';

  const selectedHasSaesModules = selectedModules.some(isSaesModule);
  const selectedHasEvolutionModules = selectedModules.some(isEvolutionModule);

  const hasRunnableDataset =
    Boolean(datasetCapability?.hasSaes) || Boolean(datasetCapability?.hasEvolution);

  const canRunAnalysis =
    Boolean(analysisState.createAnalysisForm.name.trim()) &&
    Boolean(analysisState.datasetFile) &&
    hasRunnableDataset &&
    selectedModules.length > 0 &&
    (!selectedHasEvolutionModules || evolutionOptions.xColumns.length > 0) &&
    !isSubmittingAnalysis;

  const handleOpenModal = () => {
    dispatch(clearAnalysisError());
    dispatch(clearAnalysisSuccessMessage());
    setCreationStep('idle');
    setLatestCreatedAnalysisId(null);
    setDatasetCapability(null);
    setMetricsCsvDirections(null);
    setDatasetFileName(null);
    setMetricsFileName(null);
    setSubmittedAnalysisName('');
    setSubmittedAnalysisDescription('');
    setEvolutionOptions(DEFAULT_EVOLUTION_OPTIONS);
    dispatch(setDatasetFile(null));
    dispatch(setMetricsFile(null));
    dispatch(setPlotExportFormats(['png']));
    dispatch(setAnalyzeModules([]));
    setIsCreateModalOpen(true);
  };

  const handleCloseModal = () => {
    if (isSubmittingAnalysis) return;

    setIsCreateModalOpen(false);
    setCreationStep('idle');
  };

  const handleStartEditName = (analysisId: string, currentName: string) => {
    setEditingAnalysisId(analysisId);
    setEditedName(currentName);
    setIsEditModalOpen(true);
  };

  const handleSaveName = async () => {
    if (!editingAnalysisId || !editedName.trim()) return;

    const currentAnalysis = analyses.find(
      (analysis) => analysis.id === editingAnalysisId,
    );

    const result = await dispatch(
      updateAnalysis({
        analysisId: editingAnalysisId,
        name: editedName.trim(),
        description: currentAnalysis?.description || '',
      }),
    );

    if (updateAnalysis.fulfilled.match(result)) {
      setIsEditModalOpen(false);
      setEditingAnalysisId(null);
      setEditedName('');
      await dispatch(listAnalyses());
    }
  };

  const handleDeleteClick = (analysisId: string) => {
    setDeletingAnalysisId(analysisId);
    setShowDeleteConfirm(true);
  };

  const handleDeleteAnalysis = async () => {
    if (!deletingAnalysisId) return;

    setIsDeleting(true);

    const result = await dispatch(deleteAnalysis(deletingAnalysisId));

    if (deleteAnalysis.fulfilled.match(result)) {
      setShowDeleteConfirm(false);
      setDeletingAnalysisId(null);
      await dispatch(listAnalyses());
    }

    setIsDeleting(false);
  };

  const handleDatasetChange = async (file: File | null) => {
    dispatch(setDatasetFile(file));
    setDatasetFileName(file ? file.name : null);
    setMetricsCsvDirections(null);

    if (!file) {
      setDatasetCapability(null);
      setEvolutionOptions(DEFAULT_EVOLUTION_OPTIONS);
      dispatch(setAnalyzeModules([]));
      return;
    }

    try {
      const capability = await inspectDataset(file);
      setDatasetCapability(capability);

      setEvolutionOptions((previous) => ({
        ...previous,
        xColumns: capability.detectedXColumns,
        xLabelsByColumn: {
          ...buildDefaultXLabels(capability.detectedXColumns),
          ...previous.xLabelsByColumn,
        },
        yLabelsByMetric: {
          ...buildDefaultYLabels(capability.metrics),
          ...previous.yLabelsByMetric,
        },
      }));

      const currentModules = normalizeSelectedModulesForCapability(
        analysisState.analyzeForm.modules,
        capability,
      );

      dispatch(
        setAnalyzeModules(
          currentModules.length > 0
            ? currentModules
            : getDefaultModulesForCapability(capability),
        ),
      );

      if (!analysisState.createAnalysisForm.name.trim()) {
        dispatch(
          setCreateAnalysisField({
            field: 'name',
            value: file.name.replace(/\.csv$/i, ''),
          }),
        );
      }
    } catch {
      setDatasetCapability(null);
      setEvolutionOptions(DEFAULT_EVOLUTION_OPTIONS);
      dispatch(setAnalyzeModules([]));
    }
  };

  const handleMetricsCsvChange = async (file: File | null) => {
    dispatch(setMetricsFile(file));
    setMetricsFileName(file ? file.name : null);

    if (!file) {
      setMetricsCsvDirections(null);
      return;
    }

    try {
      const parsed = await extractMetricDirectionsFromMetricsCsv(file);

      if (!parsed) {
        setMetricsCsvDirections(null);
        return;
      }

      if (detectedMetrics.length === 0) {
        setMetricsCsvDirections(parsed);
        return;
      }

      const filtered: Record<string, MetricDirection> = {};

      for (const metric of detectedMetrics) {
        const direction = parsed[metric];

        if (direction) {
          filtered[metric] = direction;
        }
      }

      setMetricsCsvDirections(Object.keys(filtered).length ? filtered : null);
    } catch {
      setMetricsCsvDirections(null);
    }
  };

  const clearDatasetFile = () => {
    if (isSubmittingAnalysis) return;

    dispatch(setDatasetFile(null));
    dispatch(setAnalyzeModules([]));
    setDatasetFileName(null);
    setDatasetCapability(null);
    setMetricsCsvDirections(null);
    setEvolutionOptions(DEFAULT_EVOLUTION_OPTIONS);
  };

  const clearMetricsFile = () => {
    if (isSubmittingAnalysis) return;

    dispatch(setMetricsFile(null));
    setMetricsFileName(null);
    setMetricsCsvDirections(null);
  };

  const handleToggleModule = (module: AnalysisModule) => {
    if (!isModuleEnabled(module, datasetCapability)) return;

    dispatch(toggleModule(module));
  };

  const handleCreateAndRunAnalysis = async () => {
    const name = analysisState.createAnalysisForm.name.trim();
    const description = analysisState.createAnalysisForm.description;
    const datasetFile = analysisState.datasetFile;
    const modules = analysisState.analyzeForm.modules;
    const metricsFile = analysisState.metricsFile;
    const plotExportFormats = analysisState.analyzeForm.plotExportFormats;

    const shouldSendMetricsDirection = selectedHasSaesModules;

    const metricsDirectionToSend =
      shouldSendMetricsDirection && metricsFile && metricsCsvDirections
        ? undefined
        : shouldSendMetricsDirection && Object.keys(displayedMetricsDirection).length > 0
        ? displayedMetricsDirection
        : undefined;

    const shouldSendPlotExportFormat =
      selectedHasSaesModules || selectedHasEvolutionModules;

    if (!canRunAnalysis || !name || !datasetFile) return;

    setSubmittedAnalysisName(name);
    setSubmittedAnalysisDescription(description.trim());

    dispatch(clearAnalysisError());
    dispatch(clearAnalysisSuccessMessage());

    setIsSubmittingAnalysis(true);
    setCreationStep('creating');

    await waitForPaint();
    scrollCreateModalTop();

    try {
      const createResult = await dispatch(
        createAnalysis({
          name,
          description: description.trim(),
        }),
      );

      if (!createAnalysis.fulfilled.match(createResult)) {
        setCreationStep('error');
        setIsSubmittingAnalysis(false);
        return;
      }

      const analysisId = createResult.payload.id;

      setLatestCreatedAnalysisId(analysisId);
      setCreationStep('uploading_dataset');

      await waitForPaint();
      scrollCreateModalTop();

      const uploadResult = await dispatch(
        uploadAnalysisDataset({
          analysisId,
          file: datasetFile,
        }),
      );

      if (!uploadAnalysisDataset.fulfilled.match(uploadResult)) {
        setCreationStep('error');
        setIsSubmittingAnalysis(false);
        return;
      }

      setCreationStep('running_analysis');

      await waitForPaint();
      scrollCreateModalTop();

      const analyzeResult = await dispatch(
        analyzeAnalysis({
          analysisId,
          modules,
          metricsDirection: metricsDirectionToSend,
          metricsFile: selectedHasSaesModules ? metricsFile : null,
          plotExportFormats: shouldSendPlotExportFormat ? plotExportFormats : undefined,

          evolutionTitle: selectedHasEvolutionModules
            ? evolutionOptions.title || 'Curva de Convergencia'
            : undefined,

          evolutionXAxisColumns: selectedHasEvolutionModules
            ? evolutionOptions.xColumns
            : undefined,

          evolutionXLabelsByColumn: selectedHasEvolutionModules
            ? evolutionOptions.xLabelsByColumn
            : undefined,

          evolutionYLabelsByMetric: selectedHasEvolutionModules
            ? evolutionOptions.yLabelsByMetric
            : undefined,

          evolutionShowGrid: selectedHasEvolutionModules
            ? evolutionOptions.showGrid
            : undefined,

          evolutionShowMinMax: selectedHasEvolutionModules
            ? evolutionOptions.showMinMax
            : undefined,

          evolutionShowStd: selectedHasEvolutionModules
            ? evolutionOptions.showStd
            : undefined,

          evolutionShowAverage: selectedHasEvolutionModules
            ? evolutionOptions.showAverage
            : undefined,

          evolutionShowMedian: selectedHasEvolutionModules
            ? evolutionOptions.showMedian
            : undefined,

          evolutionGroupByInstance: selectedHasEvolutionModules
            ? evolutionOptions.groupByInstance
            : undefined,

          evolutionGroupByMetric: selectedHasEvolutionModules
            ? evolutionOptions.groupByMetric
            : undefined,
        }),
      );

      if (!analyzeAnalysis.fulfilled.match(analyzeResult)) {
        setCreationStep('error');
        setIsSubmittingAnalysis(false);
        return;
      }

      setCreationStep('finished');

      await dispatch(listAnalyses());

      setTimeout(() => {
        setIsCreateModalOpen(false);
        setIsSubmittingAnalysis(false);
        setCreationStep('idle');
        setSubmittedAnalysisName('');
        setSubmittedAnalysisDescription('');

        navigate(`/analysis/${analysisId}`);
      }, 700);
    } catch {
      setCreationStep('error');
      setIsSubmittingAnalysis(false);
    }
  };

  const progressValue = getCreationProgress(creationStep);

  return (
    <PrivateLayout>
      <main className="min-h-screen bg-[var(--app-bg)] px-3 py-5 sm:px-4 md:px-6 xl:px-8 2xl:px-10">
        <div className="mx-auto w-full max-w-[2200px]">
          <section className="pages-hero-card pages-hero-card-analysis 2xl:p-10">
            <div className="flex flex-col gap-8 2xl:grid 2xl:grid-cols-[minmax(0,1.15fr)_minmax(520px,0.85fr)] 2xl:items-center">
              <div className="min-w-0">
                <h1 className="max-w-[14ch] text-4xl font-black tracking-tight text-[var(--text-primary)] md:text-6xl 2xl:text-7xl">
                  {t('analysis.title')}
                </h1>

                <p className="mt-5 max-w-3xl text-[15px] leading-7 text-[var(--text-secondary)] md:text-base">
                  {t('analysis.dashboard.subtitle')}
                </p>

                <div className="mt-6">
                  <button
                    type="button"
                    onClick={handleOpenModal}
                    className="pages-action-btn-primary px-7 py-3 font-black"
                  >
                    <span className="material-symbols-outlined">add_circle</span>
                    <span>{t('analysis.dashboard.newAnalysis')}</span>
                  </button>
                </div>
              </div>

              <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-3">
                <StatCard
                  label={t('analysis.dashboard.stats.total')}
                  value={stats.totalAnalyses}
                  icon="analytics"
                  tone="blue"
                />
                <StatCard
                  label={t('analysis.dashboard.stats.completed')}
                  value={stats.completed}
                  icon="check_circle"
                  tone="emerald"
                />
                <StatCard
                  label={t('analysis.dashboard.stats.withDataset')}
                  value={stats.withDataset}
                  icon="upload_file"
                  tone="amber"
                />
              </div>
            </div>
          </section>

          {error ? (
            <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-100 px-5 py-4 text-sm font-medium text-rose-700 shadow-sm">
              {t(error, { defaultValue: error })}
            </div>
          ) : null}

          <Shell className="pages-surface-section">
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-2xl font-black tracking-tight text-[var(--text-primary)]">
                {t('analysis.dashboard.table.title')}
              </h2>

              <div ref={filtersRef} className="relative self-start sm:self-auto">
                <button
                  type="button"
                  onClick={() => setIsFiltersOpen((prev) => !prev)}
                  className={`inline-flex items-center gap-2 rounded-full border px-4 py-2.5 text-sm font-bold shadow-sm transition-all hover:scale-[1.02] ${
                    hasActiveFilters
                      ? 'border-[var(--brand)] bg-[var(--brand-soft)] text-[var(--brand-strong)]'
                      : 'border-[var(--border)] bg-[var(--surface-strong)] text-[var(--text-primary)]'
                  }`}
                >
                  <span className="material-symbols-outlined text-[18px]">
                    filter_alt
                  </span>
                  <span>{t('analysis.dashboard.filters.title')}</span>
                  <span className="material-symbols-outlined text-[18px]">
                    {isFiltersOpen ? 'expand_less' : 'expand_more'}
                  </span>
                </button>

                {isFiltersOpen ? (
                  <div className="pages-floating-popover absolute right-0 top-[calc(100%+12px)] z-20 w-[320px] p-5">
                    <div className="mb-4 flex items-center justify-between">
                      <h3 className="text-sm font-black uppercase tracking-widest text-[var(--text-secondary)]">
                        {t('analysis.dashboard.filters.searchSort')}
                      </h3>

                      {hasActiveFilters ? (
                        <button
                          type="button"
                          onClick={() => {
                            setSearchTerm('');
                            setStatusFilter('all');
                            setSortOption('date_desc');
                          }}
                          className="text-xs font-bold text-[var(--brand)] transition-opacity hover:opacity-80"
                        >
                          {t('common.clear')}
                        </button>
                      ) : null}
                    </div>

                    <div className="space-y-4">
                      <input
                        type="text"
                        value={searchTerm}
                        onChange={(event) => setSearchTerm(event.target.value)}
                        placeholder={t(
                          'analysis.dashboard.placeholders.nameOrDescription',
                        )}
                        className="app-input w-full rounded-2xl px-4 py-3"
                      />

                      <StyledSelect
                        value={statusFilter}
                        onChange={(value) => setStatusFilter(value as StatusFilter)}
                      >
                        <option value="all">
                          {t('analysis.dashboard.filters.allStatuses')}
                        </option>
                        <option value="created">{t('analysis.status.created')}</option>
                        <option value="completed">
                          {t('analysis.status.completed')}
                        </option>
                        <option value="running">
                          {t('analysis.dashboard.filters.runningPending')}
                        </option>
                        <option value="error">
                          {t('analysis.dashboard.filters.errors')}
                        </option>
                      </StyledSelect>

                      <StyledSelect
                        value={sortOption}
                        onChange={(value) => setSortOption(value as SortOption)}
                      >
                        <option value="date_desc">
                          {t('analysis.dashboard.filters.recentFirst')}
                        </option>
                        <option value="date_asc">
                          {t('analysis.dashboard.filters.oldestFirst')}
                        </option>
                        <option value="name_asc">
                          {t('analysis.dashboard.filters.nameAZ')}
                        </option>
                        <option value="name_desc">
                          {t('analysis.dashboard.filters.nameZA')}
                        </option>
                      </StyledSelect>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            {filteredAndSortedAnalyses.length === 0 ? (
              <div className="pages-soft-surface-dashed px-6 py-16 text-center">
                <div className="mx-auto mb-4 inline-flex h-16 w-16 items-center justify-center rounded-3xl bg-[var(--brand-soft)] text-[var(--brand)]">
                  <span className="material-symbols-outlined text-3xl">analytics</span>
                </div>
                <p className="text-base font-bold text-[var(--text-primary)]">
                  {analyses.length === 0
                    ? t('analysis.dashboard.empty.noAnalyses')
                    : t('analysis.dashboard.empty.noResults')}
                </p>
              </div>
            ) : (
              <div className="pages-soft-surface-strong overflow-hidden rounded-[28px]">
                <div className="grid grid-cols-[minmax(0,2fr)_minmax(160px,1fr)_minmax(140px,1fr)_minmax(130px,1fr)] items-center gap-4 bg-gradient-to-r from-slate-50 to-white px-6 py-4 text-xs font-black uppercase tracking-wider text-[var(--text-muted)]">
                  <span>{t('analysis.dashboard.table.name')}</span>
                  <span>{t('analysis.dashboard.table.date')}</span>
                  <span>{t('analysis.dashboard.table.status')}</span>
                  <span className="text-center">
                    {t('analysis.dashboard.table.actions')}
                  </span>
                </div>

                <div className="divide-y divide-[var(--border)]">
                  {filteredAndSortedAnalyses.map((analysis) => (
                    <div
                      key={analysis.id}
                      className="grid grid-cols-[minmax(0,2fr)_minmax(160px,1fr)_minmax(140px,1fr)_minmax(130px,1fr)] items-center gap-4 px-6 py-5 transition-all hover:bg-gradient-to-r hover:from-[var(--brand-soft)] hover:to-transparent"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-base font-black text-[var(--text-primary)]">
                          {analysis.name}
                        </p>

                        {analysis.description ? (
                          <p className="mt-1 truncate text-sm text-[var(--text-secondary)]">
                            {analysis.description}
                          </p>
                        ) : null}
                      </div>

                      <div className="text-sm font-medium text-[var(--text-secondary)]">
                        {formatRelativeDate(analysis.updated_at || analysis.created_at)}
                      </div>

                      <div>
                        <span className={getStatusBadgeClass(analysis.status)}>
                          <span className="h-2 w-2 rounded-full bg-current opacity-70" />
                          {(() => {
                            const statusKey = getStatusLabelKey(analysis.status);

                            return statusKey
                              ? t(statusKey)
                              : analysis.status || t('analysis.status.created');
                          })()}
                        </span>
                      </div>

                      <div className="flex items-center justify-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleStartEditName(analysis.id, analysis.name)}
                          className="pages-icon-circle-btn pages-icon-circle-btn-edit inline-flex h-11 w-11 items-center justify-center rounded-2xl"
                          title={t('common.edit')}
                          aria-label={`${t('common.edit')} ${analysis.name}`}
                        >
                          <span className="material-symbols-outlined">edit</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleDeleteClick(analysis.id)}
                          className="pages-icon-circle-btn pages-icon-circle-btn-delete inline-flex h-11 w-11 items-center justify-center rounded-2xl"
                          title={t('common.delete')}
                          aria-label={`${t('common.delete')} ${analysis.name}`}
                        >
                          <span className="material-symbols-outlined">delete</span>
                        </button>

                        <Link
                          to={`/analysis/${analysis.id}`}
                          className="pages-icon-circle-btn pages-icon-circle-btn-open inline-flex h-11 w-11 items-center justify-center rounded-2xl"
                          title={t('common.open')}
                          aria-label={`${t('common.open')} ${analysis.name}`}
                        >
                          <span className="material-symbols-outlined">visibility</span>
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Shell>
        </div>

        {isCreateModalOpen ? (
          <div className="fixed inset-0 z-50 bg-black/55 px-4 py-4 md:px-6 md:py-6">
            <div className="flex h-full items-center justify-center">
              <div className="pages-modal-surface w-full max-w-7xl overflow-hidden rounded-[36px] shadow-2xl">
                <div ref={createModalScrollRef} className="max-h-[92vh] overflow-y-auto">
                  <div className="pages-modal-header p-6 md:p-8">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h2 className="text-3xl font-black tracking-tight text-[var(--text-primary)]">
                          {t('analysis.dashboard.modal.createTitle')}
                        </h2>
                        <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
                          {t('analysis.dashboard.modal.createSubtitle')}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={handleCloseModal}
                        disabled={isSubmittingAnalysis}
                        className="pages-icon-circle-btn pages-icon-circle-btn-delete inline-flex h-11 w-11 items-center justify-center rounded-2xl"
                        aria-label={t('analysis.preview.closeModal')}
                      >
                        <span className="material-symbols-outlined">close</span>
                      </button>
                    </div>

                    {isSubmittingAnalysis || creationStep === 'error' ? (
                      <div className="mt-6 rounded-[28px] p-5 shadow-sm pages-alert-surface">
                        <div className="mb-3 flex items-center justify-between gap-4">
                          <div className="min-w-0">
                            <p className="text-sm font-bold text-[var(--text-primary)]">
                              {t(getCreationMessageKey(creationStep))}
                            </p>
                            {latestCreatedAnalysisId ? (
                              <p className="mt-1 text-xs text-[var(--text-secondary)]">
                                {t('analysis.dashboard.modal.analysisId')}:{' '}
                                {latestCreatedAnalysisId}
                              </p>
                            ) : null}
                          </div>

                          <span className="text-sm font-black text-[var(--brand)]">
                            {progressValue}%
                          </span>
                        </div>

                        <div className="pages-progress-track h-3 w-full overflow-hidden rounded-full">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              creationStep === 'error'
                                ? 'bg-rose-500'
                                : 'pages-progress-fill'
                            }`}
                            style={{ width: `${progressValue}%` }}
                          />
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div className="grid grid-cols-1 gap-8 p-6 md:p-8 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
                    <div className="space-y-6">
                      <div className="pages-modal-panel-neutral rounded-[28px] p-6 shadow-sm">
                        <h3 className="mb-4 text-xl font-black text-[var(--text-primary)]">
                          {t('analysis.dashboard.modal.baseData')}
                        </h3>

                        <div className="space-y-5">
                          <input
                            value={
                              isSubmittingAnalysis
                                ? submittedAnalysisName
                                : analysisState.createAnalysisForm.name
                            }
                            onChange={(event) =>
                              dispatch(
                                setCreateAnalysisField({
                                  field: 'name',
                                  value: event.target.value,
                                }),
                              )
                            }
                            placeholder={t(
                              'analysis.dashboard.placeholders.analysisName',
                            )}
                            disabled={isSubmittingAnalysis}
                            className="app-input w-full rounded-2xl px-4 py-3"
                          />

                          <textarea
                            value={
                              isSubmittingAnalysis
                                ? submittedAnalysisDescription
                                : analysisState.createAnalysisForm.description
                            }
                            onChange={(event) =>
                              dispatch(
                                setCreateAnalysisField({
                                  field: 'description',
                                  value: event.target.value,
                                }),
                              )
                            }
                            placeholder={t('analysis.dashboard.placeholders.description')}
                            disabled={isSubmittingAnalysis}
                            className="app-input min-h-[140px] w-full resize-none rounded-2xl px-4 py-3"
                          />
                        </div>
                      </div>

                      <UploadCard
                        icon="cloud_upload"
                        title={t('analysis.dashboard.modal.uploadDatasetTitle')}
                        fileName={datasetFileName}
                        onFileChange={handleDatasetChange}
                        onClear={clearDatasetFile}
                        accept=".csv,text/csv"
                        disabled={isSubmittingAnalysis}
                        tone="blue"
                      />
                      <div className="rounded-2xl border border-blue-100 bg-blue-50/80 px-5 py-4 text-sm text-blue-800 shadow-sm">
                        <p className="mb-2 font-black text-blue-900">
                          {t('analysis.dashboard.modal.validCsvFormat.title')}
                        </p>

                        <p className="leading-6">
                          {t('analysis.dashboard.modal.validCsvFormat.saes')}{' '}
                          <strong>
                            Algorithm, Instance, MetricName, ExecutionId, MetricValue
                          </strong>
                          .
                        </p>

                        <p className="mt-2 leading-6">
                          {t('analysis.dashboard.modal.validCsvFormat.evolution')}{' '}
                          <strong>Algorithm, MetricValue</strong>{' '}
                          {t('analysis.dashboard.modal.validCsvFormat.evolutionAxis')}{' '}
                          <strong>Generation, Iteration, Time o Evaluations</strong>.
                        </p>
                      </div>
                      <UploadCard
                        icon="upload_file"
                        title={t('analysis.dashboard.modal.uploadMetricsTitle')}
                        fileName={metricsFileName}
                        onFileChange={handleMetricsCsvChange}
                        onClear={clearMetricsFile}
                        accept=".csv,text/csv"
                        disabled={isSubmittingAnalysis || !datasetCapability?.hasSaes}
                        tone="violet"
                      />
                      <div className="rounded-2xl border border-violet-100 bg-violet-50/80 px-5 py-4 text-sm text-violet-800 shadow-sm">
                        <p className="mb-2 font-black text-violet-900">
                          {t('analysis.dashboard.modal.validMetricsFormat.title')}
                        </p>

                        <p className="leading-6">
                          {t('analysis.dashboard.modal.validMetricsFormat.description')}{' '}
                          <strong>MetricName, Maximize</strong>.
                        </p>

                        <p className="mt-2 text-xs leading-5 text-violet-700">
                          {t('analysis.dashboard.modal.validMetricsFormat.values')}{' '}
                          <strong>True</strong> / <strong>False</strong>.
                        </p>
                      </div>
                      {datasetCapability ? (
                        <div className="pages-detection-surface rounded-2xl px-5 py-5 text-sm shadow-sm">
                          <p className="font-black text-[var(--text-primary)]">
                            {t('analysis.dashboard.detection.title')}
                          </p>

                          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                            <div
                              className={`pages-detection-card rounded-2xl px-4 py-3 ${
                                datasetCapability.hasSaes
                                  ? 'pages-detection-card-available'
                                  : 'pages-detection-card-unavailable'
                              }`}
                            >
                              <p className="font-bold">SAES</p>
                              <p className="mt-1 text-xs">
                                {datasetCapability.hasSaes
                                  ? t('analysis.dashboard.detection.available')
                                  : t('analysis.dashboard.detection.unavailable')}
                              </p>
                            </div>

                            <div
                              className={`pages-detection-card rounded-2xl px-4 py-3 ${
                                datasetCapability.hasEvolution
                                  ? 'pages-detection-card-available'
                                  : 'pages-detection-card-unavailable'
                              }`}
                            >
                              <p className="font-bold">
                                {t('analysis.modules.evolution_plots')}
                              </p>
                              <p className="mt-1 text-xs">
                                {datasetCapability.hasEvolution
                                  ? t('analysis.dashboard.detection.available')
                                  : t('analysis.dashboard.detection.unavailable')}
                              </p>
                            </div>
                          </div>

                          <div className="mt-4 grid grid-cols-1 gap-2 text-xs text-[var(--text-secondary)] sm:grid-cols-2">
                            <p>
                              <strong>Filas:</strong> {datasetCapability.rowCount}
                            </p>
                            <p>
                              <strong>X detectadas:</strong>{' '}
                              {datasetCapability.detectedXColumns.length > 0
                                ? datasetCapability.detectedXColumns.join(', ')
                                : '-'}
                            </p>
                            <p>
                              <strong>Métricas:</strong>{' '}
                              {datasetCapability.metrics.length || '-'}
                            </p>
                            <p>
                              <strong>Fitness:</strong>{' '}
                              {datasetCapability.detectedFitnessColumn || '-'}
                            </p>
                            <p>
                              <strong>Run:</strong>{' '}
                              {datasetCapability.detectedRunColumn || '-'}
                            </p>
                          </div>
                        </div>
                      ) : null}
                    </div>

                    <div className="space-y-6">
                      <div className="pages-modal-panel-blue rounded-[28px] p-6 shadow-sm">
                        <p className="mb-4 text-sm font-black uppercase tracking-widest text-[var(--text-secondary)]">
                          {t('analysis.dashboard.modal.availableModules')}
                        </p>

                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                          {MODULES.map((module) => {
                            const active = selectedModules.includes(module);
                            const disabledReason = getModuleDisabledReason(
                              module,
                              datasetCapability,
                            );

                            return (
                              <ModuleButton
                                key={module}
                                module={module}
                                active={active}
                                disabled={isSubmittingAnalysis || Boolean(disabledReason)}
                                disabledReason={disabledReason}
                                onClick={() => handleToggleModule(module)}
                              />
                            );
                          })}
                        </div>
                      </div>

                      {selectedModules.includes('saes_plots') ||
                      selectedModules.includes('evolution_plots') ? (
                        <div className="pages-modal-panel-violet rounded-[28px] p-6 shadow-sm">
                          <p className="mb-4 text-sm font-black uppercase tracking-widest text-[var(--text-secondary)]">
                            {t('analysis.dashboard.modal.exportFormat')}
                          </p>

                          <div className="flex flex-wrap gap-2">
                            {(
                              ['png', 'eps', 'svg', 'jpg', 'jpeg'] as PlotExportFormat[]
                            ).map((format) => {
                              const active =
                                analysisState.analyzeForm.plotExportFormats.includes(
                                  format,
                                );

                              return (
                                <button
                                  key={format}
                                  type="button"
                                  onClick={() => dispatch(togglePlotExportFormat(format))}
                                  disabled={isSubmittingAnalysis}
                                  className={`rounded-full border px-4 py-2 text-xs font-bold transition-all ${
                                    active
                                      ? 'border-[var(--brand)] bg-[var(--brand-soft)] text-[var(--brand-strong)] shadow-sm'
                                      : 'border-[var(--border)] bg-[var(--surface-strong)] text-[var(--text-primary)]'
                                  }`}
                                >
                                  {format.toUpperCase()}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      ) : null}

                      {datasetCapability?.hasEvolution && selectedHasEvolutionModules ? (
                        <div className="pages-modal-panel-blue rounded-[28px] p-6 shadow-sm">
                          <p className="mb-4 text-sm font-black uppercase tracking-widest text-[var(--text-secondary)]">
                            {t('analysis.dashboard.modal.evolutionCurves.title', {
                              defaultValue: 'Gráficas de evolución',
                            })}
                          </p>

                          <div className="space-y-5">
                            <FormField
                              label={t('analysis.dashboard.modal.evolution.titleLabel')}
                            >
                              <input
                                type="text"
                                value={evolutionOptions.title}
                                onChange={(event) =>
                                  setEvolutionOptions((previous) => ({
                                    ...previous,
                                    title: event.target.value,
                                  }))
                                }
                                disabled={isSubmittingAnalysis}
                                className="app-input w-full rounded-2xl px-4 py-3"
                                placeholder={t(
                                  'analysis.dashboard.modal.evolution.titlePlaceholder',
                                )}
                              />
                            </FormField>

                            <FormField
                              label={t('analysis.dashboard.modal.evolution.xColumns')}
                            >
                              <div className="flex flex-wrap gap-2">
                                {datasetCapability.detectedXColumns.map((column) => (
                                  <ChipButton
                                    key={column}
                                    label={column}
                                    active={evolutionOptions.xColumns.includes(column)}
                                    disabled={isSubmittingAnalysis}
                                    onClick={() =>
                                      setEvolutionOptions((previous) => ({
                                        ...previous,
                                        xColumns: toggleString(previous.xColumns, column),
                                      }))
                                    }
                                  />
                                ))}
                              </div>
                            </FormField>

                            {evolutionOptions.xColumns.length > 0 ? (
                              <FormField
                                label={t(
                                  'analysis.dashboard.modal.evolution.xAxisLabels',
                                )}
                              >
                                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                                  {evolutionOptions.xColumns.map((column) => (
                                    <label
                                      key={column}
                                      className="rounded-2xl border border-[var(--border)] bg-[var(--surface-strong)] p-3"
                                    >
                                      <span className="mb-2 block text-xs font-black text-[var(--text-secondary)]">
                                        {column}
                                      </span>
                                      <input
                                        type="text"
                                        value={
                                          evolutionOptions.xLabelsByColumn[column] ??
                                          column
                                        }
                                        onChange={(event) =>
                                          setEvolutionOptions((previous) => ({
                                            ...previous,
                                            xLabelsByColumn: {
                                              ...previous.xLabelsByColumn,
                                              [column]: event.target.value,
                                            },
                                          }))
                                        }
                                        disabled={isSubmittingAnalysis}
                                        className="app-input w-full rounded-xl px-3 py-2"
                                        placeholder={column}
                                      />
                                    </label>
                                  ))}
                                </div>
                              </FormField>
                            ) : null}

                            {detectedMetrics.length > 0 ? (
                              <FormField
                                label={t(
                                  'analysis.dashboard.modal.evolution.yAxisLabels',
                                )}
                              >
                                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                                  {detectedMetrics.map((metric) => (
                                    <label
                                      key={metric}
                                      className="rounded-2xl border border-[var(--border)] bg-[var(--surface-strong)] p-3"
                                    >
                                      <span className="mb-2 block text-xs font-black text-[var(--text-secondary)]">
                                        {metric}
                                      </span>
                                      <input
                                        type="text"
                                        value={
                                          evolutionOptions.yLabelsByMetric[metric] ??
                                          metric
                                        }
                                        onChange={(event) =>
                                          setEvolutionOptions((previous) => ({
                                            ...previous,
                                            yLabelsByMetric: {
                                              ...previous.yLabelsByMetric,
                                              [metric]: event.target.value,
                                            },
                                          }))
                                        }
                                        disabled={isSubmittingAnalysis}
                                        className="app-input w-full rounded-xl px-3 py-2"
                                        placeholder={metric}
                                      />
                                    </label>
                                  ))}
                                </div>
                              </FormField>
                            ) : null}

                            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                              <ToggleOption
                                label={t(
                                  'analysis.dashboard.modal.evolution.options.grid',
                                )}
                                checked={evolutionOptions.showGrid}
                                disabled={isSubmittingAnalysis}
                                onChange={(checked) =>
                                  setEvolutionOptions((previous) => ({
                                    ...previous,
                                    showGrid: checked,
                                  }))
                                }
                              />

                              <ToggleOption
                                label={t(
                                  'analysis.dashboard.modal.evolution.options.average',
                                )}
                                checked={evolutionOptions.showAverage}
                                disabled={isSubmittingAnalysis}
                                onChange={(checked) =>
                                  setEvolutionOptions((previous) => ({
                                    ...previous,
                                    showAverage: checked,
                                  }))
                                }
                              />

                              <ToggleOption
                                label={t(
                                  'analysis.dashboard.modal.evolution.options.median',
                                )}
                                checked={evolutionOptions.showMedian}
                                disabled={isSubmittingAnalysis}
                                onChange={(checked) =>
                                  setEvolutionOptions((previous) => ({
                                    ...previous,
                                    showMedian: checked,
                                  }))
                                }
                              />

                              <ToggleOption
                                label={t(
                                  'analysis.dashboard.modal.evolution.options.minMax',
                                )}
                                checked={evolutionOptions.showMinMax}
                                disabled={isSubmittingAnalysis}
                                onChange={(checked) =>
                                  setEvolutionOptions((previous) => ({
                                    ...previous,
                                    showMinMax: checked,
                                  }))
                                }
                              />

                              <ToggleOption
                                label={t(
                                  'analysis.dashboard.modal.evolution.options.std',
                                )}
                                checked={evolutionOptions.showStd}
                                disabled={isSubmittingAnalysis}
                                onChange={(checked) =>
                                  setEvolutionOptions((previous) => ({
                                    ...previous,
                                    showStd: checked,
                                  }))
                                }
                              />

                              <ToggleOption
                                label={t(
                                  'analysis.dashboard.modal.evolution.options.groupByInstance',
                                )}
                                checked={evolutionOptions.groupByInstance}
                                disabled={isSubmittingAnalysis}
                                onChange={(checked) =>
                                  setEvolutionOptions((previous) => ({
                                    ...previous,
                                    groupByInstance: checked,
                                  }))
                                }
                              />

                              <ToggleOption
                                label={t(
                                  'analysis.dashboard.modal.evolution.options.groupByMetric',
                                )}
                                checked={evolutionOptions.groupByMetric}
                                disabled={isSubmittingAnalysis}
                                onChange={(checked) =>
                                  setEvolutionOptions((previous) => ({
                                    ...previous,
                                    groupByMetric: checked,
                                  }))
                                }
                              />
                            </div>
                          </div>
                        </div>
                      ) : null}

                      {datasetCapability?.hasSaes && selectedHasSaesModules ? (
                        <div className="pages-accent-panel-amber p-6">
                          <p className="mb-4 text-sm font-black uppercase tracking-widest text-[var(--text-secondary)]">
                            {t('analysis.metricsDirection.title')}
                          </p>

                          {metricsCsvDirections ? (
                            <div className="mb-4 rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-700">
                              {t('analysis.metricsDirection.csvWillBeUsed')}
                            </div>
                          ) : null}

                          <div className="space-y-3">
                            {detectedMetrics.length > 0 ? (
                              detectedMetrics.map((metric) => {
                                const effectiveDirection =
                                  displayedMetricsDirection[metric] || 'maximize';

                                return (
                                  <div
                                    key={metric}
                                    className="pages-list-row-soft flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                                  >
                                    <span className="truncate font-semibold text-[var(--text-primary)]">
                                      {metric}
                                    </span>

                                    <div className="flex gap-2">
                                      <button
                                        type="button"
                                        onClick={() =>
                                          !metricsCsvDirections &&
                                          dispatch(
                                            setMetricDirection({
                                              metric,
                                              direction: 'maximize',
                                            }),
                                          )
                                        }
                                        disabled={
                                          isSubmittingAnalysis ||
                                          Boolean(metricsCsvDirections)
                                        }
                                        className={`rounded-xl px-3 py-1.5 text-xs font-bold ${
                                          effectiveDirection === 'maximize'
                                            ? 'bg-blue-100 text-blue-700'
                                            : 'bg-[var(--surface-muted)] text-[var(--text-secondary)]'
                                        }`}
                                      >
                                        Max
                                      </button>

                                      <button
                                        type="button"
                                        onClick={() =>
                                          !metricsCsvDirections &&
                                          dispatch(
                                            setMetricDirection({
                                              metric,
                                              direction: 'minimize',
                                            }),
                                          )
                                        }
                                        disabled={
                                          isSubmittingAnalysis ||
                                          Boolean(metricsCsvDirections)
                                        }
                                        className={`rounded-xl px-3 py-1.5 text-xs font-bold ${
                                          effectiveDirection === 'minimize'
                                            ? 'bg-violet-100 text-violet-700'
                                            : 'bg-[var(--surface-muted)] text-[var(--text-secondary)]'
                                        }`}
                                      >
                                        Min
                                      </button>
                                    </div>
                                  </div>
                                );
                              })
                            ) : (
                              <div className="pages-soft-surface-dashed rounded-2xl px-4 py-8 text-center text-sm text-[var(--text-muted)]">
                                {t('analysis.metricsDirection.noMetrics')}
                              </div>
                            )}
                          </div>
                        </div>
                      ) : null}

                      {!hasRunnableDataset && analysisState.datasetFile ? (
                        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm font-medium text-rose-700">
                          {t('analysis.dashboard.modal.unsupportedDataset')}
                        </div>
                      ) : null}

                      {selectedHasEvolutionModules &&
                      evolutionOptions.xColumns.length === 0 ? (
                        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm font-medium text-amber-800">
                          Selecciona al menos una columna para el eje X de las curvas de
                          convergencia.
                        </div>
                      ) : null}

                      <button
                        type="button"
                        onClick={() => void handleCreateAndRunAnalysis()}
                        disabled={!canRunAnalysis}
                        className="flex w-full items-center justify-center gap-2 rounded-full bg-[var(--brand)] py-3.5 font-bold text-white shadow-lg transition-all hover:scale-[1.01] hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <span className="material-symbols-outlined">
                          {isSubmittingAnalysis ? 'sync' : 'play_arrow'}
                        </span>
                        <span>
                          {isSubmittingAnalysis
                            ? t('analysis.dashboard.modal.running')
                            : t('analysis.dashboard.modal.createAndRun')}
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={handleCloseModal}
                disabled={isSubmittingAnalysis}
                className="absolute inset-0 -z-10 cursor-default"
                aria-label={t('analysis.preview.closeModal')}
              />
            </div>
          </div>
        ) : null}

        {isEditModalOpen ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="pages-soft-surface-strong w-full max-w-md rounded-[24px] p-6 shadow-lg">
              <h2 className="mb-4 text-lg font-bold text-[var(--text-primary)]">
                {t('analysis.dashboard.editNameTitle')}
              </h2>

              <input
                type="text"
                value={editedName}
                onChange={(event) => setEditedName(event.target.value)}
                className="mb-4 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-[var(--text-primary)] placeholder-gray-400 focus:border-[var(--brand)] focus:outline-none"
                placeholder={t('common.name')}
                autoFocus
              />

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="pages-pill-btn flex-1 rounded-lg px-4 py-2 text-sm font-semibold"
                >
                  {t('common.cancel')}
                </button>

                <button
                  type="button"
                  onClick={() => void handleSaveName()}
                  className="flex-1 rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-semibold text-white transition-all hover:opacity-90 disabled:opacity-60"
                  disabled={!editedName.trim()}
                >
                  {t('common.save')}
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {showDeleteConfirm ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="pages-soft-surface-strong w-full max-w-md rounded-[24px] p-6 shadow-lg">
              <h2 className="mb-4 text-lg font-bold text-[var(--text-primary)]">
                {`${t('common.delete')} ${t('analysis.title').toLowerCase()}`}
              </h2>

              <p className="mb-6 text-sm text-[var(--text-secondary)]">
                {t('analysis.dashboard.deleteConfirm')}
              </p>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(false)}
                  className="pages-pill-btn flex-1 rounded-lg px-4 py-2 text-sm font-semibold"
                  disabled={isDeleting}
                >
                  {t('common.cancel')}
                </button>

                <button
                  type="button"
                  onClick={() => void handleDeleteAnalysis()}
                  className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-red-700 disabled:opacity-60"
                  disabled={isDeleting}
                >
                  {isDeleting ? t('settings.account.modal.deleting') : t('common.delete')}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </main>
    </PrivateLayout>
  );
}
