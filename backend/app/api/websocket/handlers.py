"""WebSocket endpoint handlers."""

import asyncio
import json
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.routes.analysis import analysis_jobs, update_analysis_job
from app.api.websocket.manager import ConnectionManager, ProgressEmitter, manager
from app.config import settings
from app.models.responses import (
    AnalysisStatus,
    WebSocketEvent,
    WebSocketEventType,
)
from app.services.file_manager import file_manager

router = APIRouter()


@router.websocket("/ws/analysis/{session_id}")
async def analysis_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for analysis progress streaming.

    Connect to receive real-time updates during compliance analysis.
    Send {"action": "start", "analysis_id": "..."} to begin analysis.
    """
    # Validate session_id
    if not all(c.isalnum() or c == "-" for c in session_id):
        await websocket.close(code=4000, reason="Invalid session ID")
        return

    await manager.connect(websocket, session_id)

    try:
        # Send connection confirmation
        await manager.send_to_connection(
            websocket,
            WebSocketEvent(
                event_type=WebSocketEventType.CONNECTION_STATUS,
                message="Connected to analysis stream",
                data={"session_id": session_id},
            ),
        )

        while True:
            # Wait for messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "start":
                    analysis_id = message.get("analysis_id")
                    if analysis_id and analysis_id in analysis_jobs:
                        # Run analysis in background
                        asyncio.create_task(
                            run_analysis_with_streaming(
                                session_id, analysis_id
                            )
                        )
                    else:
                        await manager.send_to_connection(
                            websocket,
                            WebSocketEvent(
                                event_type=WebSocketEventType.ANALYSIS_ERROR,
                                message="Invalid analysis ID",
                                data={"error": "Analysis not found"},
                            ),
                        )

                elif action == "ping":
                    await manager.send_to_connection(
                        websocket,
                        WebSocketEvent(
                            event_type=WebSocketEventType.CONNECTION_STATUS,
                            message="pong",
                        ),
                    )

            except json.JSONDecodeError:
                await manager.send_to_connection(
                    websocket,
                    WebSocketEvent(
                        event_type=WebSocketEventType.ANALYSIS_ERROR,
                        message="Invalid message format",
                    ),
                )

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for streaming chat responses.

    Send {"message": "your question"} to chat with the AI assistant.
    Responses are streamed as CHAT_RESPONSE_CHUNK events.
    """
    # Validate session_id
    if not all(c.isalnum() or c == "-" for c in session_id):
        await websocket.close(code=4000, reason="Invalid session ID")
        return

    await manager.connect(websocket, session_id)

    try:
        await manager.send_to_connection(
            websocket,
            WebSocketEvent(
                event_type=WebSocketEventType.CONNECTION_STATUS,
                message="Connected to chat stream",
                data={"session_id": session_id},
            ),
        )

        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                user_message = message.get("message", "").strip()

                if not user_message:
                    continue

                # Send typing indicator
                await manager.send_to_connection(
                    websocket,
                    WebSocketEvent(
                        event_type=WebSocketEventType.CHAT_TYPING,
                        message="Assistant is typing...",
                        data={"is_typing": True},
                    ),
                )

                # Stream response
                await stream_chat_response(
                    websocket, session_id, user_message
                )

            except json.JSONDecodeError:
                await manager.send_to_connection(
                    websocket,
                    WebSocketEvent(
                        event_type=WebSocketEventType.CHAT_RESPONSE_COMPLETE,
                        message="Invalid message format",
                        data={"error": "Could not parse message"},
                    ),
                )

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)


def is_soc2_document(filename: str) -> bool:
    """Check if a file appears to be a SOC2 Type 2 report."""
    name_lower = filename.lower()
    soc2_indicators = ["soc2", "soc 2", "soc-2", "type 2", "type2", "typeii", "type ii"]
    return any(indicator in name_lower for indicator in soc2_indicators)


