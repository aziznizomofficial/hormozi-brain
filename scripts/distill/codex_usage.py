#!/usr/bin/env python3
"""Print the Codex plan's weekly usage % (via `codex app-server`), to pace bulk runs."""
import json, subprocess
p = subprocess.Popen(["codex", "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
for o in ({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"clientInfo": {"name": "distill", "version": "0"}}},
          {"jsonrpc": "2.0", "method": "initialized"}, {"jsonrpc": "2.0", "id": 2, "method": "account/rateLimits/read"}):
    p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
for line in p.stdout:
    if '"id":2' in line:
        r = json.loads(line)["result"]["rateLimits"]["primary"]; print(r["usedPercent"], "% of weekly window used; resets", r["resetsAt"]); break
p.kill()
