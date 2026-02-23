"""
Space Station Tracker — Web Control Panel
FastAPI-based GUI for bench-testing the antenna tracker over WiFi.

Usage:
    python web/app.py [--host 0.0.0.0] [--port 8080]
"""

import asyncio
import json
import os
import sys
import time
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

# Add parent directory to path so tracker package can be imported.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title="Space Station Tracker")

# ---------------------------------------------------------------------------
# Simulation tracker — used when real hardware is not available
# ---------------------------------------------------------------------------

class SimTracker:
    """Mimics AntennaTracker interface; runs entirely in memory (no GPIO)."""

    STEPS_PER_DEG_AZ = 160.0   # 1/16 microstep, 5:1 belt
    STEPS_PER_DEG_EL = 160.0

    def __init__(self):
        self.az_steps: int = 0
        self.el_steps: int = 0
        self.enabled: bool = False
        self.moving: bool = False
        self.jog_size_deg: float = 1.0
        self.limits = {
            "az_min": -180.0,
            "az_max":  180.0,
            "el_min":    0.0,
            "el_max":   90.0,
        }
        self.home_switch_enabled: bool = False
        self._sim = True

    # -- helpers --

    @property
    def az_deg(self) -> float:
        return self.az_steps / self.STEPS_PER_DEG_AZ

    @property
    def el_deg(self) -> float:
        return self.el_steps / self.STEPS_PER_DEG_EL

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    # -- control interface --

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def stop(self):
        self.moving = False

    def jog(self, axis: str, steps: int, direction: str):
        """Move axis by a number of steps in given direction."""
        if not self.enabled:
            return
        sign = 1 if direction == "cw" else -1
        delta = sign * steps
        if axis == "az":
            new_deg = self._clamp(
                self.az_deg + delta / self.STEPS_PER_DEG_AZ,
                self.limits["az_min"], self.limits["az_max"]
            )
            self.az_steps = round(new_deg * self.STEPS_PER_DEG_AZ)
        elif axis == "el":
            new_deg = self._clamp(
                self.el_deg + delta / self.STEPS_PER_DEG_EL,
                self.limits["el_min"], self.limits["el_max"]
            )
            self.el_steps = round(new_deg * self.STEPS_PER_DEG_EL)

    def goto(self, az: float, el: float):
        if not self.enabled:
            return
        az = self._clamp(az, self.limits["az_min"], self.limits["az_max"])
        el = self._clamp(el, self.limits["el_min"], self.limits["el_max"])
        self.az_steps = round(az * self.STEPS_PER_DEG_AZ)
        self.el_steps = round(el * self.STEPS_PER_DEG_EL)

    def home(self):
        self.az_steps = 0
        self.el_steps = 0

    def park(self):
        self.goto(0.0, 0.0)

    def set_limit(self, axis: str, limit: str, value: float):
        key = f"{axis}_{limit}"
        if key in self.limits:
            self.limits[key] = value

    def get_status(self) -> dict:
        return {
            "az_deg":    round(self.az_deg, 4),
            "el_deg":    round(self.el_deg, 4),
            "az_steps":  self.az_steps,
            "el_steps":  self.el_steps,
            "enabled":   self.enabled,
            "moving":    self.moving,
            "jog_size":  self.jog_size_deg,
            "limits":    self.limits,
            "home_switch_enabled": self.home_switch_enabled,
            "sim":       getattr(self, "_sim", False),
            "timestamp": time.time(),
        }

    def get_config(self) -> dict:
        return {
            "steps_per_deg_az": self.STEPS_PER_DEG_AZ,
            "steps_per_deg_el": self.STEPS_PER_DEG_EL,
            "limits":           self.limits,
            "home_switch_enabled": self.home_switch_enabled,
            "jog_size":         self.jog_size_deg,
            "sim":              getattr(self, "_sim", False),
        }


# ---------------------------------------------------------------------------
# Global tracker instance
# ---------------------------------------------------------------------------

tracker: Optional[SimTracker] = None


@app.on_event("startup")
async def startup():
    global tracker
    tracker = SimTracker()
    print("Running in SIM mode — use /debug for direct motor control")


