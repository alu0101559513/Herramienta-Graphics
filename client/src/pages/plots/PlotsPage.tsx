import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PrivateLayout from '../../components/PrivateLayout';
import '../../styles/pages.css';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import {
  setCurrentRunKey,
  setSelectedAnalysis,
} from '../../features/analysis/analysis.slice';
import {
  selectAnalysisFiles,
  selectCurrentRunKey,
  selectSelectedAnalysis,
} from '../../features/analysis/analysis.selectors';
import {
  downloadAnalysisPlotsZip,
  downloadAnalysisFile,
  getAnalysis,
  getAnalysisFileBlobUrl,
  listAnalysisFiles,
  reanalyzeAnalysis,
} from '../../features/analysis/analysis.thunks';
import { DEFAULT_EVOLUTION_OPTIONS } from '../../features/analysis/analysis.constants';
import { ALL_PLOT_TYPES, EVOLUTION_STATISTICS } from './plots.constants';
import type { EvolutionAnalyzeOptions } from '../../features/analysis/analysis.types';
import type {
  GridColumns,
  ImageFit,
  ImageHeight,
  OpenMenuKey,
  PlotItem,
  PlotType,
} from './plots-types';
import {
  applyEvolutionStatisticsToOptions,
  arraysEqualAsSet,
  buildAlgorithmRunKey,
  buildSelectionSignature,
  getEvolutionOptionsFromMetadata,
  getEvolutionStatisticLabel,
  getEvolutionStatisticsFromOptions,
  getFileExtension,
  getImageFitClass,
  getImageHeightClass,
  getModulesForPlotTypes,
  getPlotTypeLabel,
  isPreviewableImage,
  isRecord,
  isSupportedPlotFile,
  normalizePlotTypes,
  normalizeSaesPlotTypes,
  normalizeValues,
  parsePlotInfo,
  plotTypeArraysEqualAsSet,
  selectionAlreadyGenerated,
} from './plots-utils';

function SectionShell({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <section className={`pages-section-shell ${className}`}>{children}</section>;
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
  tone?: 'blue' | 'violet' | 'amber' | 'emerald';
}) {
  const toneClasses = {
    blue: 'pages-stat-card-icon-blue',
    violet: 'pages-stat-card-icon-violet',
    amber: 'pages-stat-card-icon-amber',
    emerald: 'pages-stat-card-icon-emerald',
  }[tone];

  return (
    <article className="pages-stat-card">
      <div className={`pages-stat-card-icon ${toneClasses}`}>
        <span className="material-symbols-outlined text-[21px]">{icon}</span>
      </div>
      <p className="pages-stat-label">{label}</p>
      <p className="pages-stat-value">{value}</p>
    </article>
  );
}

function FilterChip({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`pages-filter-chip ${
        active ? 'pages-filter-chip-active' : 'pages-filter-chip-inactive'
      }`}
      title={label}
    >
      <span className="block truncate">{label}</span>
    </button>
  );
}

function FilterSection({
  title,
  count,
  onClear,
  children,
}: {
  title: string;
  count: number;
  onClear: () => void;
  children: React.ReactNode;
}) {
  const { t } = useTranslation();

  return (
    <div className="pages-filter-section">
      <div className="pages-filter-section-header">
        <div className="flex items-center gap-2">
          <p className="pages-filter-section-title">{title}</p>
          {count > 0 ? <span className="pages-filter-badge">{count}</span> : null}
        </div>
        <button type="button" onClick={onClear} className="pages-filter-clear-btn">
          {t('common.clear')}
        </button>
      </div>
      {children}
    </div>
  );
}

function MiniOptionButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`pages-mini-option-btn ${
        active ? 'pages-mini-option-btn-active' : 'pages-mini-option-btn-inactive'
      }`}
    >
      {label}
    </button>
  );
}

function ToggleOption({
  label,
  checked,
  onChange,
  description,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  description?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`rounded-2xl border px-4 py-3 text-left transition-all ${
        checked
          ? 'border-[var(--brand)] bg-[var(--brand-soft)] text-[var(--brand-strong)]'
          : 'border-[var(--border)] bg-[var(--surface-strong)] text-[var(--text-primary)]'
      }`}
    >
      <span className="flex items-start justify-between gap-3">
        <span>
          <span className="block text-sm font-black">{label}</span>
          {description ? (
            <span className="mt-1 block text-xs leading-5 text-[var(--text-secondary)]">
              {description}
            </span>
          ) : null}
        </span>
        <span className="material-symbols-outlined text-[24px]">
          {checked ? 'toggle_on' : 'toggle_off'}
        </span>
      </span>
    </button>
  );
}

function GridPicker({
  selected,
  onSelect,
}: {
  selected: GridColumns;
  onSelect: (value: GridColumns) => void;
}) {
  const { t } = useTranslation();
  const options: GridColumns[] = [1, 2, 3, 4];

  return (
    <div className="grid grid-cols-4 gap-3">
      {options.map((cols) => (
        <button
          key={cols}
          type="button"
          onClick={() => onSelect(cols)}
          className={`pages-grid-picker-btn ${
            selected === cols
              ? 'pages-grid-picker-btn-active'
              : 'pages-grid-picker-btn-inactive'
          }`}
          title={t('analysis.plots.columnCount', { count: cols })}
        >
          <div
            className="grid gap-1"
            style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
          >
            {Array.from({ length: cols * 2 }).map((_, index) => (
              <span
                key={index}
                className={`pages-grid-picker-box ${
                  selected === cols
                    ? 'pages-grid-picker-box-active'
                    : 'pages-grid-picker-box-inactive'
                }`}
              />
            ))}
          </div>
        </button>
      ))}
    </div>
  );
}

