"""
Tire fitment and seasonal performance explorer.
Fleet Tire Optimization Strategy capstone - interactive poster display.

Run with:  streamlit run app.py

Licensed under the Apache License 2.0 (see LICENSE and NOTICE). Sources are listed in SOURCES.md.
"""

import json
import math
import time

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from tire_model import (
    COMPOUNDS, G, NEW_TREAD_MM, RAMP_RADIUS_M, SEASONS, SURFACE_KEY, SURFACE_TEMP_RANGE, VEHICLES,
    evaluate, exact_aspect, geometry, matched_aspect, pressure_at_temperature, speed_at_distance,
)

REACTION_S = 1.5
LIFT_LIMIT_KG = 23
CAR_LENGTH_M = 4.5
DEMO_SECONDS = 14
REPO_URL = "https://github.com/harrison-cormier/tire-fitment-explorer"
AUTHORS = "Harrison Cormier, Ashley Pacek and Varvara Blinova"
FUEL_DOT_STEP = 0.03

COMPOUND_COLOR = {
    "Summer": "#eb6834",
    "All-season": "#1baf7a",
    "All-weather (3PMSF)": "#eda100",
    "Winter": "#6250d6",
}

SCENARIOS = [
    dict(title="Packed snow: winter tires against the factory tire",
         season="Winter", surface="Packed snow", temp=-10, compound="Winter", dw=0, dr=0, tread=8.0),
    dict(title="Packed snow: narrower winter fitment on a smaller rim",
         season="Winter", surface="Packed snow", temp=-10, compound="Winter", dw=-20, dr=-1, tread=8.0),
    dict(title="Slush: where a narrower tire earns its keep",
         season="Winter", surface="Slush", temp=0, compound="Winter", dw=-20, dr=-1, tread=8.0),
    dict(title="Ice: every tire is slow to stop, some much slower",
         season="Winter", surface="Ice", temp=-3, compound="All-season", dw=0, dr=0, tread=8.0),
    dict(title="Standing water: a wide tire meets a summer downpour",
         season="Summer", surface="Standing water", temp=22, compound="Summer", dw=20, dr=1, tread=8.0),
    dict(title="Wet road: the same tire worn to 2 mm",
         season="Summer", surface="Wet", temp=18, compound="All-season", dw=0, dr=0, tread=2.0),
    dict(title="Hot dry road: winter tires left on into summer",
         season="Summer", surface="Dry", temp=28, compound="Winter", dw=0, dr=0, tread=8.0),
    dict(title="Hot dry road: wider, lower-profile summer fitment",
         season="Summer", surface="Dry", temp=28, compound="Summer", dw=20, dr=1, tread=8.0),
]

PAGE = "#ffffff"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e6e5e1"
SURFACE = "#fcfcfb"
SELECTED = "#2a78d6"
REFERENCE = "#8a8984"
WORSE = "#d03b3b"
LONGER = "#52514e"
TIRE = "#2b2b2a"
TREAD = "#77766f"
PANEL = "#ffffff"
BANNER = "#eef4fd"
GOOD_TEXT, NEUTRAL_TEXT, BAD_TEXT = "#0d6b49", "#1d4f8f", "#9c2424"

DARK = dict(
    PAGE="#0f1115", INK="#f2f2f0", INK_2="#b3b2ad", GRID="#30343c", SURFACE="#181b21",
    LONGER="#b5b4ae", TIRE="#4b4d52", TREAD="#9a9993", PANEL="#181b21", BANNER="#14233a",
    GOOD_TEXT="#7fe0b5", NEUTRAL_TEXT="#9cc4f5", BAD_TEXT="#ff9a9a",
)


def use_dark_theme():
    """
    Switch the page to the dark palette. Demo mode calls this so the display reads well in a dim
    room. Every component reads its colours from the module-level names above when it is drawn,
    and Streamlit re-runs the script from the top on each interaction, so replacing those names
    here changes one run only and the light palette is back as soon as demo mode is turned off.
    """
    globals().update(DARK)

# ----------------------------------------------------------------------------
# Visual components
# ----------------------------------------------------------------------------


def braking_animation(sel, ref, env, sel_label, ref_label, ref_name, surface_name, header=True):
    """
    Two cars braking side by side on a canvas. With `header` on, the top of the canvas carries
    a large heading with the road surface, temperature and braking speed so the conditions are
    readable from a distance. Demo mode turns it off because its banner already says the same
    thing, which keeps the top of the page short enough for a 13-inch laptop screen.
    """
    canvas_height = 390 if header else 306
    def sample(profile):
        idx = np.linspace(0, len(profile["t"]) - 1, 81).astype(int)
        return dict(t=profile["t"][idx].round(3).tolist(), d=profile["d"][idx].round(2).tolist(),
                    v=profile["v"][idx].round(1).tolist())

    first, other = (ref, sel) if ref["distance"] <= sel["distance"] else (sel, ref)
    data = dict(
        ref=sample(ref["profile"]), sel=sample(sel["profile"]),
        refLabel=ref_label, selLabel=sel_label, refName=ref_name, v0=env["speed"], surface=env["surface"],
        firstIsRef=first is ref, firstStop=round(first["distance"], 1),
        residual=round(speed_at_distance(other["profile"], first["distance"])),
        header=header, conditions=f"{surface_name} at {env['temp']} °C",
    )
    html = """
<style>html, body {background: __PAGE__;}</style>
<div id="wrap" style="font-family:system-ui,-apple-system,'Segoe UI',sans-serif">
  <canvas id="c" style="width:100%;height:__HEIGHT__px;border-radius:12px;display:block"></canvas>
</div>
<script>
const D = __DATA__;
const ROAD = {dry:['#474a50','#fff'], wet:['#323c4a','#fff'], flood:['#27374d','#fff'],
              slush:['#8d98a1','#0b0b0b'], snow:['#e4e9ee','#0b0b0b'], ice:['#cbdfe9','#0b0b0b']}[D.surface];
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const maxD = Math.max(D.ref.d.at(-1), D.sel.d.at(-1));
const maxT = Math.max(D.ref.t.at(-1), D.sel.t.at(-1));
const rate = Math.max(1, maxT / 7), LEAD = 0.7, HOLD = 3.2;
const TOP = D.header ? 84 : 0;
let W, H = 306 + TOP, played = 0, last = null, paused = false;

function fit() {
  const r = window.devicePixelRatio || 1;
  W = cv.clientWidth; cv.width = W * r; cv.height = H * r; ctx.setTransform(r, 0, 0, r, 0, 0);
}
function at(p, key, t) {
  if (t >= p.t.at(-1)) return p[key].at(-1);
  let i = 1; while (p.t[i] < t) i++;
  const f = (t - p.t[i-1]) / (p.t[i] - p.t[i-1] || 1);
  return p[key][i-1] + f * (p[key][i] - p[key][i-1]);
}
function car(x, y, color, braking) {
  ctx.fillStyle = 'rgba(0,0,0,.22)'; ctx.beginPath(); ctx.roundRect(x - 55, y - 11, 58, 28, 8); ctx.fill();
  ctx.fillStyle = color; ctx.beginPath(); ctx.roundRect(x - 58, y - 14, 58, 28, 8); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,.82)'; ctx.beginPath(); ctx.roundRect(x - 24, y - 10, 10, 20, 3); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,.55)'; ctx.beginPath(); ctx.roundRect(x - 48, y - 10, 7, 20, 3); ctx.fill();
  if (braking) { ctx.fillStyle = '#ff3b30'; ctx.fillRect(x - 59, y - 12, 3, 7); ctx.fillRect(x - 59, y + 5, 3, 7); }
}
function lane(p, y, color, label, t, x0, s) {
  const d = t < 0 ? D.v0 / 3.6 * t : at(p, 'd', t);
  const v = t < 0 ? D.v0 : at(p, 'v', t);
  const x = x0 + d * s, done = t >= p.t.at(-1);
  car(x, y, color, t >= 0 && !done);
  const flip = x > W - 300, tx = flip ? x - 68 : x + 12;
  const status = done ? 'Stopped in ' + p.d.at(-1).toFixed(1) + ' m' : Math.round(v) + ' km/h';
  ctx.font = '600 16px system-ui'; const lw = Math.max(ctx.measureText(label).width, 190) + 16;
  ctx.fillStyle = ROAD[0]; ctx.globalAlpha = .82; ctx.beginPath();
  ctx.roundRect(flip ? tx - lw + 8 : tx - 8, y - 46, lw, 66, 8); ctx.fill(); ctx.globalAlpha = 1;
  ctx.fillStyle = ROAD[1]; ctx.textAlign = flip ? 'right' : 'left';
  ctx.fillText(label, tx, y - 23);
  ctx.font = '700 24px system-ui'; ctx.fillText(status, tx, y + 9);
}
function frame(ms) {
  const cycle = LEAD + maxT / rate + HOLD;
  if (last !== null && !paused) played += ms - last;
  last = ms;
  const clock = (played / 1000) % cycle, t = (clock - LEAD) * rate;
  const x0 = 96, s = (W - x0 - 40) / (maxD * 1.06);
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = ROAD[0]; ctx.beginPath(); ctx.roundRect(0, 0, W, H, 12); ctx.fill();
  if (D.header) {
    ctx.fillStyle = ROAD[1]; ctx.textAlign = 'left';
    let size = 28; ctx.font = '700 28px system-ui';
    while (ctx.measureText(D.conditions).width > W - 36 && size > 15) { size--; ctx.font = '700 ' + size + 'px system-ui'; }
    ctx.fillText(D.conditions, 18, 38);
    const speed = 'Braking from ' + D.v0 + ' km/h';
    ctx.font = '600 18px system-ui'; ctx.globalAlpha = .85; ctx.fillText(speed, 18, 66);
    const hint = (rate > 1.05 ? 'Playback ' + rate.toFixed(1) + 'x real time. ' : '') + (paused ? 'Paused, click to play' : 'Click to pause');
    const used = ctx.measureText(speed).width; ctx.font = '12px system-ui'; ctx.globalAlpha = .7;
    if (used + ctx.measureText(hint).width + 60 < W) { ctx.textAlign = 'right'; ctx.fillText(hint, W - 16, 66); }
    ctx.globalAlpha = .25; ctx.fillRect(0, 82, W, 1);
  }
  const mid = TOP + 122;
  ctx.strokeStyle = ROAD[1]; ctx.globalAlpha = .35; ctx.setLineDash([18, 16]); ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(0, mid); ctx.lineTo(W, mid); ctx.stroke(); ctx.setLineDash([]);
  const step = [5, 10, 20, 50, 100].find(k => maxD / k <= 9) || 200;
  ctx.fillStyle = ROAD[1]; ctx.globalAlpha = 1; ctx.font = '13px system-ui'; ctx.textAlign = 'center';
  for (let m = 0; m <= maxD * 1.06; m += step) {
    ctx.fillRect(x0 + m * s, H - 32, 1, 8); ctx.fillText(m + ' m', x0 + m * s, H - 8);
  }
  ctx.globalAlpha = .8; ctx.fillRect(x0, TOP + 10, 2, H - TOP - 48);
  ctx.textAlign = 'right'; ctx.font = '600 13px system-ui';
  ctx.fillText('Brakes on', x0 - 8, TOP + 24); ctx.globalAlpha = 1;
  if (t >= Math.min(D.ref.t.at(-1), D.sel.t.at(-1)) && D.residual > 0) {
    const xs = x0 + D.firstStop * s;
    const msg = (D.firstIsRef ? 'Selected setup' : D.refName) + ' still doing ' + D.residual + ' km/h at this point';
    ctx.strokeStyle = ROAD[1]; ctx.setLineDash([5, 5]); ctx.beginPath();
    ctx.moveTo(xs, D.firstIsRef ? mid - 98 : mid); ctx.lineTo(xs, D.firstIsRef ? mid : mid + 98); ctx.stroke(); ctx.setLineDash([]);
    ctx.font = '600 16px system-ui'; const mw = ctx.measureText(msg).width + 28;
    const mx = Math.min(Math.max(xs - mw / 2, 8), W - mw - 8);
    ctx.fillStyle = ROAD[1]; ctx.beginPath(); ctx.roundRect(mx, mid - 16, mw, 32, 16); ctx.fill();
    ctx.fillStyle = ROAD[0]; ctx.textAlign = 'left'; ctx.fillText(msg, mx + 14, mid + 6);
  }
  lane(D.ref, mid - 64, '#b9b8b3', D.refLabel, t, x0, s);
  lane(D.sel, mid + 64, '#2a78d6', D.selLabel, t, x0, s);
  requestAnimationFrame(frame);
}
cv.style.cursor = 'pointer'; cv.addEventListener('click', () => { paused = !paused; });
fit(); window.addEventListener('resize', fit); requestAnimationFrame(frame);
</script>
""".replace("__DATA__", json.dumps(data)).replace("__HEIGHT__", str(canvas_height)).replace("__PAGE__", PAGE)
    st.iframe(html, height=canvas_height + 8)


