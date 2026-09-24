"""Unified error envelope (arch. §8.1):

    { "error": { "code": "...", "message": "...", "fields": {...} } }
"""
import logging

from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

_STATUS_TO_CODE = {
    400: "VALIDATION_ERROR",
    401: "AUTH_INVALID",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    429: "RATE_LIMITED",
    500: "SERVER_ERROR",
}


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None  # unhandled — Django's 500 path logs it

    code = _STATUS_TO_CODE.get(response.status_code, "SERVER_ERROR")
    detail = response.data

    fields = {}
    message = "Request failed."
    if isinstance(detail, dict):
        extracted = {}
        for key, value in detail.items():
            if key in ("detail", "non_field_errors"):
                message = str(value[0] if isinstance(value, list) and value else value)
            else:
                extracted[key] = value
        if extracted:
            fields = extracted
    elif isinstance(detail, list) and detail:
        message = str(detail[0])

    response.data = {"error": {"code": code, "message": message, "fields": fields}}
    return response
