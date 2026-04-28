"""Retro-terminal FastAPI dashboard for the alt-az antenna tracker.

Serves a single-page UI with two tabs (Tracker / Inmarsat), exposes a
WebSocket for live position updates, and a small REST surface for jog,
goto, home, park, stop, motor enable, limit capture, and the (stubbed)
sniffer sidecar.

Run:
    python -m web.app --port 8080 --host 0.0.0.0 --config tracker/config.yaml [--sim]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel


CONFIG_PATH = Path("tracker/config.yaml")
SIM_FORCED = False

app = FastAPI(title="space-station tracker")
state: dict[str, Any] = {
    "tracker": None,
    "sniffer": None,
    "config": {},
}


# --------------------------------------------------------------------------- #
# Lazy imports of tracker package (so module import never breaks if deps move)
# --------------------------------------------------------------------------- #


def _load_tracker(config_path: Path, sim: bool):
    from tracker.controller import AntennaTracker  # lazy
    backend = "sim" if sim else "auto"
    return AntennaTracker.from_config(config_path, gpio_backend=backend)


def _load_sniffer(sniffer_cfg: dict):
    try:
        from tracker.sniffer import SnifferSidecar  # lazy
        return SnifferSidecar(sniffer_cfg)
    except Exception:
        return None


def _read_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #


@app.on_event("startup")
async def _startup() -> None:
    cfg = _read_config(CONFIG_PATH)
    state["config"] = cfg
    sim = SIM_FORCED
    if not sim:
        try:
            import lgpio  # noqa: F401
        except Exception:
            sim = True
    try:
        state["tracker"] = _load_tracker(CONFIG_PATH, sim)
    except Exception as exc:
        print(f"[web] tracker init failed ({exc!r}) — falling back to sim", file=sys.stderr)
        state["tracker"] = _load_tracker(CONFIG_PATH, True)
    state["sniffer"] = _load_sniffer(cfg.get("sniffer", {}))


@app.on_event("shutdown")
async def _shutdown() -> None:
    tracker = state.get("tracker")
    if tracker is not None:
        try:
            tracker.disable_all()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Pydantic request models
# --------------------------------------------------------------------------- #


class JogReq(BaseModel):
    axis: str
    direction: str
    step_size_deg: float


class GotoReq(BaseModel):
    az: float
    el: float


class SetLimitReq(BaseModel):
    axis: str
    limit: str


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _require_tracker():
    t = state.get("tracker")
    if t is None:
        raise HTTPException(status_code=503, detail="tracker not initialised")
    return t


def _status_payload() -> dict[str, Any]:
    t = _require_tracker()
    s = t.status()
    return {
        "az_deg": s["az"]["position_deg"],
        "el_deg": s["el"]["position_deg"],
        "az_steps": s["az"]["position_steps"],
        "el_steps": s["el"]["position_steps"],
        "enabled": bool(s["az"]["enabled"] or s["el"]["enabled"]),
        "mode": s.get("mode", "unknown"),
    }


# --------------------------------------------------------------------------- #
# Tracker REST endpoints
# --------------------------------------------------------------------------- #


@app.post("/api/jog")
async def api_jog(req: JogReq) -> dict:
    t = _require_tracker()
    if req.axis not in ("az", "el"):
        raise HTTPException(400, "axis must be 'az' or 'el'")
    if req.direction not in ("+1", "-1"):
        raise HTTPException(400, "direction must be '+1' or '-1'")
    axis = t.az if req.axis == "az" else t.el
    sign = 1 if req.direction == "+1" else -1
    target = axis.position_deg + sign * float(req.step_size_deg)
    target = max(axis.min_angle, min(axis.max_angle, target))
    await asyncio.to_thread(axis.goto_deg, target)
    return _status_payload()


@app.post("/api/goto")
async def api_goto(req: GotoReq) -> dict:
    t = _require_tracker()
    await asyncio.to_thread(t.goto, float(req.az), float(req.el))
    return _status_payload()


@app.post("/api/home")
async def api_home() -> dict:
    t = _require_tracker()
    await asyncio.to_thread(t.home)
    return _status_payload()


@app.post("/api/park")
async def api_park() -> dict:
    t = _require_tracker()
    await asyncio.to_thread(t.park)
    return _status_payload()


@app.post("/api/stop")
async def api_stop() -> dict:
    t = _require_tracker()
    t.stop()
    return _status_payload()


@app.post("/api/motors/enable")
async def api_enable() -> dict:
    t = _require_tracker()
    t.enable_all()
    return _status_payload()


@app.post("/api/motors/disable")
async def api_disable() -> dict:
    t = _require_tracker()
    t.disable_all()
    return _status_payload()


@app.post("/api/set-limit")
async def api_set_limit(req: SetLimitReq) -> dict:
    if req.axis not in ("az", "el"):
        raise HTTPException(400, "axis must be 'az' or 'el'")
    if req.limit not in ("min", "max"):
        raise HTTPException(400, "limit must be 'min' or 'max'")
    t = _require_tracker()
    axis_obj = t.az if req.axis == "az" else t.el
    current_deg = float(axis_obj.position_deg)

    cfg = _read_config(CONFIG_PATH)
    section_axis = "azimuth" if req.axis == "az" else "elevation"
    cfg.setdefault("tracker", {}).setdefault(section_axis, {})
    cfg["tracker"][section_axis][f"{req.limit}_angle"] = current_deg

    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False, default_flow_style=False)

    if req.limit == "min":
        axis_obj.min_angle = current_deg
    else:
        axis_obj.max_angle = current_deg
    state["config"] = cfg
    return {"axis": req.axis, "limit": req.limit, "value_deg": current_deg}


# --------------------------------------------------------------------------- #
# Sniffer endpoints (stubbed)
# --------------------------------------------------------------------------- #


def _sniffer_target() -> str:
    return str(state.get("config", {}).get("sniffer", {}).get("default_target", ""))


@app.get("/api/sniffer/status")
async def api_sniffer_status() -> dict:
    target = _sniffer_target()
    sniffer = state.get("sniffer")
    if sniffer is None:
        return {
            "enabled": False,
            "configured_target": target,
            "reason": "stub — see docs/archive/merge_plan.html",
        }
    try:
        running = sniffer.is_running()
        return {
            "enabled": bool(running),
            "configured_target": target,
            "reason": "running" if running else "stopped",
        }
    except NotImplementedError:
        return {
            "enabled": False,
            "configured_target": target,
            "reason": "stub — see docs/archive/merge_plan.html",
        }
    except Exception as exc:
        return {
            "enabled": False,
            "configured_target": target,
            "reason": f"stub — see docs/archive/merge_plan.html ({exc.__class__.__name__})",
        }


@app.post("/api/sniffer/start")
async def api_sniffer_start():
    sniffer = state.get("sniffer")
    if sniffer is None:
        return JSONResponse(
            status_code=501,
            content={"detail": "inmarsat-sniffer not vendored yet — see docs/archive/merge_plan.html"},
        )
    try:
        sniffer.start()
        return {"ok": True}
    except NotImplementedError as exc:
        return JSONResponse(status_code=501, content={"detail": str(exc)})


@app.post("/api/sniffer/stop")
async def api_sniffer_stop():
    sniffer = state.get("sniffer")
    if sniffer is None:
        return JSONResponse(
            status_code=501,
            content={"detail": "inmarsat-sniffer not vendored yet — see docs/archive/merge_plan.html"},
        )
    try:
        sniffer.stop()
        return {"ok": True}
    except NotImplementedError as exc:
        return JSONResponse(status_code=501, content={"detail": str(exc)})


# --------------------------------------------------------------------------- #
# WebSocket
# --------------------------------------------------------------------------- #


@app.websocket("/ws")
async def ws_position(socket: WebSocket) -> None:
    await socket.accept()
    try:
        while True:
            try:
                payload = _status_payload()
            except HTTPException:
                payload = {"error": "tracker not ready"}
            await socket.send_text(json.dumps(payload))
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await socket.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Root page (embedded HTML/CSS/JS)
# --------------------------------------------------------------------------- #


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>SPACE-STATION // tracker</title>
<style>
:root {
  --bg: #0a0e0a;
  --bg-2: #0f140f;
  --fg: #7fff7f;
  --fg-dim: #4fae4f;
  --fg-faint: #2a5a2a;
  --warn: #ffd24f;
  --err: #ff5f5f;
  --glow: 0 0 6px rgba(127,255,127,0.45), 0 0 14px rgba(127,255,127,0.18);
}
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0; height: 100%;
  background: var(--bg);
  color: var(--fg);
  font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, 'Courier New', monospace;
  font-size: 14px;
  letter-spacing: 0.02em;
}
body::before {
  content: "";
  position: fixed; inset: 0;
  background: repeating-linear-gradient(
    to bottom, rgba(127,255,127,0.025) 0 1px, transparent 1px 3px);
  pointer-events: none;
  z-index: 99;
}
header {
  border-bottom: 1px solid var(--fg-faint);
  padding: 12px 20px;
  display: flex; align-items: center; gap: 24px;
  text-shadow: var(--glow);
}
header h1 {
  margin: 0; font-size: 16px; font-weight: 600; letter-spacing: 0.15em;
}
header .meta { color: var(--fg-dim); font-size: 12px; margin-left: auto; }
nav.tabs {
  display: flex; gap: 0; border-bottom: 1px solid var(--fg-faint);
  background: var(--bg-2);
}
nav.tabs button {
  background: transparent; border: 0; color: var(--fg-dim);
  padding: 10px 22px; cursor: pointer;
  font-family: inherit; font-size: 13px; letter-spacing: 0.12em;
  border-right: 1px solid var(--fg-faint);
}
nav.tabs button.active {
  color: var(--fg); background: var(--bg);
  text-shadow: var(--glow);
  border-bottom: 1px solid var(--bg);
  margin-bottom: -1px;
}
main { padding: 20px; max-width: 1100px; margin: 0 auto; }
.card {
  border: 1px solid var(--fg-faint);
  background: var(--bg-2);
  padding: 16px 18px;
  margin-bottom: 18px;
  position: relative;
}
.card h2 {
  margin: 0 0 12px 0; font-size: 12px; font-weight: 600;
  color: var(--fg-dim); letter-spacing: 0.18em; text-transform: uppercase;
}
.row { display: flex; gap: 18px; flex-wrap: wrap; }
.col { flex: 1 1 280px; min-width: 240px; }
button.t, input.t, select.t {
  background: var(--bg); color: var(--fg);
  border: 1px solid var(--fg-faint); padding: 6px 12px;
  font-family: inherit; font-size: 13px;
  cursor: pointer;
}
button.t:hover, button.t:focus { border-color: var(--fg); text-shadow: var(--glow); }
input.t, select.t { width: 100%; }
.position {
  display: grid; grid-template-columns: auto 1fr; gap: 6px 16px;
  font-size: 18px; text-shadow: var(--glow);
}
.position .label { color: var(--fg-dim); font-size: 11px; letter-spacing: 0.15em; }
.position .value { font-variant-numeric: tabular-nums; }
.jogpad {
  display: grid; grid-template-columns: repeat(3, 60px); grid-template-rows: repeat(3, 50px);
  gap: 6px; justify-content: center; margin: 12px 0;
}
.jogpad button {
  background: var(--bg); color: var(--fg);
  border: 1px solid var(--fg-faint);
  font-family: inherit; font-size: 18px; cursor: pointer;
}
.jogpad button:hover { border-color: var(--fg); text-shadow: var(--glow); }
.jogpad .blank { visibility: hidden; }
.jogpad .stop { color: var(--err); border-color: var(--err); }
.controls { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.kv { display: grid; grid-template-columns: 110px 1fr; gap: 6px 12px; align-items: center; }
.statusbadge {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 4px 10px; border: 1px solid var(--fg-faint);
  font-size: 12px; letter-spacing: 0.1em;
}
.dot { width: 10px; height: 10px; border-radius: 50%; box-shadow: var(--glow); }
.dot.red    { background: var(--err);  box-shadow: 0 0 8px var(--err); }
.dot.yellow { background: var(--warn); box-shadow: 0 0 8px var(--warn); }
.dot.green  { background: var(--fg);   box-shadow: 0 0 8px var(--fg); }
a { color: var(--fg); }
small.hint { color: var(--fg-dim); font-size: 11px; }
.hidden { display: none !important; }
.kbdgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 14px; font-size: 12px; color: var(--fg-dim); }
.kbdgrid kbd {
  border: 1px solid var(--fg-faint); padding: 1px 6px; font-family: inherit;
  color: var(--fg); background: var(--bg);
}
</style>
</head>
<body>
<header>
  <h1>// SPACE-STATION TRACKER //</h1>
  <span class="meta" id="modebadge">mode: --</span>
</header>
<nav class="tabs">
  <button id="tab-tracker" class="active" onclick="selectTab('tracker')">TRACKER</button>
  <button id="tab-inmarsat" onclick="selectTab('inmarsat')">INMARSAT</button>
</nav>
<main>

<section id="content-tracker" class="tab-content">

  <div class="card">
    <h2>Position</h2>
    <div class="position">
      <div class="label">AZ</div><div class="value" id="az-deg">—</div>
      <div class="label">EL</div><div class="value" id="el-deg">—</div>
      <div class="label">AZ STEPS</div><div class="value" id="az-steps">—</div>
      <div class="label">EL STEPS</div><div class="value" id="el-steps">—</div>
      <div class="label">MOTORS</div><div class="value" id="enabled">—</div>
    </div>
  </div>

  <div class="row">
    <div class="col">
      <div class="card">
        <h2>Jog</h2>
        <div class="kv">
          <label for="stepsize">step size</label>
          <select id="stepsize" class="t">
            <option value="0.01">0.01°</option>
            <option value="0.1" selected>0.1°</option>
            <option value="1">1°</option>
            <option value="5">5°</option>
            <option value="45">45°</option>
          </select>
        </div>
        <div class="jogpad">
          <span class="blank"></span>
          <button onclick="jog('el','+1')" title="EL+">▲</button>
          <span class="blank"></span>
          <button onclick="jog('az','-1')" title="AZ-">◀</button>
          <button class="stop" onclick="apiPost('/api/stop')" title="STOP">■</button>
          <button onclick="jog('az','+1')" title="AZ+">▶</button>
          <span class="blank"></span>
          <button onclick="jog('el','-1')" title="EL-">▼</button>
          <span class="blank"></span>
        </div>
        <small class="hint">shift = 10× step size</small>
      </div>
    </div>

    <div class="col">
      <div class="card">
        <h2>Goto</h2>
        <div class="kv">
          <label>AZ (deg)</label><input class="t" type="number" id="goto-az" step="0.01" value="0" />
          <label>EL (deg)</label><input class="t" type="number" id="goto-el" step="0.01" value="45" />
        </div>
        <div class="controls">
          <button class="t" onclick="doGoto()">GOTO</button>
          <button class="t" onclick="apiPost('/api/home')">HOME</button>
          <button class="t" onclick="apiPost('/api/park')">PARK</button>
        </div>
      </div>

      <div class="card">
        <h2>Motors</h2>
        <div class="controls">
          <button class="t" onclick="apiPost('/api/motors/enable')">ENABLE</button>
          <button class="t" onclick="apiPost('/api/motors/disable')">DISABLE</button>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Limit wizard</h2>
    <small class="hint">Captures the live position into config.yaml as the chosen limit.</small>
    <div class="controls" style="margin-top:10px">
      <button class="t" onclick="setLimit('az','min')">AZ MIN</button>
      <button class="t" onclick="setLimit('az','max')">AZ MAX</button>
      <button class="t" onclick="setLimit('el','min')">EL MIN</button>
      <button class="t" onclick="setLimit('el','max')">EL MAX</button>
    </div>
  </div>

  <div class="card">
    <h2>Keyboard</h2>
    <div class="kbdgrid">
      <div><kbd>←</kbd> <kbd>→</kbd> jog AZ</div>
      <div><kbd>↑</kbd> <kbd>↓</kbd> jog EL</div>
      <div><kbd>shift</kbd> + arrow — fast (×10)</div>
      <div><kbd>space</kbd> stop</div>
      <div><kbd>h</kbd> home</div>
      <div><kbd>p</kbd> park</div>
      <div><kbd>e</kbd> toggle motors</div>
    </div>
  </div>
</section>

<section id="content-inmarsat" class="tab-content hidden">
  <div class="card">
    <h2>Inmarsat sniffer</h2>
    <p>Not configured yet — pending hardware/integration.</p>
    <p>The C sidecar (<code>vendor/inmarsat-sniffer</code>) is not vendored on this build.
       The dashboard slot is wired up and will go live once the binary lands.</p>
    <div id="sniffer-badge" class="statusbadge">
      <span class="dot red"></span><span id="sniffer-text">OFFLINE — stub</span>
    </div>
    <p style="margin-top:14px"><a href="/docs/archive/merge_plan.html" target="_blank" rel="noopener">docs/archive/merge_plan.html →</a></p>
    <small class="hint">target: <span id="sniffer-target">—</span></small>
  </div>
</section>

</main>

<script>
let activeTab = 'tracker';

function selectTab(name) {
  activeTab = name;
  document.getElementById('tab-tracker').classList.toggle('active', name === 'tracker');
  document.getElementById('tab-inmarsat').classList.toggle('active', name === 'inmarsat');
  document.getElementById('content-tracker').classList.toggle('hidden', name !== 'tracker');
  document.getElementById('content-inmarsat').classList.toggle('hidden', name !== 'inmarsat');
}

async function apiPost(path, body) {
  const opts = { method: 'POST', headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  try {
    const r = await fetch(path, opts);
    return await r.json().catch(() => ({}));
  } catch (e) { console.error(e); return null; }
}

function currentStep(shift) {
  const v = parseFloat(document.getElementById('stepsize').value);
  return shift ? v * 10 : v;
}

function jog(axis, dir, shift) {
  return apiPost('/api/jog', { axis, direction: dir, step_size_deg: currentStep(!!shift) });
}

function doGoto() {
  const az = parseFloat(document.getElementById('goto-az').value);
  const el = parseFloat(document.getElementById('goto-el').value);
  return apiPost('/api/goto', { az, el });
}

function setLimit(axis, limit) {
  return apiPost('/api/set-limit', { axis, limit });
}

document.addEventListener('keydown', (ev) => {
  if (activeTab !== 'tracker') return;
  if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'SELECT') return;
  const shift = ev.shiftKey;
  switch (ev.key) {
    case 'ArrowLeft':  jog('az', '-1', shift); ev.preventDefault(); break;
    case 'ArrowRight': jog('az', '+1', shift); ev.preventDefault(); break;
    case 'ArrowUp':    jog('el', '+1', shift); ev.preventDefault(); break;
    case 'ArrowDown':  jog('el', '-1', shift); ev.preventDefault(); break;
    case ' ':          apiPost('/api/stop'); ev.preventDefault(); break;
    case 'h': case 'H': apiPost('/api/home'); break;
    case 'p': case 'P': apiPost('/api/park'); break;
    case 'e': case 'E':
      if (lastEnabled) apiPost('/api/motors/disable');
      else             apiPost('/api/motors/enable');
      break;
  }
});

let lastEnabled = false;

function applyStatus(s) {
  if (!s || s.error) return;
  document.getElementById('az-deg').textContent  = (s.az_deg ?? 0).toFixed(3) + '°';
  document.getElementById('el-deg').textContent  = (s.el_deg ?? 0).toFixed(3) + '°';
  document.getElementById('az-steps').textContent = s.az_steps;
  document.getElementById('el-steps').textContent = s.el_steps;
  document.getElementById('enabled').textContent = s.enabled ? 'ENABLED' : 'disabled';
  document.getElementById('modebadge').textContent = 'mode: ' + (s.mode || '--');
  lastEnabled = !!s.enabled;
}

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(proto + '://' + location.host + '/ws');
  ws.onmessage = (ev) => {
    try { applyStatus(JSON.parse(ev.data)); } catch (e) {}
  };
  ws.onclose = () => setTimeout(connectWS, 2000);
}
connectWS();

async function pollSniffer() {
  try {
    const r = await fetch('/api/sniffer/status');
    const j = await r.json();
    const dot = document.querySelector('#sniffer-badge .dot');
    const txt = document.getElementById('sniffer-text');
    document.getElementById('sniffer-target').textContent = j.configured_target || '—';
    dot.classList.remove('red', 'yellow', 'green');
    if (j.enabled) {
      dot.classList.add('green'); txt.textContent = 'ONLINE';
    } else if ((j.reason || '').includes('stub')) {
      dot.classList.add('red'); txt.textContent = 'OFFLINE — stub';
    } else {
      dot.classList.add('yellow'); txt.textContent = 'OFFLINE — ' + (j.reason || '?');
    }
  } catch (e) { /* keep last state */ }
}
pollSniffer();
setInterval(pollSniffer, 5000);
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.get("/docs/archive/merge_plan.html", response_class=HTMLResponse)
async def merge_plan_passthrough() -> HTMLResponse:
    p = Path("docs/archive/merge_plan.html")
    if p.exists():
        return HTMLResponse(p.read_text(encoding="utf-8"))
    return HTMLResponse("<pre>merge_plan.html not present</pre>", status_code=404)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main() -> None:
    parser = argparse.ArgumentParser(prog="web.app")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--config", default="tracker/config.yaml")
    parser.add_argument("--sim", action="store_true")
    args = parser.parse_args()

    global CONFIG_PATH, SIM_FORCED
    CONFIG_PATH = Path(args.config)
    SIM_FORCED = bool(args.sim)
    os.environ.setdefault("SPACE_STATION_CONFIG", str(CONFIG_PATH))

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
