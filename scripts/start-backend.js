#!/usr/bin/env node
const { spawn } = require("child_process");
const path = require("path");
const os = require("os");

const isWindows = os.platform() === "win32";
const pythonPath = isWindows
  ? path.join("venv", "Scripts", "python.exe")
  : path.join("venv", "bin", "python");
const python = path.resolve(process.cwd(), pythonPath);

// Use = form for --reload-exclude so globs are not expanded by the shell on Windows
const proc = spawn(python, [
  "-m", "uvicorn", "api.main:app",
  "--reload", "--port", "8000",
  "--reload-exclude=venv",
  "--reload-exclude=data",
  "--reload-exclude=node_modules",
], {
  stdio: "inherit",
  cwd: process.cwd(),
  shell: false,
});

proc.on("error", (err) => {
  console.error("Failed to start backend:", err.message);
  process.exit(1);
});

proc.on("exit", (code) => {
  process.exit(code ?? 0);
});