# ---------------------------------------------------------------------------
# HTML dashboard (embedded)
# ---------------------------------------------------------------------------

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SPACE STATION — Tracker Control</title>
<style>
  /* ── Reset & base ─────────────────────────────────────────────── */
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --green:   #00ff00;
    --dkgreen: #008800;
    --red:     #ff2222;
    --dkred:   #aa0000;
    --yellow:  #ffcc00;
    --bg:      #0a0a0a;
    --bg2:     #111111;
    --bg3:     #1a1a1a;
    --border:  #1e4a1e;
    --text:    #00cc00;
    --dim:     #005500;
  }

  html, body {
    background: var(--bg);
    color: var(--green);
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
    min-height: 100vh;
  }

  /* ── Scrollbar ─────────────────────────────────────────────────── */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--dkgreen); }

  /* ── Layout ────────────────────────────────────────────────────── */
  .container {
    max-width: 860px;
    margin: 0 auto;
    padding: 12px 12px 40px;
  }

  /* ── Header ────────────────────────────────────────────────────── */
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px;
    margin-bottom: 18px;
  }

  .logo {
    font-size: 1.4rem;
    font-weight: bold;
    letter-spacing: 0.2em;
    color: var(--green);
    text-transform: uppercase;
  }

  .logo span {
    color: var(--dkgreen);
    font-size: 0.85rem;
    display: block;
    letter-spacing: 0.1em;
    margin-top: 2px;
  }

  .conn-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.8rem;
    color: var(--dim);
  }

  .led {
    width: 10px; height: 10px;
    border-radius: 50%;
    background: var(--dkred);
    box-shadow: 0 0 6px var(--dkred);
    transition: all 0.3s;
  }
  .led.on  { background: var(--green); box-shadow: 0 0 8px var(--green); }
  .led.off { background: var(--dkred); box-shadow: 0 0 6px var(--dkred); }

  /* ── Bench-mode banner ─────────────────────────────────────────── */
  #bench-banner {
    display: none;
    background: #1a1000;
    border: 1px solid var(--yellow);
    color: var(--yellow);
    padding: 7px 12px;
    font-size: 0.82rem;
    letter-spacing: 0.05em;
    margin-bottom: 14px;
    border-radius: 2px;
  }

  #sim-banner {
    display: none;
    background: #0a000a;
    border: 1px solid #8844ff;
    color: #bb88ff;
    padding: 7px 12px;
    font-size: 0.82rem;
    letter-spacing: 0.05em;
    margin-bottom: 14px;
    border-radius: 2px;
  }

  /* ── Section card ──────────────────────────────────────────────── */
  .card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: 14px 16px;
    margin-bottom: 14px;
  }

  .card h2 {
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    color: var(--dkgreen);
    text-transform: uppercase;
    margin-bottom: 12px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
  }

  /* ── Position display ──────────────────────────────────────────── */
  .pos-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .pos-item {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 2px;
    padding: 12px;
  }

  .pos-label {
    font-size: 0.7rem;
    color: var(--dim);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 4px;
  }

  .pos-deg {
    font-size: 2.2rem;
    font-weight: bold;
    color: var(--green);
    letter-spacing: 0.02em;
    line-height: 1.1;
  }

  .pos-steps {
    font-size: 0.75rem;
    color: var(--dkgreen);
    margin-top: 3px;
  }

  .motor-status {
    margin-top: 12px;
    font-size: 0.85rem;
    letter-spacing: 0.08em;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    display: inline-block;
    background: var(--dkred);
  }
  .status-dot.enabled { background: var(--green); box-shadow: 0 0 5px var(--green); }

  /* ── Buttons (base) ────────────────────────────────────────────── */
  button {
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.82rem;
    letter-spacing: 0.08em;
    cursor: pointer;
    border-radius: 2px;
    border: 1px solid var(--dkgreen);
    background: transparent;
    color: var(--green);
    padding: 8px 14px;
    transition: background 0.15s, color 0.15s, box-shadow 0.15s;
    text-transform: uppercase;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
  }

  button:hover {
    background: #001a00;
    box-shadow: 0 0 6px var(--dkgreen);
  }

  button:active {
    background: #003300;
  }

  button.stop-btn {
    border-color: var(--red);
    color: var(--red);
  }
  button.stop-btn:hover {
    background: #1a0000;
    box-shadow: 0 0 6px var(--red);
  }

  button.warn-btn {
    border-color: var(--yellow);
    color: var(--yellow);
  }
  button.warn-btn:hover {
    background: #1a1200;
    box-shadow: 0 0 6px var(--yellow);
  }

  button:disabled {
    opacity: 0.35;
    cursor: not-allowed;
    box-shadow: none;
  }

  /* ── Jog pad ────────────────────────────────────────────────────── */
  .jog-outer {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .jog-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .jog-btn {
    width: 68px;
    height: 52px;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
  }

  .jog-btn.stop-btn {
    background: #100000;
    width: 68px;
    height: 52px;
  }

  .jog-label {
    font-size: 0.65rem;
    color: var(--dim);
    letter-spacing: 0.1em;
    text-align: center;
    width: 68px;
  }

  .jog-size-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 8px;
  }

  .jog-size-row label {
    font-size: 0.72rem;
    color: var(--dkgreen);
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  select {
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.82rem;
    background: var(--bg3);
    color: var(--green);
    border: 1px solid var(--dkgreen);
    padding: 5px 8px;
    border-radius: 2px;
    cursor: pointer;
    outline: none;
  }

  select:focus { box-shadow: 0 0 5px var(--dkgreen); }

  /* ── Control button row ─────────────────────────────────────────── */
  .ctrl-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .ctrl-row button { flex: 1 1 100px; }

  /* ── GOTO panel ─────────────────────────────────────────────────── */
  .goto-row {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: 10px;
  }

  .goto-field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1 1 100px;
  }

  .goto-field label {
    font-size: 0.68rem;
    color: var(--dim);
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  input[type="number"] {
    font-family: 'Courier New', Courier, monospace;
    font-size: 1rem;
    background: var(--bg3);
    color: var(--green);
    border: 1px solid var(--dkgreen);
    padding: 7px 10px;
    border-radius: 2px;
    width: 100%;
    outline: none;
  }

  input[type="number"]:focus { box-shadow: 0 0 5px var(--dkgreen); }

  /* ── Limits wizard ──────────────────────────────────────────────── */
  .limits-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 12px;
  }

  .limit-group h3 {
    font-size: 0.68rem;
    color: var(--dkgreen);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  .limit-group .btn-row {
    display: flex;
    gap: 6px;
    margin-bottom: 6px;
  }

  .limit-group .btn-row button {
    flex: 1;
    font-size: 0.74rem;
    padding: 6px 4px;
  }

  .limit-display {
    font-size: 0.78rem;
    color: var(--dkgreen);
    background: var(--bg3);
    border: 1px solid var(--border);
    padding: 6px 8px;
    border-radius: 2px;
  }

  .limit-val {
    color: var(--green);
    font-weight: bold;
  }

  /* ── Toast notifications ─────────────────────────────────────────── */
  #toast-area {
    position: fixed;
    bottom: 20px;
    right: 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    z-index: 999;
    pointer-events: none;
  }

  .toast {
    background: var(--bg2);
    border: 1px solid var(--dkgreen);
    color: var(--green);
    padding: 8px 14px;
    font-size: 0.78rem;
    border-radius: 2px;
    opacity: 0;
    transition: opacity 0.2s;
    pointer-events: none;
    letter-spacing: 0.06em;
    max-width: 260px;
  }
  .toast.show { opacity: 1; }
  .toast.err  { border-color: var(--red); color: var(--red); }

  /* ── Footer ──────────────────────────────────────────────────────── */
  footer {
    border-top: 1px solid var(--border);
    margin-top: 20px;
    padding-top: 12px;
    font-size: 0.68rem;
    color: var(--dim);
    letter-spacing: 0.08em;
    line-height: 1.8;
  }

  footer span { color: var(--dkgreen); }

  /* ── Responsive ──────────────────────────────────────────────────── */
  @media (max-width: 520px) {
    .pos-deg { font-size: 1.7rem; }
    .logo    { font-size: 1.1rem; }
    .jog-btn { width: 56px; height: 46px; font-size: 1rem; }
    .jog-label { width: 56px; }
    .limits-grid { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="container">

  <!-- ── Header ───────────────────────────────────────────────────── -->
  <header>
    <div class="logo">
      SPACE STATION
      <span>ANTENNA TRACKER v0.1</span>
    </div>
    <div class="conn-badge">
      <div class="led off" id="conn-led"></div>
      <span id="conn-text">DISCONNECTED</span>
    </div>
  </header>

  <!-- ── Banners ──────────────────────────────────────────────────── -->
  <div id="bench-banner">
    &#9888; BENCH MODE &mdash; No limit switches connected. Software limits only.
  </div>
  <div id="sim-banner">
    &#9670; SIMULATION MODE &mdash; No hardware detected. Position is virtual.
  </div>

  <!-- ── Position Display ─────────────────────────────────────────── -->
  <div class="card">
    <h2>Position</h2>
    <div class="pos-grid">
      <div class="pos-item">
        <div class="pos-label">Azimuth</div>
        <div class="pos-deg" id="az-deg">---.-&deg;</div>
        <div class="pos-steps" id="az-steps">step &mdash;</div>
      </div>
      <div class="pos-item">
        <div class="pos-label">Elevation</div>
        <div class="pos-deg" id="el-deg">---.-&deg;</div>
        <div class="pos-steps" id="el-steps">step &mdash;</div>
      </div>
    </div>
    <div class="motor-status">
      <span class="status-dot" id="motor-dot"></span>
      <span id="motor-text">Motors: UNKNOWN</span>
    </div>
  </div>

  <!-- ── Jog Pad ──────────────────────────────────────────────────── -->
  <div class="card">
    <h2>Jog Control</h2>
    <div class="jog-outer">
      <!-- EL up label -->
      <div class="jog-label">EL +</div>
      <!-- EL up -->
      <div class="jog-row">
        <button class="jog-btn" onclick="jog('el','cw',false)" title="Elevation Up (↑)">&#9650;</button>
      </div>
      <!-- Middle row: AZ left | STOP | AZ right -->
      <div class="jog-row">
        <div style="display:flex;flex-direction:column;align-items:center;gap:2px;">
          <div class="jog-label">AZ &minus;</div>
          <button class="jog-btn" onclick="jog('az','ccw',false)" title="Azimuth CCW (←)">&#9664;</button>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:2px;">
          <div class="jog-label">STOP</div>
          <button class="jog-btn stop-btn" onclick="stop()" title="Emergency Stop (Space)">&#9632;</button>
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;gap:2px;">
          <div class="jog-label">AZ +</div>
          <button class="jog-btn" onclick="jog('az','cw',false)" title="Azimuth CW (→)">&#9654;</button>
        </div>
      </div>
      <!-- EL down -->
      <div class="jog-row">
        <button class="jog-btn" onclick="jog('el','ccw',false)" title="Elevation Down (↓)">&#9660;</button>
      </div>
      <div class="jog-label">EL &minus;</div>

      <!-- Step size -->
      <div class="jog-size-row">
        <label for="jog-size">Step size</label>
        <select id="jog-size" onchange="setJogSize()">
          <option value="0.01">0.01&deg;</option>
          <option value="0.1">0.1&deg;</option>
          <option value="1" selected>1.0&deg;</option>
          <option value="10">10.0&deg;</option>
          <option value="45">45.0&deg;</option>
        </select>
      </div>
    </div>
  </div>

  <!-- ── Control buttons ─────────────────────────────────────────── -->
  <div class="card">
    <h2>Commands</h2>
    <div class="ctrl-row">
      <button onclick="home()" title="H">&#8962; HOME</button>
      <button onclick="park()" title="P">&#9632; PARK</button>
      <button id="enable-btn" onclick="toggleEnable()" title="E">ENABLE</button>
      <button class="stop-btn" onclick="stop()" title="Space">&#9632; E-STOP</button>
    </div>
  </div>

  <!-- ── GOTO panel ───────────────────────────────────────────────── -->
  <div class="card">
    <h2>Go To Position</h2>
    <div class="goto-row">
      <div class="goto-field">
        <label for="goto-az">Azimuth (&deg;)</label>
        <input type="number" id="goto-az" min="-180" max="360" step="0.1" value="0" placeholder="0.0">
      </div>
      <div class="goto-field">
        <label for="goto-el">Elevation (&deg;)</label>
        <input type="number" id="goto-el" min="0" max="90" step="0.1" value="0" placeholder="0.0">
      </div>
      <button style="flex:0 0 auto;padding:8px 22px;" onclick="gotoPosition()">&#9658; GO</button>
    </div>
  </div>

  <!-- ── Limit Wizard ─────────────────────────────────────────────── -->
  <div class="card">
    <h2>Endpoint / Limit Wizard</h2>
    <div class="limits-grid">
      <!-- AZ limits -->
      <div class="limit-group">
        <h3>Azimuth</h3>
        <div class="btn-row">
          <button onclick="captureLimit('az','min')" class="warn-btn">Set MIN</button>
          <button onclick="captureLimit('az','max')" class="warn-btn">Set MAX</button>
        </div>
        <div class="limit-display">
          MIN: <span class="limit-val" id="lim-az-min">&mdash;</span> &nbsp;
          MAX: <span class="limit-val" id="lim-az-max">&mdash;</span>
        </div>
      </div>
      <!-- EL limits -->
      <div class="limit-group">
        <h3>Elevation</h3>
        <div class="btn-row">
          <button onclick="captureLimit('el','min')" class="warn-btn">Set MIN</button>
          <button onclick="captureLimit('el','max')" class="warn-btn">Set MAX</button>
        </div>
        <div class="limit-display">
          MIN: <span class="limit-val" id="lim-el-min">&mdash;</span> &nbsp;
          MAX: <span class="limit-val" id="lim-el-max">&mdash;</span>
        </div>
      </div>
    </div>
    <div class="btn-row">
      <button onclick="saveLimits()" style="width:100%;">&#10003; SAVE ALL LIMITS</button>
    </div>
  </div>

  <!-- ── Footer ───────────────────────────────────────────────────── -->
  <footer>
    <span>Keyboard shortcuts:</span>
    Arrow keys: jog &nbsp;|&nbsp;
    Shift+Arrow: 10x step &nbsp;|&nbsp;
    Space: E-STOP &nbsp;|&nbsp;
    H: home &nbsp;|&nbsp;
    P: park &nbsp;|&nbsp;
    E: enable/disable
  </footer>

</div><!-- /container -->

<!-- ── Toast area ───────────────────────────────────────────────────── -->
<div id="toast-area"></div>

<!-- ── JavaScript ───────────────────────────────────────────────────── -->
<script>
// ── State ──────────────────────────────────────────────────────────
let motorEnabled = false;
let currentAz = 0;
let currentEl = 0;
let pendingLimits = {};   // staged limits before "Save"
let ws = null;
let wsRetryDelay = 1000;

// ── WebSocket ──────────────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws`);

  ws.onopen = () => {
    setLED(true);
    wsRetryDelay = 1000;
  };

  ws.onmessage = (ev) => {
    try {
      updateDisplay(JSON.parse(ev.data));
    } catch(e) {
      console.warn('Bad WS message', e);
    }
  };

  ws.onclose = () => {
    setLED(false);
    setTimeout(connectWS, wsRetryDelay);
    wsRetryDelay = Math.min(wsRetryDelay * 1.5, 10000);
  };

  ws.onerror = () => ws.close();
}

// ── Display update ─────────────────────────────────────────────────
function updateDisplay(s) {
  currentAz = s.az_deg;
  currentEl = s.el_deg;
  motorEnabled = s.enabled;

  document.getElementById('az-deg').textContent   = s.az_deg.toFixed(3) + '\u00b0';
  document.getElementById('az-steps').textContent = 'step ' + s.az_steps;
  document.getElementById('el-deg').textContent   = s.el_deg.toFixed(3) + '\u00b0';
  document.getElementById('el-steps').textContent = 'step ' + s.el_steps;

  const dot  = document.getElementById('motor-dot');
  const txt  = document.getElementById('motor-text');
  const ebtn = document.getElementById('enable-btn');
  if (s.enabled) {
    dot.classList.add('enabled');
    txt.textContent  = 'Motors: ENABLED';
    ebtn.textContent = 'DISABLE';
  } else {
    dot.classList.remove('enabled');
    txt.textContent  = 'Motors: DISABLED';
    ebtn.textContent = 'ENABLE';
  }

  // Banners
  document.getElementById('bench-banner').style.display =
    (!s.home_switch_enabled) ? 'block' : 'none';
  document.getElementById('sim-banner').style.display =
    s.sim ? 'block' : 'none';

  // Limits
  if (s.limits) {
    setLimitDisplay('az','min', s.limits.az_min);
    setLimitDisplay('az','max', s.limits.az_max);
    setLimitDisplay('el','min', s.limits.el_min);
    setLimitDisplay('el','max', s.limits.el_max);
  }
}

function setLimitDisplay(axis, bound, val) {
  const key = `lim-${axis}-${bound}`;
  const el  = document.getElementById(key);
  if (el && val !== undefined) el.textContent = val.toFixed(1) + '\u00b0';
}

// ── LED / connection ───────────────────────────────────────────────
function setLED(on) {
  const led  = document.getElementById('conn-led');
  const txt  = document.getElementById('conn-text');
  led.className = 'led ' + (on ? 'on' : 'off');
  txt.textContent = on ? 'CONNECTED' : 'DISCONNECTED';
}

// ── API helpers ────────────────────────────────────────────────────
async function apiPost(path, body) {
  try {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const d = await r.json();
    if (!r.ok) toast(d.detail || 'Error ' + r.status, true);
    return d;
  } catch(e) {
    toast('Network error: ' + e.message, true);
  }
}

// ── Jog ───────────────────────────────────────────────────────────
function getJogDeg(shift) {
  const base = parseFloat(document.getElementById('jog-size').value);
  return shift ? base * 10 : base;
}

async function jog(axis, dir, shift) {
  const deg = getJogDeg(shift);
  await apiPost('/api/jog', { axis, direction: dir, degrees: deg });
}

async function setJogSize() {
  const deg = parseFloat(document.getElementById('jog-size').value);
  await apiPost('/api/jog-size', { degrees: deg });
}

// ── Stop ──────────────────────────────────────────────────────────
async function stop() {
  await apiPost('/api/stop', {});
  toast('STOP');
}

// ── Home / Park ───────────────────────────────────────────────────
async function home() {
  await apiPost('/api/home', {});
  toast('Homing...');
}

async function park() {
  await apiPost('/api/park', {});
  toast('Parking...');
}

// ── Enable / Disable ──────────────────────────────────────────────
async function toggleEnable() {
  if (motorEnabled) {
    await apiPost('/api/motors/disable', {});
    toast('Motors disabled');
  } else {
    await apiPost('/api/motors/enable', {});
    toast('Motors enabled');
  }
}

// ── GOTO ──────────────────────────────────────────────────────────
async function gotoPosition() {
  const az = parseFloat(document.getElementById('goto-az').value);
  const el = parseFloat(document.getElementById('goto-el').value);
  if (isNaN(az) || isNaN(el)) { toast('Invalid coordinates', true); return; }
  await apiPost('/api/goto', { az, el });
  toast(`Goto AZ=${az.toFixed(1)} EL=${el.toFixed(1)}`);
}

// ── Limit wizard ──────────────────────────────────────────────────
function captureLimit(axis, bound) {
  const val = (axis === 'az') ? currentAz : currentEl;
  pendingLimits[`${axis}_${bound}`] = val;
  setLimitDisplay(axis, bound, val);
  toast(`${axis.toUpperCase()} ${bound.toUpperCase()} staged at ${val.toFixed(3)}\u00b0`);
}

async function saveLimits() {
  if (Object.keys(pendingLimits).length === 0) {
    toast('No limits staged yet', true);
    return;
  }
  for (const [key, value] of Object.entries(pendingLimits)) {
    const [axis, bound] = key.split('_');
    await apiPost('/api/set-limit', { axis, limit: bound, value });
  }
  pendingLimits = {};
  toast('Limits saved');
}

// ── Toast notifications ───────────────────────────────────────────
function toast(msg, isErr) {
  const area = document.getElementById('toast-area');
  const el   = document.createElement('div');
  el.className = 'toast' + (isErr ? ' err' : '');
  el.textContent = msg;
  area.appendChild(el);
  requestAnimationFrame(() => {
    el.classList.add('show');
    setTimeout(() => {
      el.classList.remove('show');
      setTimeout(() => el.remove(), 300);
    }, 2200);
  });
}

// ── Keyboard handler ──────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  // Skip if focus is inside an input
  if (['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)) return;

  switch (e.key) {
    case 'ArrowLeft':  e.preventDefault(); jog('az', 'ccw', e.shiftKey); break;
    case 'ArrowRight': e.preventDefault(); jog('az', 'cw',  e.shiftKey); break;
    case 'ArrowUp':    e.preventDefault(); jog('el', 'cw',  e.shiftKey); break;
    case 'ArrowDown':  e.preventDefault(); jog('el', 'ccw', e.shiftKey); break;
    case ' ':          e.preventDefault(); stop();          break;
    case 'h': case 'H': home();  break;
    case 'p': case 'P': park();  break;
    case 'e': case 'E': toggleEnable(); break;
  }
});

// ── Boot ──────────────────────────────────────────────────────────
connectWS();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard page."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/api/status")
async def get_status():
    """Return current tracker status."""
    return tracker.get_status()


