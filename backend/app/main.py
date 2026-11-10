from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

DATA_DIR = Path(os.getenv("AETHER_DATA_DIR", "./data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'aether.db').as_posix()}")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase): pass


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    documents: Mapped[list[Document]] = relationship(back_populates="project", cascade="all, delete-orphan")
    reports: Mapped[list[Report]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24), default="processed")
    warning: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    project: Mapped[Project] = relationship(back_populates="documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String(80), default="Text")
    text: Mapped[str] = mapped_column(Text)
    document: Mapped[Document] = relationship(back_populates="chunks")


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    project: Mapped[Project] = relationship(back_populates="reports")


Base.metadata.create_all(engine)
app = FastAPI(title="Aether-NAS", version="0.1.0", description="Evidence-grounded project knowledge continuity")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_methods=["*"], allow_headers=["*"])
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(20 * 1024 * 1024)))
ALLOWED = {".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md", ".csv"}


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)


def as_project(p: Project) -> dict[str, Any]:
    return {"id": p.id, "name": p.name, "description": p.description, "created_at": p.created_at.isoformat(), "documents_count": len(p.documents), "processed_count": sum(d.status == "processed" for d in p.documents)}


def extract_file(suffix: str, raw: bytes) -> tuple[str, str]:
    warning = ""
    try:
        if suffix in {".txt", ".md", ".csv"}:
            return raw.decode("utf-8-sig"), warning
        if suffix == ".pdf":
            import fitz
            doc = fitz.open(stream=raw, filetype="pdf")
            pages = [f"[Page {i+1}]\n{page.get_text()}" for i, page in enumerate(doc)]
            text = "\n\n".join(pages)
            if not text.strip(): warning = "PDF contains no extractable text (it may be scanned)."
            return text, warning
        if suffix == ".docx":
            from docx import Document as Docx
            doc = Docx(__import__("io").BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip()), warning
        if suffix == ".pptx":
            from pptx import Presentation
            prs = Presentation(__import__("io").BytesIO(raw))
            return "\n\n".join(f"[Slide {i+1}]\n" + "\n".join(s.text for s in slide.shapes if getattr(s, "has_text_frame", False)) for i, slide in enumerate(prs.slides)), warning
        if suffix == ".xlsx":
            from openpyxl import load_workbook
            wb = load_workbook(__import__("io").BytesIO(raw), read_only=True, data_only=True)
            return "\n\n".join(f"[Sheet: {ws.title}]\n" + "\n".join(" | ".join(str(c) if c is not None else "" for c in row) for row in ws.iter_rows(values_only=True)) for ws in wb.worksheets), warning
    except Exception as exc:
        return "", f"Extraction failed: {type(exc).__name__}: {exc}"
    return "", "Unsupported document format."


def chunk_text(text: str, size: int = 1100) -> list[tuple[str, str]]:
    parts = []
    for i in range(0, len(text), size):
        piece = text[i:i + size].strip()
        if piece:
            m = re.search(r"\[Page (\d+)\]|\[Slide (\d+)\]|\[Sheet: ([^\]]+)\]", piece)
            loc = f"Page {m.group(1)}" if m and m.group(1) else (f"Slide {m.group(2)}" if m and m.group(2) else (f"Sheet {m.group(3)}" if m else f"Text {len(parts)+1}"))
            parts.append((loc, piece))
    return parts


def sentence_evidence(doc: Document) -> list[dict[str, Any]]:
    out = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", doc.content):
        s = sentence.strip(" -\t\r")
        if len(s) < 24 or len(s) > 400: continue
        lowered = s.lower()
        category = "fact"
        if any(w in lowered for w in ("decided", "decision", "agreed", "selected", "will use", "adopted")): category = "decision"
        elif any(w in lowered for w in ("shall", "must", "requirement", "required", "target", "should")): category = "requirement"
        elif "?" in s or any(w in lowered for w in ("open question", "unknown", "TBD", "unresolved")): category = "question"
        out.append({"text": s, "document_id": doc.id, "filename": doc.filename, "location": next((loc for loc, piece in chunk_text(doc.content) if s[:32] in piece), "Document"), "evidence": s, "classification": category, "status": "explicit", "review_status": "unreviewed"})
    return out


