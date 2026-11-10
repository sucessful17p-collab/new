import asyncio
from app.main import (Session, Project, Document, Report, build_analysis, chunk_text,
                      create_project, seed_demo, analyze, graph, export_report)
from app.main import ProjectIn

def test_health_and_demo_seed():
    demo = seed_demo()['project']
    assert demo['name'].startswith('Aqua-Nexus')
    assert demo['documents_count'] == 10
    assert demo['processed_count'] == 10

def test_demo_analysis_has_real_source_evidence():
    p = seed_demo()['project']
    result = analyze(p['id'], {})
    assert result['claims']
    assert all(c['evidence'] == c['text'] and c['filename'] for c in result['claims'])
    assert result['provider'] == 'MockProvider'
    assert result['contradictions']

def test_project_creation_and_file_extraction_contract():
    p = create_project(ProjectIn(name='Unit test project', description=''))
    assert p['name'] == 'Unit test project'
    assert 'Requirement: retain evidence.' in chunk_text('[Page 2]\nRequirement: retain evidence.')[0][1]

def test_eight_modes_graph_and_export():
    p = seed_demo()['project']
    for mode in ('project-resurrection','decision-time-machine','knowledge-integrity','impact-analysis','knowledge-audit','gravitational-extract','topological-summarize','matrix-organize'):
        result = analyze(p['id'], {'mode': mode, 'question': 'UV'})
        assert result['mode'] == mode
        assert result['documents_analyzed']
    assert graph(p['id'])['nodes']
    with Session() as s:
        report = s.query(Report).filter_by(project_id=p['id']).first()
        assert '# Aqua-Nexus' in export_report(report.id)

def test_chunk_text_preserves_page_location():
    chunks = chunk_text('[Page 4]\nAn evidence excerpt long enough to become a stored chunk.')
    assert chunks[0][0] == 'Page 4'
