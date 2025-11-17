"""
OpenTelemetry Instrumentation Setup.

Provides:
- Automatic instrumentation for FastAPI
- Automatic instrumentation for SQLAlchemy
- Custom span creation utilities
- Metrics collection
- Export to OTLP/Jaeger
"""

import os
from typing import Optional
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY


# Prometheus metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total number of LLM requests',
    ['model', 'status', 'task_id']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total number of tokens used',
    ['model', 'token_type']
)

llm_cost_total = Counter(
    'llm_cost_usd_total',
    'Total cost in USD',
    ['model']
)

llm_latency_seconds = Histogram(
    'llm_latency_seconds',
    'LLM request latency in seconds',
    ['model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

task_duration_seconds = Histogram(
    'task_duration_seconds',
    'Task execution duration in seconds',
    ['status'],
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600]
)

task_success_total = Counter(
    'task_success_total',
    'Total number of successful tasks',
    ['status']
)

active_tasks = Gauge(
    'active_tasks',
    'Number of currently active tasks',
    ['status']
)


def setup_opentelemetry(
    service_name: str = "asa-backend",
    enable_console_export: bool = False,
    otlp_endpoint: Optional[str] = None
) -> None:
    """
    Set up OpenTelemetry instrumentation.

    Args:
        service_name: Name of the service
        enable_console_export: Enable console exporter for debugging
        otlp_endpoint: OTLP endpoint URL (e.g., "http://localhost:4317")
    """
    # Get configuration from environment
    otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    enable_otel = os.getenv("ENABLE_OPENTELEMETRY", "false").lower() == "true"

    if not enable_otel:
        print("OpenTelemetry disabled (set ENABLE_OPENTELEMETRY=true to enable)")
        return

    # Create resource
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "2.0.0",
    })

    # Set up tracing
    tracer_provider = TracerProvider(resource=resource)

    # Add OTLP exporter
    try:
        otlp_span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))
        print(f"OpenTelemetry traces exporting to: {otlp_endpoint}")
    except Exception as e:
        print(f"Warning: Failed to set up OTLP trace exporter: {e}")

    # Add console exporter for debugging
    if enable_console_export:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(tracer_provider)

    # Set up metrics
    try:
        otlp_metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
        metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=60000)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        print(f"OpenTelemetry metrics exporting to: {otlp_endpoint}")
    except Exception as e:
        print(f"Warning: Failed to set up OTLP metric exporter: {e}")


def instrument_fastapi(app) -> None:
    """
    Instrument FastAPI application.

    Args:
        app: FastAPI application instance
    """
    enable_otel = os.getenv("ENABLE_OPENTELEMETRY", "false").lower() == "true"

    if not enable_otel:
        return

    try:
        FastAPIInstrumentor.instrument_app(app)
        print("FastAPI instrumentation enabled")
    except Exception as e:
        print(f"Warning: Failed to instrument FastAPI: {e}")


def instrument_sqlalchemy(engine) -> None:
    """
    Instrument SQLAlchemy engine.

    Args:
        engine: SQLAlchemy engine instance
    """
    enable_otel = os.getenv("ENABLE_OPENTELEMETRY", "false").lower() == "true"

    if not enable_otel:
        return

    try:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        print("SQLAlchemy instrumentation enabled")
    except Exception as e:
        print(f"Warning: Failed to instrument SQLAlchemy: {e}")


def record_llm_metrics(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    latency_seconds: float,
    status: str,
    task_id: Optional[str] = None
) -> None:
    """
    Record LLM usage metrics to Prometheus.

    Args:
        model: Model name
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        cost_usd: Cost in USD
        latency_seconds: Request latency in seconds
        status: Request status
        task_id: Optional task ID
    """
    task_label = task_id or "none"

    # Record metrics
    llm_requests_total.labels(model=model, status=status, task_id=task_label).inc()
    llm_tokens_total.labels(model=model, token_type="prompt").inc(prompt_tokens)
    llm_tokens_total.labels(model=model, token_type="completion").inc(completion_tokens)
    llm_cost_total.labels(model=model).inc(cost_usd)
    llm_latency_seconds.labels(model=model).observe(latency_seconds)


def record_task_metrics(
    task_id: str,
    status: str,
    duration_seconds: float,
    success: bool
) -> None:
    """
    Record task execution metrics to Prometheus.

    Args:
        task_id: Task ID
        status: Task status
        duration_seconds: Task duration in seconds
        success: Whether task succeeded
    """
    # Record metrics
    task_duration_seconds.labels(status=status).observe(duration_seconds)

    if success:
        task_success_total.labels(status="success").inc()
    else:
        task_success_total.labels(status="failed").inc()


def get_prometheus_metrics() -> bytes:
    """
    Get Prometheus metrics in exposition format.

    Returns:
        Metrics in Prometheus format
    """
    return generate_latest(REGISTRY)
