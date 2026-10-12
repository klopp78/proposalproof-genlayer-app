import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const bundledPython = join(
  homedir(),
  ".cache",
  "codex-runtimes",
  "codex-primary-runtime",
  "dependencies",
  "python",
  process.platform === "win32" ? "python.exe" : "bin/python3",
);

const candidates = process.env.PYTHON
  ? [[process.env.PYTHON, []]]
  : process.platform === "win32"
    ? [["py", ["-3"]], ["python", []], ["python3", []], ...(existsSync(bundledPython) ? [[bundledPython, []]] : [])]
    : [["python3", []], ["python", []], ...(existsSync(bundledPython) ? [[bundledPython, []]] : [])];

for (const [command, prefix] of candidates) {
  const probe = spawnSync(command, [...prefix, "--version"], { stdio: "ignore" });
  if (probe.status !== 0) continue;

  const result = spawnSync(
    command,
    [...prefix, "-m", "unittest", "discover", "-s", "tests", "-v"],
    { stdio: "inherit" },
  );
  process.exit(result.status ?? 1);
}

console.error("Python 3 is required to run the GenVM behavior tests.");
process.exit(1);