@app.get("/api/config")
async def get_config():
    """Return tracker configuration."""
    return tracker.get_config()


@app.post("/api/jog")
async def api_jog(body: dict):
    """
    Jog an axis by a number of steps or degrees.
    Body: {"axis": "az"|"el", "direction": "cw"|"ccw",
           "steps": 100}  OR  {"degrees": 1.0}
    """
    axis      = body.get("axis", "az")
    direction = body.get("direction", "cw")

    if "degrees" in body:
        deg   = float(body["degrees"])
        spd   = (tracker.STEPS_PER_DEG_AZ if axis == "az"
                 else tracker.STEPS_PER_DEG_EL)
        steps = max(1, round(deg * spd))
    else:
        steps = int(body.get("steps", 160))

    tracker.jog(axis, steps, direction)
    return tracker.get_status()


@app.post("/api/goto")
async def api_goto(body: dict):
    """Move to absolute position. Body: {"az": 180.0, "el": 45.0}"""
    az = float(body.get("az", 0.0))
    el = float(body.get("el", 0.0))
    tracker.goto(az, el)
    return tracker.get_status()


@app.post("/api/motors/enable")
async def api_enable():
    """Enable both stepper motors."""
    tracker.enable()
    return {"ok": True, "enabled": True}


@app.post("/api/motors/disable")
async def api_disable():
    """Disable both stepper motors (de-energise coils)."""
    tracker.disable()
    return {"ok": True, "enabled": False}


