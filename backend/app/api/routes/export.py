"""Export endpoints for analysis results."""

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.api.routes.analysis import analysis_jobs
from app.models.responses import AnalysisStatus

router = APIRouter()


@router.get("/export/json/{analysis_id}")
async def export_json(analysis_id: str):
    """
    Download analysis results as JSON.

    Returns the full analysis results including compliance scores,
    findings, risk assessment, and executive summary.
    """
    if analysis_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Analysis not found")

    job = analysis_jobs[analysis_id]

    if job["status"] != AnalysisStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Analysis not completed yet",
        )

    results = job.get("results")
    if not results:
        raise HTTPException(
            status_code=500,
            detail="Results not available",
        )

    # Build export data
    export_data = {
        "analysis_id": analysis_id,
        "session_id": job["session_id"],
        "frameworks_analyzed": job["frameworks"],
        "started_at": job["started_at"].isoformat() if job.get("started_at") else None,
        "completed_at": (
            job["completed_at"].isoformat() if job.get("completed_at") else None
        ),
        "results": results,
    }

    # Generate filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"compliance_analysis_{timestamp}.json"

    return Response(
        content=json.dumps(export_data, indent=2, default=str),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/export/pdf/{analysis_id}")
async def export_pdf(analysis_id: str):
    """
    Download analysis results as PDF report.

    Generates a formatted PDF report with compliance scores,
    findings table, risk assessment, and executive summary.
    """
    if analysis_id not in analysis_jobs:
        raise HTTPException(status_code=404, detail="Analysis not found")

    job = analysis_jobs[analysis_id]

    if job["status"] != AnalysisStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Analysis not completed yet",
        )

    results = job.get("results")
    if not results:
        raise HTTPException(
            status_code=500,
            detail="Results not available",
        )

    try:
        pdf_bytes = await generate_pdf_report(analysis_id, job, results)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"compliance_report_{timestamp}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Content-Type-Options": "nosniff",
            },
        )
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="PDF generation not available. Install weasyprint.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {str(e)}",
        )