def difference(delta, unit, more, less):
    """Plain words for a change from the factory size, and whether there is a change at all."""
    amount = round(abs(delta))
    if amount == 0:
        return "same as factory", False
    if unit == "inch" and amount != 1:
        unit = "inches"
    return f"{amount} {unit} {more if delta > 0 else less}", True


def tire_diagram(sel, ref, ref_name):
    """
    Picture of the selected tire for a poster audience, in three parts.

    The top row spells out the size code as it is printed on a sidewall and says what each
    number means and how it differs from the factory size. The middle row draws the tire to
    scale from the front (where width shows) and from the side (where rim and sidewall show),
    with the factory size as a dashed outline standing on the same ground line. The bottom
    row draws the footprint on the road as a tread print, in the same rubber colour and groove
    pattern as the front view. The drawing scale is fixed per vehicle so the tire
    visibly grows and shrinks as the controls move, and only tightens for very tall tires.
    """
    g, f = sel["geo"], ref["geo"]
    s = 150 / max(g["diameter"], 1.12 * f["diameter"])
    ground, front_x, side_x = 318, 72, 256
    ghost = f'fill="none" stroke="{REFERENCE}" stroke-width="1.5" stroke-dasharray="5 4"'
    halo = f'fill="none" stroke="{PANEL}" stroke-opacity="0.55" stroke-width="3"'
    label = f'fill="{INK_2}" font-size="12"'
    value = f'fill="{INK}" font-size="12.5" font-weight="700"'
    measure = f'stroke="{SELECTED}" stroke-width="1.5"'

    def front(geo, outline):
        w, h = geo["width"] * s, geo["diameter"] * s
        x, y, corner = front_x - w / 2, ground - h, min(geo["width"] * s * 0.3, 16)
        box = f'x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{corner:.1f}"'
        if outline:
            return f'<rect {box} {halo}/><rect {box} {ghost}/>'
        grooves = "".join(f'<line x1="{x + w * k:.1f}" y1="{y + 5:.1f}" x2="{x + w * k:.1f}" y2="{ground - 5}" '
                          f'stroke="{TREAD}" stroke-width="2"/>' for k in (0.3, 0.5, 0.7))
        cuts = "".join(f'<line x1="{x + 3:.1f}" y1="{yy:.1f}" x2="{x + w * 0.3 - 3:.1f}" y2="{yy + 3:.1f}" stroke="{TREAD}"/>'
                       f'<line x1="{x + w * 0.7 + 3:.1f}" y1="{yy + 3:.1f}" x2="{x + w - 3:.1f}" y2="{yy:.1f}" stroke="{TREAD}"/>'
                       for yy in np.arange(y + corner, ground - corner, 9))
        return f'<rect {box} fill="{TIRE}"/>{grooves}{cuts}'

    def side(geo, outline):
        r_tire, r_rim = geo["diameter"] / 2 * s, geo["rim"] * 25.4 / 2 * s
        centre = f'cx="{side_x}" cy="{ground - r_tire:.1f}"'
        if outline:
            return "".join(f'<circle {centre} r="{r:.1f}" {halo}/><circle {centre} r="{r:.1f}" {ghost}/>'
                           for r in (r_tire, r_rim))
        cy = ground - r_tire
        spokes = "".join(f'<line x1="{side_x}" y1="{cy:.1f}" x2="{side_x + 0.9 * r_rim * math.sin(a):.1f}" '
                         f'y2="{cy - 0.9 * r_rim * math.cos(a):.1f}" stroke="#bdbcb7" stroke-width="{r_rim * 0.2:.1f}" '
                         f'stroke-linecap="round"/>' for a in np.arange(5) * 2 * math.pi / 5 + math.pi / 5)
        return (f'<circle {centre} r="{r_tire:.1f}" fill="{TIRE}"/>'
                f'<circle {centre} r="{r_tire - 4:.1f}" fill="none" stroke="{TREAD}" stroke-opacity="0.5"/>'
                f'<circle {centre} r="{r_rim:.1f}" fill="#e9e8e4" stroke="#a9a8a3"/>{spokes}'
                f'<circle {centre} r="{r_rim * 0.2:.1f}" fill="#a9a8a3"/>')

    def footprint(result, k, outline):
        w, h = result["patch_width"] * k, result["patch_length"] * k
        x, y, corner = front_x - w / 2, 404 - h / 2, min(h / 2, w / 2, 14)
        box = f'x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{corner:.1f}"'
        if outline:
            return f'<rect {box} {ghost}/>'
        gap = f'stroke="{SURFACE}" stroke-linecap="round"'
        grooves = "".join(f'<line x1="{x + w * j:.1f}" y1="{y + 3:.1f}" x2="{x + w * j:.1f}" y2="{y + h - 3:.1f}" '
                          f'{gap} stroke-width="3"/>' for j in (0.3, 0.5, 0.7))
        cuts = "".join(f'<line x1="{x + 4:.1f}" y1="{yy:.1f}" x2="{x + w * 0.3 - 4:.1f}" y2="{yy + 3:.1f}" {gap} stroke-width="1.5"/>'
                       f'<line x1="{x + w * 0.7 + 4:.1f}" y1="{yy + 3:.1f}" x2="{x + w - 4:.1f}" y2="{yy:.1f}" {gap} stroke-width="1.5"/>'
                       for yy in np.arange(y + corner * 0.6, y + h - corner * 0.6 - 2, 8))
        return f'<rect {box} fill="{TIRE}"/>{grooves}{cuts}'

    def code_column(x, number, line_1, line_2, change):
        words, changed = change
        note = f'fill="{SELECTED}" font-weight="700"' if changed else f'fill="{REFERENCE}"'
        return (f'<text x="{x}" y="62" text-anchor="middle" fill="{INK}" font-size="36" font-weight="700">{number}</text>'
                f'<text x="{x}" y="80" text-anchor="middle" {label}>{line_1}</text>'
                f'<text x="{x}" y="94" text-anchor="middle" {label}>{line_2}</text>'
                f'<text x="{x}" y="110" text-anchor="middle" font-size="12" {note}>{words}</text>')

    same_size = all(g[k] == f[k] for k in ("width", "aspect", "rim"))
    r_tire, r_rim = g["diameter"] / 2 * s, g["rim"] * 25.4 / 2 * s
    top, cy, half = ground - 2 * r_tire, ground - r_tire, g["width"] * s / 2
    note_x = side_x + max(r_tire, f["diameter"] / 2 * s) + 8
    k = min(0.42, 60 / max(sel["patch_length"], ref["patch_length"]), 92 / max(sel["patch_width"], ref["patch_width"]))
    patch_change = ", ".join(words for words, changed in (
        difference(sel["patch_width"] - ref["patch_width"], "mm", "wider", "narrower"),
        difference(sel["patch_length"] - ref["patch_length"], "mm", "longer", "shorter")) if changed)
    height_words, height_changed = difference(g["diameter"] - f["diameter"], "mm", "taller", "shorter")

    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 444" role="img"
     font-family="system-ui,-apple-system,Segoe UI,sans-serif" aria-label="Tire size {g['width']}/{g['aspect']}R{g['rim']} drawn to scale against the factory size">
  <rect x="0.5" y="0.5" width="419" height="443" rx="12" fill="{SURFACE}" stroke="{GRID}"/>
  <text x="16" y="22" fill="{INK}" font-size="13" font-weight="600">What the size printed on the tire means</text>
  {code_column(76, g["width"], "width", "in millimetres", difference(g["width"] - f["width"], "mm", "wider", "narrower"))}
  <text x="143" y="60" text-anchor="middle" fill="{REFERENCE}" font-size="32">/</text>
  {code_column(210, g["aspect"], "sidewall height", "as a % of the width", difference(g["sidewall"] - f["sidewall"], "mm", "taller", "shorter"))}
  <text x="277" y="60" text-anchor="middle" fill="{REFERENCE}" font-size="30">R</text>
  {code_column(344, g["rim"], "wheel (rim) size", "in inches", difference(g["rim"] - f["rim"], "inch", "larger", "smaller"))}

  <text x="{front_x}" y="136" text-anchor="middle" {label} font-weight="600">From the front</text>
  <text x="{side_x}" y="136" text-anchor="middle" {label} font-weight="600">From the side</text>
  <line x1="326" y1="132" x2="348" y2="132" {ghost}/>
  <text x="352" y="136" fill="{INK_2}" font-size="11">factory size</text>
  <line x1="12" y1="{ground}" x2="408" y2="{ground}" stroke="{GRID}" stroke-width="2"/>
  {front(g, False)}{side(g, False)}
  {"" if same_size else front(f, True) + side(f, True)}

  <path d="M{front_x - half:.1f} {top - 13:.1f}v8m0 -4h{2 * half:.1f}m0 -4v8" fill="none" {measure}/>
  <text x="{front_x}" y="{top - 16:.1f}" text-anchor="middle" {value}>{g["width"]} mm wide</text>
  <path d="M136 {top:.1f}h8m-4 0v{2 * r_tire:.1f}m-4 0h8" fill="none" {measure}/>
  <text transform="translate(131 {cy:.1f}) rotate(-90)" text-anchor="middle" {value}>{g["diameter"]:.0f} mm tall</text>
  <path d="M{side_x - r_rim:.1f} {cy:.1f}h{2 * r_rim:.1f}" fill="none" {measure}/>
  <rect x="{side_x - 33}" y="{cy - 27:.1f}" width="66" height="19" rx="9.5" fill="{PANEL}" fill-opacity="0.92"/>
  <text x="{side_x}" y="{cy - 13:.1f}" text-anchor="middle" {value}>{g["rim"]}-inch rim</text>
  <path d="M{side_x + r_rim:.1f} {cy - 5:.1f}v10m0 -5h{r_tire - r_rim:.1f}m0 -5v10" fill="none" stroke="#ffffff" stroke-width="1.5"/>
  <text x="{note_x:.1f}" y="{cy - 3:.1f}" {label}>sidewall</text>
  <text x="{note_x:.1f}" y="{cy + 12:.1f}" {value}>{g["sidewall"]:.0f} mm</text>
  <text x="{side_x}" y="336" text-anchor="middle" {label}>{"Same overall height as the factory size" if not height_changed
                                                             else height_words.capitalize() + " overall than the factory size"}</text>

  <line x1="12" y1="348" x2="408" y2="348" stroke="{GRID}"/>
  <text x="16" y="366" {label} font-weight="600">Footprint on the road, seen from above</text>
  {footprint(sel, k, False)}{footprint(ref, k, True)}
  <path d="M19 428v-44m-4 6l4 -7l4 7" fill="none" stroke="{INK_2}" stroke-width="1.5"/>
  <text transform="translate(11 406) rotate(-90)" text-anchor="middle" fill="{INK_2}" font-size="10.5">travel</text>
  <text x="134" y="394" {value}>{sel["patch_width"]:.0f} mm wide, {sel["patch_length"]:.0f} mm long</text>
  <text x="134" y="411" {label}>{patch_change.capitalize() + f" than {ref_name.lower()}" if patch_change else f"Same footprint as the {ref_name.lower()}"}</text>
  <text x="134" y="428" {label}>Depends on size, tire type and pressure</text>
