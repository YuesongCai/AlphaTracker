"""Mosaic backend entrypoint: API + static frontend + scheduler."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, scheduler, seeds
from .api.routes import router
from .auth import AccessTokenMiddleware, ensure_access_token
from .db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("mosaic")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seeds.ensure_seeded()
    ensure_access_token()
    if not os.environ.get("MOSAIC_NO_SCHED"):
        scheduler.start()
    log.info("Mosaic %s ready on http://%s:%s", config.VERSION, config.HOST, config.PORT)
    yield
    scheduler.shutdown()


app = FastAPI(title="Mosaic", version=config.VERSION, lifespan=lifespan)

app.add_middleware(AccessTokenMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local tool; frontend served same-origin, dev server excepted
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": config.VERSION}


# Serve the built frontend (SPA fallback to index.html).
if config.FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=config.FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        target = config.FRONTEND_DIST / path
        if path and target.is_file():
            return FileResponse(target)
        return FileResponse(config.FRONTEND_DIST / "index.html")
