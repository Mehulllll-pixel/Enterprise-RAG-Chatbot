import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs incoming HTTP requests, status codes, and execution latency."""
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Skip health checks to avoid noise
        is_health = request.url.path.endswith("/health") or request.url.path.endswith("/metrics")
        
        if not is_health:
            logger.info(f"Incoming: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            
            if not is_health:
                logger.info(
                    f"Outgoing: {request.method} {request.url.path} "
                    f"Status: {response.status_code} | Duration: {process_time:.2f}ms"
                )
                
            # Add execution time header
            response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
            return response
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Request Failed: {request.method} {request.url.path} | "
                f"Duration: {process_time:.2f}ms | Error: {str(e)}"
            )
            raise

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Applies strict security headers to all responses."""
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self';"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