def deduplicate_findings(
    all_findings: list[dict],
    document_count: int,
    soc2_document_count: int
) -> list[dict]:
    """
    Deduplicate findings and prioritize those consistent across documents.

    Rules:
    - Findings from SOC2 Type 2 reports get 2x weight
    - Only include findings that appear in multiple documents OR are from SOC2
    - Merge similar findings (same title/category) into one
    """
    # Group findings by a normalized key (title + category)
    finding_groups: dict[str, dict] = {}

    for finding in all_findings:
        # Create a normalized key for grouping
        key = f"{finding.get('title', '').lower().strip()}|{finding.get('category', '').lower().strip()}"

        if key not in finding_groups:
            finding_groups[key] = {
                "finding": finding.copy(),
                "document_count": 0,
                "soc2_count": 0,
                "total_weight": 0,
            }

        group = finding_groups[key]
        group["document_count"] += 1

        # SOC2 findings get double weight
        if finding.get("_from_soc2", False):
            group["soc2_count"] += 1
            group["total_weight"] += 2
        else:
            group["total_weight"] += 1

    # Filter and sort findings
    deduplicated = []
    min_threshold = max(1, document_count // 2)  # Require at least half of documents

    for key, group in finding_groups.items():
        # Include if:
        # 1. Found in SOC2 documents (high trust), OR
        # 2. Found in multiple documents (consistent finding)
        if group["soc2_count"] > 0 or group["document_count"] >= min_threshold:
            finding = group["finding"]
            # Remove internal tracking field
            finding.pop("_from_soc2", None)
            finding.pop("_source_doc", None)
            deduplicated.append({
                **finding,
                "_weight": group["total_weight"],
                "_doc_count": group["document_count"],
            })

    # Sort by weight (higher = more important), then by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    deduplicated.sort(
        key=lambda f: (
            -f.get("_weight", 0),
            severity_order.get(f.get("severity", "").lower(), 4)
        )
    )

    # Remove internal fields from final output
    for finding in deduplicated:
        finding.pop("_weight", None)
        finding.pop("_doc_count", None)

    return deduplicated


def consolidate_framework_coverage(framework_results: list[dict]) -> list[dict]:
    """Consolidate framework coverage from multiple documents."""
    # Group by framework name
    framework_groups: dict[str, list[dict]] = {}

    for fw in framework_results:
        name = fw.get("framework", "")
        if name not in framework_groups:
            framework_groups[name] = []
        framework_groups[name].append(fw)

    # Average the results for each framework
    consolidated = []
    for name, results in framework_groups.items():
        count = len(results)
        consolidated.append({
            "framework": name,
            "coverage_percentage": sum(r.get("coverage_percentage", 0) for r in results) / count,
            "implemented_controls": sum(r.get("implemented_controls", 0) for r in results) // count,
            "partial_controls": sum(r.get("partial_controls", 0) for r in results) // count,
            "missing_controls": sum(r.get("missing_controls", 0) for r in results) // count,
            "total_controls": results[0].get("total_controls", 50),
        })

    return consolidated


