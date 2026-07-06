from __future__ import annotations

import os
import subprocess
from pathlib import Path

import frappe


def build_frontend(*args, **kwargs) -> None:
	app_root = Path(frappe.get_app_path("tecponto_app")).parent
	frontend_dir = app_root / "frontend"
	package_json = frontend_dir / "package.json"
	if not package_json.exists():
		return

	env = os.environ.copy()
	env.setdefault("CI", "1")
	subprocess.run(["npm", "install", "--include=optional"], cwd=frontend_dir, env=env, check=True)
	subprocess.run(["npm", "run", "build"], cwd=frontend_dir, env=env, check=True)
