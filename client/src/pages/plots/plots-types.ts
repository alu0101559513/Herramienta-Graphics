export type SaesPlotType = 'boxplot' | 'violin' | 'histogram' | 'critical_distance';

export type EvolutionPlotType = 'evolution';

export type PlotType = SaesPlotType | EvolutionPlotType;

export type OpenMenuKey = 'filters' | 'layout' | 'warnings' | 'evolution' | null;

export type ImageHeight = 'sm' | 'md' | 'lg';

export type ImageFit = 'contain' | 'cover';

export type GridColumns = 1 | 2 | 3 | 4;

export interface PlotItem {
  category: string;
  fileName: string;
  extension: string;
  type: PlotType;
  metric: string | null;
  instance: string | null;
  xColumn: string | null;
}
