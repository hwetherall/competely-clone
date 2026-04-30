#!/usr/bin/env node
const { spawn } = require("child_process");
const path = require("path");
const os = require("os");

const isWindows = os.platform() === "win32";
const pythonPath = isWindows
  ? path.join("venv", "Scripts", "python.exe")
  : path.join("venv", "bin", "python");
const python = path.resolve(process.cwd(), pythonPath);
const reloadEnabled = process.env.BACKEND_RELOAD === "1" || process.argv.includes("--reload");

const args = [
  "-m", "uvicorn", "api.main:app",
  "--port", "8000",
];

if (reloadEnabled) {
  // Use = form for --reload-exclude so globs are not expanded by the shell on Windows.
  args.push(
    "--reload",
    "--reload-exclude=venv",
    "--reload-exclude=data",
    "--reload-exclude=node_modules",
  );
}

const proc = spawn(python, args, {
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
