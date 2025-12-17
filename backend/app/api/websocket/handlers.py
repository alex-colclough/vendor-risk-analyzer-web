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

        # Simulate analysis progress (in production, wrap actual analyzer)
        # Each file contributes 70% of progress, risk assessment 20%, summary 10%
        file_progress_share = 70 / total_files

        results = {
            "overall_compliance_score": 0,
            "frameworks": [],
            "findings": [],
            "risk_assessment": None,
            "executive_summary": None,
        }

        for i, uploaded_file in enumerate(files):
            # Document loading
            await emitter.emit(
                WebSocketEventType.DOCUMENT_LOADING,
                f"Loading {uploaded_file.original_name}...",
                data={"filename": uploaded_file.original_name},
                progress_override=i * file_progress_share,
            )

            await asyncio.sleep(0.5)  # Simulate loading time

            await emitter.emit(
                WebSocketEventType.DOCUMENT_LOADED,
                f"Loaded {uploaded_file.original_name}",
                data={
                    "filename": uploaded_file.original_name,
                    "size_bytes": uploaded_file.size_bytes,
                },
            )

            # Analyze against each framework
            await emitter.emit(
                WebSocketEventType.DOCUMENT_ANALYZING,
                f"Analyzing {uploaded_file.original_name}...",
                data={"filename": uploaded_file.original_name},
            )

            # Simulate framework analysis
            for fw in frameworks:
                await asyncio.sleep(1)  # Simulate analysis time

                # Add framework coverage (simulated)
                coverage = 65 + (hash(uploaded_file.id + fw) % 30)
                results["frameworks"].append({
                    "framework": fw,
                    "coverage_percentage": coverage,
                    "implemented_controls": int(coverage * 0.5),
                    "partial_controls": int(coverage * 0.2),
                    "missing_controls": int((100 - coverage) * 0.3),
                    "total_controls": 50,
                })

                await emitter.emit(
                    WebSocketEventType.FRAMEWORK_COMPLETE,
                    f"{fw} analysis complete",
                    data={"framework": fw, "coverage": coverage},
                )

            # Simulate finding discoveries
            sample_findings = [
                {
                    "severity": "high",
                    "category": "access_control",
                    "title": "Missing MFA enforcement",
                    "description": "Multi-factor authentication not required for all users",
                    "recommendation": "Implement mandatory MFA for all user accounts",
                },
                {
                    "severity": "medium",
                    "category": "encryption",
                    "title": "Encryption at rest not documented",
                    "description": "Data encryption at rest implementation not clearly documented",
                    "recommendation": "Document encryption mechanisms and key management procedures",
                },
            ]

            for finding in sample_findings:
                await emitter.emit(
                    WebSocketEventType.FINDING_DISCOVERED,
                    f"Found: {finding['title']}",
                    data={"finding": finding},
                )
                results["findings"].append(finding)
                await asyncio.sleep(0.3)

            update_analysis_job(
                analysis_id,
                progress=(i + 1) * file_progress_share,
                current_step=f"Analyzed {uploaded_file.original_name}",
            )

        # Risk assessment
        await emitter.emit(
            WebSocketEventType.RISK_ASSESSMENT_STARTED,
            "Calculating risk assessment...",
            progress_override=70,
        )

        await asyncio.sleep(2)  # Simulate risk calculation

        results["risk_assessment"] = {
            "inherent_risk_level": "high",
            "inherent_risk_score": 72.5,
            "residual_risk_level": "medium",
            "residual_risk_score": 38.2,
            "risk_reduction_percentage": 47.3,
        }

        await emitter.emit(
            WebSocketEventType.RISK_ASSESSMENT_COMPLETE,
            "Risk assessment complete",
            data=results["risk_assessment"],
            progress_override=85,
        )

        # Executive summary
        await emitter.emit(
            WebSocketEventType.EXECUTIVE_SUMMARY_GENERATING,
            "Generating executive summary...",
            progress_override=90,
        )

        await asyncio.sleep(1.5)  # Simulate summary generation

        results["executive_summary"] = (
            "The vendor demonstrates moderate compliance maturity with key strengths "
            "in data protection and incident response. Critical gaps exist in access "
            "control and third-party risk management. Immediate attention required for "
            "MFA implementation and security training programs."
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
