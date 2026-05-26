import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PrivateLayout from '../components/PrivateLayout';
import '../styles/pages.css';
import { useAppDispatch, useAppSelector } from '../app/hooks';
import { setSelectedAnalysis } from '../features/analysis/analysis.slice';
import {
  selectAnalysisFiles,
  selectCurrentRunKey,
  selectSelectedAnalysis,
} from '../features/analysis/analysis.selectors';
import {
  downloadAnalysisCategoryZip,
  downloadAnalysisFile,
  getAnalysis,
  getAnalysisFileBlobUrl,
  listAnalysisFiles,
} from '../features/analysis/analysis.thunks';

type LatexTableCell = {
  value: string;
  highlight?: boolean;
  shade?: number | null;
};

type LatexTablePreview = {
  caption?: string | null;
  headers: string[];
  rows: LatexTableCell[][];
  raw_tex?: string;
  report_key?: string;
  report_label?: string;
  metric?: string;
};

type ReportPreview = {
  category: string;
  baseName: string;
  previewJsonFileName?: string;
  imageFileName?: string;
  texFileName?: string;
};

type ReportFileGroup = {
  category: string;
  baseName: string;
  label: string;
  previewJsonFileName?: string;
  imageFileName?: string;
  texFileName?: string;
};

function isTex(fileName: string) {
  return fileName.toLowerCase().endsWith('.tex');
}

function isPreviewJson(fileName: string) {
  return fileName.toLowerCase().endsWith('.preview.json');
}

function isImage(fileName: string) {
  const lower = fileName.toLowerCase();

  return (
    lower.endsWith('.png') ||
    lower.endsWith('.jpg') ||
    lower.endsWith('.jpeg') ||
    lower.endsWith('.webp')
  );
}

