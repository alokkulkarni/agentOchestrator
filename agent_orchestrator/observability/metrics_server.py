"""
Prometheus metrics HTTP server for Agent Orchestrator.

Runs a simple HTTP server that exposes Prometheus metrics
on a dedicated port for scraping.
"""

import logging
from threading import Thread
from prometheus_client import start_http_server, REGISTRY
from .metrics import orchestrator_metrics

logger = logging.getLogger(__name__)


class MetricsServer:
    """HTTP server for exposing Prometheus metrics."""

    def __init__(self, port: int = 9090, addr: str = "0.0.0.0"):
        """
        Initialize metrics server.

        Args:
            port: Port to listen on (default: 9090)
            addr: Address to bind to (default: 0.0.0.0 for Docker)
        """
        self.port = port
        self.addr = addr
        self._server_thread = None
        self._started = False

    def start(self):
        """Start the metrics HTTP server in a background thread."""
        if self._started:
            logger.warning(f"Metrics server already started on {self.addr}:{self.port}")
            return

        try:
            # Start HTTP server for Prometheus scraping
            start_http_server(port=self.port, addr=self.addr, registry=orchestrator_metrics.registry)
            self._started = True
            logger.info(f"✅ Prometheus metrics server started on {self.addr}:{self.port}")
            logger.info(f"   Metrics endpoint: http://{self.addr}:{self.port}/metrics")
        except Exception as e:
            logger.error(f"❌ Failed to start metrics server: {e}")
            raise

    def start_in_background(self):
        """Start the metrics server in a background thread (non-blocking)."""
        if self._started:
            logger.warning(f"Metrics server already started on {self.addr}:{self.port}")
            return

        def run_server():
            try:
                start_http_server(port=self.port, addr=self.addr, registry=orchestrator_metrics.registry)
                self._started = True
                logger.info(f"✅ Prometheus metrics server started on {self.addr}:{self.port}")
                logger.info(f"   Metrics endpoint: http://{self.addr}:{self.port}/metrics")
            except Exception as e:
                logger.error(f"❌ Failed to start metrics server: {e}")

        self._server_thread = Thread(target=run_server, daemon=True)
        self._server_thread.start()

    def is_running(self) -> bool:
        """Check if the metrics server is running."""
        return self._started


# Global metrics server instance
metrics_server = MetricsServer()
