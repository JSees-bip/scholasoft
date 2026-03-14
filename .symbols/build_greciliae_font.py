"""
Build greciliae.ttf from the Gregorio submodule (Windows-friendly).
Outputs to .symbols/greciliae.ttf (does not write into lib/).

Requires FontForge installed and on PATH (or set FONTFORGE_EXE).
Usage: python .symbols/build_greciliae_font.py
"""

from __future__ import annotations

import os
import subprocess
import sys


def _fonts_dir() -> str:
    """Path to lib/gregorio-project/fonts (from repo root; read-only)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    return os.path.join(repo_root, "lib", "gregorio-project", "fonts")


def _output_ttf_path() -> str:
    """Path to .symbols/greciliae.ttf (where we write the built font)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "greciliae.ttf")


# FontForgeBuilds on Windows uses run_fontforge.exe; other installs use fontforge.exe.
_FONTFORGE_EXE_NAMES = ("run_fontforge.exe", "fontforge.exe")


def _common_fontforge_paths() -> list[str]:
    """Common Windows install locations for FontForge."""
    drive = os.environ.get("SystemDrive", "C:")
    program_folders = [
        os.path.join(drive, "Program Files", "FontForge"),
        os.path.join(drive, "Program Files (x86)", "FontForge"),
        os.path.join(drive, "Program Files (x86)", "FontForgeBuilds"),
    ]
    out = []
    for folder in program_folders:
        for name in _FONTFORGE_EXE_NAMES:
            exe = os.path.join(folder, name)
            if os.path.isfile(exe):
                out.append(exe)
                break
    return out


def _find_fontforge() -> tuple[str, str | None]:
    """
    Return (fontforge_exe, hint). hint is a suggested FONTFORGE_EXE if we had to guess.
    """
    exe = os.environ.get("FONTFORGE_EXE", "").strip()
    if exe:
        if os.path.isfile(exe):
            return exe, None
        return exe, None  # user set it; let subprocess report if missing
    for path in _common_fontforge_paths():
        if os.path.isfile(path):
            return path, path
    return "fontforge", None


def main() -> int:
    fonts_dir = _fonts_dir()
    if not os.path.isdir(fonts_dir):
        print(f"Fonts directory not found: {fonts_dir}", file=sys.stderr)
        return 1

    sfd = os.path.join(fonts_dir, "greciliae-base.sfd")
    json_path = os.path.join(fonts_dir, "greciliae.json")
    out_ttf = _output_ttf_path()
    symbols_dir = os.path.dirname(out_ttf)
    if not os.path.isdir(symbols_dir):
        os.makedirs(symbols_dir, exist_ok=True)
    for p in (sfd, json_path):
        if not os.path.isfile(p):
            print(f"Missing: {p}", file=sys.stderr)
            return 1

    fontforge_exe, hint = _find_fontforge()
    if hint:
        print(f"Found FontForge: {fontforge_exe}")
    else:
        print(f"Using FontForge: {fontforge_exe}")
    print(f"Working directory: {fonts_dir}")

    def run_fontforge(cmd: list[str]) -> int:
        try:
            r = subprocess.run(cmd, cwd=fonts_dir)
            return r.returncode
        except FileNotFoundError:
            print("", file=sys.stderr)
            print("FontForge was not found.", file=sys.stderr)
            if os.environ.get("FONTFORGE_EXE"):
                print("  FONTFORGE_EXE is set but the file does not exist or is not executable.", file=sys.stderr)
            else:
                print("  Install FontForge from https://fontforge.org/en-US/downloads/", file=sys.stderr)
                print("  Then either add the install folder to PATH, or set:", file=sys.stderr)
                if hint:
                    print(f"    $env:FONTFORGE_EXE = \"{hint}\"   # PowerShell", file=sys.stderr)
                else:
                    print("    $env:FONTFORGE_EXE = \"C:\\Program Files (x86)\\FontForgeBuilds\\run_fontforge.exe\"", file=sys.stderr)
            return -1

    # 1) squarize.py: .sfd -> .ttf (output to .symbols, not lib/)
    cmd1 = [
        fontforge_exe,
        "-script",
        "squarize.py",
        "greciliae-base.sfd",
        "-o", out_ttf,
        "-c", "greciliae.json",
    ]
    print("Running:", " ".join(cmd1))
    r1 = run_fontforge(cmd1)
    if r1 != 0:
        if r1 < 0:
            return 1
        print("squarize.py failed.", file=sys.stderr)
        return r1

    # 2) simplify.py on the .ttf (in .symbols)
    cmd2 = [fontforge_exe, "-script", "simplify.py", out_ttf]
    print("Running:", " ".join(cmd2))
    r2 = run_fontforge(cmd2)
    if r2 != 0:
        if r2 < 0:
            return 1
        print("simplify.py failed.", file=sys.stderr)
        return r2

    print(f"Done. Output: {out_ttf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
