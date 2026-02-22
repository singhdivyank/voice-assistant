"""Monitoring setup with OpenTelemetry and LangSmith"""

import inspect
import logging
import os
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional
import time

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from langsmith import Client as LangSmithClient
from langsmith.run_helpers import traceable

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TelemetryManager:
    """Manages OpenTelemetry instrumentation."""

    _instance: Optional["TelemetryManager"] = None
    _initialized: bool = None

    def __new__(cls) -> "TelemetryManager":
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.tracer: Optional[trace.Tracer] = None
        self.meter: Optional[metrics.Meter] = None
        self._counters: dict = {}
        self._histograms: dict = {}
    
    def initialize(self) -> None:
        """Initialize OpenTelemetry providers and exporters."""

        if not settings.otel_enabled:
            logger.info("OpenTelemetry disabled")
            return
        
        resource = Resource.create({SERVICE_NAME: settings.otel_service_name})
        tracer_provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)
        self.tracer = trace.get_tracer(__name__)
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=settings.otel_exporter_endpoint),
            export_interval_millis=60000
        )
        meterProvider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meterProvider)
        self.meter = metrics.get_meter(__name__)

        self._setup_metrics()
        self._initialized = True
        logger.info("OpenTelemetry initialized successfully")

    def _setup_metrics(self) -> None:
        """Setup custom metrics."""

        if not self.meter:
            return
        
        self._counters["session_created"] = self.meter.create_counter(
            "docjarvis.session.created",
            description="Number of consultation sessions created"
        )
        self._counters["diagnosis_completed"] = self.meter.create_counter(
            "docjarvis.session.completed",
            description="Number of consultation sessions completed"
        )
        self._counters["llm_requests"] = self.meter.create_counter(
            "docjarvis.llm.requests",
            description="Number of LLM API requests"
        )
        self._counters["llm_errors"] = self.meter.create_counter(
            "docjarvis.llm.errors",
            description="Number of LLM API errors"
        )
        self._histograms["llm_latency"] = self.meter.create_histogram(
            "docjarvis.llm.latency",
            description="LLM request latency in milliseconds",
            unit="ms"
        )
        self._histograms["session_duration"] = self.meter.create_histogram(
            "docjarvis.session.duration",
            description="Consultation session duration in seconds",
            unit="s"
        )
    
    def increment_counter(self, name: str, value: int = 1, attributes: dict = None) -> None:
        """Increment with a counter metric."""

        if name in self._counters:
            self._counters[name].add(value, attributes or {})
    
    def record_histogram(self, name: str, value: float, attributes: dict = None) -> None:
        """Record a histogram value."""

        if name in self._histograms:
            self._histograms[name].record(value, attributes or {})
    
    @contextmanager
    def span(self, name: str, attributes: dict = None):
        """Create a traced span."""

        if not self.tracer:
            yield None
        
        with self.tracer.start_as_current_span(name, attributes=attributes) as span:
            yield span
    
    def instrument_fastapi(self, app) -> None:
        """Instrument FastAPI application."""

        if settings.otel_enabled:
            FastAPIInstrumentor.instrument_app(app)
            HTTPXClientInstrumentor().instrument()


class LangSmithManager:
    """Manages LangSmith tracing for LLM calls."""

    _instance: Optional["LangSmithManager"] = None

    def __new__(cls) -> "LangSmithManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.client: Optional[LangSmithClient] = None
        self.enabled = bool(settings.langsmith_api_key and settings.langsmith_tracing)
        self.initialize()
    
    def initialize(self) -> None:
        """Initialize LangSmith client."""

        if not self.enabled:
            logger.info("LangSmith tracing disabled")
            return 
        
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        logger.info(f"LangSmith initialized for project: {settings.langsmith_project}")
    
    def trace_llm_call(self, name: str = "llm_call") -> Callable:
        """Decorator for tracing LLM calls."""

        def decorator(func: Callable) -> Callable:
            if not self.enabled:
                return func
            return traceable(name=name, run_type="llm")(func)
        return decorator
    
    def trace_chain(self, name: str = "chain"):
        """Decorator for tracing chain operations."""

        def decorator(func: Callable) -> Callable:
            if not self.enabled:
                return func
            return traceable(name=name, run_type="chain")(func)
        return decorator

def timed_operation(operation_name: str):
    """Decorator to time operations and record metrics."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            telemetry = TelemetryManager()
            start = time.perf_counter()

            try:
                with telemetry.span(operation_name):
                    result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                telemetry.record_histogram("llm_latency", duration_ms, {"operation": operation_name})
                return result
            except Exception as e:
                telemetry.increment_counter("llm_errors", attributes={"operation": operation_name})
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            telemetry = TelemetryManager()
            start = time.perf_counter()

            try:
                with telemetry.span(operation_name):
                    result = func(*args, **kwargs)
                
                duration_ms = (time.perf_counter() - start) * 1000
                telemetry.record_histogram("llm_latency", duration_ms, {"operation": operation_name})
                return result
            except Exception as e:
                telemetry.increment_counter("llm_errors", attributes={"operation": operation_name})
                raise
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


telemetry = TelemetryManager()
langsmith = LangSmithManager()


def setup_monitoring() -> None:
    """Initialize all monitoring systems."""

    telemetry.initialize()
    langsmith.initialize()
