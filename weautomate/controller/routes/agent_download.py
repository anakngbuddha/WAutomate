"""Endpoints for downloading the lightweight VM agent and installation script."""

import io
import os
import zipfile
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["Agent Distribution"])

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@router.get("/agent/bundle.zip")
def download_agent_bundle():
    """Generates an in-memory zip archive containing only the files necessary to run the VM Agent."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        agent_files = [
            ("weautomate/__init__.py", "weautomate/__init__.py"),
            ("weautomate/agent/__init__.py", "weautomate/agent/__init__.py"),
            ("weautomate/agent/agent.py", "weautomate/agent/agent.py"),
            ("weautomate/agent/hardware.py", "weautomate/agent/hardware.py"),
            ("weautomate/agent/activation.py", "weautomate/agent/activation.py"),
            ("weautomate/agent/cli.py", "weautomate/agent/cli.py"),
            ("weautomate/kms/__init__.py", "weautomate/kms/__init__.py"),
            ("weautomate/kms/validator.py", "weautomate/kms/validator.py"),
        ]
        for rel_src, rel_dest in agent_files:
            abs_src = os.path.join(PROJECT_ROOT, rel_src.replace("/", os.sep))
            if os.path.exists(abs_src):
                zf.write(abs_src, rel_dest)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=weautomate-agent.zip"},
    )


@router.get("/install.ps1")
def get_installer_script(request: Request):
    """Serves install-agent.ps1 with ControllerUrl automatically set to this server's base URL."""
    installer_path = os.path.join(PROJECT_ROOT, "scripts", "install-agent.ps1")
    if not os.path.exists(installer_path):
        return Response(content="# Installer not found", media_type="text/plain", status_code=404)

    content = open(installer_path, "r", encoding="utf-8").read()
    base_url = str(request.base_url).rstrip("/")
    # Inject current base url as default parameter
    modified = content.replace(
        '[string]$ControllerUrl = "http://127.0.0.1:8000"',
        f'[string]$ControllerUrl = "{base_url}"',
    )
    return Response(content=modified, media_type="text/plain")
