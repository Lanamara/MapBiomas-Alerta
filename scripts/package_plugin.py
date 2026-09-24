#!/usr/bin/env python3
"""Build the plugin ZIP to upload to the QGIS Plugin Repository.

Usage (from the repository root):

    python scripts/package_plugin.py

The script:
  * reads ``mapbiomas_alerta_oficial/metadata.txt`` and checks the fields
    required by plugins.qgis.org;
  * compiles every Python file to catch syntax errors;
  * zips the plugin folder, leaving out caches, hidden files and build
    leftovers, so the archive contains a single top-level folder;
  * writes ``dist/mapbiomas_alerta_oficial.<version>.zip`` and prints a
    short report.

It only uses the Python standard library.
"""

import configparser
import py_compile
import re
import sys
import zipfile
from pathlib import Path

PLUGIN_DIR_NAME = "mapbiomas_alerta_oficial"
ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT / PLUGIN_DIR_NAME
DIST_DIR = ROOT / "dist"

REQUIRED_FIELDS = (
    "name", "qgisMinimumVersion", "description", "about", "version",
    "author", "email", "repository", "tracker", "homepage",
)
VALID_CATEGORIES = {"Raster", "Vector", "Database", "Mesh", "Web"}
EXCLUDED_DIRS = {"__pycache__", "__MACOSX", ".git", ".github", ".idea", ".vscode"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".zip", ".orig", ".rej", ".swp"}
BINARY_SUFFIXES = {".exe", ".dll", ".so", ".dylib", ".pyd", ".bin"}
MAX_SIZE_MB = 20


def fail(message):
    print("ERROR: " + message)
    sys.exit(1)


def read_metadata():
    path = PLUGIN_DIR / "metadata.txt"
    if not path.exists():
        fail("metadata.txt not found in {}".format(PLUGIN_DIR))
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # keep the camelCase field names
    parser.read(path, encoding="utf-8")
    if "general" not in parser:
        fail("metadata.txt has no [general] section")
    return parser["general"]


def check_metadata(meta):
    missing = [field for field in REQUIRED_FIELDS if not meta.get(field, "").strip()]
    if missing:
        fail("missing metadata fields: " + ", ".join(missing))
    if not re.fullmatch(r"\d+(\.\d+){1,2}", meta["version"].strip()):
        fail("version must use dotted notation, e.g. 1.0.0 (found {!r})".format(meta["version"]))
    for field in ("repository", "tracker", "homepage"):
        if not meta[field].strip().startswith("https://"):
            fail("{} must be an https:// URL".format(field))
    category = meta.get("category", "").strip()
    if category and category not in VALID_CATEGORIES:
        fail("category must be one of {} (found {!r})".format(sorted(VALID_CATEGORIES), category))
    for field in ("description", "about", "changelog"):
        if re.search(r"<[a-zA-Z/][^>]*>", meta.get(field, "")):
            fail("{} must not contain HTML".format(field))
    if "plugin" in PLUGIN_DIR_NAME.lower() or "plugin" in meta["name"].lower():
        fail("the plugin name and folder must not contain the word 'plugin'")
    icon = meta.get("icon", "").strip()
    if icon and not (PLUGIN_DIR / icon).exists():
        fail("icon file {!r} not found".format(icon))


def plugin_files():
    for path in sorted(PLUGIN_DIR.rglob("*")):
        relative = path.relative_to(PLUGIN_DIR)
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in relative.parts):
            continue
        if path.is_dir() or path.suffix in EXCLUDED_SUFFIXES:
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            fail("binary file not allowed in the plugin: {}".format(relative))
        yield path, relative


def compile_sources(files):
    for path, relative in files:
        if path.suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True, cfile=None)
            except py_compile.PyCompileError as error:
                fail("syntax error in {}: {}".format(relative, error.msg))


def build_zip(version, files):
    DIST_DIR.mkdir(exist_ok=True)
    target = DIST_DIR / "{}.{}.zip".format(PLUGIN_DIR_NAME, version)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, relative in files:
            archive.write(path, "{}/{}".format(PLUGIN_DIR_NAME, relative.as_posix()))
    return target


def main():
    if not PLUGIN_DIR.is_dir():
        fail("plugin folder not found: {}".format(PLUGIN_DIR))
    meta = read_metadata()
    check_metadata(meta)
    files = list(plugin_files())
    for required in ("__init__.py", "metadata.txt", "LICENSE.txt"):
        if not any(relative.as_posix() == required for _path, relative in files):
            fail("{} is missing from the plugin folder".format(required))
    compile_sources(files)
    version = meta["version"].strip()
    target = build_zip(version, files)
    size_mb = target.stat().st_size / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        fail("package is {:.1f} MB; the limit is {} MB".format(size_mb, MAX_SIZE_MB))
    # Remove the caches py_compile may have created inside the source tree.
    for cache in PLUGIN_DIR.rglob("__pycache__"):
        for item in cache.iterdir():
            item.unlink()
        cache.rmdir()
    print("Plugin : {} {}".format(meta["name"], version))
    print("Files  : {}".format(len(files)))
    print("Package: {} ({:.2f} MB)".format(target.relative_to(ROOT), size_mb))
    print("OK - ready to upload to https://plugins.qgis.org/plugins/add/")


if __name__ == "__main__":
    main()
