# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Frugal Api Economy Environment.

This module creates an HTTP server that exposes the FrugalApiEconomyEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - WS /ws: WebSocket endpoint for persistent sessions

Usage:
    # Development (with auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m server.app
"""

from pathlib import Path

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from ..models import FrugalApiEconomyAction, FrugalApiEconomyObservation
    from .frugal_api_economy_environment import FrugalApiEconomyEnvironment
except ImportError:
    from models import FrugalApiEconomyAction, FrugalApiEconomyObservation
    from server.frugal_api_economy_environment import FrugalApiEconomyEnvironment

from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles


# Create the app with web interface and README integration
app = create_app(
    FrugalApiEconomyEnvironment,
    FrugalApiEconomyAction,
    FrugalApiEconomyObservation,
    env_name="frugal_api_economy",
    max_concurrent_envs=1,  # increase this number to allow more concurrent WebSocket sessions
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse(url="/web")


@app.get("/web", include_in_schema=False)
def web_console() -> FileResponse:
    return FileResponse(STATIC_DIR / "dashboard.html")


def main() -> None:
    """Entry point for direct execution via uv run or python -m."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
