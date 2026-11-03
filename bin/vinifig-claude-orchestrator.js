#!/usr/bin/env node
// npx github:vinifig/vinifig-claude-orchestrator --preset node
// Runs installer/install.py from this package against the current directory.
"use strict";
const { spawnSync } = require("node:child_process");
const path = require("node:path");

const installer = path.join(__dirname, "..", "installer", "install.py");
const args = process.argv.slice(2);
if (!args.some((a) => a === "--target" || a.startsWith("--target="))) args.push("--target", process.cwd());

for (const py of ["python3", "python"]) {
  const r = spawnSync(py, [installer, ...args], { stdio: "inherit" });
  if (r.error && r.error.code === "ENOENT") continue;
  process.exit(r.status === null ? 1 : r.status);
}
console.error("error: python3 (3.8+) is required to run the installer");
process.exit(1);