</svg>"""
    st.image(svg.strip(), width="stretch")


def style(fig, height=340, title=None):
    fig.update_layout(
        height=height, title=dict(text=title, font=dict(size=15, color=INK), x=0.01, xanchor="left", y=0.97, yanchor="top"),
        margin=dict(l=70, r=20, t=84 if title else 20, b=56),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", size=13, color=INK_2),
        hoverlabel=dict(bgcolor="white", font_size=13),
        legend=dict(orientation="h", y=1.03, yanchor="bottom", x=0),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, ticks="outside", tickcolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    return fig


def show(fig):
    st.plotly_chart(fig, width="stretch", theme=None, config=dict(displayModeBar=False))


def sweep_chart(xs, ys, current_x, current_y, x_title, y_range, title, tick_suffix=""):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color=SELECTED, width=2),
                             marker=dict(size=7), hovertemplate="%{x}" + tick_suffix + ": %{y:.1f} m<extra></extra>"))
    fig.add_trace(go.Scatter(x=[current_x], y=[current_y], mode="markers+text", text=[f"Selected: {current_y:.1f} m"],
                             textposition="top center", textfont=dict(color=INK, size=13),
                             marker=dict(size=14, color=SELECTED, line=dict(color=SURFACE, width=2)), hoverinfo="skip"))
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title=x_title, tickvals=xs, ticksuffix=tick_suffix)
    fig.update_yaxes(title="Braking distance (m)", range=y_range)
    return style(fig, 330, title).update_layout(margin=dict(t=50))


def tornado_chart(changes):
    changes = sorted(changes, key=lambda c: c[1])
    labels = [c[0] for c in changes]
    values = [c[1] for c in changes]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=[SELECTED if v < 0 else LONGER for v in values], cornerradius=4),
        text=[f"{round(v, 1) + 0:+.1f}%" for v in values], textposition="outside", textfont=dict(color=INK),
        hovertemplate="%{y}: %{x:+.1f}% braking distance<extra></extra>", cliponaxis=False,
    ))
    span = max(max(abs(v) for v in values) * 1.25, 5)
    fig.update_xaxes(range=[-span, span], ticksuffix="%", zeroline=True, zerolinecolor=INK_2, zerolinewidth=1)
    fig.update_layout(bargap=0.35)
    fig = style(fig, 36 * len(changes) + 110,
                 "Change in braking distance from one change at a time (blue shorter, dark grey longer)")
    return fig.update_layout(margin=dict(l=250, t=50, b=40))


def temperature_chart(cfg, env, road, current_temp):
    coldest = -15 if road == "wet" else -30
    temps = np.arange(coldest, 36, 1)
    fig = go.Figure()
    for compound in COMPOUNDS:
        ys = [evaluate({**cfg, "compound": compound}, {**env, "surface": road, "temp": float(t)})["distance"] for t in temps]
        fig.add_trace(go.Scatter(x=temps, y=ys, mode="lines", name=compound,
                                 line=dict(color=COMPOUND_COLOR[compound], width=2),
                                 hovertemplate=compound + " at %{x} °C: %{y:.1f} m<extra></extra>"))
        fig.add_annotation(x=35, y=ys[-1], text=compound.split(" ")[0], showarrow=False, xanchor="left",
                           xshift=6, font=dict(color=INK, size=12))
    fig.add_vline(x=7, line=dict(color=INK_2, width=1, dash="dot"))
    fig.add_annotation(x=7, y=1.0, yref="paper", text="7 °C rule of thumb", showarrow=False, yanchor="bottom",
                       font=dict(size=12, color=INK_2))
    fig.add_vline(x=current_temp, line=dict(color=INK, width=1))
    fig.add_annotation(x=current_temp, y=0, yref="paper", text="now", showarrow=False, yanchor="bottom",
                       xanchor="left", xshift=4, font=dict(size=12, color=INK))
    fig.update_xaxes(title="Air temperature (°C)", range=[coldest, 35])
    fig.update_yaxes(title="Braking distance (m)")
    fig = style(fig, 400, f"Braking distance from {env['speed']} km/h on a {road} road, by tire type")
    return fig.update_layout(margin=dict(r=100), hovermode="x unified")


def matrix_chart(cfg, env):
    conditions = [("Dry<br>25 °C", "dry", 25), ("Wet<br>20 °C", "wet", 20), ("Standing water<br>20 °C", "flood", 20),
                  ("Dry<br>−10 °C", "dry", -10), ("Wet<br>2 °C", "wet", 2), ("Slush<br>0 °C", "slush", 0),
                  ("Packed snow<br>−10 °C", "snow", -10), ("Ice<br>−3 °C", "ice", -3)]
    metres = np.array([[evaluate({**cfg, "compound": c}, {**env, "surface": s, "temp": t})["distance"]
                        for _, s, t in conditions] for c in COMPOUNDS])
    penalty = 100 * (metres / metres.min(axis=0) - 1)
    fig = go.Figure(go.Heatmap(
        z=penalty, x=[c[0] for c in conditions], y=COMPOUNDS, text=metres, texttemplate="%{text:.0f} m",
        colorscale=[[0, "#eef4fd"], [0.25, "#9ec5f4"], [0.6, "#2a78d6"], [1, "#0d366b"]], zmin=0, zmax=120,
        xgap=2, ygap=2, colorbar=dict(title="% longer than<br>best tire type", ticksuffix="%", thickness=12),
        hovertemplate="%{y}, %{x}<br>%{text:.1f} m, %{z:.0f}% longer than the best tire type<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(side="top", ticks="")
    return style(fig, 320).update_layout(margin=dict(l=150, t=70, b=20))


def slip_chart(sel, ref, surface_name):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ref["slip"], y=ref["slip_mu"], mode="lines", name="Reference",
                             line=dict(color=REFERENCE, width=2, dash="dash"),
                             hovertemplate="Reference at %{x:.0f}% slip: %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=sel["slip"], y=sel["slip_mu"], mode="lines", name="Selected",
                             line=dict(color=SELECTED, width=2),
                             hovertemplate="Selected at %{x:.0f}% slip: %{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[sel["peak_slip"]], y=[sel["mu"]], mode="markers", showlegend=False,
                             marker=dict(size=12, color=SELECTED, line=dict(color=SURFACE, width=2)), hoverinfo="skip"))
    fig.add_annotation(x=sel["peak_slip"], y=sel["mu"], text=f"Peak grip at {sel['peak_slip']:.0f}% slip",
                       showarrow=True, arrowcolor=INK_2, ax=70, ay=-28, font=dict(color=INK))
    fig.add_annotation(x=100, y=sel["locked_mu"], text="Wheel locked or spinning", showarrow=True,
                       arrowcolor=INK_2, ax=-70, ay=-28, font=dict(color=INK))
    fig.update_xaxes(title="Wheel slip (%): 0 is rolling freely, 100 is locked", range=[0, 102])
    fig.update_yaxes(title="Grip (friction coefficient)", rangemode="tozero")
    return style(fig, 380, f"Grip against wheel slip on {surface_name.lower()}")


def car_length_chart(sel, ref, speed, ref_name):
    metres = [ref["distance"], sel["distance"]]
    fig = go.Figure(go.Bar(
        x=metres, y=[ref_name, "Selected"], orientation="h", width=0.55,
        marker=dict(color=[REFERENCE, SELECTED], cornerradius=4),
        text=[f"{m:.0f} m  ≈  {m / CAR_LENGTH_M:.0f} car lengths" for m in metres],
        textposition="outside", textfont=dict(color=INK, size=16), cliponaxis=False,
        hovertemplate="%{y}: %{x:.1f} m<extra></extra>",
    ))
    fig.update_xaxes(range=[0, max(metres) * 1.75], ticksuffix=" m")
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=15, color=INK))
    return style(fig, 230, f"Distance needed to stop from {speed} km/h").update_layout(margin=dict(l=120, t=50, b=40))


def braking_trace_chart(sel, ref, speed):
    fig = go.Figure()
    for result, name, line in [(ref, "Reference", dict(color=REFERENCE, width=2, dash="dash")),
                               (sel, "Selected", dict(color=SELECTED, width=2))]:
        fig.add_trace(go.Scatter(x=result["profile"]["d"], y=result["profile"]["v"], mode="lines", name=name, line=line,
                                 hovertemplate=name + " at %{x:.0f} m: %{y:.0f} km/h<extra></extra>"))
    first, other = (ref, sel) if ref["distance"] <= sel["distance"] else (sel, ref)
    residual = speed_at_distance(other["profile"], first["distance"])
    if residual >= 1:
        fig.add_trace(go.Scatter(x=[first["distance"]], y=[residual], mode="markers", showlegend=False, hoverinfo="skip",
                                 marker=dict(size=12, color=INK, line=dict(color=SURFACE, width=2))))
        fig.add_annotation(x=first["distance"], y=residual, text=f"{residual:.0f} km/h remaining", showarrow=True,
                           arrowcolor=INK_2, ax=60, ay=-30, font=dict(color=INK))
    if sel["v_hp"] and sel["v_hp"] < speed * 1.25:
        fig.add_hline(y=sel["v_hp"], line=dict(color=WORSE, width=1, dash="dot"))
        fig.add_annotation(x=1, xref="paper", y=sel["v_hp"], text="Hydroplaning onset, selected", showarrow=False,
                           xanchor="right", yanchor="bottom", font=dict(color=INK, size=12))
    fig.update_xaxes(title="Distance from brake application (m)", rangemode="tozero")
    fig.update_yaxes(title="Speed (km/h)", rangemode="tozero")
    return style(fig, 400, "Speed against distance under full braking")


def grip_envelope_chart(sel, ref):
    angle = np.linspace(0, 2 * np.pi, 181)
    fig = go.Figure()
    for result, name, line in [(ref, "Reference", dict(color=REFERENCE, width=2, dash="dash")),
                               (sel, "Selected", dict(color=SELECTED, width=2))]:
        fig.add_trace(go.Scatter(x=0.95 * result["mu"] * np.cos(angle), y=result["mu"] * np.sin(angle), mode="lines",
                                 name=name, line=line, hovertemplate=name + ": %{x:.2f} g lateral, %{y:.2f} g longitudinal<extra></extra>"))
    limit = max(sel["mu"], ref["mu"]) * 1.2
    fig.update_xaxes(title="Cornering (g)", range=[-limit, limit], constrain="domain", zeroline=True, zerolinecolor=GRID)
    fig.update_yaxes(title="Accelerating / braking (g)", range=[-limit, limit], scaleanchor="x", constrain="domain",
                     zeroline=True, zerolinecolor=GRID)
    return style(fig, 400, "Grip envelope: braking and cornering share one budget")


def demo_banner(index, conditions):
    """
    Large heading for demo mode: which scenario is playing and the conditions it sets, readable
    from across a room. It stands in for the page title, which demo mode hides to save height.
    """
    chip = (f'display:inline-block;background:{PANEL};border:1px solid {GRID};border-radius:999px;'
            f'padding:6px 16px;margin:0 8px 6px 0;font-size:1.25rem;font-weight:600;color:{INK}')
    steps = "".join(f'<span style="display:inline-block;width:28px;height:6px;border-radius:3px;margin-right:5px;'
                    f'background:{SELECTED if i == index else GRID}"></span>' for i in range(len(SCENARIOS)))
    st.html(f"""