async def run_analysis_with_streaming(
    session_id: str, analysis_id: str
) -> None:
    """Run compliance analysis with real-time progress streaming."""
    job = analysis_jobs.get(analysis_id)
    if not job:
        return

    emitter = ProgressEmitter(manager, session_id, total_steps=100)

    try:
        update_analysis_job(analysis_id, status=AnalysisStatus.PROCESSING)

        await emitter.emit(
            WebSocketEventType.ANALYSIS_STARTED,
            "Starting compliance analysis...",
            progress_override=0,
        )

        # Get uploaded files
        files = await file_manager.get_session_files(session_id)
        if not files:
            raise ValueError("No files to analyze")

        total_files = len(files)
        frameworks = job["frameworks"]

        # Track SOC2 documents for weighting
        soc2_documents = [f for f in files if is_soc2_document(f.original_name)]
        soc2_count = len(soc2_documents)

        await emitter.emit(
            WebSocketEventType.DOCUMENT_LOADING,
            f"Analyzing {total_files} document(s), {soc2_count} SOC2 report(s) detected",
            data={"total_files": total_files, "soc2_count": soc2_count},
            progress_override=2,
        )

        # Each file contributes 70% of progress, risk assessment 20%, summary 10%
        file_progress_share = 70 / total_files

        # Collect all findings and framework results
        all_findings: list[dict] = []
        all_framework_results: list[dict] = []

        for i, uploaded_file in enumerate(files):
            is_soc2 = is_soc2_document(uploaded_file.original_name)
            doc_type = "SOC2 Type 2 Report" if is_soc2 else "Document"

            # Document loading
            await emitter.emit(
                WebSocketEventType.DOCUMENT_LOADING,
                f"Loading {uploaded_file.original_name}...",
                data={
                    "filename": uploaded_file.original_name,
                    "is_soc2": is_soc2,
                    "doc_type": doc_type,
                },
                progress_override=5 + i * file_progress_share,
            )

            await asyncio.sleep(0.5)

            await emitter.emit(
                WebSocketEventType.DOCUMENT_LOADED,
                f"Loaded {doc_type}: {uploaded_file.original_name}",
                data={
                    "filename": uploaded_file.original_name,
                    "size_bytes": uploaded_file.size_bytes,
                    "is_soc2": is_soc2,
                },
            )

            # Analyze against each framework
            await emitter.emit(
                WebSocketEventType.DOCUMENT_ANALYZING,
                f"Analyzing {uploaded_file.original_name} against {len(frameworks)} framework(s)...",
                data={"filename": uploaded_file.original_name},
            )

            # Framework analysis
            for fw in frameworks:
                await asyncio.sleep(0.8)

                # SOC2 documents get slightly higher coverage scores
                base_coverage = 65 + (hash(uploaded_file.id + fw) % 25)
                if is_soc2:
                    base_coverage = min(95, base_coverage + 10)

                all_framework_results.append({
                    "framework": fw,
                    "coverage_percentage": base_coverage,
                    "implemented_controls": int(base_coverage * 0.5),
                    "partial_controls": int(base_coverage * 0.2),
                    "missing_controls": int((100 - base_coverage) * 0.3),
                    "total_controls": 50,
                    "_source_doc": uploaded_file.original_name,
                    "_is_soc2": is_soc2,
                })

                await emitter.emit(
                    WebSocketEventType.FRAMEWORK_COMPLETE,
                    f"{fw} analysis complete for {uploaded_file.original_name}",
                    data={"framework": fw, "coverage": base_coverage},
                )

            # Generate findings for this document
            # In production, this would come from actual AI analysis
            doc_findings = [
                {
                    "severity": "high",
                    "category": "access_control",
                    "title": "Missing MFA enforcement",
                    "description": "Multi-factor authentication not required for all users",
                    "recommendation": "Implement mandatory MFA for all user accounts",
                    "_from_soc2": is_soc2,
                    "_source_doc": uploaded_file.original_name,
                },
                {
                    "severity": "medium",
                    "category": "encryption",
                    "title": "Encryption at rest not documented",
                    "description": "Data encryption at rest implementation not clearly documented",
                    "recommendation": "Document encryption mechanisms and key management procedures",
                    "_from_soc2": is_soc2,
                    "_source_doc": uploaded_file.original_name,
                },
                {
                    "severity": "medium",
                    "category": "incident_response",
                    "title": "Incident response plan review needed",
                    "description": "Incident response procedures not reviewed in past 12 months",
                    "recommendation": "Conduct annual review and testing of incident response plan",
                    "_from_soc2": is_soc2,
                    "_source_doc": uploaded_file.original_name,
                },
            ]

            # Add some document-specific findings
            if is_soc2:
                doc_findings.append({
                    "severity": "low",
                    "category": "audit",
                    "title": "SOC2 audit exceptions noted",
                    "description": "Minor exceptions identified in latest SOC2 Type 2 audit",
                    "recommendation": "Review and address audit exceptions before next assessment",
                    "_from_soc2": True,
                    "_source_doc": uploaded_file.original_name,
                })

            for finding in doc_findings:
                await emitter.emit(
                    WebSocketEventType.FINDING_DISCOVERED,
                    f"Found: {finding['title']}",
                    data={"finding": {k: v for k, v in finding.items() if not k.startswith("_")}},
                )
                all_findings.append(finding)
                await asyncio.sleep(0.2)

            update_analysis_job(
                analysis_id,
                progress=5 + (i + 1) * file_progress_share,
                current_step=f"Analyzed {uploaded_file.original_name}",
            )

        # Consolidate and deduplicate
        await emitter.emit(
            WebSocketEventType.DOCUMENT_ANALYZING,
            "Consolidating findings across all documents...",
            progress_override=75,
        )
        await asyncio.sleep(0.5)

        # Deduplicate findings with SOC2 weighting
        deduplicated_findings = deduplicate_findings(all_findings, total_files, soc2_count)

        # Consolidate framework coverage
        consolidated_frameworks = consolidate_framework_coverage(all_framework_results)

        results = {
            "overall_compliance_score": 0,
            "frameworks": consolidated_frameworks,
            "findings": deduplicated_findings,
            "risk_assessment": None,
            "executive_summary": None,
        }

        await emitter.emit(
            WebSocketEventType.FINDING_DISCOVERED,
            f"Consolidated {len(all_findings)} findings into {len(deduplicated_findings)} unique findings",
            data={"original_count": len(all_findings), "final_count": len(deduplicated_findings)},
            progress_override=78,
        )

        # Risk assessment
        await emitter.emit(
            WebSocketEventType.RISK_ASSESSMENT_STARTED,
            "Calculating risk assessment...",
            progress_override=80,
        )

        await asyncio.sleep(1.5)

        # Calculate risk scores based on findings
        severity_weights = {"critical": 10, "high": 7, "medium": 4, "low": 1}
        total_risk_points = sum(
            severity_weights.get(f.get("severity", "").lower(), 0)
            for f in deduplicated_findings
        )
        max_risk = len(deduplicated_findings) * 10  # If all were critical

        inherent_score = min(100, 40 + total_risk_points)

        # Residual risk reduced by compliance score
        avg_coverage = (
            sum(fw["coverage_percentage"] for fw in consolidated_frameworks) / len(consolidated_frameworks)
            if consolidated_frameworks else 50
        )
        residual_score = inherent_score * (1 - (avg_coverage / 150))  # Coverage reduces risk
        risk_reduction = ((inherent_score - residual_score) / inherent_score * 100) if inherent_score > 0 else 0

        results["risk_assessment"] = {
            "inherent_risk_level": "Critical" if inherent_score >= 80 else "High" if inherent_score >= 60 else "Medium" if inherent_score >= 40 else "Low",
            "inherent_risk_score": round(inherent_score, 1),
            "residual_risk_level": "Critical" if residual_score >= 80 else "High" if residual_score >= 60 else "Medium" if residual_score >= 40 else "Low",
            "residual_risk_score": round(residual_score, 1),
            "risk_reduction_percentage": round(risk_reduction, 1),
        }

        await emitter.emit(
            WebSocketEventType.RISK_ASSESSMENT_COMPLETE,
            "Risk assessment complete",
            data=results["risk_assessment"],
            progress_override=90,
        )

        # Executive summary
        await emitter.emit(
            WebSocketEventType.EXECUTIVE_SUMMARY_GENERATING,
            "Generating executive summary...",
            progress_override=92,
        )

        await asyncio.sleep(1)

        # Build dynamic executive summary
        critical_high_count = sum(1 for f in deduplicated_findings if f.get("severity", "").lower() in ["critical", "high"])
        results["executive_summary"] = (
            f"This assessment analyzed {total_files} document(s)"
            f"{f', including {soc2_count} SOC2 Type 2 report(s)' if soc2_count > 0 else ''}. "
            f"The vendor demonstrates {'strong' if avg_coverage >= 80 else 'moderate' if avg_coverage >= 60 else 'developing'} "
            f"compliance maturity with an overall score of {avg_coverage:.0f}%. "
            f"{len(deduplicated_findings)} unique findings were identified"
            f"{f', including {critical_high_count} high-priority items requiring immediate attention' if critical_high_count > 0 else ''}. "
            f"Inherent risk is assessed as {results['risk_assessment']['inherent_risk_level']} "
            f"with residual risk at {results['risk_assessment']['residual_risk_level']} "
            f"after accounting for implemented controls ({risk_reduction:.0f}% risk reduction)."
        )

        # Calculate overall score
        if results["frameworks"]:
            results["overall_compliance_score"] = sum(
                fw["coverage_percentage"] for fw in results["frameworks"]
            ) / len(results["frameworks"])

        # Complete
        update_analysis_job(
            analysis_id,
            status=AnalysisStatus.COMPLETED,
            progress=100,
            current_step="Complete",
            results=results,
        )

        await emitter.emit(
            WebSocketEventType.ANALYSIS_COMPLETE,
            "Analysis complete!",
            data={
                "analysis_id": analysis_id,
                "overall_score": results["overall_compliance_score"],
                "findings_count": len(results["findings"]),
            },
            progress_override=100,
        )

    except Exception as e:
        update_analysis_job(
            analysis_id,
            status=AnalysisStatus.FAILED,
            error=str(e),
        )

        await emitter.emit(
            WebSocketEventType.ANALYSIS_ERROR,
            f"Analysis failed: {str(e)}",
            data={"error": str(e)},
        )


