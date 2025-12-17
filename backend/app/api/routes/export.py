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

    # Build HTML report
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Compliance Analysis Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                color: #333;
            }}
            h1 {{
                color: #1a365d;
                border-bottom: 2px solid #3182ce;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #2c5282;
                margin-top: 30px;
            }}
            .score-card {{
                background: #ebf8ff;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .score {{
                font-size: 48px;
                font-weight: bold;
                color: #2b6cb0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                border: 1px solid #e2e8f0;
                padding: 12px;
                text-align: left;
            }}
            th {{
                background: #edf2f7;
                font-weight: bold;
            }}
            .severity-critical {{
                color: #c53030;
                font-weight: bold;
            }}
            .severity-high {{
                color: #dd6b20;
            }}
            .severity-medium {{
                color: #d69e2e;
            }}
            .severity-low {{
                color: #38a169;
            }}
            .executive-summary {{
                background: #f7fafc;
                padding: 20px;
                border-left: 4px solid #3182ce;
                margin: 20px 0;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e2e8f0;
                font-size: 12px;
                color: #718096;
            }}
        </style>
    </head>
    <body>
        <h1>Vendor Security Compliance Report</h1>

        <p><strong>Analysis ID:</strong> {analysis_id}</p>
        <p><strong>Generated:</strong> {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</p>
        <p><strong>Frameworks:</strong> {", ".join(job.get("frameworks", []))}</p>

        <div class="score-card">
            <p>Overall Compliance Score</p>
            <p class="score">{results.get("overall_compliance_score", 0):.1f}%</p>
        </div>

        <h2>Executive Summary</h2>
        <div class="executive-summary">
            {results.get("executive_summary", "No summary available.")}
        </div>

        <h2>Framework Coverage</h2>
        <table>
            <tr>
                <th>Framework</th>
                <th>Coverage</th>
                <th>Implemented</th>
                <th>Partial</th>
                <th>Missing</th>
            </tr>
            {"".join(f'''
            <tr>
                <td>{fw.get("framework", "")}</td>
                <td>{fw.get("coverage_percentage", 0):.1f}%</td>
                <td>{fw.get("implemented_controls", 0)}</td>
                <td>{fw.get("partial_controls", 0)}</td>
                <td>{fw.get("missing_controls", 0)}</td>
            </tr>
            ''' for fw in results.get("frameworks", []))}
        </table>

        <h2>Findings</h2>
        <table>
            <tr>
                <th>Severity</th>
                <th>Category</th>
                <th>Title</th>
                <th>Recommendation</th>
            </tr>
            {"".join(f'''
            <tr>
                <td class="severity-{f.get("severity", "").lower()}">{f.get("severity", "").upper()}</td>
                <td>{f.get("category", "")}</td>
                <td>{f.get("title", "")}</td>
                <td>{f.get("recommendation", "")}</td>
            </tr>
            ''' for f in results.get("findings", []))}
        </table>

        {"" if not results.get("risk_assessment") else f'''
        <h2>Risk Assessment</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Inherent Risk</td>
                <td>{results["risk_assessment"].get("inherent_risk_level", "N/A")} ({results["risk_assessment"].get("inherent_risk_score", 0):.1f})</td>
            </tr>
            <tr>
                <td>Residual Risk</td>
                <td>{results["risk_assessment"].get("residual_risk_level", "N/A")} ({results["risk_assessment"].get("residual_risk_score", 0):.1f})</td>
            </tr>
            <tr>
                <td>Risk Reduction</td>
                <td>{results["risk_assessment"].get("risk_reduction_percentage", 0):.1f}%</td>
            </tr>
        </table>
        '''}

        <div class="footer">
            <p>Generated by Vendor Security Analyzer</p>
            <p>This report is confidential and intended for authorized recipients only.</p>
        </div>
    </body>
    </html>
    """

    # Generate PDF
    html = HTML(string=html_content)
    return html.write_pdf()