@app.post("/api/stop")
async def api_stop():
    """Emergency stop — halt all motion immediately."""
    tracker.stop()
    return {"ok": True}


@app.post("/api/home")
async def api_home():
    """Run homing sequence (sim: zero position)."""
    tracker.home()
    return tracker.get_status()


@app.post("/api/park")
async def api_park():
    """Move antenna to park position (AZ=0, EL=0)."""
    tracker.park()
    return tracker.get_status()


@app.post("/api/set-limit")
async def api_set_limit(body: dict):
    """
    Save an axis limit.
    Body: {"axis": "az"|"el", "limit": "min"|"max", "value": 180.0}
    """
    axis  = body.get("axis", "az")
    limit = body.get("limit", "min")
    value = float(body.get("value", 0.0))
    tracker.set_limit(axis, limit, value)
    return {"ok": True, "limits": tracker.limits}


@app.post("/api/jog-size")
async def api_jog_size(body: dict):
    """Set the default jog step size in degrees. Body: {"degrees": 1.0}"""
    deg = float(body.get("degrees", 1.0))
    tracker.jog_size_deg = deg
    return {"ok": True, "jog_size": deg}


# ---------------------------------------------------------------------------
# WebSocket — live position feed at 0.5 s interval
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            status = tracker.get_status()
            await websocket.send_json(status)
            await asyncio.sleep(0.5)
    except (WebSocketDisconnect, Exception):
        pass  # Client disconnected — clean exit


