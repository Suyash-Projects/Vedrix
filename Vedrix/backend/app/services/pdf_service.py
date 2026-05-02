import io
from xhtml2pdf import pisa
from typing import Dict, Any, Optional

def generate_interview_pdf(candidate_name: str, job_role: str, report: Dict[str, Any], transcript: list) -> bytes:
    """
    Generates a professional PDF report from interview data using xhtml2pdf.
    """
    
    # 1. Map scores to colors and labels
    def get_score_color(score):
        if score >= 8: return "#34d399"
        if score >= 5: return "#f59e0b"
        return "#f87171"

    overall_color = get_score_color(report.get('overall_score', 0))
    
    # 2. Build HTML Template (Dark Theme inspired by the UI)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: 'Helvetica', 'Arial', sans-serif;
                background-color: #020617;
                color: #f8fafc;
                line-height: 1.6;
            }}
            .header {{
                text-align: center;
                padding-bottom: 20px;
                border-bottom: 2px solid #1e293b;
            }}
            .logo {{
                font-size: 24px;
                font-weight: 900;
                color: #8b5cf6;
            }}
            .section {{
                margin-top: 30px;
            }}
            .section-title {{
                font-size: 12px;
                font-weight: 800;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 2px;
                margin-bottom: 15px;
            }}
            .score-card {{
                background-color: #0f172a;
                border-radius: 20px;
                padding: 40px;
                text-align: center;
                border: 1px solid #1e293b;
            }}
            .score-value {{
                font-size: 60px;
                font-weight: 900;
                color: {overall_color};
            }}
            .recommendation {{
                display: inline-block;
                padding: 10px 20px;
                border-radius: 50px;
                background-color: rgba(139, 92, 246, 0.1);
                color: #a78bfa;
                font-weight: 800;
                font-size: 14px;
                margin-top: 10px;
            }}
            .metrics-table {{
                width: 100%;
                margin-top: 20px;
            }}
            .metric-row {{
                margin-bottom: 10px;
            }}
            .metric-label {{
                font-size: 12px;
                font-weight: 700;
                color: #64748b;
            }}
            .summary-box {{
                background-color: #0f172a;
                padding: 20px;
                border-left: 4px solid #8b5cf6;
                font-style: italic;
                color: #cbd5e1;
            }}
            .list-item {{
                margin-bottom: 8px;
                color: #cbd5e1;
            }}
            .transcript-row {{
                margin-bottom: 20px;
                padding-bottom: 15px;
                border-bottom: 1px solid #1e293b;
            }}
            .role-assistant {{ color: #a78bfa; font-weight: 900; font-size: 10px; }}
            .role-user {{ color: #34d399; font-weight: 900; font-size: 10px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">VEDRIX AI</div>
            <div style="font-size: 14px; color: #64748b;">EVALUATION DOSSIER</div>
        </div>

        <div class="section">
            <div class="score-card">
                <div class="section-title">Overall Assessment</div>
                <div class="score-value">{report.get('overall_score', '0.0')}</div>
                <div class="recommendation">{report.get('hire_recommendation', 'MAYBE')}</div>
                <div style="margin-top: 20px; color: #94a3b8;">
                    <strong>Candidate:</strong> {candidate_name}<br/>
                    <strong>Role:</strong> {job_role}
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Executive Summary</div>
            <div class="summary-box">
                "{report.get('summary', 'No summary provided.')}"
            </div>
        </div>

        <div class="section">
            <div class="section-title">Key Strengths</div>
            {"".join(f'<div class="list-item">• {s}</div>' for s in report.get('strengths', []))}
        </div>

        <div class="section">
            <div class="section-title">Improvement Areas</div>
            {"".join(f'<div class="list-item">• {w}</div>' for w in report.get('weaknesses', []))}
        </div>

        <div class="section" style="page-break-before: always;">
            <div class="section-title">Interview Transcript</div>
            {"".join(f'''
                <div class="transcript-row">
                    <div class="role-{m['role']}">{m['role'].upper()}</div>
                    <div style="font-size: 12px; margin-top: 5px;">{m['content']}</div>
                </div>
            ''' for m in transcript)}
        </div>
    </body>
    </html>
    """
    
    # 3. Generate PDF
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html_content.encode("UTF-8")), result)
    
    if not pdf.err:
        return result.getvalue()
    else:
        raise Exception(f"PDF Generation Error: {pdf.err}")
