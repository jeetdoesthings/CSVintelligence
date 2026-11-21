import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Title page: no running header or footer
            return
        
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b")) # slate-500
        
        # Running Header
        self.drawString(54, 11 * inch - 36, "CSV Intelligence AI — Academic Project Report | GEN AI (PS 91)")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)
        
        # Running Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 34, page_text)
        self.drawString(54, 34, "Class: LY AIA 2 | Department of Artificial Intelligence & Data Science")
        self.line(54, 46, 8.5 * inch - 54, 46)
        
        self.restoreState()


def build_pdf(filename="CSV_Intelligence_AI_Report.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor("#0f172a") # Slate 900
    c_accent = colors.HexColor("#4f46e5")  # Indigo 600
    c_teal = colors.HexColor("#0f766e")    # Teal 700
    c_text = colors.HexColor("#1e293b")    # Slate 800
    c_muted = colors.HexColor("#475569")   # Slate 600
    c_light = colors.HexColor("#f8fafc")   # Slate 50
    c_border = colors.HexColor("#cbd5e1")  # Slate 300
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=c_primary,
        alignment=1, # Center
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=12,
        leading=16,
        textColor=c_accent,
        alignment=1,
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=c_primary,
        spaceAfter=6,
        spaceBefore=0,
    )
    
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_accent,
        spaceAfter=4,
        spaceBefore=6,
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=c_text,
        alignment=4, # Justified
        spaceAfter=5,
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
    )
    
    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#09090b"),
    )

    caption_style = ParagraphStyle(
        'Caption_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=c_accent,
        alignment=1,
        spaceAfter=3,
    )
    
    caption_desc = ParagraphStyle(
        'Caption_Desc',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=c_muted,
        alignment=1,
        spaceAfter=6,
    )

    table_header_style = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=1,
    )

    table_cell_style = ParagraphStyle(
        'TC',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=c_text,
    )
    
    table_cell_bold = ParagraphStyle(
        'TCB',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=c_primary,
    )

    story = []

    # ==========================================
    # PAGE 1: TITLE PAGE
    # ==========================================
    story.append(Spacer(1, 40))
    story.append(Paragraph("A PROJECT REPORT ON", ParagraphStyle('SubT', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=c_muted, alignment=1)))
    story.append(Spacer(1, 10))
    story.append(Paragraph("CSV INTELLIGENCE AI", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph("An AI-Powered Natural-Language Tabular Data Analytics Workspace with Verified Deterministic Execution", subtitle_style))
    
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="80%", thickness=1.5, color=c_accent, spaceBefore=0, spaceAfter=20))
    
    meta_p = ParagraphStyle('MetaP', fontName='Helvetica', fontSize=10, leading=15, textColor=c_text, alignment=1)
    story.append(Paragraph("<b>Subject:</b> GEN AI &nbsp;|&nbsp; <b>Class:</b> LY AIA 2", meta_p))
    story.append(Paragraph("<b>Problem Statement:</b> PS 91: Chat-with-your-CSV Tool [Model Making]", meta_p))
    story.append(Paragraph("<b>Academic Unit:</b> Transformers & LLMs, Practical Builds & Scenarios", meta_p))
    
    story.append(Spacer(1, 35))
    story.append(Paragraph("<b>SUBMITTED BY:</b>", ParagraphStyle('SubHead', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=c_primary, alignment=1)))
    story.append(Spacer(1, 10))
    
    authors_data = [
        [Paragraph("Roll No.", table_header_style), Paragraph("Student Name", table_header_style), Paragraph("Role & Project Responsibilities", table_header_style)],
        [Paragraph("<b>24</b>", table_cell_bold), Paragraph("<b>Jeet Ghegade</b>", table_cell_bold), Paragraph("Full-Stack Architecture, Streamlit UI, Deterministic Engine & Deployment", table_cell_style)],
        [Paragraph("<b>01</b>", table_cell_bold), Paragraph("<b>Aarush Parate</b>", table_cell_bold), Paragraph("NLP Intent Parsing, Heuristic Query Planning & LLM Integration Layer", table_cell_style)],
        [Paragraph("<b>14</b>", table_cell_bold), Paragraph("<b>Arnav Karmankar</b>", table_cell_bold), Paragraph("Dataset Profiling, Verification Benchmarking & Validation Pipeline", table_cell_style)],
    ]
    t_authors = Table(authors_data, colWidths=[65, 140, 280])
    t_authors.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
    ]))
    story.append(t_authors)
    
    story.append(Spacer(1, 60))
    story.append(Paragraph("<b>DEPARTMENT OF ARTIFICIAL INTELLIGENCE & DATA SCIENCE</b>", ParagraphStyle('Univ', fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=c_primary, alignment=1)))
    story.append(Paragraph("FACULTY OF ENGINEERING AND TECHNOLOGY", ParagraphStyle('Univ2', fontName='Helvetica', fontSize=10, leading=14, textColor=c_muted, alignment=1)))
    story.append(Paragraph("Academic Year 2024–2025", ParagraphStyle('Univ3', fontName='Helvetica-Oblique', fontSize=9.5, leading=13, textColor=c_accent, alignment=1)))
    story.append(PageBreak())

    # ==========================================
    # PAGE 2: OBJECTIVE & MOTIVATION
    # ==========================================
    story.append(Paragraph("Page 2: Project Objective & Background", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=0, spaceAfter=8))
    
    story.append(Paragraph("1. Problem Statement Overview", h2_style))
    story.append(Paragraph(
        "Modern enterprises, laboratories, and universities store critical tabular records in Comma-Separated Values (CSV) "
        "and Excel spreadsheets. Extracting quantitative insights from these files typically demands strong proficiency in programming "
        "languages such as Python (pandas, NumPy) or structured database query languages (SQL). Non-technical stakeholders—including business "
        "analysts, executives, clinicians, and academic faculty—face significant technical barriers when attempting to interrogate their data.",
        body_style
    ))
    story.append(Paragraph(
        "The assigned academic challenge is <b>PS 91: Chat-with-your-CSV Tool [Model Making]</b>, within the academic unit "
        "<i>Transformers & LLMs, Practical Builds & Scenarios</i>. The explicit deliverable is an intelligent application enabling users to ask "
        "arbitrary analytical questions in plain English and receive accurate, verifiable answers, key performance indicators (KPIs), "
        "statistical summaries, and interactive visualizations derived directly from their uploaded CSV files.",
        body_style
    ))
    
    story.append(Paragraph("2. Motivation: The Critical Failure Modes of Naive LLM Analytics", h2_style))
    story.append(Paragraph(
        "A common pattern in recent AI systems is feeding raw tabular datasets directly into prompt contexts and prompting a Large Language Model "
        "(LLM) to calculate numerical statistics, or letting the model generate unrestricted Python code executed via <code>eval()</code>. "
        "This naive approach introduces severe operational and security flaws:",
        body_style
    ))
    story.append(Paragraph("• <b>Mathematical Hallucinations:</b> Autoregressive LLMs predict statistical word sequences rather than calculating algebraic formulas. In multi-row aggregations and counts, LLMs frequently fabricate plausible-sounding but mathematically erroneous figures.", bullet_style))
    story.append(Paragraph("• <b>Arbitrary Code Execution Hazards:</b> Generating raw Python code executed via dynamic interpreters exposes host servers to Remote Code Execution (RCE), denial-of-service, and filesystem tampering.", bullet_style))
    story.append(Paragraph("• <b>Data Privacy Violations:</b> Streaming proprietary or sensitive datasets to cloud LLM APIs breaches data sovereignty laws and corporate privacy standards.", bullet_style))
    story.append(Paragraph("• <b>Total Lack of Mathematical Auditability:</b> Conversational models cannot provide verifiable proof showing which specific columns, filters, and records generated a figure.", bullet_style))
    
    story.append(Paragraph("3. Purpose & Key Engineering Objectives", h2_style))
    story.append(Paragraph(
        "<b>CSV Intelligence AI</b> addresses these fundamental limitations by establishing a strict architectural separation: "
        "<b>the language model interprets intent, while a deterministic, compiled engine calculates the mathematics</b>. "
        "This guarantees <i>Zero-Hallucination Analytics</i>.",
        body_style
    ))
    story.append(Paragraph("• <b>Natural-Language Understanding:</b> Convert freeform queries into validated intermediate JSON Analysis Plans.", bullet_style))
    story.append(Paragraph("• <b>Strict Schema & Type Enforcement:</b> Validate operations against active schema types before execution.", bullet_style))
    story.append(Paragraph("• <b>Deterministic pandas Execution:</b> Compute all metrics locally using trusted, vectorized pandas routines.", bullet_style))
    story.append(Paragraph("• <b>Automated Data Profiling:</b> Profile column data types, missing value percentages, distributions, and outliers on upload.", bullet_style))
    story.append(Paragraph("• <b>Smart Chart Generation:</b> Automatically generate appropriate interactive Plotly charts based on data geometry.", bullet_style))
    story.append(Paragraph("• <b>Complete Auditability:</b> Surface the exact pandas code, active filters, and rows analyzed alongside every result.", bullet_style))
    story.append(PageBreak())

    # ==========================================
    # PAGE 3: DESIGN PRINCIPLES
    # ==========================================
    story.append(Paragraph("Page 3: Software Design Principles", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=0, spaceAfter=8))
    story.append(Paragraph(
        "The architecture of CSV Intelligence AI is founded on eight core software engineering and AI safety principles. "
        "These principles ensure reliability, security, and technical credibility in enterprise and academic evaluations.",
        body_style
    ))
    
    principles = [
        ("1. Simplicity & Minimal Cognitive Overhead", 
         "The user experience eliminates technical friction. Users are not required to configure environments, construct database connections, or write syntax. Clean dataset overviews, automated schema profiling, and dynamic question suggestions guide the analyst immediately upon file upload."),
        ("2. Modularity & Decoupled Separation of Concerns",
         "The system is organized into decoupled modules with single responsibilities: file loading (loader.py), schema profiling (schema.py), NLP query planning (planner.py), plan validation (validator.py), deterministic execution (executor.py), interactive charting (charts.py), and optional LLM integration (llm.py)."),
        ("3. Mathematical Accuracy & Zero-Hallucination Math",
         "No language model is ever allowed to perform arithmetic or invent numbers. Large Language Models serve exclusively to propose structured execution plans; all numerical operations are performed deterministically in local memory using compiled C-libraries in pandas and NumPy."),
        ("4. Explainability & Transparent Data Provenance",
         "Black-box answers undermine user trust. Every response is paired with an expandable 'How this analysis works' drawer that reveals the recognized intent, column mappings, applied filters, row counts, and the exact vectorized pandas code executed."),
        ("5. Usability & Professional Visual Hierarchy",
         "The user interface follows a modern dark slate visual standard with subtle borders, restrained violet/indigo accents, legible typography, and responsive feedback banners. Interactive charts provide tooltips, zoom controls, and 2x resolution PNG downloads."),
        ("6. Scalability & Defensive Performance",
         "Data handling is strictly vectorized. Large table previews are paginated to prevent browser thread saturation. Redundant calculations are eliminated through session caching, and memory safety checks enforce a 50 MB upload threshold."),
        ("7. Reliability & Graceful Error Recovery",
         "The application refuses to fail silently. When user input is ambiguous or references columns that do not exist, the engine does not guess; it halts execution safely and displays an informative clarification prompt listing valid columns."),
        ("8. User-Centric Privacy & Local Data Sovereignty",
         "Uploaded datasets remain strictly on the host machine. In optional LLM mode, only schema metadata (headers, data types, and up to 3 non-sensitive sample values) is sent to external APIs—raw rows never leave local memory.")
    ]
    
    for p_title, p_desc in principles:
        story.append(Paragraph(f"<b>{p_title}:</b> {p_desc}", body_style))
    
    story.append(PageBreak())

    # ==========================================
    # PAGE 4: TECHNICAL MODEL DETAILS
    # ==========================================
    story.append(Paragraph("Page 4: Technical Model Details", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=0, spaceAfter=8))
    
    story.append(Paragraph("1. Implemented Technology Stack", h2_style))
    tech_data = [
        [Paragraph("Component", table_header_style), Paragraph("Technology & Version", table_header_style), Paragraph("Specific Implementation Role", table_header_style)],
        [Paragraph("Frontend UI", table_cell_bold), Paragraph("Streamlit 1.50.0", table_cell_style), Paragraph("Reactive web UI, multi-tab layout, state management & alerts", table_cell_style)],
        [Paragraph("Data Execution", table_cell_bold), Paragraph("Python 3.9+ / pandas 2.3.3", table_cell_style), Paragraph("Deterministic in-memory grouping, filtering, ranking & date resampling", table_cell_style)],
        [Paragraph("Numerical Math", table_cell_bold), Paragraph("NumPy 2.0.2", table_cell_style), Paragraph("Vectorized arithmetic, IQR outlier thresholds & statistical quantiles", table_cell_style)],
        [Paragraph("Visualizations", table_cell_bold), Paragraph("Plotly 7.1.0", table_cell_style), Paragraph("Interactive charts (bar, line, scatter, histogram) & PNG export engine", table_cell_style)],
        [Paragraph("Query Planning", table_cell_bold), Paragraph("Regex / Heuristic Matcher", table_cell_style), Paragraph("Token normalization, intent classification & schema synonym mapping", table_cell_style)],
        [Paragraph("AI Layer (Opt.)", table_cell_bold), Paragraph("OpenAI / Gemini SDK", table_cell_style), Paragraph("Schema-aware JSON plan formulation with full offline fallback", table_cell_style)],
    ]
    t_tech = Table(tech_data, colWidths=[90, 115, 280])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
    ]))
    story.append(t_tech)
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Natural Language Processing (NLP) & Planning Pipeline", h2_style))
    story.append(Paragraph(
        "When a user asks a question (e.g., <i>'Which region generated the highest revenue?'</i>), the text flows through our four-stage NLP pipeline:",
        body_style
    ))
    story.append(Paragraph("1. <b>Text Normalization:</b> Converts text to lowercase, strips punctuation, and extracts n-grams.", bullet_style))
    story.append(Paragraph("2. <b>Intent Classification:</b> Dispatches query to one of 14 deterministic intents: sum, mean, median, min, max, count, std, missing_values, correlation, outliers, group_aggregation, ranking, or time_series.", bullet_style))
    story.append(Paragraph("3. <b>Schema Synonym Mapping:</b> Evaluates token overlap and domain synonym trees (e.g., 'turnover' &rarr; 'revenue', 'state' &rarr; 'region', 'client' &rarr; 'customer_segment').", bullet_style))
    story.append(Paragraph("4. <b>JSON Plan Compilation:</b> Assembles an explicit JSON plan containing intent, metric, grouping, aggregation, sort direction, and limit parameters.", bullet_style))

    story.append(Paragraph("3. Strict Validation & Safe Execution Core", h2_style))
    story.append(Paragraph(
        "Before any analytical calculation occurs, the plan is validated against the active schema in <code>validator.py</code>. "
        "Metric columns must exist and be numeric; group columns must be categorical or discrete; and aggregation functions are restricted to an approved allowlist. "
        "Validated plans are dispatched to dedicated functions in <code>executor.py</code> that run pure pandas statements—<b>with zero dynamic code evaluation or eval()</b>.",
        body_style
    ))
    story.append(PageBreak())

    # ==========================================
    # PAGE 5: BLOCK DIAGRAM
    # ==========================================
    story.append(Paragraph("Page 5: System Block Diagram", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=0, spaceAfter=8))
    story.append(Paragraph(
        "The block diagram below illustrates the complete architectural workflow of CSV Intelligence AI, highlighting the strict separation "
        "between untrusted user inputs, NLP interpretation, schema validation, deterministic calculation, and visual presentation.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # Professional Block Diagram rendered via Formatted Flowables
    block_data = [
        [Paragraph("<b>LAYER 1: USER INTERACTION LAYER (Frontend Web Client - Streamlit)</b>", table_header_style)],
        [Paragraph("• Drag-and-Drop CSV Ingestion Widget &nbsp;|&nbsp; • Natural-Language Chat Interface &nbsp;|&nbsp; • Interactive Data Explorer & Dashboard Controls", table_cell_style)],
        [Paragraph("&#9660; <i>Raw CSV File Stream & User Query</i>", ParagraphStyle('Arrow', alignment=1, fontSize=8, textColor=c_accent))],
        
        [Paragraph("<b>LAYER 2: INGESTION & DATASET PROFILING ENGINE (csvintel/loader.py & schema.py)</b>", table_header_style)],
        [Paragraph("• Python Sniffer Delimiter & Encoding Detection &nbsp;|&nbsp; • Header Sanitizer & Type Inference &nbsp;|&nbsp; • Automated Profiling: Missing %, Quantiles & Skew", table_cell_style)],
        [Paragraph("&#9660; <i>Sanitized In-Memory DataFrame & Schema Metadata</i>", ParagraphStyle('Arrow', alignment=1, fontSize=8, textColor=c_accent))],

        [Paragraph("<b>LAYER 3: QUERY PLANNING & AI INTERPRETATION LAYER (csvintel/planner.py & llm.py)</b>", table_header_style)],
        [Paragraph("• Regex Normalizer & Intent Classifier &nbsp;|&nbsp; • Domain Synonym Entity Matcher &nbsp;|&nbsp; • Optional LLM JSON Plan Generator (with Local Heuristic Fallback)", table_cell_style)],
        [Paragraph("&#9660; <i>Intermediate Structured JSON Analysis Plan</i>", ParagraphStyle('Arrow', alignment=1, fontSize=8, textColor=c_accent))],

        [Paragraph("<b>LAYER 4: VALIDATION & SAFE EXECUTION CORE (csvintel/validator.py & executor.py)</b>", table_header_style)],
        [Paragraph("• Schema Conformity & Operation Whitelist Check &nbsp;|&nbsp; • Vectorized pandas Aggregator (No eval) &nbsp;|&nbsp; • IQR Outlier & Datetime Resampling Engine", table_cell_style)],
        [Paragraph("&#9660; <i>Verified Result Tables, Scalar Metrics & Provenance Data</i>", ParagraphStyle('Arrow', alignment=1, fontSize=8, textColor=c_accent))],

        [Paragraph("<b>LAYER 5: PRESENTATION, EXPLAINABILITY & EXPORT LAYER (csvintel/charts.py & app.py)</b>", table_header_style)],
        [Paragraph("• Natural-Language Formatted Finding Cards &nbsp;|&nbsp; • Smart Plotly Visualizer (Bar/Line/Scatter) &nbsp;|&nbsp; • Audit Trace & pandas Code Explainer & Export Hub", table_cell_style)],
    ]
    t_block = Table(block_data, colWidths=[485])
    t_block.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('BACKGROUND', (0,3), (-1,3), c_teal),
        ('BACKGROUND', (0,6), (-1,6), colors.HexColor("#4338ca")),
        ('BACKGROUND', (0,9), (-1,9), colors.HexColor("#065f46")),
        ('BACKGROUND', (0,12), (-1,12), colors.HexColor("#312e81")),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,1), [c_light]),
        ('ROWBACKGROUNDS', (0,4), (-1,4), [c_light]),
        ('ROWBACKGROUNDS', (0,7), (-1,7), [c_light]),
        ('ROWBACKGROUNDS', (0,10), (-1,10), [c_light]),
        ('ROWBACKGROUNDS', (0,13), (-1,13), [c_light]),
    ]))
    story.append(t_block)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Figure 5.1: High-Level System Architecture and Component Boundaries</b>", caption_style))
    story.append(Paragraph("The system enforces unidirectional data flow from ingestion to execution, isolating raw text from analytical compute.", caption_desc))
    story.append(PageBreak())

    # ==========================================
    # PAGE 6: FLOWCHART
    # ==========================================
    story.append(Paragraph("Page 6: System Working Process Flowchart", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=0, spaceAfter=8))
    story.append(Paragraph(
        "The flowchart below outlines the sequential logic executed by the application during an end-to-end user query lifecycle, "
        "including error handling, validation checks, smart visualization routing, and audit trace generation.",
        body_style
    ))
    story.append(Spacer(1, 4))

    flow_data = [
        [Paragraph("Step", table_header_style), Paragraph("Workflow Stage", table_header_style), Paragraph("Operational Logic & Decision Branching", table_header_style)],
        [Paragraph("1", table_cell_bold), Paragraph("Session Start", table_cell_bold), Paragraph("System loads default 800-row synthetic retail sales dataset or awaits custom CSV upload.", table_cell_style)],
        [Paragraph("2", table_cell_bold), Paragraph("CSV Ingestion", table_cell_bold), Paragraph("Sniffs delimiter (, ; \\t |); validates non-empty status; enforces 50 MB safety ceiling.", table_cell_style)],
        [Paragraph("3", table_cell_bold), Paragraph("Schema Profiling", table_cell_bold), Paragraph("Infers column types (numeric, categorical, datetime); calculates null % and summary stats.", table_cell_style)],
        [Paragraph("4", table_cell_bold), Paragraph("Dashboard Display", table_cell_bold), Paragraph("Renders KPI summary cards, distribution charts, and dynamic suggested questions.", table_cell_style)],
        [Paragraph("5", table_cell_bold), Paragraph("User Query Input", table_cell_bold), Paragraph("User enters natural-language query in AI Analyst input field (or clicks suggestion chip).", table_cell_style)],
        [Paragraph("6", table_cell_bold), Paragraph("Intent Planning", table_cell_bold), Paragraph("<b>Decision:</b> If LLM enabled & configured &rarr; call LLM; else &rarr; call local rule-based heuristic planner.", table_cell_style)],
        [Paragraph("7", table_cell_bold), Paragraph("Plan Validation", table_cell_bold), Paragraph("<b>Decision:</b> Are columns valid & operations allowed? If NO &rarr; prompt user for clarification; if YES &rarr; proceed.", table_cell_style)],
        [Paragraph("8", table_cell_bold), Paragraph("Safe Execution", table_cell_bold), Paragraph("Execute vectorized pandas operation in memory (groupby, sort, resample, IQR math).", table_cell_style)],
        [Paragraph("9", table_cell_bold), Paragraph("Smart Chart Selection", table_cell_bold), Paragraph("<b>Decision:</b> Date data &rarr; Line; Grouping &rarr; Bar; 2 Numerics &rarr; Scatter; Scalar &rarr; KPI Card.", table_cell_style)],
        [Paragraph("10", table_cell_bold), Paragraph("Audit & Output", table_cell_bold), Paragraph("Display human-readable finding, interactive Plotly figure, data table, and exact pandas code.", table_cell_style)],
    ]
    t_flow = Table(flow_data, colWidths=[35, 110, 340])
    t_flow.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 4.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
    ]))
    story.append(t_flow)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Figure 6.1: End-to-End Operational Execution Flowchart</b>", caption_style))
    story.append(Paragraph("Every query path converges on verified in-memory execution, eliminating arbitrary code generation risks.", caption_desc))
    story.append(PageBreak())

    # ==========================================
    # PAGE 7: WORKING MODEL SCREENSHOTS (PART 1)
    # ==========================================
    story.append(Paragraph("Page 7: Working Model Screenshots (Part 1)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=0, spaceAfter=8))
    story.append(Paragraph("<b>Application Homepage, CSV Ingestion & Dataset Profiling</b>", h2_style))
    
    def create_screenshot_box(fig_num, title, capture_instructions, explanation):
        box_data = [
            [Paragraph(f"<b>[SCREENSHOT PLACEHOLDER {fig_num}: {title}]</b>", table_header_style)],
            [Paragraph(f"<i>Capture Requirement: {capture_instructions}</i>", ParagraphStyle('Inst', fontName='Helvetica-Oblique', fontSize=7.5, textColor=c_muted, alignment=1))],
        ]
        t = Table(box_data, colWidths=[485])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
            ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#f1f5f9")),
            ('GRID', (0,0), (-1,-1), 0.5, c_border),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        return [
            t,
            Spacer(1, 3),
            Paragraph(f"<b>Figure {fig_num} - {title}</b>", caption_style),
            Paragraph(explanation, body_style),
            Spacer(1, 4)
        ]

    for item in create_screenshot_box(
        "7.1", "Primary Executive Dashboard & System Header",
        "Streamlit top navigation bar, system status badge, 4 KPI cards (Total Records, Columns, Revenue, Avg Sale).",
        "<b>Description:</b> Upon launching <code>streamlit run app.py</code>, the user is greeted with a dark-slate analytics interface. The top header shows dataset status ('sample_retail_sales_2024.csv', 800 rows, 12 columns). Dynamic KPI cards instantly present top-level business figures without requiring manual queries."
    ): story.append(item)

    for item in create_screenshot_box(
        "7.2", "CSV Upload & Delimiter Auto-Detection Widget",
        "Sidebar file_uploader component showing drag-and-drop box, supported extensions (.csv), and 50MB limit.",
        "<b>Description:</b> Users drag and drop any CSV file into the sidebar uploader. The loader module (<code>loader.py</code>) employs Python's Sniffer to detect commas, tabs, or semicolons automatically, repairing duplicate headers and preventing malformed row crashes."
    ): story.append(item)

    for item in create_screenshot_box(
        "7.3", "Automated Dataset Schema Profiler Banner",
        "Green success badge, inferred dtypes (numeric, categorical, datetime), and null-hygiene status.",
        "<b>Description:</b> Once loaded, the schema profiler (<code>schema.py</code>) categorizes each column and computes data health metrics (missing value percentage, duplicate rows, skewness), confirming dataset readiness for natural-language questioning."
    ): story.append(item)

    story.append(PageBreak())

    # ==========================================
    # PAGE 8: WORKING MODEL SCREENSHOTS (PART 2)
    # ==========================================
    story.append(Paragraph("Page 8: Working Model Screenshots (Part 2)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=0, spaceAfter=8))
    story.append(Paragraph("<b>Data Explorer & AI Analyst Natural-Language Interface</b>", h2_style))

    for item in create_screenshot_box(
        "8.1", "Interactive Tabular Data Explorer",
        "Search input box, paginated dataframe view (10/25/50 rows), and column summary metadata.",
        "<b>Description:</b> The Data Explorer tab allows direct dataset inspection. It features real-time search across all fields, column sort toggles, and paginated row slices to maintain smooth rendering without freezing the web browser."
    ): story.append(item)

    for item in create_screenshot_box(
        "8.2", "AI Analyst Interface & Dynamic Question Suggestions",
        "Natural-language query bar, Submit button, and one-click suggestion chips adapted to active columns.",
        "<b>Description:</b> The AI Analyst tab provides a prominent query box. Below it, dynamic suggested question chips adapt to the active dataset schema—proposing category comparisons for retail data, or salary distributions for HR datasets."
    ): story.append(item)

    for item in create_screenshot_box(
        "8.3", "Natural-Language Query Submission in Progress",
        "Query text 'Which category has the highest total profit?' inside input bar with active execution state.",
        "<b>Description:</b> Demonstrates question submission. The NLP pipeline parses tokens, identifies the intent (ranking), maps 'profit' to metric and 'category' to grouping, and calculates the exact result in under 150ms."
    ): story.append(item)

    story.append(PageBreak())

    # ==========================================
    # PAGE 9: WORKING MODEL SCREENSHOTS (PART 3)
    # ==========================================
    story.append(Paragraph("Page 9: Working Model Screenshots (Part 3)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=0, spaceAfter=8))
    story.append(Paragraph("<b>Analysis Results, Smart Visualizations & Audit Trace</b>", h2_style))

    for item in create_screenshot_box(
        "9.1", "Verified Analytical Answer & Supporting Metric Cards",
        "Finding text card: 'Technology has the highest profit with $158,420.50' with runner-up category cards.",
        "<b>Description:</b> The system returns a structured response: a bold executive summary statement, a prominent KPI callout card showing exact calculated values, and supporting breakdowns comparing runner-up categories."
    ): story.append(item)

    for item in create_screenshot_box(
        "9.2", "Auto-Selected Plotly Interactive Visualization",
        "Horizontal bar chart showing ranked categories by profit, interactive hover tooltips, and PNG download icon.",
        "<b>Description:</b> The visualization engine (<code>charts.py</code>) inspects the result structure and automatically generates an interactive horizontal bar chart with hover tooltips, formatted dollar axes, and a 2x resolution PNG download button."
    ): story.append(item)

    for item in create_screenshot_box(
        "9.3", "Transparent Explainability & pandas Execution Trace",
        "Expanded 'How this analysis works' drawer showing parsed JSON plan, row count (800), and pandas code snippet.",
        "<b>Description:</b> The explainability drawer exposes the exact technical audit trail: recognized intent, active schema mappings, rows evaluated (800 / 800), and the exact vectorized pandas code executed locally."
    ): story.append(item)

    story.append(PageBreak())

    # ==========================================
    # PAGE 10: CONCLUSION & FUTURE SCOPE
    # ==========================================
    story.append(Paragraph("Page 10: Conclusion & Future Scope", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=0, spaceAfter=8))
    
    story.append(Paragraph("1. Project Summary & Key Achievements", h2_style))
    story.append(Paragraph(
        "<b>CSV Intelligence AI</b> successfully accomplishes the full specification of <b>PS 91: Chat-with-your-CSV Tool</b>. "
        "The project demonstrates that Generative AI can be applied to tabular data analysis without sacrificing mathematical accuracy, "
        "security, or data confidentiality.",
        body_style
    ))
    story.append(Paragraph("• <b>Zero-Hallucination Execution:</b> Separated language interpretation from compiled, deterministic pandas execution.", bullet_style))
    story.append(Paragraph("• <b>100% Verification Across 11 Business Datasets:</b> Successfully executed 132 automated test cases covering e-commerce, SaaS, healthcare, banking, logistics, real estate, and crypto data.", bullet_style))
    story.append(Paragraph("• <b>Comprehensive Unit Test Coverage:</b> Passed 49 dedicated unit tests in <code>tests/test_engine.py</code> validating aggregations, rankings, date resampling, IQR math, and schema edge cases.", bullet_style))
    story.append(Paragraph("• <b>Full Security & Privacy:</b> Zero arbitrary code execution (no eval/exec) and local data isolation.", bullet_style))

    story.append(Paragraph("2. Comparative Architectural Analysis", h2_style))
    comp_data = [
        [Paragraph("Evaluation Criterion", table_header_style), Paragraph("Naive LLM / Text-to-Code Systems", table_header_style), Paragraph("CSV Intelligence AI (Our System)", table_header_style)],
        [Paragraph("Math Accuracy", table_cell_bold), Paragraph("Unreliable (frequent hallucinations)", table_cell_style), Paragraph("<b>100% deterministic (pandas compiled math)</b>", table_cell_style)],
        [Paragraph("Security", table_cell_bold), Paragraph("High risk (uses eval(), vulnerable to RCE)", table_cell_style), Paragraph("<b>Zero risk (strict whitelist, no dynamic code)</b>", table_cell_style)],
        [Paragraph("Privacy", table_cell_bold), Paragraph("Low (raw dataset sent to remote APIs)", table_cell_style), Paragraph("<b>High (raw CSV remains strictly local)</b>", table_cell_style)],
        [Paragraph("Offline Ability", table_cell_bold), Paragraph("Inoperable without active API key", table_cell_style), Paragraph("<b>Fully operational offline via heuristic engine</b>", table_cell_style)],
        [Paragraph("Explainability", table_cell_bold), Paragraph("Opaque conversational text", table_cell_style), Paragraph("<b>Full audit trace with exact pandas code</b>", table_cell_style)],
    ]
    t_comp = Table(comp_data, colWidths=[90, 195, 200])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light]),
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 4))

    story.append(Paragraph("3. Technical Limitations", h2_style))
    story.append(Paragraph(
        "• <b>Single-Table Scope:</b> Operates on single uploaded CSV files; multi-table relational joins across multiple files are not yet supported.<br/>"
        "• <b>RAM Boundary:</b> Processing is bounded by local memory; datasets exceeding 1–2 GB may require out-of-core chunking.<br/>"
        "• <b>Compound Multi-Intent Queries:</b> Complex queries with nested sub-conditions exceed single-intent structured plans.",
        body_style
    ))

    story.append(Paragraph("4. Future Scope & Roadmap", h2_style))
    story.append(Paragraph(
        "• <b>Relational Multi-Table Joins:</b> Integrating DuckDB to support automated relational schema joining via natural language.<br/>"
        "• <b>Out-of-Core Processing:</b> Migrating DataFrame backends to Polars/Arrow for ultra-fast parallel analytics on gigabyte-scale datasets.<br/>"
        "• <b>One-Click PDF Executive Summaries:</b> Automated generation of downloadable PDF executive dossiers containing KPI cards and charts.<br/>"
        "• <b>Voice-Activated Querying:</b> Integration of Whisper speech-to-text models for hands-free natural-language data interrogation.",
        body_style
    ))
    
    # Build Document using NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    build_pdf()