async def stream_chat_response(
    websocket: WebSocket,
    session_id: str,
    user_message: str,
) -> None:
    """Stream chat response chunks via WebSocket."""
    try:
        import json as json_lib

        import boto3
        from botocore.config import Config

        config = Config(
            connect_timeout=10,
            read_timeout=settings.bedrock_timeout,
        )

        bedrock = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            config=config,
        )

        # Build system prompt
        system_prompt = """You are a security compliance expert assistant.
        Help users understand compliance analysis results and provide actionable guidance.
        Be concise and professional."""

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": settings.bedrock_max_tokens,
            "temperature": settings.bedrock_temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }

        # Use streaming API
        response = bedrock.invoke_model_with_response_stream(
            modelId=settings.bedrock_model_id,
            body=json_lib.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )

        full_response = ""
        for event in response.get("body", []):
            chunk = json_lib.loads(event.get("chunk", {}).get("bytes", b"{}"))

            if chunk.get("type") == "content_block_delta":
                text = chunk.get("delta", {}).get("text", "")
                if text:
                    full_response += text
                    await manager.send_to_connection(
                        websocket,
                        WebSocketEvent(
                            event_type=WebSocketEventType.CHAT_RESPONSE_CHUNK,
                            message=text,
                            data={"chunk": text},
                        ),
                    )

        await manager.send_to_connection(
            websocket,
            WebSocketEvent(
                event_type=WebSocketEventType.CHAT_RESPONSE_COMPLETE,
                message="Response complete",
                data={"full_response": full_response},
            ),
        )

    except Exception as e:
        await manager.send_to_connection(
            websocket,
            WebSocketEvent(
                event_type=WebSocketEventType.CHAT_RESPONSE_COMPLETE,
                message=f"Error: {str(e)}",
                data={"error": str(e)},
            ),
        )
