from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional
import httpx

from backend.app.collectors.base import BaseCollector

logger = logging.getLogger("netpath.collector.http")


class HttpCollector(BaseCollector):
    """
    Executes HTTP/HTTPS probe request, capturing precise timings (TTFB, total latency),
    HTTP status code, response headers, and redirect chains.
    """

    def __init__(self, timeout_seconds: float = 8.0, latency_threshold_ms: float = 1000.0) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self.latency_threshold_ms = latency_threshold_ms

    async def collect_async(self, url: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "url": url,
            "status_code": None,
            "ttfb_ms": 0.0,
            "total_latency_ms": 0.0,
            "response_bytes": 0,
            "redirect_count": 0,
            "headers": {},
            "status": "SUCCESS",
            "error_message": None,
        }

        # Track TTFB using httpx streaming
        client_timeout = httpx.Timeout(self.timeout_seconds, connect=self.timeout_seconds)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

        start_time = time.perf_counter()
        ttfb_recorded = False
        ttfb_ms = 0.0

        # Translate test-service hostnames to 127.0.0.1 for local host execution
        target_url = url
        headers = {"User-Agent": "NetPath-Diagnostic-Engine/1.0"}
        for mock_host in ("test-service-a", "test-service-b", "test-service-c"):
            if f"://{mock_host}:" in target_url or f"://{mock_host}/" in target_url or target_url.endswith(f"://{mock_host}"):
                target_url = target_url.replace(f"://{mock_host}", "://127.0.0.1")
                headers["Host"] = mock_host

        try:
            async with httpx.AsyncClient(
                timeout=client_timeout,
                limits=limits,
                follow_redirects=True,
                verify=False  # Handshake validation is strictly performed by TLSCollector
            ) as client:
                req = client.build_request("GET", target_url, headers=headers)
                response = await client.send(req, stream=True)
                
                # Monotonic marker when headers received = TTFB
                ttfb_ms = (time.perf_counter() - start_time) * 1000.0
                ttfb_recorded = True

                # Read response body
                content = await response.aread()
                total_duration_ms = (time.perf_counter() - start_time) * 1000.0

                result["status_code"] = response.status_code
                result["ttfb_ms"] = round(ttfb_ms, 2)
                result["total_latency_ms"] = round(total_duration_ms, 2)
                result["response_bytes"] = len(content)
                result["redirect_count"] = len(response.history)

                # Keep relevant diagnostic headers
                diag_headers = {}
                for header_key in [
                    "server", "content-type", "content-length", "date",
                    "cache-control", "x-cache", "retry-after", "via"
                ]:
                    val = response.headers.get(header_key)
                    if val:
                        diag_headers[header_key] = val
                result["headers"] = diag_headers

                # Analyze HTTP status code
                code = response.status_code
                if 200 <= code < 400:
                    if total_duration_ms > self.latency_threshold_ms:
                        result["status"] = "HTTP_APPLICATION_LATENCY"
                        result["error_message"] = (
                            f"HTTP response latency ({total_duration_ms:.1f}ms) "
                            f"exceeded threshold ({self.latency_threshold_ms:.1f}ms)"
                        )
                    else:
                        result["status"] = "SUCCESS"
                elif code == 404:
                    result["status"] = "HTTP_APPLICATION_ERROR"
                    result["error_message"] = "HTTP 404: Requested resource not found"
                elif code == 429:
                    result["status"] = "HTTP_APPLICATION_ERROR"
                    result["error_message"] = "HTTP 429: Too many requests / rate limited"
                elif code == 500:
                    result["status"] = "HTTP_APPLICATION_ERROR"
                    result["error_message"] = "HTTP 500: Internal server error"
                elif code == 502:
                    result["status"] = "HTTP_APPLICATION_ERROR"
                    result["error_message"] = "HTTP 502: Bad gateway (upstream server invalid response)"
                elif code == 503:
                    result["status"] = "HTTP_APPLICATION_ERROR"
                    result["error_message"] = "HTTP 503: Service temporarily unavailable"
                elif code == 504:
                    result["status"] = "HTTP_APPLICATION_ERROR"
                    result["error_message"] = "HTTP 504: Gateway timeout from upstream server"
                else:
                    result["status"] = "HTTP_APPLICATION_ERROR"
                    result["error_message"] = f"HTTP error status code {code}"

        except httpx.ConnectTimeout:
            dur = (time.perf_counter() - start_time) * 1000.0
            result["total_latency_ms"] = round(dur, 2)
            result["status"] = "HTTP_APPLICATION_ERROR"
            result["error_message"] = f"HTTP connection timed out after {self.timeout_seconds}s"
        except httpx.ReadTimeout:
            dur = (time.perf_counter() - start_time) * 1000.0
            result["total_latency_ms"] = round(dur, 2)
            result["status"] = "HTTP_APPLICATION_LATENCY"
            result["error_message"] = f"HTTP read timed out waiting for server response after {self.timeout_seconds}s"
        except httpx.ConnectError as e:
            dur = (time.perf_counter() - start_time) * 1000.0
            result["total_latency_ms"] = round(dur, 2)
            result["status"] = "HTTP_APPLICATION_ERROR"
            result["error_message"] = f"HTTP connection failed: {str(e)}"
        except Exception as ex:
            dur = (time.perf_counter() - start_time) * 1000.0
            result["total_latency_ms"] = round(dur, 2)
            result["status"] = "HTTP_APPLICATION_ERROR"
            result["error_message"] = f"HTTP request failed: {str(ex)}"

        return result

    def collect(self, url: str) -> Dict[str, Any]:
        """Synchronous wrapper for collect_async."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.collect_async(url)).result()
            return loop.run_until_complete(self.collect_async(url))
        except RuntimeError:
            return asyncio.run(self.collect_async(url))