<div style="background:{BANNER};border-left:8px solid {SELECTED};border-radius:12px;padding:14px 24px 8px">
  <div style="font-size:0.95rem;font-weight:700;letter-spacing:0.08em;color:{SELECTED};margin-bottom:6px">
    TIRE FITMENT EXPLORER &nbsp;|&nbsp; DEMO {index + 1} OF {len(SCENARIOS)} &nbsp; {steps}</div>
  <div style="font-size:2rem;font-weight:700;line-height:1.2;color:{INK};margin-bottom:10px">{SCENARIOS[index]["title"]}</div>
  <div>{"".join(f'<span style="{chip}">{c}</span>' for c in conditions)}</div>
</div>""")


def verdict(delta_m, residual, ref_name):
    """One plain sentence on whether the selected setup stops sooner or later than the reference."""
    other = ref_name.lower()
    cars = abs(delta_m) / CAR_LENGTH_M
    lengths = "less than one car length" if cars < 0.75 else f"about {cars:.0f} car length{'s' if cars >= 1.5 else ''}"
    if abs(delta_m) < 0.5:
        colour, mark = NEUTRAL_TEXT, "="
        text = f"On this road the selected setup stops in about the same distance as the {other}."
    elif delta_m < 0:
        colour, mark = GOOD_TEXT, "&#10003;"
        text = f"The selected setup stops {abs(delta_m):.1f} m sooner than the {other}: {lengths}."
    else:
        colour, mark = BAD_TEXT, "!"
        text = (f"The selected setup needs {delta_m:.1f} m more to stop than the {other}: {lengths}. "
                f"It is still doing {residual:.0f} km/h where the {other} has stopped.")
    st.html(f'<div style="background:{colour}22;color:{colour};border-radius:10px;padding:14px 18px;font-size:1rem;'
            f'line-height:1.5"><span style="display:inline-block;width:1.5em;height:1.5em;line-height:1.4em;'
            f'text-align:center;border:1.5px solid {colour};border-radius:50%;font-weight:700;margin-right:10px">'
            f'{mark}</span>{text}</div>')


def footer():
    """Small print under every view: what the numbers are, who made it, and where the sources and licence live."""
    st.caption(f"Screening model tuned to published tire tests, for comparing choices. Not a measurement of any "
               f"specific tire and not safety advice. © 2026 {AUTHORS}. Work conducted at the University of "
               f"Waterloo. [Sources]({REPO_URL}/blob/main/SOURCES.md) · [Code and licence (Apache 2.0)]({REPO_URL})")


def dots(ratio, step=0.10):
    """Five-dot rating against the reference. Each dot is one `step` of change, and three dots means within half a step."""
    filled = int(min(max(math.floor(3.5 + (ratio - 1) / step), 1), 5))
    word = {1: "Much worse", 2: "Worse", 3: "About the same", 4: "Better", 5: "Much better"}[filled]
    return "●" * filled + "○" * (5 - filled), word


# ----------------------------------------------------------------------------
# State
# ----------------------------------------------------------------------------


def reset_size():
    width, aspect, rim = VEHICLES[st.session_state.vehicle]["oem"]
    st.session_state.update(width=width, rim=rim, aspect=aspect, keep_od=True,
                            pressure=VEHICLES[st.session_state.vehicle]["placard"])


def reset_season():
    season = SEASONS[st.session_state.season]
    st.session_state.update(surface=season["surfaces"][0], temp=season["temp"][2])


def set_fitment(dw, dr):
    width, _, rim = VEHICLES[st.session_state.vehicle]["oem"]
    st.session_state.update(width=width + dw, rim=rim + dr, keep_od=True)


def apply_scenario(scenario):
    width, _, rim = VEHICLES[st.session_state.vehicle]["oem"]
    st.session_state.update(
        season=scenario["season"], surface=scenario["surface"], temp=scenario["temp"],
        compound=scenario["compound"], width=width + scenario["dw"], rim=rim + scenario["dr"],
        tread=scenario["tread"], keep_od=True, pressure=VEHICLES[st.session_state.vehicle]["placard"],
    )


def start_demo():
    st.session_state.update(demo_index=0, demo_pending=True, demo_last=time.time())


@st.fragment(run_every=DEMO_SECONDS)
def demo_ticker():
    if time.time() - st.session_state.demo_last >= DEMO_SECONDS - 1:
        st.session_state.demo_index = (st.session_state.demo_index + 1) % len(SCENARIOS)
        st.session_state.demo_pending = True
        st.session_state.demo_last = time.time()
        st.rerun()


st.set_page_config(page_title="Tire fitment explorer", page_icon=":material/tire_repair:", layout="wide")

defaults = dict(view="Simple", vehicle=list(VEHICLES)[0], season="Winter", compound="Winter", speed=80, tread=8.0,
                adjusted=True, ref_compound="All-season", demo=False, demo_index=0, demo_pending=False, demo_last=0.0)
for key, value in defaults.items():
    st.session_state.setdefault(key, value)
if "width" not in st.session_state:
    reset_size()
if "surface" not in st.session_state:
    st.session_state.update(surface="Packed snow", temp=-8)
if st.session_state.demo and st.session_state.demo_pending:
    apply_scenario(SCENARIOS[st.session_state.demo_index])
    st.session_state.demo_pending = False

if st.session_state.demo:
    use_dark_theme()

st.markdown(f"""
<style>
.block-container {{padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1500px;}}
[data-testid="stMetric"] {{background: {SURFACE}; border: 1px solid {GRID}; border-radius: 12px; padding: 14px 16px;}}
[data-testid="stMetricValue"] {{font-size: 2rem;}}
h1 {{font-size: 2rem !important; margin-bottom: 0 !important;}}
[data-testid="stImage"] img {{max-height: 430px; object-fit: contain;}}
</style>
""", unsafe_allow_html=True)
if st.session_state.demo:
    st.markdown(f"""
