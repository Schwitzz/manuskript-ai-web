"""Project-level operations: rename, delete to trash, zip download, zip upload."""

import io
import shutil
import time
import zipfile
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app import projects as store
from app.auth.deps import current_user
from app.schemas import ProjectName, TrashedOut
from app.config import get_settings
from msklib.project import Project

router = APIRouter(prefix="/api/projects", tags=["project-ops"], dependencies=[Depends(current_user)])

MAX_UPLOAD = 200 * 1024 * 1024      # compressed bytes
MAX_UNPACKED = 1024 * 1024 * 1024   # total uncompressed bytes (zip-bomb guard)
MAX_FILES = 20000


class RenameProject(BaseModel):
    new_name: str = Field(min_length=1, max_length=100)


def _marker(path):
    return path.with_name(path.name + ".msk")


@router.post("/{name}/rename", response_model=ProjectName)
def rename_project(name: str, body: RenameProject):
    src = store.project_path(name)
    dst = store.project_path(body.new_name)
    with store._lock_for(name):
        if not (src / "MANUSKRIPT").exists():
            raise HTTPException(404, "Project not found")
        if dst.exists() or _marker(dst).exists():
            raise HTTPException(409, "A project with that name already exists")
        src.rename(dst)
        if _marker(src).exists():
            _marker(src).rename(_marker(dst))
    return {"name": body.new_name}


@router.delete("/{name}", response_model=TrashedOut)
def delete_project(name: str):
    """Moves the whole project to projects/.trash; nothing is hard deleted."""
    src = store.project_path(name)
    with store._lock_for(name):
        if not (src / "MANUSKRIPT").exists():
            raise HTTPException(404, "Project not found")
        trash = get_settings().projects_dir / ".trash"
        trash.mkdir(exist_ok=True)
        dest = trash / f"{name}-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.move(str(src), str(dest))
        if _marker(src).exists():
            shutil.move(str(_marker(src)), str(dest) + ".msk")
    return {"ok": True, "trashed_as": dest.name}


@router.get("/{name}/download")
def download_project(name: str):
    path = store.project_path(name)
    if not (path / "MANUSKRIPT").exists():
        raise HTTPException(404, "Project not found")
    buf = io.BytesIO()
    with store._lock_for(name), zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(path.rglob("*")):
            rel = f.relative_to(path)
            if f.is_file() and not any(part.startswith(".") for part in rel.parts):
                zf.write(f, f"{name}/{rel.as_posix()}")
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name}.zip"'})


def _safe_members(zf: zipfile.ZipFile) -> tuple[str, list[zipfile.ZipInfo]]:
    """Validate an archive; returns (top folder name, files to extract)."""
    infos = [i for i in zf.infolist() if not i.is_dir()]
    if not infos or len(infos) > MAX_FILES:
        raise HTTPException(400, "Archive is empty or has too many files")
    if sum(i.file_size for i in infos) > MAX_UNPACKED:
        raise HTTPException(400, "Archive is too large when unpacked")
    tops = set()
    for i in infos:
        p = PurePosixPath(i.filename)
        if p.is_absolute() or ".." in p.parts or "\\" in i.filename or len(p.parts) < 2:
            raise HTTPException(400, f"Unsafe path in archive: {i.filename}")
        if (i.external_attr >> 16) & 0o170000 == 0o120000:
            raise HTTPException(400, "Archive contains a symlink")
        tops.add(p.parts[0])
    if len(tops) != 1:
        raise HTTPException(400, "Archive must contain exactly one project folder")
    top = tops.pop()
    if not any(i.filename == f"{top}/MANUSKRIPT" for i in infos):
        raise HTTPException(400, "Not a Manuskript project (no MANUSKRIPT file)")
    return top, infos


@router.post("/upload", status_code=201, response_model=ProjectName)
async def upload_project(file: UploadFile):
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Upload too large")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise HTTPException(400, "Not a zip file")
    top, infos = _safe_members(zf)
    dest = store.project_path(top)
    if dest.exists():
        raise HTTPException(409, "A project with that name already exists")
    tmp = dest.with_name(f".upload-{top}-{time.time_ns()}")
    try:
        for info in infos:
            target = tmp / PurePosixPath(info.filename).relative_to(top)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
        tmp.rename(dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"name": top}


@router.post("/import-msk", status_code=201, response_model=ProjectName)
async def import_zipped_msk(file: UploadFile, name: str):
    """Import a desktop-style zipped `.msk` file (files at the zip root) as a new editable
    folder project called `name`."""
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Upload too large")
    dest = store.project_path(name)
    if dest.exists() or _marker(dest).exists():
        raise HTTPException(409, "A project with that name already exists")
    stamp = time.time_ns()
    tmp_zip = dest.with_name(f".import-{stamp}.zip")
    tmp_dir = dest.with_name(f".import-{stamp}")
    try:
        tmp_zip.parent.mkdir(parents=True, exist_ok=True)
        tmp_zip.write_bytes(data)
        try:
            infos = zipfile.ZipFile(tmp_zip).infolist()
            if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > MAX_UNPACKED:
                raise HTTPException(400, "Archive is too large")
            Project.load_zip(tmp_zip).extract_to(tmp_dir)
        except zipfile.BadZipFile:
            raise HTTPException(400, "Not a zip file")
        except ValueError as e:
            raise HTTPException(400, str(e))
        tmp_dir.rename(dest)
        _marker(dest).write_text("1", encoding="utf8")
    finally:
        tmp_zip.unlink(missing_ok=True)
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return {"name": name}