def build_analysis(project: Project, mode: str, question: str = "") -> dict[str, Any]:
    docs = [d for d in project.documents if d.status == "processed" and d.content.strip()]
    claims = [claim for d in docs for claim in sentence_evidence(d)]
    terms = {}
    for claim in claims:
        for word in re.findall(r"\b[A-Z][A-Za-z0-9-]{3,}\b", claim["text"]): terms[word] = terms.get(word, 0) + 1
    concepts = sorted(terms, key=lambda x: (-terms[x], x))[:12]
    requirements = [c for c in claims if c["classification"] == "requirement"]
    decisions = [c for c in claims if c["classification"] == "decision"]
    questions = [c for c in claims if c["classification"] == "question"]
    contradictions = []
    for i, left in enumerate(requirements):
        for right in requirements[i+1:]:
            if left["document_id"] != right["document_id"] and _opposed(left["text"], right["text"]):
                contradictions.append({"claim_a": left, "claim_b": right, "type": "potential_conflict", "status": "human_review_required", "explanation": "The statements share a subject or measure but appear to specify different values or conditions."})
    word_count = sum(len(d.content.split()) for d in docs)
    evidence_coverage = round(100 * len(claims) / max(1, len(claims) + len(questions)))
    base = {"project_id": project.id, "project_name": project.name, "mode": mode, "provider": "MockProvider", "provider_note": "Deterministic extraction from uploaded source text; no external model was called.", "created_at": datetime.now(timezone.utc).isoformat(), "documents_analyzed": [{"id": d.id, "filename": d.filename} for d in docs], "claims": claims, "decisions": decisions, "requirements": requirements, "questions": questions, "concepts": concepts, "contradictions": contradictions, "relationships": [], "word_count": word_count}
    if mode in ("project-resurrection", "knowledge-audit", "knowledge-integrity", "decision-time-machine", "gravitational-extract", "topological-summarize", "matrix-organize", "impact-analysis", "handover"):
        base["executive_overview"] = f"{len(docs)} processed source documents contain {len(claims)} extractable statements ({len(decisions)} decision candidates, {len(requirements)} requirement candidates, {len(questions)} open question candidates). These are source observations, not verification of current real-world status."
        base["objectives"] = [c for c in claims if any(w in c["text"].lower() for w in ("objective", "aim", "goal", "purpose"))]
        base["timeline"] = sorted(claims, key=lambda c: next((d.created_at.isoformat() for d in docs if d.id == c["document_id"]), ""))
        base["knowledge_debt"] = {"evidence_coverage_percent": evidence_coverage, "document_count": len(docs), "claims_with_evidence": len(claims), "potential_conflicts": len(contradictions), "unresolved_questions": len(questions), "method": "Coverage = extracted source statements / (statements + question candidates). This is a transparent inventory indicator, not a quality guarantee."}
        base["next_actions"] = ["Review potential conflicts against original sources.", "Resolve open questions with project owners.", "Confirm which documented decisions remain current."]
    if mode == "impact-analysis":
        termset = {w.lower() for w in re.findall(r"\w+", question) if len(w) > 3}
        base["impact_query"] = question
        base["affected_evidence"] = [c for c in claims if termset & {w.lower() for w in re.findall(r"\w+", c["text"])}]
        base["approval_required"] = True
    if mode == "matrix-organize": base["matrix"] = [{"document": d.filename, "claims": [c for c in claims if c["document_id"] == d.id], "categories": sorted({c["classification"] for c in claims if c["document_id"] == d.id})} for d in docs]
    if mode == "topological-summarize": base["summary_by_document"] = [{"document": d.filename, "statements": [c for c in claims if c["document_id"] == d.id][:8]} for d in docs]
    if mode == "gravitational-extract": base["high_frequency_concepts"] = concepts
    return base


def _opposed(a: str, b: str) -> bool:
    # Conservative demo heuristic: shared meaningful token plus explicit opposite/unequal terms.
    aa, bb = a.lower(), b.lower()
    tokens_a = set(re.findall(r"[a-z]{4,}", aa)); tokens_b = set(re.findall(r"[a-z]{4,}", bb))
    shared = tokens_a & tokens_b
    opposing = any(x in aa and y in bb or y in aa and x in bb for x, y in (("shall", "shall not"), ("minimum", "maximum"), ("required", "optional"), ("increase", "decrease")))
    numbers_a, numbers_b = re.findall(r"\d+(?:\.\d+)?", aa), re.findall(r"\d+(?:\.\d+)?", bb)
    return len(shared) >= 2 and (opposing or bool(numbers_a and numbers_b and numbers_a != numbers_b))


@app.get("/api/health")
def health(): return {"status": "ok", "service": "Aether-NAS", "provider": os.getenv("AI_PROVIDER", "mock")}


