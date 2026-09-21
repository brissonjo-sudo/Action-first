"""Build a deterministic ZIP containing the canonical Action First skill."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "action-first" / "SKILL.md"
DIST = ROOT / "dist"
ARCHIVE = DIST / "action-first.zip"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def build() -> tuple[Path, str]:
    DIST.mkdir(exist_ok=True)
    payload = SOURCE.read_bytes()
    info = zipfile.ZipInfo("action-first/SKILL.md", FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    with zipfile.ZipFile(ARCHIVE, "w") as archive:
        archive.writestr(info, payload)
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    (DIST / "SHA256SUMS").write_text(
        f"{digest}  {ARCHIVE.name}\n", encoding="utf-8", newline="\n"
    )
    return ARCHIVE, digest


if __name__ == "__main__":
    archive, sha256 = build()
    print(f"{archive} {sha256}")