<style>
.stApp, [data-testid="stHeader"] {{background: {PAGE};}}
[data-testid="stMain"], [data-testid="stMain"] [data-testid="stMarkdownContainer"] :is(p, li, td, th, strong, h1, h2, h3, h4),
[data-testid="stMain"] [data-testid="stMetricLabel"], [data-testid="stMain"] [data-testid="stMetricValue"] {{color: {INK};}}
[data-testid="stMain"] [data-testid="stCaptionContainer"] :is(p, li) {{color: {INK_2};}}
[data-testid="stMain"] a {{color: #7db3f2;}}
[data-testid="stMain"] :is(table, th, td) {{border-color: {GRID} !important;}}
[data-testid="stMain"] hr {{border-color: {GRID};}}
[data-testid="stMain"] [data-testid="stCaptionContainer"] {{opacity: 1;}}
[data-testid="stMetricDelta"] * {{color: inherit !important;}}
[data-testid="stHeader"] :is(button, svg), [data-testid="stExpandSidebarButton"] :is(button, svg, span) {{color: {INK} !important; fill: {INK};}}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Controls
# ----------------------------------------------------------------------------

veh = VEHICLES[st.session_state.vehicle]
oem_w, oem_a, oem_r = veh["oem"]
oem_geo = geometry(oem_w, oem_a, oem_r)

with st.sidebar:
    st.radio("View", ["Simple", "Technical"], key="view", horizontal=True)
    technical = st.session_state.view != "Simple"
    ref_name = "Reference" if technical else "Factory tire"
    st.header("Conditions")
    st.radio("Season", list(SEASONS), key="season", horizontal=True, on_change=reset_season)
    season = SEASONS[st.session_state.season]
    if st.session_state.surface not in season["surfaces"]:
        reset_season()
    st.radio("Road surface", season["surfaces"], key="surface")
    t_min, t_max = SURFACE_TEMP_RANGE.get(st.session_state.surface, season["temp"][:2])
    st.session_state.temp = int(min(max(st.session_state.temp, t_min), t_max))
    st.slider("Air temperature (°C)", t_min, t_max, key="temp")
    st.slider("Speed when brakes are applied (km/h)", 30, 110, key="speed", step=10)

    st.header("Tire setup")
    st.selectbox("Vehicle class and factory size", list(VEHICLES), key="vehicle", on_change=reset_size)
    st.radio("Tire type", COMPOUNDS, key="compound")

    st.caption("Quick fitments")
    b1, b2, b3 = st.columns(3)
    b1.button("Stock", on_click=set_fitment, args=(0, 0), width="stretch")
    b2.button("−1 in", on_click=set_fitment, args=(-10, -1), width="stretch",
              help="10 mm narrower on a rim one inch smaller, the usual winter downsizing.")
    b3.button("+1 in", on_click=set_fitment, args=(10, 1), width="stretch",
              help="10 mm wider on a rim one inch larger.")

    widths = list(range(oem_w - 30, oem_w + 40, 10))
    rims = list(range(oem_r - 2, oem_r + 3))
    st.select_slider("Section width (mm)", widths, key="width")
    st.select_slider("Rim diameter (inches)", rims, key="rim")
    st.toggle("Hold overall diameter at factory size", key="keep_od",
              help="On: the sidewall is adjusted so the tire stays the same height, which isolates width and rim effects. "
                   "Off: choose the aspect ratio yourself to make the whole tire taller or shorter.")
    if st.session_state.keep_od:
        st.session_state.aspect = matched_aspect(st.session_state.width, st.session_state.rim, oem_geo["diameter"])
    else:
        st.select_slider("Aspect ratio (sidewall height as % of width)", list(range(30, 90, 5)), key="aspect")
    st.caption(f"Size shown: **{st.session_state.width}/{st.session_state.aspect}R{st.session_state.rim}**. "
               "Sidewall ratios move in steps of 5, so check that a size is sold before quoting it.")
    st.slider("Tread depth remaining (mm)", 1.6, 9.0, key="tread", step=0.2, format="%.1f")
    st.slider("Pressure set in the shop at 20 °C (psi)", 24, 44, key="pressure")
    st.toggle("Pressure topped up for outside temperature", key="adjusted")

    st.header("Display")
    st.selectbox(f"{ref_name} type", COMPOUNDS, key="ref_compound",
                 help=f"The {ref_name.lower()} is what every setup is compared against: always the factory size, "
                      "new tread, at placard pressure. Choose which tire type it wears.")
    st.toggle("Demo mode (cycle through scenarios)", key="demo", on_change=start_demo,
              help="Steps through preset scenarios. Each step resets the conditions and tire setup, "
                   "so turn it off to explore on your own.")

ss = st.session_state
env = dict(vehicle=ss.vehicle, surface=SURFACE_KEY[ss.surface], temp=ss.temp, speed=ss.speed)
running_psi = ss.pressure if ss.adjusted else pressure_at_temperature(ss.pressure, ss.temp)
cfg = dict(compound=ss.compound, width=ss.width, aspect=ss.aspect, rim=ss.rim, tread=ss.tread, pressure=running_psi)
ref_cfg = dict(compound=ss.ref_compound, width=oem_w, aspect=oem_a, rim=oem_r, tread=NEW_TREAD_MM, pressure=veh["placard"])
sel, ref = evaluate(cfg, env), evaluate(ref_cfg, env)

size_name = f"{ss.width}/{ss.aspect}R{ss.rim}"
sel_label = f"Selected: {size_name} {ss.compound.split(' ')[0].lower()}"
ref_label = f"{ref_name}: {oem_w}/{oem_a}R{oem_r} {ss.ref_compound.split(' ')[0].lower()}"

# ----------------------------------------------------------------------------
# Page
# ----------------------------------------------------------------------------

if ss.demo:
    st.markdown("<style>.block-container {padding-top: 2rem;} "
                '[data-testid="stImage"] img {max-height: 390px;}</style>', unsafe_allow_html=True)
    demo_banner(ss.demo_index, [ss.season, ss.surface, f"{ss.temp} °C", f"Braking from {ss.speed} km/h",
                                f"{size_name} {ss.compound.split(' ')[0].lower()} tire", f"{ss.tread:.0f} mm tread"])
    demo_ticker()
else:
    st.title("How tire size and type change stopping, slip and safety")
    st.caption(f"Fleet Tire Optimization Strategy  |  {ss.season}, {ss.surface.lower()}, {ss.temp} °C  |  "
               f"{sel_label}  against  {ref_label}")

delta_m = sel["distance"] - ref["distance"]
residual = speed_at_distance(sel["profile"], ref["distance"])
vs = f"vs {ref_name.lower()}"
k1, k2, k3, k4, k5 = st.columns(5) if technical else st.columns(3) + [None, None]
k1.metric("Braking distance", f"{sel['distance']:.1f} m", f"{round(delta_m, 1) + 0:+.1f} m {vs}", delta_color="inverse")
k2.metric("Speed at reference stop" if technical else "Speed where the factory tire has stopped", f"{residual:.0f} km/h",
          "Already stopped" if delta_m <= 0 else "Still moving", delta_color="normal" if delta_m <= 0 else "inverse",
          delta_arrow="off")
if not technical:
    k3.metric("Grip limit on a highway ramp", f"{sel['corner']:.0f} km/h", f"{sel['corner'] - ref['corner']:+.0f} km/h {vs}")
else:
    if sel["v_hp"]:
        k3.metric("Hydroplaning starts near", f"{sel['v_hp']:.0f} km/h", f"{sel['v_hp'] - ref['v_hp']:+.0f} km/h vs reference")
    else:
        k3.metric("Peak grip", f"{sel['mu']:.2f}", f"{100 * (sel['mu'] / ref['mu'] - 1):+.0f}% vs reference")
    k4.metric(f"Cornering limit, {RAMP_RADIUS_M} m ramp", f"{sel['corner']:.0f} km/h", f"{sel['corner'] - ref['corner']:+.0f} km/h vs reference")
    k5.metric("Grip lost if wheels lock", f"{100 * (1 - sel['locked_mu'] / sel['mu']):.0f}%",
              f"Peak at {sel['peak_slip']:.0f}% slip", delta_color="off")

braking_note = (f"Braking distance only. Add {ss.speed / 3.6 * REACTION_S:.0f} m travelled during a {REACTION_S} s driver "
                f"reaction at {ss.speed} km/h. Modelled values for comparison, not a measurement of any specific tire.")
left, right = st.columns([1.45, 1])
with left:
    braking_animation(sel, ref, env, sel_label, ref_label, ref_name, ss.surface, header=not ss.demo)
    if not ss.demo:
        st.caption(braking_note)
    verdict(delta_m, residual, ref_name)
with right:
    tire_diagram(sel, ref, ref_name)

if ss.demo:
    st.html(f'<div style="text-align:center;color:{INK_2};font-size:1rem;padding:2px 0 10px">'
            'Scroll down for the comparison charts &darr;</div>')
    st.divider()
    st.caption(braking_note)
if not technical:
    c1, c2 = st.columns([1.2, 1])
    with c1:
        show(car_length_chart(sel, ref, ss.speed, ref_name))
    with c2:
        ratings = [("Stopping", ref["distance"] / sel["distance"]), ("Cornering grip", sel["corner"] / ref["corner"])]
        if sel["v_hp"]:
            ratings.append(("Staying in contact through water or slush", sel["v_hp"] / ref["v_hp"]))
        ratings += [("Ride comfort", 100 / sel["harshness"]), ("Pothole protection", 100 / sel["impact_risk"]),
                    ("Fuel economy", 1 - (sel["fuel_delta"] - ref["fuel_delta"]) / 100, FUEL_DOT_STEP)]
        table = "| Compared with the factory tire | Rating | |\n|---|---|---|\n"
        table += "\n".join(f"| {name} | {dots(*r)[0]} | {dots(*r)[1]} |" for name, *r in ratings)
        st.markdown(table)
        st.caption("Three dots means the same as the factory tire: the factory size with new tread at the recommended pressure. Switch to the Technical view for the numbers behind each rating.")
    footer()
    st.stop()

tabs = st.tabs(["Braking physics", "Width vs diameter vs everything else", "Winter vs summer", "Slip and stability",
                "Health and safety", "Four pillars", "Model and sources"])

with tabs[0]:
    c1, c2 = st.columns([1.5, 1])
    with c1:
        show(braking_trace_chart(sel, ref, ss.speed))
    with c2:
        show(grip_envelope_chart(sel, ref))
    st.caption(f"Peak friction {sel['mu']:.2f} selected, {ref['mu']:.2f} reference. Mean deceleration "
               f"{(ss.speed / 3.6) ** 2 / (2 * sel['distance']) / G:.2f} g selected, {(ss.speed / 3.6) ** 2 / (2 * ref['distance']) / G:.2f} g reference. "
               "On water and slush the trace bends because grip recovers as speed falls below the hydroplaning onset.")

with tabs[1]:
    def with_size(width=None, rim=None, aspect=None, **extra):
        width, rim = width or ss.width, rim or ss.rim
        aspect = aspect or exact_aspect(width, rim, sel["geo"]["diameter"])
        return evaluate({**cfg, "width": width, "rim": rim, "aspect": aspect, **extra}, env)["distance"]

    width_ys = [with_size(width=w) for w in widths]
    rim_ys = [with_size(rim=r) for r in rims]
    low, high = min(width_ys + rim_ys), max(width_ys + rim_ys)
    pad = max(0.15 * sel["distance"] - (high - low) / 2, 0.08 * (high - low))
    y_range = [low - pad, high + pad]
    c1, c2 = st.columns(2)
    with c1:
        show(sweep_chart(widths, width_ys, ss.width, sel["distance"], "Section width (mm)", y_range,
                         "Changing width only (same overall diameter)"))
    with c2:
        show(sweep_chart(rims, rim_ys, ss.rim, sel["distance"], "Rim diameter (inches)", y_range,
                         "Changing rim only (same width and overall diameter)", '"'))
    st.caption("Both charts share one vertical scale, so a flat line means that change barely matters on this surface. "
               "Overall diameter is held exactly, so some points fall between the aspect ratios that are actually sold.")

    changes = [
        ("20 mm wider", with_size(width=ss.width + 20)),
        ("20 mm narrower", with_size(width=ss.width - 20)),
        ("Rim 1 inch larger, shorter sidewall", with_size(rim=ss.rim + 1)),
        ("Rim 1 inch smaller, taller sidewall", with_size(rim=ss.rim - 1)),
        ("Taller tire overall (+5 aspect ratio)", with_size(aspect=ss.aspect + 5)),
        ("Tread worn to 4 mm", with_size(aspect=ss.aspect, tread=4.0)),
        ("Tread worn to 2 mm", with_size(aspect=ss.aspect, tread=2.0)),
        ("Pressure 6 psi low", with_size(aspect=ss.aspect, pressure=running_psi - 6)),
    ] + [(f"Switch to {c.split(' ')[0].lower()} tires", with_size(aspect=ss.aspect, compound=c))
         for c in COMPOUNDS if c != ss.compound]
    show(tornado_chart([(name, 100 * (d / sel["distance"] - 1)) for name, d in changes]))

with tabs[2]:
    road = st.radio("Road", ["dry", "wet"], horizontal=True, label_visibility="collapsed",
                    format_func=lambda r: f"{r.capitalize()} road")
    show(temperature_chart(cfg, env, road, ss.temp))
    st.caption("Liquid water below 0 °C assumes a salted road, so the wet chart stops at −15 °C. The 7 °C line is the common changeover guidance; "
               "in this model the wet-road crossover sits near it, while on dry pavement summer and all-season "
               "compounds keep an edge to well below freezing.")
    st.markdown(f"**Braking distance from {ss.speed} km/h for the selected size, by tire type and condition**")
    show(matrix_chart(cfg, env))

with tabs[3]:
    c1, c2 = st.columns([1.6, 1])
    with c1:
        show(slip_chart(sel, ref, ss.surface))
    with c2:
        st.markdown(f"""
**Reading the curve**

A tire grips hardest when it slips a little: about **{sel['peak_slip']:.0f}%** on this surface. ABS and traction
control work to hold the wheel near that peak. Past it the wheel locks or spins and grip falls by
**{100 * (1 - sel['locked_mu'] / sel['mu']):.0f}%**, which is also when steering control is lost.

On ice and packed snow the peak arrives at very low slip, so a small amount of extra throttle or brake
pushes the tire over the top. That is why slides start so easily in winter.
""")
        m1, m2 = st.columns(2)
        m1.metric("Steepest hill start", f"{sel['grade']:.0f}% grade", f"{sel['grade'] - ref['grade']:+.0f} pts vs reference")
        m2.metric("Steering response index", f"{100 * sel['response']:.0f}",
                  f"{100 * (sel['response'] - ref['response']):+.0f} vs reference")
        st.caption(f"Hill start assumes {veh['drive']} with {100 * veh['driven']:.0f}% of weight on the driven wheels. "
                   "Steering response rises with a shorter sidewall, more width and a firmer compound.")

with tabs[4]:
    def status(level):
        return {0: "🟢&nbsp;OK", 1: "🟡&nbsp;Caution", 2: "🔴&nbsp;High&nbsp;risk"}[level]

    rows = []
    rows.append(("Stopping distance", f"{sel['distance']:.1f} m ({delta_m:+.1f} m vs reference)",
                 status(0 if delta_m <= 0.5 else 1 if delta_m / ref["distance"] < 0.15 else 2),
                 "Rear-end and intersection collisions."))
    rows.append(("Speed where the reference has stopped", f"{residual:.0f} km/h",
                 status(0 if residual < 1 else 1 if residual < 30 else 2),
                 "Impact severity: injury risk climbs steeply with impact speed."))
    if sel["v_hp"]:
        margin = sel["v_hp"] - ss.speed
        rows.append(("Hydroplaning margin", f"{margin:+.0f} km/h at {ss.speed} km/h",
                     status(0 if margin > 20 else 1 if margin > 0 else 2),
                     "Total loss of steering and braking on water or slush. Wider and worn tires lose margin first."))
    rows.append(("Skid threshold", f"Peak grip at {sel['peak_slip']:.0f}% slip, {sel['mu']:.2f} friction",
                 status(0 if sel["mu"] > 0.5 else 1 if sel["mu"] > 0.2 else 2),
                 "Low grip with an early peak means little warning before a slide."))
    rows.append((f"Cornering limit on a {RAMP_RADIUS_M} m ramp", f"{sel['corner']:.0f} km/h",
                 status(0 if sel["corner"] >= 50 else 1 if sel["corner"] >= 35 else 2),
                 "Run-off-road and loss-of-control crashes."))
    temp_level = (1 if (ss.compound == "Summer" and ss.temp < 7) or (ss.compound == "Winter" and ss.temp > 15) else 0)
    temp_level = 2 if ss.compound == "Summer" and ss.temp < -7 else temp_level
    rows.append(("Compound in its temperature range", f"{ss.compound} at {ss.temp} °C", status(temp_level),
                 "Summer compounds harden in the cold; winter compounds go soft and wear fast in heat."))
    rows.append(("Tread depth", f"{ss.tread:.1f} mm", status(0 if ss.tread >= 4 else 1 if ss.tread >= 3 else 2),
                 "Wet and snow grip fall away quickly below about 4 mm."))
    drift = pressure_at_temperature(ss.pressure, ss.temp)
    off_placard = 100 * abs(running_psi / veh["placard"] - 1)
    rows.append(("Running pressure", f"{running_psi:.0f} psi (placard {veh['placard']} psi). "
                 f"Set at 20 °C and left alone it would read {drift:.0f} psi at {ss.temp} °C",
                 status(0 if off_placard < 10 else 1 if off_placard < 20 else 2),
                 "Under-inflation lowers hydroplaning speed, dulls steering and overheats the tire. "
                 "Over-inflation shrinks the footprint and hardens the ride."))
    rows.append(("Speedometer error", f"{sel['speedo']:+.1f}% true speed vs indicated",
                 status(0 if abs(sel["speedo"]) <= 3 else 1),
                 "A taller tire makes the vehicle faster than the dial shows."))
    rows.append(("Pothole and curb damage risk index", f"{sel['impact_risk']:.0f} (reference 100)",
                 status(0 if sel["impact_risk"] <= 120 else 1 if sel["impact_risk"] <= 160 else 2),
                 "Short sidewalls protect the rim less: blowouts and roadside stops."))
    rows.append(("Ride harshness index", f"{sel['harshness']:.0f} (reference 100)",
                 status(0 if sel["harshness"] <= 115 else 1),
                 "Whole-body vibration and fatigue over long driving days."))
    rows.append(("Wheel and tire weight", f"About {sel['assembly_kg']:.0f} kg each",
                 status(0 if sel["assembly_kg"] <= LIFT_LIMIT_KG else 1),
                 f"Manual handling at seasonal changeovers. {LIFT_LIMIT_KG} kg is the NIOSH lifting reference load."))

    table = "| Hazard indicator | This setup | Status | Why it matters |\n|---|---|---|---|\n"
    table += "\n".join(f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows)
    st.markdown(table)
    st.caption("Indices are relative to the factory size at 100. Status bands are screening thresholds for discussion, not compliance limits. "
               "The grip and cornering bands are absolute, so snow and ice can show high risk on every tire; "
               "the comparison with the reference is in the first two rows.")

with tabs[5]:
    km = 25000
    litres = veh["fuel"] * km / 100
    co2 = (sel["fuel_delta"] - ref["fuel_delta"]) / 100 * litres * 2.3

    def cell(value, reference, unit="", fmt=".0f"):
        return f"{value:{fmt}}{unit} (reference {reference:{fmt}}{unit})"

    pillars = [
        ("**Cost** (primary)", "Tire purchase price index", cell(sel["price"], ref["price"])),
        ("", "Fuel use from rolling resistance", f"{sel['fuel_delta'] - ref['fuel_delta']:+.1f}% vs reference"),
        ("**Health and safety** (primary)", "Braking distance", cell(sel["distance"], ref["distance"], " m", ".1f")),
        ("", "Cornering limit", cell(sel["corner"], ref["corner"], " km/h")),
        ("", "Hydroplaning onset", cell(sel["v_hp"], ref["v_hp"], " km/h") if sel["v_hp"] else "No water film on this surface"),
        ("**Operational efficiency** (secondary)", "Tread wear rate index", cell(100 * sel["wear"], 100 * ref["wear"])),
        ("", "Wheel and tire weight at changeover", cell(sel["assembly_kg"], ref["assembly_kg"], " kg")),
        ("**Environmental performance** (secondary)", f"CO2 from fuel over {km:,} km", f"{co2:+.0f} kg per vehicle per year vs reference"),
        ("", "Tire wear particles (tracks wear rate)", cell(100 * sel["wear"], 100 * ref["wear"])),
    ]
    table = "| Pillar | Indicator | Selected setup |\n|---|---|---|\n" + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in pillars)
    st.markdown(table)
    st.caption(f"Screening estimates. Fuel baseline {veh['fuel']} L/100 km, 2.3 kg CO2 per litre of gasoline. "
               "Price and wear indices are simple scaling rules and should be replaced with fleet purchase and service records.")

with tabs[6]:
    st.markdown(f"""
**What this is.** A transparent screening model that shows the direction and rough size of each effect. It is
calibrated to published independent tire tests, not fitted to any one tire model. Individual tires vary more
between brands than between sizes, so use it to compare choices, not to predict a specific stopping distance.

**Grip.** Each tire type has an effective braking friction value for each surface and temperature
(interpolated from a lookup table in the code). Friction is then scaled for size, tread depth and pressure, and
braking distance is integrated from the chosen speed to a stop.

**Published tests the model was tuned to.** Only sources whose figures could be confirmed are listed.
- Cool dry road: winter tires stop about 15% longer than summer tires. Braking from 100 km/h at 5.5 °C, summer tires
  needed 5.8 m less on average ([What Car?, "Should I buy winter tyres?"](https://www.whatcar.com/news/winter-tyres/)).
- Cold wet road: winter tires stopped 4.0 m sooner than summer tires from 80 km/h at 4 °C (What Car?, same article).
- Wet road by temperature: all-season leads summer in the cold and the two meet between 10 and 15 °C. At +2 °C
  all-season tires stopped almost 6.5 m shorter from 80 km/h; at +12 °C the two were comparable
  ([Tyre Reviews, 2025 Summer and All Season Combined Tyre Test](https://www.tyrereviews.com/Article/2025-Summer-and-All-Season-Combined-Tyre-Test.htm)).
- Packed snow: summer tires take at least twice the distance of winter tires
  ([What Car?, "Snow and ice"](https://www.whatcar.com/news/snow-and-ice/n11592): 17.7 m for winter tires, more than twice that for summer).
- Ice: winter tires stop about a third shorter than all-season tires
  ([Tire Rack ice rink tests](https://www.tirerack.com/tires/tests/testDisplay.jsp?ttid=116): 35.1 ft against 53.6 ft from 12 mph).
- Width in winter: narrower tires have the advantage in aquaplaning, slush and on snow, wider tires on a dry road, and
  width matters less than the tire model. In 7 mm of water 225 mm tires lost contact near 70 km/h and 195 mm tires
  above 80 km/h ([ADAC winter tire width comparison](https://presse.adac.de/meldungen/adac-ev/tests/reifenbreitenvergleich-winterreifen.html)).
  On packed snow four widths of one tire were too close for a driver to notice
  (Tyre Reviews test, as reported by [Motor1](https://www.motor1.com/news/696279/wide-vs-narrow-winter-tires-explained/)).
- Width in summer: wider tires stop shorter on dry and wet roads, narrower tires aquaplane at a higher speed
  ([ADAC, narrow against wide tires](https://www.adac.de/rund-ums-fahrzeug/ausstattung-technik-zubehoer/reifen/sicherheit/reifengroesse/)).
- Tread wear: wet braking barely changes down to 4 mm and is about 17% longer at 2 mm; snow traction falls 8.8% at
  4 mm and 15.9% at 2 mm ([ADAC worn tire test](https://www.adac.de/rund-ums-fahrzeug/ausstattung-technik-zubehoer/reifen/sicherheit/abgefahrene-reifen/)).

**Key papers and references**
- Hydroplaning: Horne, W. B., and Dreher, R. C. (1963). *Phenomena of Pneumatic Tire Hydroplaning*.
  [NASA Technical Note D-2056](https://ntrs.nasa.gov/citations/19640000612). The model uses its relation between
  onset speed and pressure (speed in km/h = 6.35 x square root of pressure in kPa), scaled for tread depth against
  water depth and for footprint shape (wider and shorter footprints ride up sooner).
- Wheel slip: Burckhardt, M. (1993). *Fahrwerktechnik: Radschlupf-Regelsysteme*. Vogel Verlag. The grip against slip
  curve uses the Burckhardt model form for dry, wet, snow and ice, scaled to the peak friction from the grip model.
  The ice curve is given a mild fall-off after its peak.
- Manual lifting: Waters, T. R., Putz-Anderson, V., Garg, A., and Fine, L. J. (1993). Revised NIOSH equation for the
  design and evaluation of manual lifting tasks. [*Ergonomics* 36(7), 749-776](https://doi.org/10.1080/00140139308967940).
  Source of the {LIFT_LIMIT_KG} kg reference load.
- CO2 from fuel: Natural Resources Canada,
  [*2026 Fuel Consumption Guide*](https://natural-resources.canada.ca/sites/admin/files/documents/2026-02/2026-Fuel-Consumption-Guide.pdf).
  Source of 2.3 kg of CO2 per litre of gasoline.

**Pressure and temperature.** Gauge pressure follows the gas law: roughly 1 psi lost per 5 to 6 °C of cooling.

**Judgement values, with no published support.** The rise in ice friction as ice gets colder, slush friction, the
size of the hydroplaning effect on braking distance, and the exponents for width, sidewall and diameter set the
direction of an effect and a plausible size only. Steering response, ride harshness, damage risk, price, wear, wheel
weight and fuel use are simple scaling rules on sidewall height, width, diameter and pressure; fuel use assumes
rolling resistance accounts for a quarter of fuel burned. The full list is in
[SOURCES.md]({REPO_URL}/blob/main/SOURCES.md).

**Temperature ranges.** Packed snow is limited to 2 °C and colder, ice to 0 °C and colder, slush to between
−10 and 3 °C, and a wet road to −15 °C and warmer. Slush grip is held constant with temperature.

**Limits.** No vehicle dynamics, ABS tuning, load transfer, studs, road crown or brand differences. Vehicle
classes are generic placeholders, not a real fleet.

**Authors and acknowledgement.** {AUTHORS}, who contributed equally. The work was conducted at the University of
Waterloo as part of the Fleet Tire Optimization Strategy capstone project.

**Use and licence.** This is a student project and it is not safety advice: do not use it to choose tires for a
specific vehicle. The tire makers, test organisations and publications named here are credited as sources only and
did not review or endorse this work. © 2026 {AUTHORS}. The code is open source under the Apache License 2.0 at
[{REPO_URL.split("//")[1]}]({REPO_URL}).
""")
footer()