DEMO_DOCS = {
    "01 Project proposal.md": "SYNTHETIC DEMO DOCUMENT — Aqua-Nexus project proposal\nObjective: Develop a modular water purification research demonstrator for small communities. The target is to evaluate turbidity and microbial reduction. This is a research prototype, not a certified treatment system. Open question: Who owns field validation?",
    "02 Initial architecture.md": "SYNTHETIC DEMO DOCUMENT — Initial architecture\nThe first design uses a three-stage train: sediment prefilter, activated carbon, and UV-C treatment. The team decided to use a gravity-fed flow path to reduce power needs. Requirement: The system shall process 8 liters per hour. UV exposure validation is required before any safety claim.",
    "03 Revised architecture.md": "SYNTHETIC DEMO DOCUMENT — Revised architecture\nMeeting decision: replace gravity feed with a low-voltage pump because head pressure varied in bench trials. The carbon stage remains. Requirement: The system shall process 12 liters per hour at nominal test conditions. This revision is a proposed bench configuration and has not been field validated.",
    "04 Research notes.md": "SYNTHETIC DEMO DOCUMENT — Research notes\nCarbon media may reduce odor and some dissolved compounds; performance depends on media and contact time. UV-C effectiveness depends on dose, water clarity, and lamp output. These notes do not establish potable water safety. Open question: Which microbial assay will be used?",
    "05 Meeting minutes.md": "SYNTHETIC DEMO DOCUMENT — Meeting minutes\n2025-02-10: Team agreed to log flow rate, turbidity, and lamp hours during each bench run. Decision: keep the enclosure serviceable so media can be replaced. Unresolved: enclosure ingress rating is not selected. The team deferred public health claims until independent testing.",
    "06 Requirements.md": "SYNTHETIC DEMO DOCUMENT — Requirements\nRequirement: The demonstrator must process 8 liters per hour. Requirement: Water turbidity shall be below 5 NTU before UV exposure. Requirement: All test runs must log inlet and outlet readings. Requirement: The device shall not claim drinking-water safety without validated microbiological results.",
    "07 Testing summary.md": "SYNTHETIC DEMO DOCUMENT — Testing summary\nThree bench runs recorded flow between 9 and 11 liters per hour. Turbidity readings were incomplete for one run. No microbiological assay was performed. Observed carbon stage pressure drop increased across the test sequence. These results are preliminary and do not demonstrate pathogen reduction.",
    "08 Risk assessment.md": "SYNTHETIC DEMO DOCUMENT — Risk assessment\nRisk: UV lamp degradation may reduce dose without obvious external signs. Mitigation under consideration: hour counter and scheduled replacement. Risk: cloudy inlet water may reduce UV performance. Missing evidence: validated dose-response study, microbial results, and electrical enclosure review.",
    "09 Conflicting specifications.md": "SYNTHETIC DEMO DOCUMENT — Example conflicting specifications\nRequirement: The outlet turbidity shall be below 1 NTU before UV exposure. Requirement: The outlet turbidity shall be below 5 NTU before UV exposure. These values appear inconsistent; document owners have not reconciled which threshold applies.",
    "10 Open questions.md": "SYNTHETIC DEMO DOCUMENT — Open questions\nOpen question: Which flow target is approved, 8 or 12 liters per hour? Open question: Who approves the turbidity threshold? Open question: What protocol and lab will validate microbial performance? Open question: Is the prototype intended for research only or a later deployment study?"
}


@app.post("/api/demo/seed", status_code=201)
def seed_demo():
    with Session() as s:
        existing = s.scalar(select(Project).where(Project.name == "Aqua-Nexus — Intelligent Water Purification Research"))
        if existing: return {"project": as_project(existing), "created": False}
        p = Project(name="Aqua-Nexus — Intelligent Water Purification Research", description="Synthetic research project for demonstrating evidence-grounded project resurrection.")
        s.add(p); s.flush()
        for name, content in DEMO_DOCS.items():
            raw = content.encode(); d = Document(project_id=p.id, filename=name, checksum=hashlib.sha256(raw).hexdigest(), content=content, status="processed")
            s.add(d); s.flush(); (UPLOAD_DIR / f"{d.id}.md").write_bytes(raw)
            for n, (location, chunk) in enumerate(chunk_text(content)):
                s.add(DocumentChunk(document_id=d.id, ordinal=n, location=location, text=chunk))
        s.commit(); s.refresh(p)
        return {"project": as_project(p), "created": True}


