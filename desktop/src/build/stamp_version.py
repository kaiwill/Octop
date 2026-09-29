#!/usr/bin/env python3
"""Stamp the product version and brand into Wails desktop metadata copies."""

from __future__ import annotations

import argparse
import json
import plistlib
import re
import shutil
import sys
from pathlib import Path

_MANIFEST_IDENTITY = re.compile(
    r'(<assemblyIdentity\b[^>]*\bname="com\.tencent\.octop"[^>]*\bversion=")[^"]+(")',
    re.IGNORECASE,
)

# pep440 public versions such as 1.0.2b1 / 1.0.2rc1 / 1.0.2.post1 — capture the
# leading numeric release so Windows VI*Version / assemblyIdentity stay X.X.X.X.
_PEP440_NUMERIC = re.compile(
    r"""
    ^v?
    (?P<a>\d+)
    (?:\.(?P<b>\d+))?
    (?:\.(?P<c>\d+))?
    (?:\.(?P<d>\d+))?
    (?:
      (?:a|b|c|rc|alpha|beta|pre|preview)\d*
      |\.?(?:post|rev|r)\d*
      |\.?dev\d*
    )*
    (?:\+[a-z0-9.]+)?
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)


def should_stamp(version: str) -> bool:
    """Skip placeholders that are not a product version (NSIS needs x.y.z)."""
    return bool(version) and version != "dev"


def four_part_version(version: str) -> str | None:
    """Map pep440 / dotted versions to Windows X.X.X.X (display string unchanged)."""
    raw = version.strip()
    if not raw or raw == "dev":
        return None
    parts = raw.split(".")
    if parts and all(p.isdigit() for p in parts):
        while len(parts) < 4:
            parts.append("0")
        return ".".join(parts[:4])
    m = _PEP440_NUMERIC.match(raw)
    if not m:
        return None
    nums = [m.group("a"), m.group("b") or "0", m.group("c") or "0", m.group("d") or "0"]
    return ".".join(nums)


def stamp_plist(path: Path, version: str) -> None:
    if not should_stamp(version):
        return
    data = plistlib.loads(path.read_bytes())
    data["CFBundleVersion"] = version
    data["CFBundleShortVersionString"] = version
    path.write_bytes(plistlib.dumps(data))


def stamp_info_json(src: Path, dest: Path, version: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dest.resolve():
        shutil.copyfile(src, dest)
    if not should_stamp(version):
        return
    data = json.loads(dest.read_text(encoding="utf-8"))
    # PE fixed file version must be numeric X.X.X.X; ProductVersion string may be pep440.
    dotted = four_part_version(version)
    if dotted is not None:
        data["fixed"]["file_version"] = dotted
    data["info"]["0000"]["ProductVersion"] = version
    dest.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


def stamp_manifest(src: Path, dest: Path, version: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dest.resolve():
        shutil.copyfile(src, dest)
    if not should_stamp(version):
        return
    dotted = four_part_version(version)
    if dotted is None:
        return
    text = dest.read_text(encoding="utf-8")
    updated, n = _MANIFEST_IDENTITY.subn(rf"\g<1>{dotted}\2", text, count=1)
    if n != 1:
        raise SystemExit(f"octop assemblyIdentity not found in {dest}")
    dest.write_text(updated, encoding="utf-8")


def _nsis_quote(value: str) -> str:
    """Escape a value for a double-quoted NSIS ``!define`` string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def brand_defines(project_name: str, info_json: Path) -> dict[str, str]:
    """Read the installer brand strings from the checked-in ``windows/info.json``.

    wails_tools.nsh only falls back to the upstream "Octop" placeholders via
    ``!ifndef``, so project.nsi (which includes this file first) must define them.
    """
    data = json.loads(info_json.read_text(encoding="utf-8"))
    info = data.get("info", {}).get("0000", {})
    missing = [key for key in ("CompanyName", "ProductName", "LegalCopyright") if not info.get(key)]
    if missing:
        raise SystemExit(f"{info_json} is missing {', '.join(missing)}")
    return {
        "INFO_PROJECTNAME": project_name,
        "INFO_COMPANYNAME": info["CompanyName"],
        "INFO_PRODUCTNAME": info["ProductName"],
        "INFO_COPYRIGHT": info["LegalCopyright"],
    }


def write_nsis_defines(path: Path, version: str, project_name: str, info_json: Path) -> None:
    """Write ``!define`` lines for NSIS (brand + display + numeric VI*Version)."""
    product = version.strip() or "dev"
    filever = four_part_version(product)
    if filever is None:
        if product == "dev":
            filever = "0.0.0.0"
        else:
            raise SystemExit(f"cannot map version to X.X.X.X: {product!r}")
    defines = {
        **brand_defines(project_name, info_json),
        "INFO_PRODUCTVERSION": product,
        "INFO_FILEVERSION": filever,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        # Included by project.nsi before wails_tools.nsh (!ifndef guards).
        "".join(f'!define {key} "{_nsis_quote(value)}"\n' for key, value in defines.items()),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    plist_p = sub.add_parser("plist", help="Set CFBundleVersion keys on a copied Info.plist")
    plist_p.add_argument("path", type=Path)
    plist_p.add_argument("version")

    json_p = sub.add_parser("json", help="Copy windows/info.json and set file/product version")
    json_p.add_argument("src", type=Path)
    json_p.add_argument("dest", type=Path)
    json_p.add_argument("version")

    man_p = sub.add_parser("manifest", help="Copy wails.exe.manifest and set assembly version")
    man_p.add_argument("src", type=Path)
    man_p.add_argument("dest", type=Path)
    man_p.add_argument("version")

    four_p = sub.add_parser(
        "four-part",
        help="Print Windows X.X.X.X for VI*Version / assemblyIdentity (stdout)",
    )
    four_p.add_argument("version")

    nsis_p = sub.add_parser(
        "nsis-defines",
        help="Write INFO_* !define lines (brand + version) for project.nsi",
    )
    nsis_p.add_argument("version")
    nsis_p.add_argument("path", type=Path)
    nsis_p.add_argument("--project-name", required=True, help="Binary name (INFO_PROJECTNAME)")
    nsis_p.add_argument(
        "--info-json",
        type=Path,
        required=True,
        help="windows/info.json providing CompanyName / ProductName / LegalCopyright",
    )

    args = parser.parse_args(argv)
    if args.cmd == "plist":
        stamp_plist(args.path, args.version)
    elif args.cmd == "json":
        stamp_info_json(args.src, args.dest, args.version)
    elif args.cmd == "four-part":
        dotted = four_part_version(args.version)
        if dotted is None:
            raise SystemExit(f"cannot map version to X.X.X.X: {args.version!r}")
        print(dotted)
    elif args.cmd == "nsis-defines":
        write_nsis_defines(args.path, args.version, args.project_name, args.info_json)
    else:
        stamp_manifest(args.src, args.dest, args.version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
