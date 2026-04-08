from pathlib import Path

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
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


app = create_app(
    FrugalApiEconomyEnvironment,
    FrugalApiEconomyAction,
    FrugalApiEconomyObservation,
    env_name="frugal_api_economy",
    max_concurrent_envs=1,
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
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
