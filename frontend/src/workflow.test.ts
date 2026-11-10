import {describe,expect,it} from 'vitest';
import {modeFor,modes} from './workflow';

describe('analysis workflow selection',()=>{
  it('maps project views to operating modes',()=>{
    expect(modeFor('Timeline')).toBe('decision-time-machine');
    expect(modeFor('Integrity')).toBe('knowledge-integrity');
    expect(modeFor('Impact analysis')).toBe('impact-analysis');
    expect(modeFor('Handover')).toBe('handover');
  });
  it('exposes all eight deterministic modes',()=>{
    expect(modes).toHaveLength(8);
    expect(modes).toContain('project-resurrection');
    expect(modes).toContain('matrix-organize');
  });
});
