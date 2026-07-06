#!/usr/bin/env python3
"""Fail when tracked text files contain encoding corruption.

This catches the two classes that already hurt Tecponto:
- replacement/question-mark corruption inside Portuguese words
- mojibake produced by decoding UTF-8 bytes as a Windows/OEM code page
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


SKIP_SUFFIXES = {
	".gif",
	".ico",
	".jpeg",
	".jpg",
	".pdf",
	".png",
	".pyc",
	".ttf",
	".woff",
	".woff2",
}

MOJIBAKE_RE = re.compile(
	r"[\u00c2\u00c3][\u0080-\u00bf\u00a0-\u00bf]"
	r"|\u00e2[\u0080-\u00bf\u20ac\u201a-\u201e\u2020-\u2022]"
)
WORD_QUESTION_RE = re.compile(
	r"[A-Za-z\u00c0-\u024f]\?[A-Za-z\u00c0-\u024f]"
	r"|\?\?"
	r"|^\s*\"label\"\s*:\s*\"\?"
)
REPLACEMENT_CHAR = "\ufffd"


def tracked_files() -> list[str]:
	return subprocess.check_output(["git", "ls-files"], text=True, encoding="utf-8").splitlines()


def should_skip(path: Path) -> bool:
	return path.suffix.lower() in SKIP_SUFFIXES or "__pycache__" in path.parts


def scan_file(path: Path) -> list[tuple[int, str, str]]:
	if should_skip(path) or not path.exists():
		return []

	data = path.read_bytes()
	if b"\x00" in data:
		return []

	try:
		text = data.decode("utf-8")
	except UnicodeDecodeError as exc:
		return [(0, "not_utf8", str(exc))]

	findings = []
	for line_no, line in enumerate(text.splitlines(), 1):
		if REPLACEMENT_CHAR in line:
			findings.append((line_no, "replacement_char", line.strip()))
		if MOJIBAKE_RE.search(line):
			findings.append((line_no, "mojibake", line.strip()))
		if WORD_QUESTION_RE.search(line):
			findings.append((line_no, "question_mark_corruption", line.strip()))
	return findings


def main() -> int:
	files = sys.argv[1:] or tracked_files()
	problems = []
	for file_name in files:
		path = Path(file_name)
		for line_no, kind, snippet in scan_file(path):
			problems.append((path, line_no, kind, snippet))

	if not problems:
		return 0

	print("Encoding corruption found. Save files as UTF-8 and fix the text:", file=sys.stderr)
	for path, line_no, kind, snippet in problems:
		location = f"{path}:{line_no}" if line_no else str(path)
		print(f"{location}: {kind}: {snippet}", file=sys.stderr)
	return 1


if __name__ == "__main__":
	raise SystemExit(main())
