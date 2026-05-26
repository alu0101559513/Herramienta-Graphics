function normalizeMessage(message: string): string {
  return message.replace(/^Value error,\s*/i, '').trim();
}

export function mapAnalysisBackendErrorToI18nKey(message: string): string {
  const normalized = normalizeMessage(message);

  switch (true) {
    case normalized.startsWith('Invalid module'):
      return 'analysis.backend.invalidModules';

    case normalized.startsWith('Invalid plot type'):
      return 'analysis.backend.invalidPlotType';

    case normalized.startsWith('Invalid plot export format'):
      return 'analysis.backend.invalidPlotExportFormat';

    case normalized.startsWith('Unsupported dataset format'):
      return 'analysis.backend.unsupportedDatasetFormat';

    case normalized.startsWith('SAES outputs are not available'):
      return 'analysis.backend.saesNotAvailable';

    case normalized.startsWith('Evolution plots are not available'):
      return 'analysis.backend.evolutionNotAvailable';

    case normalized.startsWith('SAES did not generate any plot files'):
      return 'analysis.backend.noSaesPlotsGenerated';

    case normalized.startsWith('SAES did not generate any report files'):
      return 'analysis.backend.noSaesReportsGenerated';

    case normalized.startsWith(
      'Evolution plot generation did not produce any output files',
    ):
      return 'analysis.backend.noEvolutionPlotsGenerated';

    case normalized === 'Analysis not found':
      return 'analysis.backend.analysisNotFound';

    case normalized === 'Only CSV files are allowed':
      return 'analysis.backend.onlyCsvAllowed';

    case normalized === 'Only CSV files are allowed for metrics file':
      return 'analysis.backend.onlyMetricsCsvAllowed';

    case normalized === 'Invalid CSV encoding':
      return 'analysis.backend.invalidCsvEncoding';

    case normalized === 'Invalid CSV format':
      return 'analysis.backend.invalidCsvFormat';

    case normalized === 'Dataset not uploaded':
      return 'analysis.backend.datasetNotUploaded';

    case normalized === 'Modules must not be empty':
    case normalized === 'At least one module must be selected':
      return 'analysis.backend.emptyModules';

    case normalized === 'Invalid metrics_direction format':
      return 'analysis.backend.invalidMetricsDirectionFormat';

    case normalized === 'metrics_direction must be a JSON object':
      return 'analysis.backend.invalidMetricsDirectionObject';

    case normalized === 'At least one algorithm must be selected':
      return 'analysis.backend.emptySelectedAlgorithms';

    case normalized === 'Dataset file not found':
      return 'analysis.backend.datasetFileNotFound';

    case normalized === 'Dataset is empty':
      return 'analysis.backend.datasetEmpty';

    case normalized === 'Metrics file not found':
      return 'analysis.backend.metricsFileNotFound';

    case normalized === 'Filtered dataset file not found':
      return 'analysis.backend.filteredDatasetNotFound';

    case normalized === 'Category not found':
      return 'analysis.backend.categoryNotFound';

    case normalized === 'File not found':
      return 'analysis.backend.fileNotFound';

    case normalized ===
      'Dataset cannot be exported to SAES format. Missing required column: Algorithm':
      return 'analysis.backend.missingAlgorithmColumn';

    case normalized ===
      'Dataset cannot be exported to SAES format. Missing required column: Instance':
      return 'analysis.backend.missingInstanceColumn';

    case normalized ===
      'Dataset cannot be exported to SAES format. Missing required column: MetricName':
      return 'analysis.backend.missingMetricNameColumn';

    case normalized ===
      'Dataset cannot be exported to SAES format. Missing required column: ExecutionId':
      return 'analysis.backend.missingExecutionIdColumn';

    case normalized ===
      'Dataset cannot be exported to SAES format. Missing required column: MetricValue':
      return 'analysis.backend.missingMetricValueColumn';

    default:
      return 'analysis.backend.unknownError';
  }
}
