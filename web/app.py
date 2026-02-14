"""
Space Station web control dashboard.

FastAPI app providing:
- Real-time dish position and status display
- Manual dish control (goto, park, home)
- Live SDR waterfall display via WebSocket
- Observation target list with visibility
- Maser observation results viewer
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

logger = logging.getLogger(__name__)

app = FastAPI(title="Space Station", version="1.0")

# Static files and templates
static_dir = Path(__file__).parent / "static"
template_dir = Path(__file__).parent / "templates"
static_dir.mkdir(exist_ok=True)
template_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(template_dir))

# Global references (set during startup)
tracker = None
lnb_controller = None


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/status")
async def get_status():
    """Get current tracker status."""
    if tracker is None:
        return {"error": "Tracker not initialized", "simulation": True}
    return tracker.get_status()


@app.post("/api/goto")
async def goto_position(az: float, el: float):
    """Command dish to position."""
    if tracker is None:
        return {"error": "Tracker not initialized"}

    if not (0 <= az <= 360):
        return {"error": "Azimuth must be 0-360"}
    if not (0 <= el <= 90):
        return {"error": "Elevation must be 0-90"}

    tracker.goto(az, el, blocking=False)
    return {"status": "slewing", "target_az": az, "target_el": el}


@app.post("/api/stop")
async def stop():
    """Emergency stop."""
    if tracker:
        tracker.stop()
    return {"status": "stopped"}


@app.post("/api/park")
async def park():
    """Park the dish."""
    if tracker:
        tracker.park()
    return {"status": "parking"}


@app.post("/api/home")
async def home():
    """Home the tracker."""
    if tracker is None:
        return {"error": "Tracker not initialized"}
    success = tracker.home()
    return {"status": "homed" if success else "homing_failed"}


@app.get("/api/targets")
async def get_targets():
    """Get observable targets with current visibility."""
    from tracker.celestial import load_maser_catalog, radec_to_altaz, load_site, source_rise_set

    site = load_site()
    targets = load_maser_catalog()
    now = datetime.now(timezone.utc)

    result = []
    for t in targets:
        az, el = radec_to_altaz(t["ra_deg"], t["dec_deg"], site, now)
        info = source_rise_set(t["ra_deg"], t["dec_deg"], site)

        result.append({
            "name": t["name"],
            "molecule": t["molecule"],
            "frequency_mhz": t["frequency_mhz"],
            "peak_flux_jy": t["peak_flux_jy"],
            "az": round(az, 2),
            "el": round(el, 2),
            "visible": el > 10,
            "max_elevation": round(info["max_elevation"], 1),
            "notes": t["notes"],
        })

    # Sort by elevation (visible first, then by flux)
    result.sort(key=lambda x: (-x["visible"], -x["el"]))
    return result


@app.get("/api/lnb")
async def get_lnb_status():
    """Get LNB status."""
    if lnb_controller is None:
        return {"error": "LNB controller not initialized"}
    return lnb_controller.get_status()


@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """WebSocket for real-time status updates."""
    await websocket.accept()
    try:
        while True:
            status = tracker.get_status() if tracker else {"simulation": True}
            status["timestamp"] = datetime.now(timezone.utc).isoformat()
            await websocket.send_json(status)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass


# Create the dashboard template
DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Space Station - Radio Telescope Control</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: #0a0a1a;
            color: #00ff88;
            min-height: 100vh;
        }
        .header {
            background: #111;
            padding: 12px 20px;
            border-bottom: 1px solid #00ff88;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { font-size: 18px; }
        .header .time { color: #888; font-size: 14px; }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            padding: 15px;
        }
        .panel {
            background: #111;
            border: 1px solid #333;
            border-radius: 4px;
            padding: 15px;
        }
        .panel h2 {
            font-size: 14px;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 10px;
            border-bottom: 1px solid #222;
            padding-bottom: 5px;
        }
        .position {
            font-size: 32px;
            font-weight: bold;
            text-align: center;
            padding: 15px;
        }
        .position .label { font-size: 12px; color: #666; }
        .position .value { color: #00ff88; }
        .position .target { color: #ffaa00; font-size: 18px; }
        .status-led {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .led-green { background: #00ff88; }
        .led-red { background: #ff4444; }
        .led-yellow { background: #ffaa00; }
        .controls { display: flex; gap: 8px; flex-wrap: wrap; }
        .btn {
            background: #222;
            color: #00ff88;
            border: 1px solid #00ff88;
            padding: 8px 16px;
            cursor: pointer;
            font-family: inherit;
            font-size: 13px;
            border-radius: 2px;
        }
        .btn:hover { background: #00ff88; color: #000; }
        .btn-danger { border-color: #ff4444; color: #ff4444; }
        .btn-danger:hover { background: #ff4444; color: #000; }
        input[type="number"] {
            background: #1a1a2a;
            color: #00ff88;
            border: 1px solid #333;
            padding: 6px 10px;
            width: 80px;
            font-family: inherit;
        }
        .target-list {
            max-height: 300px;
            overflow-y: auto;
        }
        .target-row {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            border-bottom: 1px solid #1a1a2a;
            font-size: 13px;
        }
        .target-row.visible { color: #00ff88; }
        .target-row.hidden { color: #444; }
        .target-row .name { width: 140px; }
        .target-row .mol { width: 60px; color: #888; }
        .target-row .el { width: 50px; text-align: right; }
        .target-row .flux { width: 70px; text-align: right; color: #ffaa00; }
        .target-row .goto-btn {
            cursor: pointer;
            color: #00aaff;
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>SPACE STATION</h1>
        <span class="time" id="clock"></span>
    </div>

    <div class="grid">
        <div class="panel">
            <h2>Dish Position</h2>
            <div class="position">
                <div>
                    <span class="label">AZ</span><br>
                    <span class="value" id="az-pos">---.-</span>&deg;
                </div>
                <div style="margin-top:10px">
                    <span class="label">EL</span><br>
                    <span class="value" id="el-pos">---.-</span>&deg;
                </div>
                <div style="margin-top:10px">
                    <span class="label">TARGET</span><br>
                    <span class="target" id="target-pos">---</span>
                </div>
            </div>
            <div style="text-align:center; margin-top:10px">
                <span class="status-led" id="status-led"></span>
                <span id="status-text">Disconnected</span>
            </div>
        </div>

        <div class="panel">
            <h2>Controls</h2>
            <div style="margin-bottom:15px">
                <label>AZ: <input type="number" id="goto-az" min="0" max="360" step="0.1" value="0"></label>
                <label>EL: <input type="number" id="goto-el" min="0" max="90" step="0.1" value="45"></label>
                <button class="btn" onclick="gotoPos()">GOTO</button>
            </div>
            <div class="controls">
                <button class="btn" onclick="doHome()">HOME</button>
                <button class="btn" onclick="doPark()">PARK</button>
                <button class="btn btn-danger" onclick="doStop()">STOP</button>
            </div>
        </div>

        <div class="panel" style="grid-column: 1 / -1">
            <h2>Observable Targets</h2>
            <div class="target-list" id="target-list">
                <div style="color:#666">Loading targets...</div>
            </div>
        </div>
    </div>

    <script>
        // Clock
        setInterval(() => {
            document.getElementById('clock').textContent = new Date().toISOString().slice(0,19) + ' UTC';
        }, 1000);

        // WebSocket for live status
        let ws;
        function connectWS() {
            ws = new WebSocket(`ws://${location.host}/ws/status`);
            ws.onmessage = (e) => {
                const s = JSON.parse(e.data);
                document.getElementById('az-pos').textContent = s.az_position?.toFixed(2) ?? '---';
                document.getElementById('el-pos').textContent = s.el_position?.toFixed(2) ?? '---';
                document.getElementById('target-pos').textContent =
                    `AZ ${s.az_target?.toFixed(1)} EL ${s.el_target?.toFixed(1)}`;

                const led = document.getElementById('status-led');
                const txt = document.getElementById('status-text');
                if (s.is_tracking) {
                    led.className = 'status-led led-green';
                    txt.textContent = 'Tracking';
                } else if (s.is_slewing) {
                    led.className = 'status-led led-yellow';
                    txt.textContent = 'Slewing';
                } else {
                    led.className = 'status-led led-green';
                    txt.textContent = s.is_homed ? 'Ready' : 'Not homed';
                }
            };
            ws.onclose = () => {
                document.getElementById('status-led').className = 'status-led led-red';
                document.getElementById('status-text').textContent = 'Disconnected';
                setTimeout(connectWS, 3000);
            };
        }
        connectWS();

        // Controls
        async function gotoPos() {
            const az = document.getElementById('goto-az').value;
            const el = document.getElementById('goto-el').value;
            await fetch(`/api/goto?az=${az}&el=${el}`, { method: 'POST' });
        }
        async function doHome() { await fetch('/api/home', { method: 'POST' }); }
        async function doPark() { await fetch('/api/park', { method: 'POST' }); }
        async function doStop() { await fetch('/api/stop', { method: 'POST' }); }

        async function gotoTarget(az, el) {
            document.getElementById('goto-az').value = az;
            document.getElementById('goto-el').value = el;
            await gotoPos();
        }

        // Load targets
        async function loadTargets() {
            try {
                const resp = await fetch('/api/targets');
                const targets = await resp.json();
                const list = document.getElementById('target-list');
                list.innerHTML = targets.map(t => `
                    <div class="target-row ${t.visible ? 'visible' : 'hidden'}">
                        <span class="name">${t.name}</span>
                        <span class="mol">${t.molecule}</span>
                        <span class="flux">${t.peak_flux_jy} Jy</span>
                        <span class="el">${t.el.toFixed(1)}&deg;</span>
                        ${t.visible ? `<span class="goto-btn" onclick="gotoTarget(${t.az},${t.el})">GOTO</span>` : ''}
                    </div>
                `).join('');
            } catch(e) {
                document.getElementById('target-list').innerHTML = '<div style="color:#ff4444">Failed to load targets</div>';
            }
        }
        loadTargets();
        setInterval(loadTargets, 60000);
    </script>
</body>
</html>
"""


def create_template():
    """Write the dashboard template file."""
    template_path = template_dir / "dashboard.html"
    if not template_path.exists():
        template_path.write_text(DASHBOARD_HTML)


def start_server(
    tracker_instance=None,
    lnb_instance=None,
    host: str = "0.0.0.0",
    port: int = 8080,
):
    """Start the web server."""
    global tracker, lnb_controller
    tracker = tracker_instance
    lnb_controller = lnb_instance

    create_template()

    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting dashboard at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Space Station web dashboard")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--no-tracker", action="store_true", help="Run without tracker hardware")
    args = parser.parse_args()

    tracker_inst = None
    if not args.no_tracker:
        try:
            from tracker.controller import AntennaTracker
            tracker_inst = AntennaTracker()
        except Exception as e:
            logger.warning(f"Tracker init failed: {e} -- running without hardware")

    start_server(tracker_inst, host=args.host, port=args.port)
