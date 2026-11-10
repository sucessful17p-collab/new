export const modes = ['project-resurrection','decision-time-machine','knowledge-integrity','impact-analysis','knowledge-audit','gravitational-extract','topological-summarize','matrix-organize'] as const;
export type AnalysisMode = typeof modes[number];
export function modeFor(page: string): AnalysisMode | 'handover' {
  if (page === 'Timeline') return 'decision-time-machine';
  if (page === 'Integrity') return 'knowledge-integrity';
  if (page === 'Impact analysis') return 'impact-analysis';
  if (page === 'Handover') return 'handover';
  return 'project-resurrection';
}