async def generate_pdf_report(
    analysis_id: str, job: dict, results: dict
) -> bytes:
    """Generate PDF report from analysis results."""
    from weasyprint import HTML

    # Get risk assessment data
    risk = results.get("risk_assessment", {})
    inherent_score = risk.get("inherent_risk_score", 0)
    residual_score = risk.get("residual_risk_score", 0)
    inherent_level = risk.get("inherent_risk_level", "N/A")
    residual_level = risk.get("residual_risk_level", "N/A")
    risk_reduction = risk.get("risk_reduction_percentage", 0)

    # Count findings by severity
    findings = results.get("findings", [])
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f.get("severity", "").lower()
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Build HTML report with professional styling
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Vendor Security Assessment Report</title>
        <style>
            @page {{
                size: letter;
                margin: 0.75in;
                @top-right {{
                    content: "CONFIDENTIAL";
                    font-size: 9px;
                    color: #999;
                }}
                @bottom-center {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 9px;
                    color: #666;
                }}
            }}
            body {{
                font-family: 'Helvetica Neue', Arial, sans-serif;
                font-size: 10pt;
                line-height: 1.5;
                color: #2d3748;
            }}
            .cover-page {{
                text-align: center;
                padding-top: 2in;
                page-break-after: always;
            }}
            .cover-title {{
                font-size: 28pt;
                font-weight: bold;
                color: #1a365d;
                margin-bottom: 0.5in;
            }}
            .cover-subtitle {{
                font-size: 14pt;
                color: #4a5568;
                margin-bottom: 1in;
            }}
            .cover-meta {{
                font-size: 11pt;
                color: #718096;
                margin-top: 2in;
            }}
            .cover-meta p {{
                margin: 5px 0;
            }}
            h1 {{
                font-size: 18pt;
                color: #1a365d;
                border-bottom: 2px solid #3182ce;
                padding-bottom: 8px;
                margin-top: 30px;
                margin-bottom: 15px;
            }}
            h2 {{
                font-size: 14pt;
                color: #2c5282;
                margin-top: 25px;
                margin-bottom: 10px;
            }}
            h3 {{
                font-size: 12pt;
                color: #2d3748;
                margin-top: 20px;
                margin-bottom: 8px;
            }}
            .section {{
                margin-bottom: 25px;
            }}
            .score-container {{
                display: flex;
                justify-content: space-between;
                margin: 20px 0;
            }}
            .score-box {{
                text-align: center;
                padding: 20px;
                border-radius: 8px;
                width: 30%;
                box-sizing: border-box;
            }}
            .score-box.primary {{
                background: linear-gradient(135deg, #1a365d 0%, #2c5282 100%);
                color: white;
            }}
            .score-box.inherent {{
                background: #fed7d7;
                border: 2px solid #fc8181;
            }}
            .score-box.residual {{
                background: #fefcbf;
                border: 2px solid #f6e05e;
            }}
            .score-value {{
                font-size: 36pt;
                font-weight: bold;
                margin: 10px 0;
            }}
            .score-label {{
                font-size: 10pt;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .score-sublabel {{
                font-size: 9pt;
                opacity: 0.8;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                font-size: 9pt;
            }}
            th {{
                background: #2d3748;
                color: white;
                padding: 10px 12px;
                text-align: left;
                font-weight: 600;
            }}
            td {{
                padding: 10px 12px;
                border-bottom: 1px solid #e2e8f0;
            }}
            tr:nth-child(even) {{
                background: #f7fafc;
            }}
            .severity-badge {{
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 8pt;
                font-weight: 600;
                text-transform: uppercase;
            }}
            .severity-critical {{
                background: #c53030;
                color: white;
            }}
            .severity-high {{
                background: #dd6b20;
                color: white;
            }}
            .severity-medium {{
                background: #d69e2e;
                color: white;
            }}
            .severity-low {{
                background: #38a169;
                color: white;
            }}
            .executive-summary {{
                background: #f7fafc;
                padding: 20px;
                border-left: 4px solid #3182ce;
                margin: 20px 0;
                font-size: 10pt;
            }}
            .findings-summary {{
                display: flex;
                justify-content: space-around;
                margin: 20px 0;
                padding: 15px;
                background: #f7fafc;
                border-radius: 8px;
            }}
            .finding-count {{
                text-align: center;
            }}
            .finding-count .count {{
                font-size: 24pt;
                font-weight: bold;
            }}
            .finding-count .label {{
                font-size: 9pt;
                text-transform: uppercase;
            }}
            .finding-count.critical .count {{ color: #c53030; }}
            .finding-count.high .count {{ color: #dd6b20; }}
            .finding-count.medium .count {{ color: #d69e2e; }}
            .finding-count.low .count {{ color: #38a169; }}
            .risk-matrix {{
                margin: 20px 0;
            }}
            .framework-bar {{
                background: #e2e8f0;
                height: 24px;
                border-radius: 4px;
                margin: 8px 0;
                position: relative;
            }}
            .framework-bar-fill {{
                height: 100%;
                border-radius: 4px;
                background: linear-gradient(90deg, #3182ce 0%, #2c5282 100%);
            }}
            .framework-bar-label {{
                position: absolute;
                right: 10px;
                top: 3px;
                font-size: 9pt;
                font-weight: 600;
                color: #2d3748;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 2px solid #e2e8f0;
                font-size: 9pt;
                color: #718096;
            }}
            .disclaimer {{
                background: #fffaf0;
                border: 1px solid #ed8936;
                padding: 15px;
                border-radius: 4px;
                margin: 20px 0;
                font-size: 9pt;
            }}
            .page-break {{
                page-break-before: always;
            }}
        </style>
    </head>
    <body>
        <!-- Cover Page -->
        <div class="cover-page">
            <div class="cover-title">Vendor Security<br>Assessment Report</div>
            <div class="cover-subtitle">Third-Party Risk Analysis &amp; Compliance Review</div>
            <div class="cover-meta">
                <p><strong>Report ID:</strong> {analysis_id[:16].upper()}</p>
                <p><strong>Assessment Date:</strong> {datetime.utcnow().strftime("%B %d, %Y")}</p>
                <p><strong>Frameworks Evaluated:</strong> {", ".join(job.get("frameworks", []))}</p>
                <p><strong>Classification:</strong> CONFIDENTIAL</p>
            </div>
        </div>

        <!-- Executive Summary -->
        <h1>1. Executive Summary</h1>
        <div class="section">
            <div class="executive-summary">
                {results.get("executive_summary", "No summary available.")}
            </div>

            <div class="score-container">
                <div class="score-box primary">
                    <div class="score-label">Overall Compliance</div>
                    <div class="score-value">{results.get("overall_compliance_score", 0):.0f}%</div>
                    <div class="score-sublabel">Composite Score</div>
                </div>
                <div class="score-box inherent">
                    <div class="score-label">Inherent Risk</div>
                    <div class="score-value" style="color: #c53030;">{inherent_score:.0f}</div>
                    <div class="score-sublabel">{inherent_level}</div>
                </div>
                <div class="score-box residual">
                    <div class="score-label">Residual Risk</div>
                    <div class="score-value" style="color: #d69e2e;">{residual_score:.0f}</div>
                    <div class="score-sublabel">{residual_level} ({risk_reduction:.0f}% reduction)</div>
                </div>
            </div>
        </div>

        <!-- Findings Overview -->
        <h1>2. Findings Overview</h1>
        <div class="section">
            <div class="findings-summary">
                <div class="finding-count critical">
                    <div class="count">{severity_counts["critical"]}</div>
                    <div class="label">Critical</div>
                </div>
                <div class="finding-count high">
                    <div class="count">{severity_counts["high"]}</div>
                    <div class="label">High</div>
                </div>
                <div class="finding-count medium">
                    <div class="count">{severity_counts["medium"]}</div>
                    <div class="label">Medium</div>
                </div>
                <div class="finding-count low">
                    <div class="count">{severity_counts["low"]}</div>
                    <div class="label">Low</div>
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th style="width: 80px;">Severity</th>
                        <th style="width: 120px;">Category</th>
                        <th>Finding</th>
                        <th>Recommendation</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(f'''
                    <tr>
                        <td><span class="severity-badge severity-{f.get("severity", "").lower()}">{f.get("severity", "").upper()}</span></td>
                        <td>{f.get("category", "").replace("_", " ").title()}</td>
                        <td><strong>{f.get("title", "")}</strong><br><span style="color: #718096; font-size: 8pt;">{f.get("description", "")}</span></td>
                        <td>{f.get("recommendation", "")}</td>
                    </tr>
                    ''' for f in findings)}
                </tbody>
            </table>
        </div>

        <!-- Framework Coverage -->
        <h1 class="page-break">3. Framework Coverage Analysis</h1>
        <div class="section">
            <table>
                <thead>
                    <tr>
                        <th>Framework</th>
                        <th style="width: 100px;">Coverage</th>
                        <th style="width: 80px;">Implemented</th>
                        <th style="width: 80px;">Partial</th>
                        <th style="width: 80px;">Missing</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(f'''
                    <tr>
                        <td><strong>{fw.get("framework", "")}</strong></td>
                        <td>
                            <div class="framework-bar">
                                <div class="framework-bar-fill" style="width: {fw.get("coverage_percentage", 0)}%;"></div>
                                <span class="framework-bar-label">{fw.get("coverage_percentage", 0):.0f}%</span>
                            </div>
                        </td>
                        <td style="text-align: center; color: #38a169; font-weight: 600;">{fw.get("implemented_controls", 0)}</td>
                        <td style="text-align: center; color: #d69e2e; font-weight: 600;">{fw.get("partial_controls", 0)}</td>
                        <td style="text-align: center; color: #c53030; font-weight: 600;">{fw.get("missing_controls", 0)}</td>
                    </tr>
                    ''' for fw in results.get("frameworks", []))}
                </tbody>
            </table>
        </div>

        {"" if not results.get("risk_assessment") else f'''
        <!-- Risk Assessment -->
        <h1>4. Risk Assessment</h1>
        <div class="section">
            <table>
                <thead>
                    <tr>
                        <th>Risk Metric</th>
                        <th>Score</th>
                        <th>Rating</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Inherent Risk</strong></td>
                        <td style="text-align: center; font-weight: 600;">{inherent_score:.1f}</td>
                        <td><span class="severity-badge severity-high">{inherent_level}</span></td>
                        <td>Risk level before considering existing controls</td>
                    </tr>
                    <tr>
                        <td><strong>Residual Risk</strong></td>
                        <td style="text-align: center; font-weight: 600;">{residual_score:.1f}</td>
                        <td><span class="severity-badge severity-medium">{residual_level}</span></td>
                        <td>Risk level after accounting for implemented controls</td>
                    </tr>
                    <tr>
                        <td><strong>Control Effectiveness</strong></td>
                        <td style="text-align: center; font-weight: 600;">{risk_reduction:.1f}%</td>
                        <td><span class="severity-badge severity-low">Moderate</span></td>
                        <td>Percentage of inherent risk mitigated by controls</td>
                    </tr>
                </tbody>
            </table>
        </div>
        '''}

        <!-- Disclaimer -->
        <div class="disclaimer">
            <strong>Disclaimer:</strong> This assessment is based on the documentation provided and represents a point-in-time evaluation.
            Findings should be validated with the vendor and reassessed periodically. This report does not constitute legal advice
            or guarantee compliance with any regulatory framework.
        </div>

        <!-- Footer -->
        <div class="footer">
            <p><strong>Generated by:</strong> Vendor Security Analyzer</p>
            <p><strong>Report Generated:</strong> {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
            <p style="margin-top: 10px;">This document contains confidential information intended solely for the authorized recipient(s).
            Unauthorized distribution, copying, or disclosure is strictly prohibited.</p>
        </div>
    </body>
    </html>
    """

    # Generate PDF
    html = HTML(string=html_content)
    return html.write_pdf()