export default function AnalysisPlotsPage() {
  const { t } = useTranslation();
  const { analysisId } = useParams();
  const dispatch = useAppDispatch();

  const selectedAnalysis = useAppSelector(selectSelectedAnalysis);
  const files = useAppSelector(selectAnalysisFiles);
  const currentRunKey = useAppSelector(selectCurrentRunKey);
  const resolvedAnalysisId = analysisId ?? '';

  const [plotSearch, setPlotSearch] = useState('');
  const [selectedAlgorithms, setSelectedAlgorithms] = useState<string[]>([]);
  const [selectedTypes, setSelectedTypes] = useState<PlotType[]>([]);
  const [appliedAlgorithms, setAppliedAlgorithms] = useState<string[]>([]);
  const [appliedTypes, setAppliedTypes] = useState<PlotType[]>([]);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [selectedInstances, setSelectedInstances] = useState<string[]>([]);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  const [selectedExtensions, setSelectedExtensions] = useState<string[]>([]);
  const [appliedInstances, setAppliedInstances] = useState<string[]>([]);
  const [appliedMetrics, setAppliedMetrics] = useState<string[]>([]);
  const [appliedExtensions, setAppliedExtensions] = useState<string[]>([]);
  const [gridColumns, setGridColumns] = useState<GridColumns>(2);
  const [visibleRows, setVisibleRows] = useState(2);
  const [imageHeight, setImageHeight] = useState<ImageHeight>('md');
  const [imageFit, setImageFit] = useState<ImageFit>('contain');
  const [showMeta, setShowMeta] = useState(false);
  const [showAllEvolutionGenerated, setShowAllEvolutionGenerated] = useState(false);
  const [previewFile, setPreviewFile] = useState<PlotItem | null>(null);
  const [imageBlobUrls, setImageBlobUrls] = useState<Record<string, string>>({});
  const [openMenu, setOpenMenu] = useState<OpenMenuKey>(null);
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const [evolutionOptions, setEvolutionOptions] = useState<EvolutionAnalyzeOptions>(
    DEFAULT_EVOLUTION_OPTIONS,
  );

  const imageBlobUrlsRef = useRef<Record<string, string>>({});
  const menuAreaRef = useRef<HTMLDivElement | null>(null);
  const hasInitializedRef = useRef(false);
  const lastResolvedSelectionKeyRef = useRef('');
  const inFlightSelectionKeyRef = useRef('');

  const allAlgorithms = useMemo(
    () => normalizeValues(selectedAnalysis?.algorithms || []),
    [selectedAnalysis?.algorithms],
  );

  const hasSaesCapability =
    Boolean(selectedAnalysis?.dataset_capabilities?.saes_plots) ||
    Boolean(selectedAnalysis?.dataset_capabilities?.saes_reports) ||
    Boolean(selectedAnalysis?.dataset_capabilities?.notebooks) ||
    Boolean(selectedAnalysis?.metrics?.length);

  const hasEvolutionCapability = Boolean(
    selectedAnalysis?.dataset_capabilities?.evolution_plots,
  );

  useEffect(() => {
    imageBlobUrlsRef.current = imageBlobUrls;
  }, [imageBlobUrls]);

  useEffect(() => {
    return () => {
      Object.values(imageBlobUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);

  const clearImageCache = () => {
    Object.values(imageBlobUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    imageBlobUrlsRef.current = {};
    setImageBlobUrls({});
    setPreviewFile(null);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!menuAreaRef.current) return;

      if (!menuAreaRef.current.contains(event.target as Node)) {
        setOpenMenu(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    setPlotSearch('');
    setSelectedAlgorithms([]);
    setSelectedTypes([]);
    setAppliedAlgorithms([]);
    setAppliedTypes([]);
    setApplyError(null);
    setSelectedInstances([]);
    setSelectedMetrics([]);
    setSelectedExtensions([]);
    setAppliedInstances([]);
    setAppliedMetrics([]);
    setAppliedExtensions([]);
    setGridColumns(2);
    setVisibleRows(2);
    setImageHeight('md');
    setImageFit('contain');
    setShowMeta(false);
    setShowAllEvolutionGenerated(false);
    setPreviewFile(null);
    setOpenMenu(null);
    setIsReanalyzing(false);
    setEvolutionOptions(DEFAULT_EVOLUTION_OPTIONS);

    hasInitializedRef.current = false;
    lastResolvedSelectionKeyRef.current = '';
    inFlightSelectionKeyRef.current = '';

    Object.values(imageBlobUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    imageBlobUrlsRef.current = {};
    setImageBlobUrls({});
  }, [analysisId]);

  useEffect(() => {
    if (!analysisId) return;

    const load = async () => {
      const result = await dispatch(getAnalysis(analysisId));

      if (getAnalysis.fulfilled.match(result)) {
        dispatch(setSelectedAnalysis(result.payload));
      }
    };

    void load();
  }, [analysisId, dispatch]);

  useEffect(() => {
    if (!selectedAnalysis) return;
    if (hasInitializedRef.current) return;

    const initialAlgorithms = normalizeValues(selectedAnalysis.algorithms || []);
    const metadata = selectedAnalysis.evolution_metadata || {};
    const initialEvolutionOptions = getEvolutionOptionsFromMetadata(metadata);

    setSelectedAlgorithms(initialAlgorithms);
    setAppliedAlgorithms(initialAlgorithms);
    setAppliedTypes([]);
    setEvolutionOptions(initialEvolutionOptions);
    dispatch(setCurrentRunKey('all'));

    hasInitializedRef.current = true;
    lastResolvedSelectionKeyRef.current = buildSelectionSignature(
      initialAlgorithms,
      [],
      initialEvolutionOptions,
    );
  }, [selectedAnalysis, dispatch]);

  useEffect(() => {
    if (!resolvedAnalysisId) return;

    void dispatch(
      listAnalysisFiles({
        analysisId: resolvedAnalysisId,
        runKey: currentRunKey || 'all',
      }),
    );
  }, [resolvedAnalysisId, currentRunKey, dispatch]);

  useEffect(() => {
    Object.values(imageBlobUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    imageBlobUrlsRef.current = {};
    setImageBlobUrls({});
    setPreviewFile(null);
  }, [currentRunKey]);

  const plotCategories = useMemo(() => {
    const categories: string[] = [];

    if (files.saes_plots?.length) categories.push('saes_plots');
    if (files.evolution_plots?.length) categories.push('evolution_plots');

    return categories;
  }, [files]);

  const hasEvolutionPlots = Boolean(files.evolution_plots?.length);
  const hasSaesPlots = Boolean(files.saes_plots?.length);

  const plotItems = useMemo(() => {
    return plotCategories
      .flatMap((category) =>
        (files[category] || []).filter(isSupportedPlotFile).map((fileName) => {
          const plotInfo = parsePlotInfo(category, fileName);

          if (!plotInfo) return null;

          return {
            ...plotInfo,
            category,
            extension: getFileExtension(fileName),
          };
        }),
      )
      .filter((item): item is PlotItem => item !== null)
      .sort((a, b) => {
        if (a.type !== b.type) return a.type.localeCompare(b.type);
        return a.fileName.localeCompare(b.fileName);
      });
  }, [files, plotCategories]);

  const availableInstances = useMemo(() => {
    return Array.from(
      new Set(plotItems.map((item) => item.instance).filter(Boolean) as string[]),
    ).sort((a, b) => a.localeCompare(b));
  }, [plotItems]);

  const availableMetrics = useMemo(() => {
    return Array.from(
      new Set(plotItems.map((item) => item.metric).filter(Boolean) as string[]),
    ).sort((a, b) => a.localeCompare(b));
  }, [plotItems]);

  const availableExtensions = useMemo(() => {
    return Array.from(
      new Set(plotItems.map((item) => item.extension).filter(Boolean)),
    ).sort((a, b) => a.localeCompare(b));
  }, [plotItems]);

  useEffect(() => {
    setSelectedInstances((prev) =>
      prev.filter((value) => availableInstances.includes(value)),
    );
    setAppliedInstances((prev) =>
      prev.filter((value) => availableInstances.includes(value)),
    );
  }, [availableInstances]);

  useEffect(() => {
    setSelectedMetrics((prev) =>
      prev.filter((value) => availableMetrics.includes(value)),
    );
    setAppliedMetrics((prev) => prev.filter((value) => availableMetrics.includes(value)));
  }, [availableMetrics]);

  useEffect(() => {
    setSelectedExtensions((prev) =>
      prev.filter((value) => availableExtensions.includes(value)),
    );
    setAppliedExtensions((prev) =>
      prev.filter((value) => availableExtensions.includes(value)),
    );
  }, [availableExtensions]);

  const filteredPlots = useMemo(() => {
    const search = plotSearch.trim().toLowerCase();

    return plotItems.filter((plot) => {
      if (showAllEvolutionGenerated && plot.type !== 'evolution') {
        return false;
      }

      const matchesType = appliedTypes.length === 0 || appliedTypes.includes(plot.type);

      const matchesMetric =
        appliedMetrics.length === 0 ||
        (plot.metric !== null && appliedMetrics.includes(plot.metric));

      const matchesInstance =
        appliedInstances.length === 0 ||
        (plot.instance !== null && appliedInstances.includes(plot.instance));

      const matchesExtension =
        appliedExtensions.length === 0 || appliedExtensions.includes(plot.extension);

      const matchesSearch =
        search.length === 0 ||
        plot.fileName.toLowerCase().includes(search) ||
        (plot.metric ?? '').toLowerCase().includes(search) ||
        (plot.instance ?? '').toLowerCase().includes(search) ||
        (plot.xColumn ?? '').toLowerCase().includes(search) ||
        plot.extension.toLowerCase().includes(search) ||
        t(getPlotTypeLabel(plot.type)).toLowerCase().includes(search);

      return (
        matchesType &&
        matchesMetric &&
        matchesInstance &&
        matchesExtension &&
        matchesSearch
      );
    });
  }, [
    plotItems,
    plotSearch,
    appliedTypes,
    appliedMetrics,
    appliedInstances,
    appliedExtensions,
    showAllEvolutionGenerated,
    t,
  ]);

  const maxRows = useMemo(() => {
    return Math.max(1, Math.ceil(filteredPlots.length / gridColumns));
  }, [filteredPlots.length, gridColumns]);

  useEffect(() => {
    setVisibleRows((prev) => Math.min(Math.max(1, prev), maxRows));
  }, [maxRows]);

  const maxVisibleItems = gridColumns * visibleRows;

  const visiblePlots = useMemo(() => {
    return filteredPlots.slice(0, maxVisibleItems);
  }, [filteredPlots, maxVisibleItems]);

  useEffect(() => {
    if (!previewFile) return;

    const stillVisible = filteredPlots.some(
      (plot) =>
        plot.category === previewFile.category && plot.fileName === previewFile.fileName,
    );

    if (!stillVisible) {
      setPreviewFile(null);
    }
  }, [filteredPlots, previewFile]);

  const ensureBlobUrl = async (category: string, fileName: string) => {
    if (!selectedAnalysis) return;
    if (!isPreviewableImage(fileName)) return;

    const key = `${selectedAnalysis.id}::${
      currentRunKey || 'all'
    }::${category}::${fileName}`;

    if (imageBlobUrlsRef.current[key]) return;

    const result = await dispatch(
      getAnalysisFileBlobUrl({
        analysisId: selectedAnalysis.id,
        category,
        fileName,
        runKey: currentRunKey || 'all',
      }),
    );

    if (getAnalysisFileBlobUrl.fulfilled.match(result)) {
      setImageBlobUrls((prev) => ({
        ...prev,
        [key]: result.payload.blobUrl,
      }));
    }
  };

  useEffect(() => {
    if (!selectedAnalysis) return;

    visiblePlots.forEach((plot) => {
      if (isPreviewableImage(plot.fileName)) {
        void ensureBlobUrl(plot.category, plot.fileName);
      }
    });
  }, [selectedAnalysis, visiblePlots, currentRunKey]);

  useEffect(() => {
    if (!previewFile) return;
    if (!isPreviewableImage(previewFile.fileName)) return;

    void ensureBlobUrl(previewFile.category, previewFile.fileName);
  }, [previewFile, currentRunKey]);

  const toggleAlgorithm = (algorithm: string) => {
    setSelectedAlgorithms((prev) => {
      if (!prev.includes(algorithm)) {
        setApplyError(null);
        return [...prev, algorithm];
      }

      if (prev.length <= 1) {
        setApplyError(t('analysis.plots.mustSelectAlgorithm'));
        return prev;
      }

      setApplyError(null);
      return prev.filter((item) => item !== algorithm);
    });
  };

  const toggleType = (type: PlotType) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((item) => item !== type) : [...prev, type],
    );
  };

  const toggleMetric = (metric: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(metric) ? prev.filter((item) => item !== metric) : [...prev, metric],
    );
  };

  const toggleInstance = (instance: string) => {
    setSelectedInstances((prev) =>
      prev.includes(instance)
        ? prev.filter((item) => item !== instance)
        : [...prev, instance],
    );
  };

  const toggleExtension = (extension: string) => {
    setSelectedExtensions((prev) =>
      prev.includes(extension)
        ? prev.filter((item) => item !== extension)
        : [...prev, extension],
    );
  };

  const toggleEvolutionGenerationStatistic = (
    statistic: (typeof EVOLUTION_STATISTICS)[number],
  ) => {
    const selected = getEvolutionStatisticsFromOptions(evolutionOptions);
    const nextStatistics = selected.includes(statistic)
      ? selected.filter((item) => item !== statistic)
      : [...selected, statistic];

    setEvolutionOptions((prev) =>
      applyEvolutionStatisticsToOptions(prev, nextStatistics),
    );
  };

  const refreshAnalysisAndFiles = async (runKey: string) => {
    if (!resolvedAnalysisId) return;

    clearImageCache();
    dispatch(setCurrentRunKey(runKey));

    const refreshed = await dispatch(getAnalysis(resolvedAnalysisId));

    if (getAnalysis.fulfilled.match(refreshed)) {
      dispatch(setSelectedAnalysis(refreshed.payload));
    }

    await dispatch(
      listAnalysisFiles({
        analysisId: resolvedAnalysisId,
        runKey,
      }),
    );
  };

  const resolveSelection = async (
    algorithmsSelection: string[],
    plotTypesSelection: PlotType[],
    optionsSelection: EvolutionAnalyzeOptions,
    metricsSelection: string[] = selectedMetrics,
    instancesSelection: string[] = selectedInstances,
  ) => {
    if (!resolvedAnalysisId || !selectedAnalysis) return;

    const normalizedSelection = normalizeValues(algorithmsSelection);
    const normalizedPlotTypes = normalizePlotTypes(plotTypesSelection);

    if (normalizedSelection.length === 0) return;

    const normalizedMetrics = normalizeValues(metricsSelection);
    const normalizedInstances = normalizeValues(instancesSelection);

    const requestedRunKey = buildAlgorithmRunKey(normalizedSelection, allAlgorithms);

    const signatureAlgorithms = requestedRunKey === 'all' ? [] : normalizedSelection;

    const selectionKey = buildSelectionSignature(
      signatureAlgorithms,
      normalizedPlotTypes,
      optionsSelection,
      normalizedMetrics,
      normalizedInstances,
    );
    if (inFlightSelectionKeyRef.current === selectionKey) return;

    if (
      lastResolvedSelectionKeyRef.current === selectionKey &&
      currentRunKey === requestedRunKey
    ) {
      return;
    }

    if (
      selectionAlreadyGenerated(
        selectedAnalysis.outputs,
        requestedRunKey,
        normalizedPlotTypes,
        optionsSelection,
        signatureAlgorithms,
        normalizedMetrics,
        normalizedInstances,
      )
    ) {
      await refreshAnalysisAndFiles(requestedRunKey);
      lastResolvedSelectionKeyRef.current = selectionKey;
      return;
    }

    const modulesToRun = getModulesForPlotTypes(
      normalizedPlotTypes,
      hasSaesCapability,
      hasEvolutionCapability,
    );
    const selectedSaesPlotTypes = normalizeSaesPlotTypes(normalizedPlotTypes);

    if (modulesToRun.length === 0) return;

    inFlightSelectionKeyRef.current = selectionKey;

    try {
      setIsReanalyzing(true);

      const result = await dispatch(
        reanalyzeAnalysis({
          analysisId: resolvedAnalysisId,
          selectedAlgorithms: normalizedSelection,
          modules: modulesToRun,
          selectedPlotTypes:
            selectedSaesPlotTypes.length > 0 ? selectedSaesPlotTypes : undefined,
          evolutionTitle: optionsSelection.title,
          evolutionXAxisColumns: optionsSelection.xColumns,
          evolutionXLabelsByColumn: optionsSelection.xLabelsByColumn,
          evolutionYLabelsByMetric: optionsSelection.yLabelsByMetric,
          evolutionSelectedAlgorithms: signatureAlgorithms,
          evolutionSelectedMetrics: normalizedMetrics,
          evolutionSelectedInstances: normalizedInstances,
          evolutionShowGrid: optionsSelection.showGrid,
          evolutionShowMinMax: optionsSelection.showMinMax,
          evolutionShowStd: optionsSelection.showStd,
          evolutionShowAverage: optionsSelection.showAverage,
          evolutionShowMedian: optionsSelection.showMedian,
          evolutionGroupByInstance: optionsSelection.groupByInstance,
          evolutionGroupByMetric: optionsSelection.groupByMetric,
        }),
      );

      if (!reanalyzeAnalysis.fulfilled.match(result)) return;

      const nextRunKey =
        result.payload.current_run_key ||
        buildAlgorithmRunKey(normalizedSelection, allAlgorithms);

      await refreshAnalysisAndFiles(nextRunKey);
      lastResolvedSelectionKeyRef.current = selectionKey;
    } finally {
      inFlightSelectionKeyRef.current = '';
      setIsReanalyzing(false);
    }
  };

  const pendingAlgorithms = useMemo(
    () => normalizeValues(selectedAlgorithms),
    [selectedAlgorithms],
  );

  const pendingTypes = useMemo(() => normalizePlotTypes(selectedTypes), [selectedTypes]);

  const pendingMetrics = useMemo(
    () => normalizeValues(selectedMetrics),
    [selectedMetrics],
  );

  const pendingInstances = useMemo(
    () => normalizeValues(selectedInstances),
    [selectedInstances],
  );

  const pendingExtensions = useMemo(
    () => normalizeValues(selectedExtensions),
    [selectedExtensions],
  );

  const pendingSelectionKey = useMemo(() => {
    if (pendingAlgorithms.length === 0) return '';

    const pendingRunKey = buildAlgorithmRunKey(pendingAlgorithms, allAlgorithms);
    const pendingSignatureAlgorithms = pendingRunKey === 'all' ? [] : pendingAlgorithms;

    return buildSelectionSignature(
      pendingSignatureAlgorithms,
      pendingTypes,
      evolutionOptions,
      pendingMetrics,
      pendingInstances,
    );
  }, [
    pendingAlgorithms,
    pendingTypes,
    evolutionOptions,
    pendingMetrics,
    pendingInstances,
    allAlgorithms,
  ]);

  const hasPendingApply =
    !arraysEqualAsSet(selectedAlgorithms, appliedAlgorithms) ||
    !plotTypeArraysEqualAsSet(selectedTypes, appliedTypes) ||
    !arraysEqualAsSet(selectedMetrics, appliedMetrics) ||
    !arraysEqualAsSet(selectedInstances, appliedInstances) ||
    !arraysEqualAsSet(selectedExtensions, appliedExtensions) ||
    (pendingSelectionKey.length > 0 &&
      pendingSelectionKey !== lastResolvedSelectionKeyRef.current);

  const handleApplyFilters = () => {
    const normalizedAlgorithms = pendingAlgorithms;
    const normalizedTypes = pendingTypes;
    const normalizedMetrics = pendingMetrics;
    const normalizedInstances = pendingInstances;
    const normalizedExtensions = pendingExtensions;

    if (normalizedAlgorithms.length === 0) {
      setApplyError(t('analysis.plots.mustSelectAlgorithm'));
      return;
    }

    const needsEvolution =
      normalizedTypes.length === 0 || normalizedTypes.includes('evolution');

    if (
      needsEvolution &&
      !evolutionOptions.showStd &&
      !evolutionOptions.showMedian &&
      !evolutionOptions.showAverage &&
      !evolutionOptions.showMinMax
    ) {
      setApplyError('Selecciona al menos una capa de evolución.');
      return;
    }

    setApplyError(null);
    clearImageCache();
    setAppliedAlgorithms(normalizedAlgorithms);
    setAppliedTypes(normalizedTypes);
    setAppliedMetrics(normalizedMetrics);
    setAppliedInstances(normalizedInstances);
    setAppliedExtensions(normalizedExtensions);

    void resolveSelection(
      normalizedAlgorithms,
      normalizedTypes,
      evolutionOptions,
      normalizedMetrics,
      normalizedInstances,
    );
  };

  const updateEvolutionOption = (updates: Partial<EvolutionAnalyzeOptions>) => {
    setEvolutionOptions((prev) => ({
      ...prev,
      ...updates,
    }));
  };
  const handleDownloadAllPlots = () => {
    if (!resolvedAnalysisId) return;

    const zipCategories = ['saes_plots', 'evolution_plots'].filter(
      (category) => Array.isArray(files[category]) && files[category].length > 0,
    );

    if (zipCategories.length === 0) return;

    void dispatch(
      downloadAnalysisPlotsZip({
        analysisId: resolvedAnalysisId,
        categories: zipCategories,
        filesByCategory: files,
        runKey: currentRunKey || 'all',
      }),
    );
  };

  const totalActiveFilters =
    selectedAlgorithms.length +
    selectedTypes.length +
    selectedMetrics.length +
    selectedInstances.length +
    selectedExtensions.length;

  const imageHeightClass = getImageHeightClass(imageHeight);
  const imageFitClass = getImageFitClass(imageFit);

  const previewKey = previewFile
    ? `${selectedAnalysis?.id}::${currentRunKey || 'all'}::${previewFile.category}::${
        previewFile.fileName
      }`
    : '';

  const plotWarnings = useMemo(() => {
    const outputs = selectedAnalysis?.outputs;

    if (!isRecord(outputs)) return [] as string[];

    const resolvedRunKey = currentRunKey || selectedAnalysis?.current_run_key || 'all';

    const analysisRuns = isRecord(outputs.analysis_runs) ? outputs.analysis_runs : null;
    const saesRuns = isRecord(outputs.saes_runs) ? outputs.saes_runs : null;

    const analysisRunOutputs =
      analysisRuns && isRecord(analysisRuns[resolvedRunKey])
        ? (analysisRuns[resolvedRunKey] as Record<string, unknown>)
        : null;

    const saesRunOutputs =
      saesRuns && isRecord(saesRuns[resolvedRunKey])
        ? (saesRuns[resolvedRunKey] as Record<string, unknown>)
        : null;

    const warningsRaw = [
      ...(Array.isArray(analysisRunOutputs?.saes_plot_warnings)
        ? analysisRunOutputs.saes_plot_warnings
        : []),
      ...(Array.isArray(analysisRunOutputs?.evolution_plot_warnings)
        ? analysisRunOutputs.evolution_plot_warnings
        : []),
      ...(Array.isArray(saesRunOutputs?.saes_plot_warnings)
        ? saesRunOutputs.saes_plot_warnings
        : []),
      ...(Array.isArray(outputs.saes_plot_warnings) ? outputs.saes_plot_warnings : []),
      ...(Array.isArray(outputs.evolution_plot_warnings)
        ? outputs.evolution_plot_warnings
        : []),
    ];

    return Array.from(
      new Set(
        warningsRaw
          .filter((value): value is string => typeof value === 'string')
          .map((value) => value.trim())
          .filter(Boolean),
      ),
    );
  }, [selectedAnalysis?.outputs, selectedAnalysis?.current_run_key, currentRunKey]);

  const isBusyGenerating = isReanalyzing;
  const canDownloadZip = Boolean(
    analysisId &&
      ['saes_plots', 'evolution_plots'].some(
        (category) => Array.isArray(files[category]) && files[category].length > 0,
      ),
  );
  const canOpenEvolutionSettings = hasEvolutionCapability || hasEvolutionPlots;
  const selectedGenerationStatistics =
    getEvolutionStatisticsFromOptions(evolutionOptions);

  return (
    <PrivateLayout>
      <main className="min-h-screen bg-[var(--app-bg)] px-3 py-5 sm:px-4 md:px-6 xl:px-8 2xl:px-10">
        <div className="mx-auto w-full max-w-[2200px]">
          <div className="mb-6">
            <Link
              to={resolvedAnalysisId ? `/analysis/${resolvedAnalysisId}` : '/analysis'}
              className="pages-back-link"
            >
              <span className="material-symbols-outlined text-[18px]">arrow_back</span>
              {t('common.back')}
            </Link>
          </div>

          <section className="pages-hero-card pages-hero-card-plots rounded-[36px] 2xl:p-10">
            <div className="flex flex-col gap-8 2xl:grid 2xl:grid-cols-[minmax(0,1.2fr)_minmax(520px,0.8fr)] 2xl:items-center">
              <div className="min-w-0">
                <h1 className="max-w-[16ch] text-4xl font-black tracking-tight text-[var(--text-primary)] md:text-6xl 2xl:text-7xl">
                  {t('analysis.plots.title')}
                </h1>

                <p className="mt-4 max-w-3xl text-[15px] leading-7 text-[var(--text-secondary)] md:text-base">
                  {selectedAnalysis?.name || t('analysis.plots.subtitle')}
                </p>

                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs font-semibold text-[var(--text-muted)]">
                  {hasEvolutionPlots ? (
                    <span className="rounded-full bg-[var(--brand-soft)] px-3 py-1.5 text-[var(--brand)]">
                      {t('analysis.plots.plotType.evolution')}
                    </span>
                  ) : null}

                  {hasSaesPlots ? (
                    <span className="rounded-full bg-[var(--surface-muted)] px-3 py-1.5">
                      SAES
                    </span>
                  ) : null}

                  {isBusyGenerating ? (
                    <span className="rounded-full bg-[var(--brand-soft)] px-3 py-1.5 text-[var(--brand)] shadow-sm">
                      {t('analysis.plots.generatingSelection')}
                    </span>
                  ) : null}

                  {plotWarnings.length > 0 ? (
                    <button
                      type="button"
                      onClick={() =>
                        setOpenMenu((prev) => (prev === 'warnings' ? null : 'warnings'))
                      }
                      className="rounded-full bg-amber-100 px-3 py-1.5 text-amber-800 transition-all hover:bg-amber-200"
                      title={t('analysis.plots.warningsTitle')}
                    >
                      {t('analysis.plots.warningsTitle')} · {plotWarnings.length}
                    </button>
                  ) : null}
                </div>

                <div className="mt-6 flex flex-wrap gap-3">
                  {canDownloadZip ? (
                    <button
                      type="button"
                      onClick={handleDownloadAllPlots}
                      className="pages-action-btn-primary px-6 py-3 font-bold"
                    >
                      <span className="material-symbols-outlined text-[18px]">
                        folder_zip
                      </span>
                      {t('analysis.results.downloadAll')}
                    </button>
                  ) : null}
                </div>
              </div>

              <div className="grid w-full grid-cols-2 gap-4 sm:grid-cols-4">
                <StatCard
                  label={t('analysis.plots.stats.total')}
                  value={plotItems.length}
                  icon="bar_chart"
                  tone="violet"
                />
                <StatCard
                  label={t('analysis.plots.stats.filtered')}
                  value={isBusyGenerating ? 0 : filteredPlots.length}
                  icon="filter_alt"
                  tone="blue"
                />
                <StatCard
                  label={t('analysis.plots.stats.visible')}
                  value={isBusyGenerating ? 0 : visiblePlots.length}
                  icon="visibility"
                  tone="emerald"
                />
                <StatCard
                  label={t('analysis.plots.stats.formats')}
                  value={availableExtensions.length}
                  icon="image"
                  tone="amber"
                />
              </div>
            </div>
          </section>

          {openMenu === 'warnings' && plotWarnings.length > 0 ? (
            <div className="mt-2 mb-6 rounded-2xl border border-amber-200 bg-amber-50/80 px-5 py-4 text-amber-900 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-bold">{t('analysis.plots.warningsTitle')}</p>
                  <p className="mt-1 text-sm text-amber-800">
                    {t('analysis.plots.warningsDescription')}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => setOpenMenu(null)}
                  className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-amber-800 transition-colors hover:bg-amber-100"
                  aria-label={t('analysis.plots.close')}
                >
                  <span className="material-symbols-outlined text-[20px]">close</span>
                </button>
              </div>

              <ul className="mt-3 max-h-28 list-disc space-y-1 overflow-y-auto pl-5 text-sm">
                {plotWarnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <SectionShell className="mb-5">
            <div ref={menuAreaRef} className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2 text-xs font-semibold text-[var(--text-muted)]">
                  <span className="rounded-full bg-[var(--surface-muted)] px-3 py-1.5">
                    {isBusyGenerating ? 0 : visiblePlots.length} {t('common.of')}{' '}
                    {isBusyGenerating ? 0 : filteredPlots.length}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={handleApplyFilters}
                    disabled={!hasPendingApply || isBusyGenerating}
                    className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-[var(--brand)] px-4 text-sm font-bold text-white shadow-sm transition-all hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-50"
                    title={t('analysis.plots.applyFilters')}
                  >
                    <span className="material-symbols-outlined text-[18px]">check</span>
                    {t('analysis.plots.apply')}
                  </button>

                  <div className="relative">
                    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
                      <span className="material-symbols-outlined text-[18px]">
                        search
                      </span>
                    </span>

                    <input
                      value={plotSearch}
                      onChange={(event) => setPlotSearch(event.target.value)}
                      placeholder={t('analysis.plots.searchPlaceholder')}
                      className="w-[170px] rounded-full border border-[var(--border)] bg-[var(--surface-strong)] py-2.5 pl-10 pr-3 text-sm text-[var(--text-primary)] outline-none transition-all placeholder:text-[var(--text-muted)] focus:border-[var(--brand)] sm:w-[210px]"
                    />
                  </div>

                  {canOpenEvolutionSettings ? (
                    <button
                      type="button"
                      onClick={() =>
                        setOpenMenu((prev) => (prev === 'evolution' ? null : 'evolution'))
                      }
                      className={`pages-icon-action-btn ${
                        openMenu === 'evolution'
                          ? 'pages-icon-action-btn-active'
                          : 'pages-icon-action-btn-inactive'
                      }`}
                      aria-label="Opciones de evolución"
                      title="Opciones de evolución"
                    >
                      <span className="material-symbols-outlined text-[20px]">tune</span>
                    </button>
                  ) : null}

                  <button
                    type="button"
                    onClick={() =>
                      setOpenMenu((prev) => (prev === 'filters' ? null : 'filters'))
                    }
                    className={`relative pages-icon-action-btn ${
                      openMenu === 'filters'
                        ? 'pages-icon-action-btn-active'
                        : 'pages-icon-action-btn-inactive'
                    }`}
                    aria-label={t('analysis.plots.filters')}
                    title={t('analysis.plots.filters')}
                  >
                    <span className="material-symbols-outlined text-[20px]">
                      filter_alt
                    </span>

                    {totalActiveFilters > 0 ? (
                      <span className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-[var(--brand)] px-1 text-[10px] font-bold text-white">
                        {totalActiveFilters}
                      </span>
                    ) : null}
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      setOpenMenu((prev) => (prev === 'layout' ? null : 'layout'))
                    }
                    className={`pages-icon-action-btn ${
                      openMenu === 'layout'
                        ? 'pages-icon-action-btn-active'
                        : 'pages-icon-action-btn-inactive'
                    }`}
                    aria-label={t('analysis.plots.gridSettings')}
                    title={t('analysis.plots.gridSettings')}
                  >
                    <span className="material-symbols-outlined text-[20px]">
                      grid_view
                    </span>
                  </button>
                </div>
              </div>

              {openMenu === 'evolution' ? (
                <div className="rounded-[24px] border border-[var(--border)] bg-[var(--surface-muted)]/70 p-4">
                  <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-black text-[var(--text-primary)]">
                        Capas de evolución
                      </p>
                      <p className="mt-1 text-sm text-[var(--text-secondary)]">
                        Selecciona qué capas mostrar en la gráfica de evolución.
                      </p>
                    </div>

                    {hasPendingApply ? (
                      <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
                        Cambios pendientes · pulsa Aplicar
                      </span>
                    ) : null}
                  </div>

                  <div className="mb-6 max-w-xl">
                    <ToggleOption
                      label="Ver evoluciones generadas"
                      description="Muestra solo las gráficas de evolución generadas, sin incluir las de SAES."
                      checked={showAllEvolutionGenerated}
                      onChange={setShowAllEvolutionGenerated}
                    />
                  </div>

                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                    {EVOLUTION_STATISTICS.map((statistic) => (
                      <ToggleOption
                        key={statistic}
                        label={getEvolutionStatisticLabel(statistic)}
                        description="Se dibuja como capa dentro de la misma gráfica."
                        checked={selectedGenerationStatistics.includes(statistic)}
                        onChange={() => toggleEvolutionGenerationStatistic(statistic)}
                      />
                    ))}
                  </div>

                  <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                    <ToggleOption
                      label="Grid"
                      description="Añade o quita la rejilla de la gráfica."
                      checked={evolutionOptions.showGrid}
                      onChange={(checked) => updateEvolutionOption({ showGrid: checked })}
                    />

                    <ToggleOption
                      label="Agrupar por instancia"
                      description="Genera gráficas separadas por instancia."
                      checked={evolutionOptions.groupByInstance}
                      onChange={(checked) =>
                        updateEvolutionOption({ groupByInstance: checked })
                      }
                    />

                    <ToggleOption
                      label="Agrupar por métrica"
                      description="Genera gráficas separadas por métrica."
                      checked={evolutionOptions.groupByMetric}
                      onChange={(checked) =>
                        updateEvolutionOption({ groupByMetric: checked })
                      }
                    />
                  </div>
                </div>
              ) : null}

              {openMenu === 'filters' ? (
                <div className="rounded-[24px] border border-[var(--border)] bg-[var(--surface-muted)]/70 p-4">
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-[var(--text-secondary)]">
                      {t('analysis.plots.filterHelper')}
                    </p>

                    {hasPendingApply ? (
                      <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
                        {t('analysis.plots.pendingChanges')}
                      </span>
                    ) : null}
                  </div>

                  {applyError ? (
                    <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
                      {applyError}
                    </div>
                  ) : null}

                  <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1.4fr_1fr_1fr_1fr]">
                    <FilterSection
                      title={t('analysis.plots.algorithm')}
                      count={selectedAlgorithms.length}
                      onClear={() => setSelectedAlgorithms(allAlgorithms)}
                    >
                      {allAlgorithms.length === 0 ? (
                        <p className="text-sm text-[var(--text-muted)]">
                          {t('analysis.plots.noAlgorithms')}
                        </p>
                      ) : (
                        <div className="max-h-72 overflow-y-auto pr-1">
                          <div className="grid grid-cols-1 gap-2">
                            {allAlgorithms.map((algorithm) => (
                              <FilterChip
                                key={algorithm}
                                active={selectedAlgorithms.includes(algorithm)}
                                label={algorithm}
                                onClick={() => toggleAlgorithm(algorithm)}
                              />
                            ))}
                          </div>
                        </div>
                      )}
                    </FilterSection>

                    <FilterSection
                      title={t('analysis.plots.type')}
                      count={selectedTypes.length}
                      onClear={() => setSelectedTypes([])}
                    >
                      <div className="max-h-72 overflow-y-auto pr-1">
                        <div className="grid grid-cols-1 gap-2 2xl:grid-cols-2">
                          {ALL_PLOT_TYPES.map((type) => (
                            <FilterChip
                              key={type}
                              active={selectedTypes.includes(type)}
                              label={t(getPlotTypeLabel(type))}
                              onClick={() => toggleType(type)}
                            />
                          ))}
                        </div>
                      </div>
                    </FilterSection>

                    <FilterSection
                      title={t('analysis.plots.format')}
                      count={selectedExtensions.length}
                      onClear={() => setSelectedExtensions([])}
                    >
                      {availableExtensions.length === 0 ? (
                        <p className="text-sm text-[var(--text-muted)]">
                          {t('analysis.plots.noFormats')}
                        </p>
                      ) : (
                        <div className="max-h-72 overflow-y-auto pr-1">
                          <div className="grid grid-cols-2 gap-2">
                            {availableExtensions.map((extension) => (
                              <FilterChip
                                key={extension}
                                active={selectedExtensions.includes(extension)}
                                label={extension.toUpperCase()}
                                onClick={() => toggleExtension(extension)}
                              />
                            ))}
                          </div>
                        </div>
                      )}
                    </FilterSection>

                    <FilterSection
                      title={t('analysis.detail.parameters.metricsTitle')}
                      count={selectedMetrics.length}
                      onClear={() => setSelectedMetrics([])}
                    >
                      {availableMetrics.length === 0 ? (
                        <p className="text-sm text-[var(--text-muted)]">
                          {t('analysis.plots.noMetrics')}
                        </p>
                      ) : (
                        <div className="max-h-72 overflow-y-auto pr-1">
                          <div className="grid grid-cols-1 gap-2">
                            {availableMetrics.map((metric) => (
                              <FilterChip
                                key={metric}
                                active={selectedMetrics.includes(metric)}
                                label={metric}
                                onClick={() => toggleMetric(metric)}
                              />
                            ))}
                          </div>
                        </div>
                      )}
                    </FilterSection>

                    <FilterSection
                      title={t('analysis.detail.parameters.instancesTitle')}
                      count={selectedInstances.length}
                      onClear={() => setSelectedInstances([])}
                    >
                      {availableInstances.length === 0 ? (
                        <p className="text-sm text-[var(--text-muted)]">
                          {t('analysis.plots.noInstances')}
                        </p>
                      ) : (
                        <div className="max-h-72 overflow-y-auto pr-1">
                          <div className="grid grid-cols-1 gap-2">
                            {availableInstances.map((instance) => (
                              <FilterChip
                                key={instance}
                                active={selectedInstances.includes(instance)}
                                label={instance}
                                onClick={() => toggleInstance(instance)}
                              />
                            ))}
                          </div>
                        </div>
                      )}
                    </FilterSection>
                  </div>
                </div>
              ) : null}

              {openMenu === 'layout' ? (
                <div className="rounded-[24px] border border-[var(--border)] bg-[var(--surface-muted)]/70 p-4">
                  <div className="flex flex-col gap-5">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-black text-[var(--text-primary)]">
                        {t('analysis.plots.settings')}
                      </p>

                      <button
                        type="button"
                        onClick={() => {
                          setGridColumns(2);
                          setVisibleRows(2);
                          setImageHeight('md');
                          setImageFit('contain');
                          setShowMeta(false);
                        }}
                        className="text-xs font-semibold text-[var(--brand)] hover:underline"
                      >
                        {t('analysis.plots.reset')}
                      </button>
                    </div>

                    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(220px,280px)_minmax(180px,220px)_minmax(220px,260px)_minmax(220px,240px)]">
                      <div>
                        <p className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
                          {t('analysis.plots.columns')}
                        </p>
                        <GridPicker selected={gridColumns} onSelect={setGridColumns} />
                      </div>

                      <div>
                        <div className="mb-3 flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-[var(--text-primary)]">
                            {t('analysis.plots.rows')}
                          </p>
                          <span className="text-xs font-semibold text-[var(--text-muted)]">
                            {t('analysis.plots.max')} {maxRows}
                          </span>
                        </div>

                        <div className="max-h-48 overflow-y-auto pr-1">
                          <div className="grid grid-cols-4 gap-2">
                            {Array.from({ length: maxRows }, (_, index) => index + 1).map(
                              (row) => (
                                <FilterChip
                                  key={row}
                                  active={visibleRows === row}
                                  label={`${row}`}
                                  onClick={() => setVisibleRows(row)}
                                />
                              ),
                            )}
                          </div>
                        </div>
                      </div>

                      <div>
                        <p className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
                          {t('analysis.plots.imageSize')}
                        </p>

                        <div className="flex flex-wrap gap-2">
                          <MiniOptionButton
                            active={imageHeight === 'sm'}
                            label={t('analysis.plots.densityLow')}
                            onClick={() => setImageHeight('sm')}
                          />
                          <MiniOptionButton
                            active={imageHeight === 'md'}
                            label={t('analysis.plots.densityMedium')}
                            onClick={() => setImageHeight('md')}
                          />
                          <MiniOptionButton
                            active={imageHeight === 'lg'}
                            label={t('analysis.plots.densityHigh')}
                            onClick={() => setImageHeight('lg')}
                          />
                        </div>

                        <div className="mt-3 flex flex-wrap gap-2">
                          <MiniOptionButton
                            active={imageFit === 'contain'}
                            label={t('analysis.plots.fitContain')}
                            onClick={() => setImageFit('contain')}
                          />
                          <MiniOptionButton
                            active={imageFit === 'cover'}
                            label={t('analysis.plots.fitCover')}
                            onClick={() => setImageFit('cover')}
                          />
                        </div>
                      </div>

                      <div>
                        <p className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
                          {t('analysis.plots.metadata')}
                        </p>

                        <div className="flex flex-wrap gap-2">
                          <MiniOptionButton
                            active={!showMeta}
                            label={t('analysis.plots.hidden')}
                            onClick={() => setShowMeta(false)}
                          />
                          <MiniOptionButton
                            active={showMeta}
                            label={t('analysis.plots.visible')}
                            onClick={() => setShowMeta(true)}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </SectionShell>

          <section
            className="grid gap-4"
            style={{
              gridTemplateColumns: `repeat(${gridColumns}, minmax(0, 1fr))`,
            }}
          >
            {isBusyGenerating ? (
              <div className="pages-soft-surface-strong col-span-full rounded-[32px] p-12 text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--brand-soft)] text-[var(--brand)]">
                  <span className="material-symbols-outlined animate-spin text-[32px]">
                    sync
                  </span>
                </div>
                <h3 className="text-xl font-black text-[var(--text-primary)]">
                  {t('analysis.plots.loadingTitle')}
                </h3>
                <p className="mx-auto mt-2 max-w-md text-[var(--text-secondary)]">
                  {t('analysis.plots.loadingDescription')}
                </p>
              </div>
            ) : visiblePlots.length === 0 ? (
              <div className="pages-soft-surface-strong col-span-full rounded-[28px] p-10 text-center text-[var(--text-muted)]">
                {t('analysis.plots.noResults')}
              </div>
            ) : (
              visiblePlots.map((plot) => {
                const key = `${selectedAnalysis?.id}::${currentRunKey || 'all'}::${
                  plot.category
                }::${plot.fileName}`;
                const blobUrl = imageBlobUrls[key] ?? '';
                const canPreviewInline = isPreviewableImage(plot.fileName);

                return (
                  <article
                    key={`${currentRunKey || 'all'}-${plot.category}-${plot.fileName}`}
                    className="pages-soft-surface group overflow-hidden rounded-[24px] transition-all hover:shadow-[0_14px_34px_rgba(15,23,42,0.08)]"
                  >
                    {showMeta ? (
                      <div className="p-4 pb-0">
                        <p className="text-[11px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
                          {t(getPlotTypeLabel(plot.type))}
                        </p>
                        <h3
                          className="truncate text-sm font-black text-[var(--text-primary)]"
                          title={plot.fileName}
                        >
                          {plot.fileName}
                        </h3>
                        <p className="mt-1 text-xs text-[var(--text-secondary)]">
                          {t('analysis.plots.metric')}: {plot.metric || '-'} ·{' '}
                          {t('analysis.plots.instance')}: {plot.instance || '-'} · X:{' '}
                          {plot.xColumn || '-'} · {t('analysis.plots.format')}:{' '}
                          {plot.extension.toUpperCase() || '-'}
                        </p>
                      </div>
                    ) : null}

                    <div className={showMeta ? 'p-3' : 'p-4'}>
                      <div
                        className={`relative w-full overflow-hidden rounded-[20px] bg-[var(--surface-muted)] ${imageHeightClass}`}
                      >
                        {canPreviewInline ? (
                          blobUrl ? (
                            <img
                              src={blobUrl}
                              alt={plot.fileName}
                              className={`h-full w-full transition-transform duration-200 group-hover:scale-[1.01] ${imageFitClass}`}
                            />
                          ) : (
                            <div className="flex h-full items-center justify-center text-sm text-[var(--text-muted)]">
                              {t('analysis.plots.loadingPreview')}
                            </div>
                          )
                        ) : plot.extension === 'pdf' ? (
                          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-[var(--text-muted)]">
                            {t('analysis.plots.pdfAvailable')}
                          </div>
                        ) : (
                          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-[var(--text-muted)]">
                            {t('analysis.plots.noInlinePreview')}
                          </div>
                        )}

                        <div className="absolute right-3 top-3 flex items-center gap-2 opacity-100 md:opacity-0 md:transition-opacity md:duration-200 md:group-hover:opacity-100">
                          {canPreviewInline ? (
                            <button
                              type="button"
                              onClick={() => setPreviewFile(plot)}
                              className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-[var(--text-secondary)] shadow-sm backdrop-blur transition-colors hover:bg-white hover:text-[var(--brand)]"
                              aria-label={t('analysis.plots.viewImage')}
                              title={t('analysis.plots.viewImage')}
                            >
                              <span className="material-symbols-outlined text-[18px]">
                                open_in_full
                              </span>
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => {
                                if (!selectedAnalysis) return;

                                void dispatch(
                                  downloadAnalysisFile({
                                    analysisId: selectedAnalysis.id,
                                    category: plot.category,
                                    fileName: plot.fileName,
                                    openInNewTab: plot.extension === 'pdf',
                                    runKey: currentRunKey || 'all',
                                  }),
                                );
                              }}
                              className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-[var(--text-secondary)] shadow-sm backdrop-blur transition-colors hover:bg-white hover:text-[var(--brand)]"
                              aria-label={
                                plot.extension === 'pdf'
                                  ? t('analysis.plots.openFile')
                                  : t('analysis.plots.viewFile')
                              }
                              title={
                                plot.extension === 'pdf'
                                  ? t('analysis.plots.openFile')
                                  : t('analysis.plots.viewFile')
                              }
                            >
                              <span className="material-symbols-outlined text-[18px]">
                                {plot.extension === 'pdf' ? 'open_in_new' : 'visibility'}
                              </span>
                            </button>
                          )}

                          <button
                            type="button"
                            onClick={() => {
                              if (!selectedAnalysis) return;

                              void dispatch(
                                downloadAnalysisFile({
                                  analysisId: selectedAnalysis.id,
                                  category: plot.category,
                                  fileName: plot.fileName,
                                  openInNewTab: false,
                                  runKey: currentRunKey || 'all',
                                }),
                              );
                            }}
                            className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-[var(--text-secondary)] shadow-sm backdrop-blur transition-colors hover:bg-white hover:text-emerald-600"
                            aria-label={t('common.download')}
                            title={t('common.download')}
                          >
                            <span className="material-symbols-outlined text-[18px]">
                              download
                            </span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })
            )}
          </section>
        </div>

        {previewFile ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 py-6 backdrop-blur-[2px]">
            <div className="pages-soft-surface-strong relative flex max-h-[90vh] w-full max-w-6xl flex-col overflow-hidden rounded-[32px] shadow-2xl">
              <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase tracking-widest text-[var(--text-muted)]">
                    {t(getPlotTypeLabel(previewFile.type))}
                  </p>
                  <h3
                    className="truncate text-base font-black text-[var(--text-primary)]"
                    title={previewFile.fileName}
                  >
                    {previewFile.fileName}
                  </h3>
                </div>

                <button
                  type="button"
                  onClick={() => setPreviewFile(null)}
                  className="flex h-11 w-11 items-center justify-center rounded-full text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-muted)] hover:text-red-500"
                  aria-label={t('analysis.plots.close')}
                >
                  <span className="material-symbols-outlined text-[28px]">close</span>
                </button>
              </div>

              <div className="flex-1 overflow-auto p-5">
                <div className="flex min-h-[60vh] items-center justify-center overflow-hidden rounded-[24px] bg-[var(--surface-muted)] p-4">
                  {imageBlobUrls[previewKey] ? (
                    <img
                      src={imageBlobUrls[previewKey]}
                      alt={previewFile.fileName}
                      className="max-h-[75vh] w-full object-contain"
                    />
                  ) : (
                    <div className="text-sm text-[var(--text-muted)]">
                      {t('analysis.plots.loadingPreview')}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setPreviewFile(null)}
              className="absolute inset-0 -z-10 cursor-default"
              aria-label={t('analysis.plots.closeModal')}
            />
          </div>
        ) : null}
      </main>
    </PrivateLayout>
  );
}