@app.get("/api/projects")
def list_projects(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    with Session() as s:
        items = s.scalars(select(Project).order_by(Project.created_at.desc()).offset(offset).limit(limit)).all()
        return {"items": [as_project(p) for p in items], "limit": limit, "offset": offset}


@app.post("/api/projects", status_code=201)
def create_project(data: ProjectIn):
    with Session() as s:
        p = Project(name=data.name.strip(), description=data.description.strip()); s.add(p); s.commit(); s.refresh(p); return as_project(p)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    with Session() as s:
        p = s.get(Project, project_id)
        if not p: raise HTTPException(404, "Project not found")
        return {**as_project(p), "documents": [as_document(d) for d in p.documents]}


def as_document(d: Document): return {"id": d.id, "filename": d.filename, "status": d.status, "warning": d.warning, "checksum": d.checksum, "created_at": d.created_at.isoformat(), "characters": len(d.content)}


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str):
    with Session() as s:
        p = s.get(Project, project_id)
        if not p: raise HTTPException(404, "Project not found")
        for d in p.documents:
            (UPLOAD_DIR / f"{d.id}{Path(d.filename).suffix.lower()}").unlink(missing_ok=True)
        s.delete(p); s.commit()


@app.post("/api/projects/{project_id}/documents", status_code=201)
async def upload_documents(project_id: str, files: list[UploadFile] = File(...)):
    with Session() as s:
        p = s.get(Project, project_id)
        if not p: raise HTTPException(404, "Project not found")
        result = []
        for f in files:
            safe_name = (f.filename or "upload").replace("\\", "/").split("/")[-1]
            suffix = Path(safe_name).suffix.lower()
            if suffix not in ALLOWED:
                result.append({"filename": safe_name, "status": "unsupported", "warning": f"Unsupported format: {suffix or 'no extension'}"}); continue
            raw = await f.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                result.append({"filename": safe_name, "status": "failed", "warning": f"File exceeds {MAX_FILE_BYTES // (1024*1024)} MB limit"}); continue
            checksum = hashlib.sha256(raw).hexdigest()
            dup = s.scalar(select(Document).where(Document.project_id == project_id, Document.checksum == checksum))
            if dup:
                result.append({**as_document(dup), "duplicate": True}); continue
            content, warning = extract_file(suffix, raw)
            doc = Document(project_id=project_id, filename=safe_name, checksum=checksum, content=content, status="failed" if not content else "processed", warning=warning)
            s.add(doc); s.flush()
            for n, (location, chunk) in enumerate(chunk_text(content)):
                s.add(DocumentChunk(document_id=doc.id, ordinal=n, location=location, text=chunk))
            (UPLOAD_DIR / f"{doc.id}{suffix}").write_bytes(raw)
            result.append(as_document(doc))
        s.commit()
        return {"results": result}


@app.get("/api/projects/{project_id}/documents")
def list_documents(project_id: str):
    with Session() as s:
        if not s.get(Project, project_id): raise HTTPException(404, "Project not found")
        docs = s.scalars(select(Document).where(Document.project_id == project_id).order_by(Document.created_at)).all()
        return {"items": [as_document(d) for d in docs]}


@app.get("/api/documents/{document_id}")
def get_document(document_id: str):
    with Session() as s:
        d = s.get(Document, document_id)
        if not d: raise HTTPException(404, "Document not found")
        return {**as_document(d), "content": d.content, "chunks": [{"location": c.location, "text": c.text} for c in d.chunks]}


@app.post("/api/projects/{project_id}/analyze")
@app.post("/api/projects/{project_id}/resurrect")
def analyze(project_id: str, payload: dict[str, Any] | None = None):
    mode = (payload or {}).get("mode", "project-resurrection")
    question = str((payload or {}).get("question", ""))[:500]
    allowed = {"project-resurrection", "decision-time-machine", "knowledge-integrity", "impact-analysis", "knowledge-audit", "gravitational-extract", "topological-summarize", "matrix-organize", "handover"}
    if mode not in allowed: raise HTTPException(422, "Unknown analysis mode")
    with Session() as s:
        p = s.get(Project, project_id)
        if not p: raise HTTPException(404, "Project not found")
        if not any(d.status == "processed" and d.content.strip() for d in p.documents): raise HTTPException(422, "Upload at least one successfully processed document first")
        result = build_analysis(p, mode, question)
        report = Report(project_id=project_id, mode=mode, payload=__import__("json").dumps(result, ensure_ascii=False)); s.add(report); s.commit(); result["report_id"] = report.id
        return result


