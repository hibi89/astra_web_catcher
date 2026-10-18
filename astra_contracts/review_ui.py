"""Localhost-only UI for *unverified* reviewer opinions, never an approval service."""
from __future__ import annotations

import argparse
import re
import secrets
import sys
import tempfile
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse, JSONResponse
from pydantic import ValidationError

from astra_contracts.data_mapping import MappingReport, OwnedSchemaDeclaration
from astra_contracts.functional_spec import FunctionalSpecDraft
from astra_contracts.generation_contract import fingerprint
from astra_contracts.reviewer_decisions import ReviewRecord, ReviewSubmission, build_packet, record_opinions
from astra_contracts.review_transfer import MAX_TRANSFER_BYTES, export_bundle, import_bundle

HERE = Path(__file__).resolve().parent
MAX_BODY = 65536
RECORD_ID = re.compile(r"^[0-9a-f]{24}$")


def _safe_folder(path: Path) -> Path:
    parent = Path(tempfile.gettempdir()).resolve()
    if (path.is_symlink() or not path.is_dir() or path.parent.resolve() != parent
            or path.resolve().parent != parent or not path.name.startswith("astra-review-")):
        raise ValueError("record storage must be an existing direct astra-review-* temp folder")
    return path


def create_review_app(spec: FunctionalSpecDraft, schema: OwnedSchemaDeclaration,
                      mapping: MappingReport, storage: Path) -> FastAPI:
    """All writes are opinion-only JSON in isolated temp; no customer DB/API access."""
    packet = build_packet(spec, schema, mapping)  # revalidates input mapping
    folder = _safe_folder(Path(storage))
    local_token = secrets.token_urlsafe(32)
    app = FastAPI(title="ASTRA local review", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0].lower()
        if host not in {"127.0.0.1", "localhost", "testserver"}:
            return PlainTextResponse("Invalid host", status_code=403)
        origin = request.headers.get("origin")
        if origin and origin != f"http://{request.headers.get('host')}":
            return PlainTextResponse("Invalid origin", status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"
        )
        return response

    @app.get("/", response_class=HTMLResponse)
    def home():
        return HTMLResponse((HERE / "review_ui.html").read_text(encoding="utf-8"))

    @app.get("/review.js")
    def js():
        return FileResponse(HERE / "review_ui.js", media_type="application/javascript")

    @app.get("/review.css")
    def css():
        return FileResponse(HERE / "review_ui.css", media_type="text/css")

    @app.get("/api/packet")
    def packet_json():
        return {"packet": packet.model_dump(mode="json"), "packet_sha256": fingerprint(packet),
                "review_token": local_token, "storage": "isolated_temporary_only",
                "authorization_granted": False}

    def require_token(value: str | None):
        if not value or not secrets.compare_digest(value, local_token):
            raise HTTPException(403, "Missing/invalid local review token")

    @app.post("/api/opinions")
    async def save(request: Request, x_astra_review_token: str | None = Header(default=None)):
        require_token(x_astra_review_token)
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            raise HTTPException(415, "JSON required")
        if int(request.headers.get("content-length", "0") or "0") > MAX_BODY:
            raise HTTPException(413, "Review too large")
        raw = await request.body()
        if len(raw) > MAX_BODY:
            raise HTTPException(413, "Review too large")
        try:
            submission = ReviewSubmission.model_validate_json(raw)
            recorded = record_opinions(packet, submission)
        except (ValidationError, ValueError) as e:
            raise HTTPException(422, "Invalid or stale review; no file saved") from e
        _safe_folder(folder)
        identifier = secrets.token_hex(12)
        path = folder / f"{identifier}.json"
        with path.open("x", encoding="utf-8") as out:
            out.write(recorded.model_dump_json(indent=2) + "\n")
        return {"record_id": identifier, "record": recorded.model_dump(mode="json"),
                "authorization_granted": False}

    @app.get("/api/opinions/{record_id}")
    def load(record_id: str, x_astra_review_token: str | None = Header(default=None)):
        require_token(x_astra_review_token)
        if not RECORD_ID.fullmatch(record_id):
            raise HTTPException(404, "Record not found")
        _safe_folder(folder)
        path = folder / f"{record_id}.json"
        if path.is_symlink() or not path.is_file():
            raise HTTPException(404, "Record not found")
        try:
            record = ReviewRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as e:
            raise HTTPException(422, "Invalid record file") from e
        if record.packet_sha256 != fingerprint(packet):
            raise HTTPException(409, "Stale packet fingerprint")
        return {"record_id": record_id, "record": record.model_dump(mode="json"),
                "authorization_granted": False}

    @app.get("/api/export/{record_id}")
    def export_opinion(record_id: str, x_astra_review_token: str | None = Header(default=None)):
        require_token(x_astra_review_token)
        if not RECORD_ID.fullmatch(record_id):
            raise HTTPException(404, "Record not found")
        _safe_folder(folder)
        path = folder / f"{record_id}.json"
        if path.is_symlink() or not path.is_file():
            raise HTTPException(404, "Record not found")
        try:
            if path.stat().st_size > MAX_TRANSFER_BYTES:
                raise ValueError("Stored review too large")
            record = ReviewRecord.model_validate_json(path.read_bytes())
            bundle = export_bundle(packet, record)
        except (OSError, ValueError, ValidationError) as exc:
            raise HTTPException(422, "Invalid or stale review record") from exc
        return JSONResponse(
            bundle.model_dump(mode="json"),
            headers={"Content-Disposition": f'attachment; filename="astra-opinions-{record_id}.json"'},
        )

    @app.post("/api/import")
    async def import_opinion(request: Request,
                             x_astra_review_token: str | None = Header(default=None)):
        require_token(x_astra_review_token)
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            raise HTTPException(415, "JSON required")
        try:
            if int(request.headers.get("content-length", "0") or "0") > MAX_TRANSFER_BYTES:
                raise HTTPException(413, "Transfer too large")
        except ValueError as exc:
            raise HTTPException(400, "Invalid content length") from exc
        data = await request.body()
        if len(data) > MAX_TRANSFER_BYTES:
            raise HTTPException(413, "Transfer too large")
        try:
            record = import_bundle(packet, data)
        except (ValueError, ValidationError) as exc:
            raise HTTPException(422, "Invalid or stale opinion transfer") from exc
        _safe_folder(folder)
        identifier = secrets.token_hex(12)
        path = folder / f"{identifier}.json"
        with path.open("x", encoding="utf-8") as out:
            out.write(record.model_dump_json(indent=2) + "\n")
        return {"record_id": identifier, "record": record.model_dump(mode="json"),
                "authorization_granted": False, "imported_unverified_opinions": True}

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manual opinions UI, local only, not approval")
    parser.add_argument("spec", type=Path)
    parser.add_argument("schema", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("--port", type=int, default=8018)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    try:
        spec = FunctionalSpecDraft.model_validate_json(args.spec.read_text(encoding="utf-8"))
        schema = OwnedSchemaDeclaration.model_validate_json(args.schema.read_text(encoding="utf-8"))
        mapping = MappingReport.model_validate_json(args.mapping.read_text(encoding="utf-8"))
        folder = Path(tempfile.mkdtemp(prefix="astra-review-"))
        folder.chmod(0o700)
        app = create_review_app(spec, schema, mapping, folder)
    except (OSError, UnicodeError, ValidationError, ValueError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(f"Local review UI: http://127.0.0.1:{args.port}/", flush=True)
    print(f"Opinion storage (temporary): {folder}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
