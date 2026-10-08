from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.models.response import AnalysisResponse
from app.services.analyzer import (
    AnalyzerConfigurationError,
    LogValidationError,
    MissingRepositoryError,
    ModelProviderError,
    MAX_LOG_BYTES,
    MAX_TOTAL_LOG_BYTES,
    MAX_LOG_FILES,
    parse_uploaded_logs,
    analyze_logs as run_analysis,
)

router = APIRouter()


@router.post(
    "/analyze-logs",
    response_model=AnalysisResponse,
    summary="Analyze uploaded logs against the dummy source repository",
)
def analyze_logs(
    files: list[UploadFile] = File(...),
    application_name: str | None = Form(None, max_length=200),
    environment_name: str | None = Form(None, max_length=200),
    incident_details: str | None = Form(None, max_length=2_000),
):
    if len(files) > MAX_LOG_FILES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Upload no more than {MAX_LOG_FILES} log files.",
        )

    uploaded: list[tuple[str | None, bytes]] = []
    total_size = 0
    for upload in files:
        content = upload.file.read(MAX_LOG_BYTES + 1)
        total_size += len(content)
        if len(content) > MAX_LOG_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{upload.filename or 'Uploaded file'} exceeds the per-file size limit.",
            )
        if total_size > MAX_TOTAL_LOG_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    "Combined log size exceeds the "
                    f"{MAX_TOTAL_LOG_BYTES}-byte limit."
                ),
            )
        uploaded.append((upload.filename, content))

    try:
        parsed_logs = parse_uploaded_logs(uploaded)
        return run_analysis(
            parsed_logs,
            incident_context={
                "application_name": application_name or "",
                "environment_name": environment_name or "",
                "incident_details": incident_details or "",
            },
        )
    except LogValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except AnalyzerConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except MissingRepositoryError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    except ModelProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