@app.get("/api/projects/{project_id}/analysis")
def analysis_history(project_id: str):
    with Session() as s:
        items = s.scalars(select(Report).where(Report.project_id == project_id).order_by(Report.created_at.desc())).all()
        return {"items": [{"id": r.id, "mode": r.mode, "created_at": r.created_at.isoformat()} for r in items]}


@app.get("/api/projects/{project_id}/graph")
def graph(project_id: str):
    with Session() as s:
        p = s.get(Project, project_id)
        if not p: raise HTTPException(404, "Project not found")
        nodes = [{"id": d.id, "label": d.filename, "type": "document", "explicit": True} for d in p.documents if d.status == "processed"]
        edges = []
        for d in p.documents:
            if d.status != "processed": continue
            for j, term in enumerate(re.findall(r"\b[A-Z][A-Za-z0-9-]{3,}\b", d.content)):
                node_id = "concept:" + term.lower()
                if not any(n["id"] == node_id for n in nodes): nodes.append({"id": node_id, "label": term, "type": "concept", "explicit": False})
                edges.append({"source": d.id, "target": node_id, "type": "derivedFrom", "explicit": False})
        return {"nodes": nodes, "edges": edges[:150]}


@app.get("/api/projects/{project_id}/timeline")
def timeline(project_id: str): return analyze(project_id, {"mode": "decision-time-machine"}).get("timeline", [])


@app.get("/api/projects/{project_id}/integrity")
def integrity(project_id: str): return analyze(project_id, {"mode": "knowledge-integrity"}).get("contradictions", [])


@app.get("/api/projects/{project_id}/knowledge-debt")
def knowledge_debt(project_id: str): return analyze(project_id, {"mode": "knowledge-audit"}).get("knowledge_debt", {})


@app.post("/api/projects/{project_id}/impact-analysis")
def impact(project_id: str, payload: dict[str, Any]): return analyze(project_id, {**payload, "mode": "impact-analysis"})


@app.post("/api/projects/{project_id}/handover")
def handover(project_id: str): return analyze(project_id, {"mode": "handover"})


@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    with Session() as s:
        r = s.get(Report, report_id)
        if not r: raise HTTPException(404, "Report not found")
        return __import__("json").loads(r.payload)


@app.get("/api/reports/{report_id}/export", response_class=PlainTextResponse)
def export_report(report_id: str):
    with Session() as s:
        r = s.get(Report, report_id)
        if not r: raise HTTPException(404, "Report not found")
        data = __import__("json").loads(r.payload)
        lines = [f"# {data['project_name']} — {r.mode.replace('-', ' ').title()}", "", f"> Deterministic source-text extraction. Generated {data['created_at']}. Every claim below includes source evidence.", "", data.get("executive_overview", "")]
        for title, key in (("Decisions", "decisions"), ("Requirements", "requirements"), ("Open questions", "questions"), ("Potential conflicts", "contradictions")):
            lines += ["", f"## {title}"]
            vals = data.get(key, [])
            if not vals: lines.append("No candidates found in processed source text.")
            for v in vals:
                if "claim_a" in v: lines.append(f"- Potential conflict requiring human review: {v['claim_a']['text']} ({v['claim_a']['filename']}) ↔ {v['claim_b']['text']} ({v['claim_b']['filename']})")
                else: lines.append(f"- {v['text']} — **{v['filename']}**, {v['location']}; evidence: “{v['evidence']}”")
        lines += ["", "## Source documents", *[f"- {d['filename']}" for d in data["documents_analyzed"]]]
        return "\n".join(lines)


@app.get("/api/integrations/uliya/status")
def uliya_status(): return {"connected": False, "adapter": "DemoUliyaAdapter", "mode": "offline", "message": "No documented UGREEN connection is configured. Local demo workflows remain available."}


@app.get("/api/integrations/uliya/capabilities")
def uliya_capabilities(): return {"available": False, "capabilities": {"ug-filesystem": {"agent": "file-agent", "operations": ["find", "ls", "cat", "stat"]}, "ug-document": {"agent": "document-agent", "operations": ["metadata", "page-count", "qa", "extract", "reconcile"]}, "ug-knowledge": {"agent": "knowledge-agent", "operations": ["collect-evidence", "answer-official", "save-text"]}}, "message": "Capability names reflect the supplied integration brief; connection and delegation need a documented SDK/API and NAS access."}
