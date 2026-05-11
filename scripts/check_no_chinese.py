#!/usr/bin/env python3
"""Fail if changed text files contain Chinese characters."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def changed_files(base: str, head: str) -> list[str]:
    if base and set(base) == {"0"}:
        out = run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", head])
        return [line for line in out.splitlines() if line]
    out = run(["git", "diff", "--name-only", base, head])
    return [line for line in out.splitlines() if line]


def is_text_file(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    return b"\x00" not in data


def contains_han(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        if (
            0x4E00 <= code <= 0x9FFF
            or 0x3400 <= code <= 0x4DBF
            or 0x20000 <= code <= 0x2A6DF
            or 0x2A700 <= code <= 0x2B73F
            or 0x2B740 <= code <= 0x2B81F
            or 0x2B820 <= code <= 0x2CEAF
            or 0xF900 <= code <= 0xFAFF
            or 0x2F800 <= code <= 0x2FA1F
        ):
            return True
    return False


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else ""
    head = sys.argv[2] if len(sys.argv) > 2 else "HEAD"

    files = changed_files(base, head)
    violations: list[tuple[str, int, str]] = []

    for rel in files:
        path = Path(rel)
        if not path.exists() or not path.is_file():
            continue
        if not is_text_file(path):
            continue

        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for i, line in enumerate(lines, start=1):
            if contains_han(line):
                violations.append((rel, i, line.strip()))
                break

    if violations:
        print("Found Chinese characters in changed files:")
        for file, line_no, line in violations:
            preview = line[:120]
            print(f"- {file}:{line_no}: {preview}")
        print("\nPlease remove Chinese text before pushing.")
        return 1

    print("No Chinese characters found in changed files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

