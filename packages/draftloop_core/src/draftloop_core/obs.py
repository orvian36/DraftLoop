"""Observability: structlog logging + OTel span decorator.

Every public entry point in a package should be wrapped with
``@traced("<package>.<op>")``.
"""

from __future__ import annotations

import contextlib
import functools
import logging
import sys
from collections.abc import Callable
from typing import TypeVar, cast

import structlog
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

T = TypeVar("T")

_LOGGING_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog + OTel. Idempotent."""
    global _LOGGING_CONFIGURED
    log_level = getattr(logging, level.upper())

    logging.basicConfig(
        stream=sys.stderr,
        level=log_level,
        format="%(message)s",
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )

    if not _LOGGING_CONFIGURED:
        provider = TracerProvider(resource=Resource.create({"service.name": "draftloop"}))
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        # Tracer provider may already be set in test contexts; ignore.
        with contextlib.suppress(Exception):
            trace.set_tracer_provider(provider)
        _LOGGING_CONFIGURED = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))


def traced(span_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Wrap a callable in an OTel span. Re-raises exceptions after recording."""

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        tracer = trace.get_tracer("draftloop")

        @functools.wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> T:
            with tracer.start_as_current_span(span_name) as span:
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(trace.StatusCode.ERROR, str(exc))
                    raise

        return wrapper

    return decorator
