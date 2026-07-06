"""Shared instrumentation seam for every protocol client (REST, GraphQL, gRPC, ...).

Every protocol call is wrapped with this helper so latency, payload size,
error/retry outcome, and tracing are captured identically regardless of
protocol -- write the instrumentation once, reuse for all 10 protocols.
"""

import functools
import json
import time

from shopsmart.config import get_max_retries
from shopsmart.fault_injector import ProtocolFault
from shopsmart.metrics import ProtocolCallResult, SystemMetrics

_active_metrics: SystemMetrics | None = None


def set_active_metrics(metrics: SystemMetrics | None) -> None:
    """Set the shared SystemMetrics instance every @timed_protocol_call records into.

    Protocol client functions are decorated at import time, before
    build_system() creates the SystemMetrics instance, so the decorator reads
    this module-level reference at call time rather than at decoration time.
    """
    global _active_metrics
    _active_metrics = metrics


def _payload_bytes(payload) -> int:
    try:
        return len(json.dumps(payload, default=str).encode("utf-8"))
    except Exception:
        return len(str(payload).encode("utf-8"))


def timed_protocol_call(protocol_name: str):
    """Decorator: times a protocol client call, retries on failure, records metrics + traces.

    The wrapped function should return the response payload (dict/list) on
    success and raise on failure (including `ProtocolFault` from fault_injector).
    Metrics are recorded into whatever SystemMetrics was set via
    `set_active_metrics()` at call time (may be None, e.g. in standalone tests).
    """

    def decorator(func):
        try:
            from langsmith import traceable

            traced_func = traceable(name=f"protocol.{protocol_name.lower()}", run_type="tool")(func)
        except Exception:
            traced_func = func

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            max_retries = get_max_retries(protocol_name)
            attempt = 0
            last_exc = None

            while attempt <= max_retries:
                start = time.perf_counter()
                try:
                    lf_span = None
                    try:
                        from langfuse import get_client

                        lf_span = get_client().start_as_current_span(
                            name=f"protocol.{protocol_name.lower()}"
                        )
                        lf_span.__enter__()
                    except Exception:
                        lf_span = None

                    try:
                        result = traced_func(*args, **kwargs)
                    finally:
                        if lf_span is not None:
                            try:
                                lf_span.__exit__(None, None, None)
                            except Exception:
                                pass

                    latency_ms = (time.perf_counter() - start) * 1000
                    if _active_metrics is not None:
                        _active_metrics.record_protocol_call(
                            ProtocolCallResult(
                                protocol=protocol_name,
                                latency_ms=latency_ms,
                                payload_bytes=_payload_bytes(result),
                                success=True,
                                error_type=None,
                                retry_count=attempt,
                            )
                        )
                    return result
                except Exception as exc:
                    latency_ms = (time.perf_counter() - start) * 1000
                    error_type = exc.mode if isinstance(exc, ProtocolFault) else type(exc).__name__
                    if _active_metrics is not None:
                        _active_metrics.record_protocol_call(
                            ProtocolCallResult(
                                protocol=protocol_name,
                                latency_ms=latency_ms,
                                payload_bytes=0,
                                success=False,
                                error_type=error_type,
                                retry_count=attempt,
                            )
                        )
                    last_exc = exc
                    attempt += 1

            raise last_exc

        return wrapper

    return decorator
