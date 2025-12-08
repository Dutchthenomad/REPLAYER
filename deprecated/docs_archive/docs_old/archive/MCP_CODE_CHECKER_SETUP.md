# MCP Code Checker Setup

## Installation Status: ✅ COMPLETE

The `mcp-code-checker` plugin has been successfully installed into the `rugs-rl-bot` virtual environment.

**Location**: `/home/nomad/Desktop/rugs-rl-bot/.venv/bin/mcp-code-checker`

---

## What It Does

The MCP Code Checker provides automated code quality checks via MCP (Model Context Protocol):

- **Pylint**: Static code analysis for Python
- **Pytest**: Test execution and reporting
- **Mypy**: Static type checking

---

## Manual Server Startup (For Testing)

To start the server manually:

```bash
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/mcp-code-checker \
  --project-dir /home/nomad/Desktop/REPLAYER \
  --venv-path /home/nomad/Desktop/rugs-rl-bot/.venv \
  --test-folder src/tests \
  --console-only
```

**Server Output** (example from test run):
```
2025-11-16 20:39:53 [info] Starting MCP server
2025-11-16 20:39:55 [debug] About to call server.run() project_dir=/home/nomad/Desktop/REPLAYER
```

---

## Integration with Claude Code (MCP Configuration)

### Option 1: MCP Settings File (Recommended)

If Claude Code uses MCP settings, add to your MCP configuration file (typically `~/.config/claude-code/mcp.json` or similar):

```json
{
  "mcpServers": {
    "code_checker": {
      "command": "/home/nomad/Desktop/rugs-rl-bot/.venv/bin/mcp-code-checker",
      "args": [
        "--project-dir",
        "/home/nomad/Desktop/REPLAYER",
        "--venv-path",
        "/home/nomad/Desktop/rugs-rl-bot/.venv",
        "--test-folder",
        "src/tests"
      ]
    }
  }
}
```

### Option 2: Claude MCP CLI (If Available)

If the `claude mcp add` command exists:

```bash
claude mcp add code_checker \
  --args "--project-dir /home/nomad/Desktop/REPLAYER --venv-path /home/nomad/Desktop/rugs-rl-bot/.venv --test-folder src/tests"
```

---

## Available Options

- `--project-dir` (required): Base directory for code checking
- `--venv-path`: Virtual environment path (uses its Python interpreter)
- `--python-executable`: Alternative to venv-path (specific Python interpreter)
- `--test-folder`: Test directory (default: `tests`, we use `src/tests`)
- `--keep-temp-files`: Preserve temporary files for debugging
- `--log-level`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `--log-file`: Path for structured JSON logs
- `--console-only`: Log to console only (no file)

---

## Example Usage Commands

### Full Path Test
```bash
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/mcp-code-checker \
  --project-dir /home/nomad/Desktop/REPLAYER \
  --venv-path /home/nomad/Desktop/rugs-rl-bot/.venv \
  --test-folder src/tests
```

### With Debug Logging
```bash
/home/nomad/Desktop/rugs-rl-bot/.venv/bin/mcp-code-checker \
  --project-dir /home/nomad/Desktop/REPLAYER \
  --venv-path /home/nomad/Desktop/rugs-rl-bot/.venv \
  --test-folder src/tests \
  --log-level DEBUG \
  --keep-temp-files
```

---

## Troubleshooting

### Server Not Accessible in Claude Code

1. **Check MCP Configuration Location**:
   ```bash
   # Common locations:
   ~/.config/claude-code/mcp.json
   ~/Library/Application Support/Claude/mcp.json  # macOS
   ```

2. **Verify Server Status**:
   ```bash
   ps aux | grep mcp-code-checker
   ```

3. **Test Server Manually**:
   ```bash
   /home/nomad/Desktop/rugs-rl-bot/.venv/bin/mcp-code-checker \
     --project-dir /home/nomad/Desktop/REPLAYER \
     --console-only
   ```

4. **Check Logs**:
   - Console output (with `--console-only`)
   - Log files in `/home/nomad/Desktop/REPLAYER/logs/` (without `--console-only`)

---

## Comparison with aicode-review Plugin

| Feature | aicode-review | mcp-code-checker |
|---------|--------------|------------------|
| **Design Patterns** | ✅ Yes (architect.yaml) | ❌ No |
| **Coding Rules** | ✅ Yes (RULES.yaml) | ❌ No |
| **Pylint** | ❌ No | ✅ Yes |
| **Pytest** | ❌ No | ✅ Yes |
| **Mypy** | ❌ No | ✅ Yes |
| **Custom Patterns** | ✅ Fully customizable | ❌ Standard tools only |

**Recommendation**: Use **both** plugins for comprehensive code review:
- `aicode-review`: Architecture patterns, thread safety, design patterns
- `mcp-code-checker`: Static analysis (pylint, mypy), test execution (pytest)

---

## Next Steps

1. ✅ **Installation**: Complete
2. ⏳ **Configuration**: Add to MCP settings (see Option 1 above)
3. ⏳ **Testing**: Verify MCP tools appear in Claude Code
4. ⏳ **Usage**: Use code checker on REPLAYER files

---

## Related Files

- **Design Patterns**: `/home/nomad/Desktop/REPLAYER/architect.yaml`
- **Coding Rules**: `/home/nomad/Desktop/REPLAYER/RULES.yaml`
- **Toolkit Config**: `/home/nomad/Desktop/REPLAYER/toolkit.yaml`
- **This Guide**: `/home/nomad/Desktop/REPLAYER/MCP_CODE_CHECKER_SETUP.md`