# ---------------------------------------------------------------------------
# Debug page — direct GPIO motor testing
# ---------------------------------------------------------------------------

DEBUG_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>MOTOR DEBUG</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0a0a0a; color: #00ff00; font-family: monospace; padding: 12px; }
h1 { font-size: 1.4em; margin-bottom: 12px; text-align: center; }
.section { border: 1px solid #333; padding: 12px; margin-bottom: 12px; border-radius: 4px; }
.section h2 { font-size: 1em; margin-bottom: 8px; color: #00cc00; }
label { display: block; margin: 6px 0 2px; font-size: 0.85em; color: #888; }
input, select { background: #111; color: #0f0; border: 1px solid #333; padding: 8px;
  font-family: monospace; font-size: 1em; width: 100%; border-radius: 3px; }
.row { display: flex; gap: 8px; flex-wrap: wrap; }
.row > * { flex: 1; min-width: 80px; }
button { background: #111; color: #0f0; border: 2px solid #0f0; padding: 14px 8px;
  font-family: monospace; font-size: 1.1em; cursor: pointer; border-radius: 4px;
  width: 100%; touch-action: manipulation; }
button:active { background: #0f0; color: #000; }
.btn-red { border-color: #f00; color: #f00; }
.btn-red:active { background: #f00; color: #fff; }
.btn-yellow { border-color: #ff0; color: #ff0; }
.btn-yellow:active { background: #ff0; color: #000; }
.btn-blue { border-color: #08f; color: #08f; }
.btn-blue:active { background: #08f; color: #fff; }
#log { background: #050505; border: 1px solid #222; padding: 8px; height: 150px;
  overflow-y: auto; font-size: 0.8em; white-space: pre-wrap; color: #0a0; }
.status { padding: 6px; margin: 4px 0; font-size: 0.9em; }
.ok { color: #0f0; } .err { color: #f44; } .warn { color: #ff0; }
</style>
</head>
<body>
<h1>MOTOR DEBUG</h1>

<div class="section">
  <h2>MOTOR SELECT</h2>
  <div class="row">
    <button onclick="selMotor(1)" id="btn-m1" style="border-color:#0f0">M1 AZ (19/13/12)</button>
    <button onclick="selMotor(2)" id="btn-m2" class="btn-blue">M2 EL (18/24/4)</button>
  </div>
</div>

<div class="section">
  <h2>GPIO CONTROL</h2>
  <div class="row">
    <button onclick="holdTest()" class="btn-yellow">HOLD TEST (10s)</button>
  </div>
  <div style="height:8px"></div>
  <div class="row">
    <div><label>Direction</label>
      <select id="dir">
        <option value="cw">CW (clockwise)</option>
        <option value="ccw">CCW (counter-clockwise)</option>
      </select>
    </div>
  </div>
</div>

<div class="section">
  <h2>STEP TEST</h2>
  <div class="row">
    <div><label>Steps</label><input type="number" id="steps" value="200"></div>
    <div><label>Delay (ms)</label><input type="number" id="delay" value="10" step="1"></div>
  </div>
  <div style="height:8px"></div>
  <button onclick="runSteps()" style="font-size:1.4em; padding:18px">▶ RUN STEPS</button>
  <div style="height:8px"></div>
  <div class="row">
    <button onclick="quick(200)">200</button>
    <button onclick="quick(1600)">1600</button>
    <button onclick="quick(3200)">3200</button>
    <button onclick="quick(6400)" class="btn-yellow">6400 (1 rev)</button>
  </div>
</div>

<div class="section">
  <h2>SPEED SWEEP</h2>
  <div class="row">
    <div><label>From (ms)</label><input type="number" id="sweep_from" value="20"></div>
    <div><label>To (ms)</label><input type="number" id="sweep_to" value="2"></div>
    <div><label>Steps</label><input type="number" id="sweep_steps" value="3200"></div>
  </div>
  <div style="height:8px"></div>
  <button onclick="runSweep()" class="btn-blue">▶ SPEED SWEEP</button>
</div>

<div class="section">
  <h2>HAT CONFIG</h2>
  <div class="row">
    <div><label>Microstepping</label>
      <select id="microstep">
        <option value="1">Full step</option>
        <option value="2">1/2</option>
        <option value="4">1/4</option>
        <option value="8">1/8</option>
        <option value="16">1/16</option>
        <option value="32" selected>1/32</option>
      </select>
    </div>
    <div><label>Steps/rev (calculated)</label>
      <input type="text" id="calc_spr" value="6400" readonly style="color:#888">
    </div>
  </div>
  <div class="status" id="hat-info">DIP switches set microstepping — this is for display only</div>
</div>

<div class="section">
  <h2>LOG</h2>
  <div id="log"></div>
  <button onclick="document.getElementById('log').textContent=''" style="margin-top:6px; font-size:0.8em">Clear</button>
</div>

<div style="text-align:center; margin-top:12px">
  <a href="/" style="color:#08f">← Back to main UI</a>
</div>

<script>
let motor = 1;
const logEl = document.getElementById('log');

function log(msg, cls='ok') {
    const t = new Date().toLocaleTimeString();
    logEl.innerHTML += `<span class="${cls}">[${t}] ${msg}</span>\n`;
    logEl.scrollTop = logEl.scrollHeight;
}

function selMotor(m) {
    motor = m;
    document.getElementById('btn-m1').style.borderColor = m===1 ? '#0f0' : '#333';
    document.getElementById('btn-m1').style.color = m===1 ? '#0f0' : '#888';
    document.getElementById('btn-m2').style.borderColor = m===2 ? '#08f' : '#333';
    document.getElementById('btn-m2').style.color = m===2 ? '#08f' : '#888';
    log(`Selected Motor ${m}`);
}

async function cmd(action) {
    log(`CMD: ${action} motor=${motor}`, 'warn');
    try {
        const r = await fetch('/debug/cmd', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({motor, action})
        });
        const j = await r.json();
        if (j.ok) log(j.msg); else log(j.msg, 'err');
    } catch(e) { log('Error: '+e, 'err'); }
}

async function holdTest() {
    const secs = 10;
    log(`HOLD TEST: motor=${motor} for ${secs}s`, 'warn');
    try {
        const r = await fetch('/debug/hold', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({motor, seconds: secs})
        });
        const j = await r.json();
        if (j.ok) log(j.msg); else log(j.msg, 'err');
    } catch(e) { log('Error: '+e, 'err'); }
}

async function runSteps() {
    const steps = parseInt(document.getElementById('steps').value);
    const delay = parseFloat(document.getElementById('delay').value);
    const dir = document.getElementById('dir').value;
    log(`RUN: ${steps} steps, ${delay}ms delay, dir=${dir}, motor=${motor}`, 'warn');
    try {
        const r = await fetch('/debug/step', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({motor, steps, delay_ms: delay, dir})
        });
        const j = await r.json();
        if (j.ok) log(j.msg); else log(j.msg, 'err');
    } catch(e) { log('Error: '+e, 'err'); }
}

function quick(n) {
    document.getElementById('steps').value = n;
    runSteps();
}

async function runSweep() {
    const from_ms = parseFloat(document.getElementById('sweep_from').value);
    const to_ms = parseFloat(document.getElementById('sweep_to').value);
    const steps = parseInt(document.getElementById('sweep_steps').value);
    const dir = document.getElementById('dir').value;
    log(`SWEEP: ${steps} steps, ${from_ms}ms→${to_ms}ms, dir=${dir}, motor=${motor}`, 'warn');
    try {
        const r = await fetch('/debug/sweep', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({motor, steps, from_ms, to_ms, dir})
        });
        const j = await r.json();
        if (j.ok) log(j.msg); else log(j.msg, 'err');
    } catch(e) { log('Error: '+e, 'err'); }
}

document.getElementById('microstep').onchange = function() {
    const ms = parseInt(this.value);
    document.getElementById('calc_spr').value = 200 * ms;
};
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Debug GPIO — in-process lgpio (no subprocesses, no pin floating)
# ---------------------------------------------------------------------------

_DEBUG_MOTORS = {
    1: {"step": 19, "dir": 13, "enable": 12, "name": "AZ"},
    2: {"step": 18, "dir": 24, "enable": 4,  "name": "EL"},
}

_gpio_handle = None
_gpio_claimed = set()
_hold_task = None  # asyncio task for timed hold


def _gpio_init():
    """Open lgpio handle once, claim all motor pins."""
    global _gpio_handle, _gpio_claimed
    if _gpio_handle is not None:
        return True
    try:
        import lgpio
        _gpio_handle = lgpio.gpiochip_open(0)
        for m in _DEBUG_MOTORS.values():
            for pin in [m["step"], m["dir"], m["enable"]]:
                if pin not in _gpio_claimed:
                    lgpio.gpio_claim_output(_gpio_handle, pin, 0)
                    _gpio_claimed.add(pin)
        # Start with motors disabled (HIGH)
        for m in _DEBUG_MOTORS.values():
            lgpio.gpio_write(_gpio_handle, m["enable"], 1)
        return True
    except Exception as e:
        print(f"GPIO init failed: {e}")
        _gpio_handle = None
        return False


def _gpio_write(pin, val):
    import lgpio
    lgpio.gpio_write(_gpio_handle, pin, val)


def _gpio_step(m, steps, delay_ms, dir_val):
    """Blocking step loop — run in thread to avoid blocking event loop."""
    import time
    _gpio_write(m["enable"], 0)  # enable
    _gpio_write(m["dir"], dir_val)
    time.sleep(0.01)
    delay = delay_ms / 1000.0
    t0 = time.time()
    for _ in range(steps):
        _gpio_write(m["step"], 1)
        time.sleep(0.000005)
        _gpio_write(m["step"], 0)
        time.sleep(delay)
    elapsed = time.time() - t0
    _gpio_write(m["enable"], 1)  # disable
    return elapsed


@app.get("/debug", response_class=HTMLResponse)
async def debug_page():
    return HTMLResponse(content=DEBUG_HTML)


@app.post("/debug/hold")
async def debug_hold(body: dict):
    """Enable motor for N seconds then disable."""
    global _hold_task
    if not _gpio_init():
        return {"ok": False, "msg": "GPIO not available"}

    m = _DEBUG_MOTORS[body.get("motor", 1)]
    seconds = min(int(body.get("seconds", 10)), 120)

    # Cancel previous hold if running
    if _hold_task and not _hold_task.done():
        _hold_task.cancel()
        _gpio_write(m["enable"], 1)
        await asyncio.sleep(0.05)

    async def _do_hold():
        _gpio_write(m["enable"], 0)
        await asyncio.sleep(seconds)
        _gpio_write(m["enable"], 1)

    _hold_task = asyncio.create_task(_do_hold())
    return {"ok": True, "msg": f"Motor {m['name']} HOLD {seconds}s"}


@app.post("/debug/release")
async def debug_release(body: dict):
    """Immediately disable motor."""
    global _hold_task
    if not _gpio_init():
        return {"ok": False, "msg": "GPIO not available"}

    m = _DEBUG_MOTORS[body.get("motor", 1)]
    if _hold_task and not _hold_task.done():
        _hold_task.cancel()
    _gpio_write(m["enable"], 1)
    return {"ok": True, "msg": f"Motor {m['name']} RELEASED"}


@app.post("/debug/step")
async def debug_step(body: dict):
    """Step motor — runs in thread pool to not block the event loop."""
    if not _gpio_init():
        return {"ok": False, "msg": "GPIO not available"}

    m = _DEBUG_MOTORS[body.get("motor", 1)]
    steps = int(body.get("steps", 200))
    delay_ms = float(body.get("delay_ms", 10))
    dir_val = 1 if body.get("dir", "cw") == "cw" else 0
    dir_name = "CW" if dir_val else "CCW"

    loop = asyncio.get_event_loop()
    elapsed = await loop.run_in_executor(
        None, _gpio_step, m, steps, delay_ms, dir_val
    )
    sps = int(steps / elapsed) if elapsed > 0 else 0
    return {"ok": True, "msg": f"{steps} steps {dir_name} in {elapsed:.1f}s ({sps} sps)"}


@app.post("/debug/sweep")
async def debug_sweep(body: dict):
    """Speed sweep — runs in thread pool."""
    if not _gpio_init():
        return {"ok": False, "msg": "GPIO not available"}

    m = _DEBUG_MOTORS[body.get("motor", 1)]
    steps = int(body.get("steps", 3200))
    from_ms = float(body.get("from_ms", 20))
    to_ms = float(body.get("to_ms", 2))
    dir_val = 1 if body.get("dir", "cw") == "cw" else 0
    dir_name = "CW" if dir_val else "CCW"

    def _do_sweep():
        import time as _time
        _gpio_write(m["enable"], 0)
        _gpio_write(m["dir"], dir_val)
        _time.sleep(0.01)
        t0 = _time.time()
        for i in range(steps):
            frac = i / max(steps - 1, 1)
            delay = (from_ms + (to_ms - from_ms) * frac) / 1000.0
            _gpio_write(m["step"], 1)
            _time.sleep(0.000005)
            _gpio_write(m["step"], 0)
            _time.sleep(delay)
        elapsed = _time.time() - t0
        _gpio_write(m["enable"], 1)
        return elapsed

    loop = asyncio.get_event_loop()
    elapsed = await loop.run_in_executor(None, _do_sweep)
    return {"ok": True, "msg": f"Sweep {dir_name}: {steps} steps in {elapsed:.1f}s ({from_ms}ms->{to_ms}ms)"}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Space Station Tracker — Web Control Panel"
    )
    parser.add_argument(
        "--host", default="0.0.0.0",
        help="Bind address (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080,
        help="TCP port (default: 8080)"
    )
    parser.add_argument(
        "--reload", action="store_true",
        help="Enable auto-reload (dev mode)"
    )
    args = parser.parse_args()

    print(f"Starting Space Station Tracker UI at http://{args.host}:{args.port}")
    uvicorn.run(
        "app:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
