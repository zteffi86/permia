from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Any


def problem_response(
    request: Request,
    status: int,
    code: str,
    title: str,
    detail: Any,
) -> JSONResponse:
    """
    Return RFC 7807 Problem Details response

    https://datatracker.ietf.org/doc/html/rfc7807
    """
    return JSONResponse(
        status_code=status,
        content={
            "type": f"https://permia.is/errors/{code}",
            "title": title,
            "status": status,
            "code": code,
            "detail": detail,
            "correlation_id": getattr(request.state, "correlation_id", "unknown"),
        },
    )
