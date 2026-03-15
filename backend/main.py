from __future__ import annotations

import os

import uvicorn

from app.api import create_app


def main() -> None:
    app = create_app()
    host = os.getenv("TRACELOG_HOST", "127.0.0.1")
    port = int(os.getenv("TRACELOG_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level=os.getenv("TRACELOG_LOG_LEVEL", "info"))


if __name__ == "__main__":
    main()

