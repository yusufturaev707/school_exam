"""
Every API error leaves the server in one shape: `{"code": "MACHINE_CODE", "message": "debug text"}`.
The frontend maps `code` to child-friendly Uzbek text and never shows `message`.
"""

import logging

from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

logger = logging.getLogger(__name__)

CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    406: "NOT_ACCEPTABLE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    429: "RATE_LIMITED",
}


class ApiError(APIException):
    """A business rule said no. Usage: `raise ApiError(409, "ATTEMPT_CLOSED")`."""

    def __init__(self, status_code: int, code: str, message: str | None = None):
        self.status_code = status_code
        self.code = code
        self.detail = message or code


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)  # also rolls back an open atomic block

    if response is None:
        # Unexpected bug. Log the traceback, but never send internals to the client.
        logger.exception("Unhandled API error", exc_info=exc)
        set_rollback()
        return Response({"code": "INTERNAL_ERROR", "message": "Internal error"}, status=500)

    if isinstance(exc, ValidationError):
        # The contract uses 422 for invalid input; DRF's default would be 400.
        response.status_code = 422
        response.data = {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "errors": exc.detail,
        }
    elif isinstance(exc, ApiError):
        response.data = {"code": exc.code, "message": exc.detail}
    else:
        code = CODE_BY_STATUS.get(response.status_code, "ERROR")
        response.data = {"code": code, "message": str(getattr(exc, "detail", exc))}
    return response