function prettifyName(value: string) {
  return value
    .replace(/\.preview\.json$/i, '')
    .replace(/\.(tex|png|jpg|jpeg|webp)$/i, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function getBaseName(fileName: string) {
  return fileName
    .replace(/\.preview\.json$/i, '')
    .replace(/\.(tex|png|jpg|jpeg|webp)$/i, '');
}

function getFileKey(analysisId: string | undefined, category: string, fileName?: string) {
  if (!analysisId || !fileName) return null;

  return `${analysisId}::${category}::${fileName}`;
}

function SectionShell({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <section className={`pages-section-shell ${className}`}>{children}</section>;
}

function IconAction({
  icon,
  title,
  onClick,
  active = false,
}: {
  icon: string;
  title: string;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`pages-icon-action-btn ${
        active ? 'pages-icon-action-btn-active' : 'pages-icon-action-btn-inactive'
      }`}
      aria-label={title}
      title={title}
    >
      <span className="material-symbols-outlined text-[20px]">{icon}</span>
    </button>
  );
}

function ReportChip({
  file,
  active,
  compareActive,
  compareMode,
  onOpen,
  onCompare,
  onDownload,
}: {
  file: ReportFileGroup;
  active: boolean;
  compareActive: boolean;
  compareMode: boolean;
  onOpen: () => void;
  onCompare: () => void;
  onDownload: () => void;
}) {
  const { t } = useTranslation();

  return (
    <article
      className={`pages-report-chip ${
        active || compareActive
          ? 'pages-report-chip-active'
          : 'pages-report-chip-inactive'
      }`}
    >
      <p className="pages-report-chip-title" title={file.label}>
        {file.label}
      </p>

      <p className="pages-report-chip-subtitle">
        {[
          file.previewJsonFileName ? 'TABLE' : null,
          file.imageFileName ? 'IMAGE' : null,
          file.texFileName ? 'TEX' : null,
        ]
          .filter(Boolean)
          .join(' · ')}
      </p>

      <div className="pages-report-chip-actions">
        <IconAction
          icon="visibility"
          title={t('analysis.reports.view')}
          onClick={onOpen}
          active={active}
        />

        {compareMode ? (
          <IconAction
            icon="compare_arrows"
            title={t('analysis.reports.compare')}
            onClick={onCompare}
            active={compareActive}
          />
        ) : null}

        <IconAction icon="download" title={t('common.download')} onClick={onDownload} />
      </div>
    </article>
  );
}

function getShadeClasses(shade?: number | null) {
  if (shade == null) return '';
  if (shade >= 90) return 'pages-report-table-shade-heavy';
  if (shade >= 50) return 'pages-report-table-shade-medium';

  return 'pages-report-table-shade-light';
}

function ReportTableView({ preview }: { preview?: LatexTablePreview }) {
  const { t } = useTranslation();

  if (!preview) return null;

  return (
    <div className="pages-report-table-container">
      <div className="pages-report-table-header">
        {preview.report_label ? (
          <p className="pages-report-table-label">{preview.report_label}</p>
        ) : null}

        {preview.caption ? (
          <p className="pages-report-table-caption">{preview.caption}</p>
        ) : null}

        {preview.metric ? (
          <p className="pages-report-table-metric">
            {t('analysis.reports.metric')}: {preview.metric}
          </p>
        ) : null}
      </div>

      <table className="pages-report-table">
        <thead>
          <tr>
            {preview.headers.map((header, index) => (
              <th key={`${header}-${index}`} className="pages-report-table-th">
                {header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {preview.rows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td
                  key={`cell-${rowIndex}-${cellIndex}`}
                  className={`pages-report-table-td ${
                    cellIndex === 0 ? 'pages-report-table-td-first' : ''
                  } ${getShadeClasses(cell.shade)}`}
                  title={
                    cell.highlight
                      ? `${t('analysis.reports.highlightedBySaes')}${
                          cell.shade != null ? ` (gray${cell.shade})` : ''
                        }`
                      : undefined
                  }
                >
                  {cell.value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReportPreviewPanel({
  preview,
  previewBlobUrl,
  latexSource,
  tablePreview,
  onDownloadPreferred,
  onDownloadTex,
}: {
  preview: ReportPreview | null;
  previewBlobUrl?: string;
  latexSource?: string;
  tablePreview?: LatexTablePreview;
  onDownloadPreferred: () => void;
  onDownloadTex?: () => void;
}) {
  const { t } = useTranslation();

  if (!preview) {
    return (
      <div className="flex min-h-[420px] items-center justify-center rounded-[24px] bg-[var(--surface-muted)] text-sm text-[var(--text-muted)]">
        {t('analysis.reports.selectReport')}
      </div>
    );
  }

  const hasStructuredTable = Boolean(tablePreview);
  const hasImageFile = Boolean(preview.imageFileName);
  const hasImage = Boolean(hasImageFile && previewBlobUrl);
  const onlyLatex = !hasStructuredTable && !hasImageFile;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs tracking-wide text-[var(--text-muted)]">
            {t('analysis.reports.statisticalReport')}
          </p>

          <h3
            className="truncate text-lg font-black text-[var(--text-primary)]"
            title={preview.baseName}
          >
            {prettifyName(preview.baseName)}
          </h3>
        </div>

        <div className="flex items-center gap-2">
          <IconAction
            icon="download"
            title={t('analysis.reports.downloadMainView')}
            onClick={onDownloadPreferred}
          />

          {preview.texFileName && onDownloadTex ? (
            <IconAction
              icon="article"
              title={t('analysis.reports.downloadTex')}
              onClick={onDownloadTex}
            />
          ) : null}
        </div>
      </div>

      <div className="pages-report-preview-shell">
        {hasStructuredTable ? (
          <ReportTableView preview={tablePreview} />
        ) : hasImage ? (
          <div className="pages-report-content-surface overflow-hidden p-4">
            <img
              src={previewBlobUrl}
              alt={prettifyName(preview.baseName)}
              className="mx-auto max-h-[720px] w-auto max-w-full rounded-xl object-contain"
            />
          </div>
        ) : hasImageFile ? (
          <div className="flex min-h-[420px] items-center justify-center rounded-[24px] bg-[var(--surface-muted)] text-sm text-[var(--text-muted)]">
            {t('analysis.reports.loadingContent')}
          </div>
        ) : (
          <pre className="pages-report-preformatted">
            {latexSource || t('analysis.reports.loadingContent')}
          </pre>
        )}

        {onlyLatex ? (
          <p className="mt-3 text-xs text-[var(--text-muted)]">
            {t('analysis.reports.noStructuredPreview')}
          </p>
        ) : null}

        {hasStructuredTable && latexSource ? (
          <details className="pages-report-source-details">
            <summary className="cursor-pointer text-sm font-semibold text-[var(--text-primary)]">
              {t('analysis.reports.showLatexSource')}
            </summary>

            <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs text-[var(--text-primary)]">
              {latexSource}
            </pre>
          </details>
        ) : null}
      </div>
    </div>
  );
}

export default function AnalysisReportsPage() {
  const { t } = useTranslation();
  const { analysisId } = useParams();
  const dispatch = useAppDispatch();

  const selectedAnalysis = useAppSelector(selectSelectedAnalysis);
  const files = useAppSelector(selectAnalysisFiles);
  const currentRunKey = useAppSelector(selectCurrentRunKey);

  const [reportSearch, setReportSearch] = useState('');
  const [primaryPreview, setPrimaryPreview] = useState<ReportPreview | null>(null);
  const [secondaryPreview, setSecondaryPreview] = useState<ReportPreview | null>(null);
  const [compareMode, setCompareMode] = useState(false);

  const [fileBlobUrls, setFileBlobUrls] = useState<Record<string, string>>({});
  const [reportTextContent, setReportTextContent] = useState<Record<string, string>>({});
  const [reportStructuredContent, setReportStructuredContent] = useState<
    Record<string, LatexTablePreview>
  >({});

  const fileBlobUrlsRef = useRef<Record<string, string>>({});
  const reportTextContentRef = useRef<Record<string, string>>({});
  const reportStructuredContentRef = useRef<Record<string, LatexTablePreview>>({});

  useEffect(() => {
    fileBlobUrlsRef.current = fileBlobUrls;
  }, [fileBlobUrls]);

  useEffect(() => {
    reportTextContentRef.current = reportTextContent;
  }, [reportTextContent]);

  useEffect(() => {
    reportStructuredContentRef.current = reportStructuredContent;
  }, [reportStructuredContent]);

  useEffect(() => {
    return () => {
      Object.values(fileBlobUrlsRef.current).forEach((url) => {
        window.URL.revokeObjectURL(url);
      });
    };
  }, []);

  useEffect(() => {
    setPrimaryPreview(null);
    setSecondaryPreview(null);
    setReportSearch('');
    setCompareMode(false);
    setReportTextContent({});
    setReportStructuredContent({});
    reportTextContentRef.current = {};
    reportStructuredContentRef.current = {};

    Object.values(fileBlobUrlsRef.current).forEach((url) => {
      window.URL.revokeObjectURL(url);
    });

    fileBlobUrlsRef.current = {};
    setFileBlobUrls({});
  }, [analysisId]);

  useEffect(() => {
    if (!compareMode) {
      setSecondaryPreview(null);
    }
  }, [compareMode]);

  useEffect(() => {
    if (!analysisId) return;

    const load = async () => {
      const result = await dispatch(getAnalysis(analysisId));

      if (getAnalysis.fulfilled.match(result)) {
        dispatch(setSelectedAnalysis(result.payload));
        await dispatch(
          listAnalysisFiles({
            analysisId,
            runKey: currentRunKey || 'all',
          }),
        );
      }
    };

    void load();
  }, [analysisId, currentRunKey, dispatch]);

  const reportCategory =
    files.saes_reports && files.saes_reports.length > 0 ? 'saes_reports' : null;

  const groupedReports = useMemo(() => {
    const candidates = reportCategory ? files[reportCategory] || [] : [];
    const groups = new Map<string, ReportFileGroup>();

    for (const fileName of candidates) {
      if (!isPreviewJson(fileName) && !isTex(fileName) && !isImage(fileName)) {
        continue;
      }

      const baseName = getBaseName(fileName);
      const existing = groups.get(baseName) || {
        category: reportCategory || 'saes_reports',
        baseName,
        label: prettifyName(baseName),
      };

      if (isPreviewJson(fileName)) {
        existing.previewJsonFileName = fileName;
      } else if (isImage(fileName)) {
        existing.imageFileName = fileName;
      } else if (isTex(fileName)) {
        existing.texFileName = fileName;
      }

      groups.set(baseName, existing);
    }

    return Array.from(groups.values()).sort((a, b) => a.label.localeCompare(b.label));
  }, [files, reportCategory]);

  const filteredReports = useMemo(() => {
    const search = reportSearch.trim().toLowerCase();

    return groupedReports.filter((file) => {
      return (
        search.length === 0 ||
        file.baseName.toLowerCase().includes(search) ||
        file.label.toLowerCase().includes(search) ||
        (file.previewJsonFileName || '').toLowerCase().includes(search) ||
        (file.imageFileName || '').toLowerCase().includes(search) ||
        (file.texFileName || '').toLowerCase().includes(search)
      );
    });
  }, [groupedReports, reportSearch]);

  const ensureFileBlobUrl = async (category: string, fileName: string) => {
    if (!analysisId) return undefined;

    const key = `${analysisId}::${category}::${fileName}`;

    if (fileBlobUrlsRef.current[key]) {
      return fileBlobUrlsRef.current[key];
    }

    const result = await dispatch(
      getAnalysisFileBlobUrl({
        analysisId,
        category,
        fileName,
        runKey: currentRunKey || 'all',
      }),
    );

    if (!getAnalysisFileBlobUrl.fulfilled.match(result)) {
      return undefined;
    }

    const blobUrl = result.payload.blobUrl;

    fileBlobUrlsRef.current = {
      ...fileBlobUrlsRef.current,
      [key]: blobUrl,
    };

    setFileBlobUrls((prev) => ({
      ...prev,
      [key]: blobUrl,
    }));

    return blobUrl;
  };

  const ensureReportTextContent = async (category: string, fileName: string) => {
    if (!analysisId) return undefined;

    const key = `${analysisId}::${category}::${fileName}`;

    if (reportTextContentRef.current[key]) {
      return reportTextContentRef.current[key];
    }

    const blobUrl = await ensureFileBlobUrl(category, fileName);
    if (!blobUrl) return undefined;

    const response = await fetch(blobUrl);
    const text = await response.text();

    reportTextContentRef.current = {
      ...reportTextContentRef.current,
      [key]: text,
    };

    setReportTextContent((prev) => ({
      ...prev,
      [key]: text,
    }));

    return text;
  };

  const ensureReportStructuredContent = async (category: string, fileName: string) => {
    if (!analysisId) return undefined;

    const key = `${analysisId}::${category}::${fileName}`;

    if (reportStructuredContentRef.current[key]) {
      return reportStructuredContentRef.current[key];
    }

    const blobUrl = await ensureFileBlobUrl(category, fileName);
    if (!blobUrl) return undefined;

    const response = await fetch(blobUrl);
    const json = (await response.json()) as LatexTablePreview;

    reportStructuredContentRef.current = {
      ...reportStructuredContentRef.current,
      [key]: json,
    };

    setReportStructuredContent((prev) => ({
      ...prev,
      [key]: json,
    }));

    return json;
  };

  const getPreferredFileName = (report: ReportPreview | ReportFileGroup) => {
    return report.previewJsonFileName || report.imageFileName || report.texFileName || '';
  };

  const downloadFile = (report: ReportPreview | ReportFileGroup, fileName: string) => {
    if (!analysisId || !fileName) return;

    void dispatch(
      downloadAnalysisFile({
        analysisId,
        category: report.category,
        fileName,
        openInNewTab: false,
        runKey: currentRunKey || 'all',
      }),
    );
  };

  const openPreview = async (
    target: 'primary' | 'secondary',
    report: ReportFileGroup,
  ) => {
    const preview: ReportPreview = {
      category: report.category,
      baseName: report.baseName,
      previewJsonFileName: report.previewJsonFileName,
      imageFileName: report.imageFileName,
      texFileName: report.texFileName,
    };

    if (target === 'primary') {
      setPrimaryPreview(preview);
    } else {
      setSecondaryPreview(preview);
    }

    await Promise.all([
      report.imageFileName
        ? ensureFileBlobUrl(report.category, report.imageFileName)
        : Promise.resolve(undefined),
      report.previewJsonFileName
        ? ensureReportStructuredContent(report.category, report.previewJsonFileName)
        : Promise.resolve(undefined),
      report.texFileName
        ? ensureReportTextContent(report.category, report.texFileName)
        : Promise.resolve(undefined),
    ]);
  };

  useEffect(() => {
    if (filteredReports.length === 0) {
      setPrimaryPreview(null);
      setSecondaryPreview(null);
      return;
    }

    const primaryStillExists =
      primaryPreview &&
      filteredReports.some((file) => file.baseName === primaryPreview.baseName);

    if (!primaryStillExists) {
      void openPreview('primary', filteredReports[0]);
    }

    const secondaryStillExists =
      secondaryPreview &&
      filteredReports.some((file) => file.baseName === secondaryPreview.baseName);

    if (!secondaryStillExists) {
      setSecondaryPreview(null);
    }
  }, [filteredReports, primaryPreview, secondaryPreview]);

  const primaryImageKey = getFileKey(
    analysisId,
    primaryPreview?.category || '',
    primaryPreview?.imageFileName,
  );

  const secondaryImageKey = getFileKey(
    analysisId,
    secondaryPreview?.category || '',
    secondaryPreview?.imageFileName,
  );

  const primaryTexKey = getFileKey(
    analysisId,
    primaryPreview?.category || '',
    primaryPreview?.texFileName,
  );

  const secondaryTexKey = getFileKey(
    analysisId,
    secondaryPreview?.category || '',
    secondaryPreview?.texFileName,
  );

  const primaryPreviewJsonKey = getFileKey(
    analysisId,
    primaryPreview?.category || '',
    primaryPreview?.previewJsonFileName,
  );

  const secondaryPreviewJsonKey = getFileKey(
    analysisId,
    secondaryPreview?.category || '',
    secondaryPreview?.previewJsonFileName,
  );

  return (
    <PrivateLayout>
      <main className="min-h-screen bg-[var(--app-bg)] px-3 py-5 sm:px-4 md:px-6 xl:px-8 2xl:px-10">
        <div className="mx-auto w-full max-w-[2200px]">
          <div className="mb-6">
            <Link
              to={analysisId ? `/analysis/${analysisId}` : '/analysis'}
              className="pages-back-link"
            >
              <span className="material-symbols-outlined text-[18px]">arrow_back</span>
              {t('common.back')}
            </Link>
          </div>

          <section className="pages-hero-card pages-hero-card-reports md:p-8 2xl:p-10">
            <div className="flex flex-col gap-8 2xl:grid 2xl:grid-cols-[minmax(0,1.2fr)_minmax(520px,0.8fr)] 2xl:items-center">
              <div className="min-w-0">
                <h1 className="max-w-[16ch] text-4xl font-black tracking-tight text-[var(--text-primary)] md:text-6xl 2xl:text-7xl">
                  {t('analysis.reports.title')}
                </h1>

                <p className="mt-4 max-w-3xl text-[15px] leading-7 text-[var(--text-secondary)] md:text-base">
                  {selectedAnalysis?.name || t('analysis.reports.subtitle')}
                </p>

                <div className="mt-6 flex flex-wrap gap-3">
                  {reportCategory && groupedReports.length > 0 ? (
                    <button
                      type="button"
                      onClick={() => {
                        void dispatch(
                          downloadAnalysisCategoryZip({
                            analysisId: analysisId || '',
                            category: reportCategory,
                            runKey: currentRunKey || 'all',
                          }),
                        );
                      }}
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

              <div className="flex w-full justify-end">
                <article className="pages-stat-card w-full max-w-[180px]">
                  <div className="pages-stat-card-icon pages-stat-card-icon-emerald">
                    <span className="material-symbols-outlined text-[21px]">
                      table_chart
                    </span>
                  </div>

                  <p className="pages-stat-label">{t('analysis.reports.stats.total')}</p>

                  <p className="pages-stat-value">{groupedReports.length}</p>
                </article>
              </div>
            </div>
          </section>

          <SectionShell className="mb-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-[var(--text-muted)]">
                <span className="rounded-full bg-[var(--surface-muted)] px-3 py-1.5">
                  {filteredReports.length} {t('common.of')} {groupedReports.length}
                </span>
              </div>

              <div className="flex items-center justify-end gap-2">
                <div className="relative">
                  <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
                    <span className="material-symbols-outlined text-[18px]">search</span>
                  </span>

                  <input
                    value={reportSearch}
                    onChange={(event) => setReportSearch(event.target.value)}
                    placeholder={t('analysis.reports.searchPlaceholder')}
                    className="w-[190px] rounded-full border border-[var(--border)] bg-[var(--surface-strong)] py-2.5 pl-10 pr-4 text-sm text-[var(--text-primary)] outline-none transition-all placeholder:text-[var(--text-muted)] focus:border-[var(--brand)] sm:w-[240px]"
                  />
                </div>

                <IconAction
                  icon="compare_arrows"
                  title={
                    compareMode
                      ? t('analysis.reports.compareDisable')
                      : t('analysis.reports.compareEnable')
                  }
                  onClick={() => setCompareMode((prev) => !prev)}
                  active={compareMode}
                />
              </div>
            </div>
          </SectionShell>

          <div className="space-y-6">
            {compareMode ? (
              <section className="grid grid-cols-1 gap-6 2xl:grid-cols-2">
                <div className="pages-soft-surface rounded-[24px] p-5">
                  <ReportPreviewPanel
                    preview={primaryPreview}
                    previewBlobUrl={
                      primaryImageKey ? fileBlobUrls[primaryImageKey] : undefined
                    }
                    latexSource={
                      primaryTexKey ? reportTextContent[primaryTexKey] : undefined
                    }
                    tablePreview={
                      primaryPreviewJsonKey
                        ? reportStructuredContent[primaryPreviewJsonKey]
                        : undefined
                    }
                    onDownloadPreferred={() => {
                      if (!primaryPreview) return;
                      downloadFile(primaryPreview, getPreferredFileName(primaryPreview));
                    }}
                    onDownloadTex={
                      primaryPreview?.texFileName
                        ? () => {
                            downloadFile(
                              primaryPreview,
                              primaryPreview.texFileName || '',
                            );
                          }
                        : undefined
                    }
                  />
                </div>

                <div className="pages-soft-surface rounded-[24px] p-5">
                  <ReportPreviewPanel
                    preview={secondaryPreview}
                    previewBlobUrl={
                      secondaryImageKey ? fileBlobUrls[secondaryImageKey] : undefined
                    }
                    latexSource={
                      secondaryTexKey ? reportTextContent[secondaryTexKey] : undefined
                    }
                    tablePreview={
                      secondaryPreviewJsonKey
                        ? reportStructuredContent[secondaryPreviewJsonKey]
                        : undefined
                    }
                    onDownloadPreferred={() => {
                      if (!secondaryPreview) return;
                      downloadFile(
                        secondaryPreview,
                        getPreferredFileName(secondaryPreview),
                      );
                    }}
                    onDownloadTex={
                      secondaryPreview?.texFileName
                        ? () => {
                            downloadFile(
                              secondaryPreview,
                              secondaryPreview.texFileName || '',
                            );
                          }
                        : undefined
                    }
                  />
                </div>
              </section>
            ) : (
              <section className="pages-soft-surface rounded-[24px] p-5">
                <ReportPreviewPanel
                  preview={primaryPreview}
                  previewBlobUrl={
                    primaryImageKey ? fileBlobUrls[primaryImageKey] : undefined
                  }
                  latexSource={
                    primaryTexKey ? reportTextContent[primaryTexKey] : undefined
                  }
                  tablePreview={
                    primaryPreviewJsonKey
                      ? reportStructuredContent[primaryPreviewJsonKey]
                      : undefined
                  }
                  onDownloadPreferred={() => {
                    if (!primaryPreview) return;
                    downloadFile(primaryPreview, getPreferredFileName(primaryPreview));
                  }}
                  onDownloadTex={
                    primaryPreview?.texFileName
                      ? () => {
                          downloadFile(primaryPreview, primaryPreview.texFileName || '');
                        }
                      : undefined
                  }
                />
              </section>
            )}

            <SectionShell>
              <div className="mb-4 flex items-center justify-between gap-3">
                <h2 className="text-lg font-black text-[var(--text-primary)]">
                  {t('analysis.reports.availableTitle')}
                </h2>

                <span className="text-sm text-[var(--text-secondary)]">
                  {filteredReports.length}
                </span>
              </div>

              {filteredReports.length === 0 ? (
                <p className="text-sm text-[var(--text-muted)]">
                  {t('analysis.reports.noResults')}
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <div className="flex min-w-max gap-3 pb-1">
                    {filteredReports.map((file) => {
                      const active = primaryPreview?.baseName === file.baseName;
                      const compareActive = secondaryPreview?.baseName === file.baseName;

                      return (
                        <ReportChip
                          key={`${file.category}-${file.baseName}`}
                          file={file}
                          active={active}
                          compareActive={compareActive}
                          compareMode={compareMode}
                          onOpen={() => void openPreview('primary', file)}
                          onCompare={() => void openPreview('secondary', file)}
                          onDownload={() =>
                            downloadFile(file, getPreferredFileName(file))
                          }
                        />
                      );
                    })}
                  </div>
                </div>
              )}
            </SectionShell>
          </div>
        </div>
      </main>
    </PrivateLayout>
  );
}
