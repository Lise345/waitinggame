"""
Monkey Banana Battle — single-file Streamlit app.

- No ?team= param  →  main game screen (show on projector/TV)
- ?team=left       →  voter screen for left team
- ?team=right      →  voter screen for right team

Deploy to Streamlit Cloud, then set the QR code URL to your app URL,
e.g. https://your-app.streamlit.app
QR codes will automatically point to  <your-url>?team=left  and  ?team=right
"""

import streamlit as st
import math, json, time, os, io, base64, random

st.set_page_config(
    page_title="🍌 Monkey Banana Battle",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── shared state via st.session_state (works on Streamlit Cloud) ─────────────
# We use a single shared dict stored in session_state under a stable key.
# On Cloud all users share the same server process, so this is effectively global.
# For local use, a JSON file is also written as backup.

VOTES_FILE = "votes.json"
GAME_FILE  = "game_state.json"
TURN_SECS  = 15

def _init_game():
    return {
        "score_left": 0, "score_right": 0,
        "phase": "voting",   # voting | result
        "turn": "left",
        "turn_start": time.time(),
        "last_throw": None,
        "wind": round(random.uniform(-7, 7), 1),
    }

def _init_votes():
    return {"left": [], "right": []}

# Use st.session_state as the shared store (survives reruns within a session,
# and on Cloud the server process is shared across connections)
if "game" not in st.session_state:
    # Try loading from file first (local persistence)
    if os.path.exists(GAME_FILE):
        try:
            with open(GAME_FILE) as f:
                st.session_state.game = json.load(f)
        except Exception:
            st.session_state.game = _init_game()
    else:
        st.session_state.game = _init_game()

if "votes" not in st.session_state:
    if os.path.exists(VOTES_FILE):
        try:
            with open(VOTES_FILE) as f:
                st.session_state.votes = json.load(f)
        except Exception:
            st.session_state.votes = _init_votes()
    else:
        st.session_state.votes = _init_votes()

def save_state():
    try:
        with open(GAME_FILE, "w") as f: json.dump(st.session_state.game, f)
        with open(VOTES_FILE, "w") as f: json.dump(st.session_state.votes, f)
    except Exception:
        pass  # read-only filesystem on Cloud is fine; session_state is the truth

def clear_votes():
    st.session_state.votes = _init_votes()
    save_state()

# ─── physics ──────────────────────────────────────────────────────────────────
# Canvas 900×380. Left monkey ≈ (155,170), right ≈ (745,150)
LMX, LMY = 155, 170
RMX, RMY = 745, 150
HIT_R = 40

def compute_trajectory(angle_deg, power, direction, wind):
    if direction == "left":
        x, y = LMX, LMY
        rad = math.radians(angle_deg)
        vx =  math.cos(rad) * power * 0.52
        vy = -math.sin(rad) * power * 0.52
    else:
        x, y = RMX, RMY
        rad = math.radians(180 - angle_deg)
        vx =  math.cos(rad) * power * 0.52
        vy = -math.sin(rad) * power * 0.52
    we = wind * 0.010
    g  = 0.17
    pts = []
    for _ in range(300):
        pts.append([round(x,1), round(y,1)])
        vx += we; vy += g; x += vx; y += vy
        if y > 400: break
    return pts

def check_hit(pts, direction):
    tx, ty = (RMX, RMY) if direction == "left" else (LMX, LMY)
    for px, py in pts:
        if (px-tx)**2 + (py-ty)**2 < HIT_R**2:
            return True
    return False

# ─── QR helper ────────────────────────────────────────────────────────────────
def make_qr(url):
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(url); qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""

def qr_tag(b64, url, w=120):
    if b64:
        return f"<img src='data:image/png;base64,{b64}' style='width:{w}px;border-radius:6px;'/>"
    return f"<div style='font-size:.65rem;color:#aaa;word-break:break-all'>{url}</div>"

# ─── route by query param ──────────────────────────────────────────────────────
params = st.query_params
team_param = params.get("team", "")

# ══════════════════════════════════════════════════════════════════════════════
# VOTER PAGE
# ══════════════════════════════════════════════════════════════════════════════
if team_param in ("left", "right"):
    team = team_param
    tc   = "#ffcc44" if team == "left" else "#44ccff"
    tbg  = "#2d3a1e" if team == "left" else "#1a2a3a"
    tbr  = "#ffcc44" if team == "left" else "#44ccff"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@400;700&display=swap');
    html,body,[class*="css"]{{font-family:'Nunito',sans-serif}}
    .th{{background:{tbg};border:3px solid {tbr};border-radius:20px;
         padding:20px;text-align:center;margin-bottom:16px}}
    .tn{{font-family:'Bangers',cursive;font-size:2.4rem;color:{tc};letter-spacing:3px;margin:0}}
    .bv{{font-family:'Bangers',cursive;font-size:2.8rem;text-align:center;color:{tc};margin:4px 0}}
    .vb{{background:#1a1a1a;border-radius:14px;padding:16px;margin:12px 0;border:1px solid #333}}
    .pl{{font-family:'Bangers',cursive;font-size:1.2rem;color:#fff;letter-spacing:1px}}
    .pd{{color:#888;font-size:.78rem;margin:2px 0 10px}}
    .ok{{background:#1a3a1a;border:2px solid #4caf50;border-radius:16px;padding:22px;text-align:center}}
    </style>
    <div class="th">
      <p class="tn">TEAM {'LEFT 🟡' if team=='left' else 'RIGHT 🔵'}</p>
      <p style="color:#aaa;font-size:.88rem;margin:4px 0">🍌 Choose your throw!</p>
    </div>
    """, unsafe_allow_html=True)

    voted_key = f"voted_{team}"
    if voted_key not in st.session_state:
        st.session_state[voted_key] = False

    game = st.session_state.game
    now  = time.time()
    secs_left = max(0, TURN_SECS - (now - game.get("turn_start", now)))

    # Show countdown on voter page too
    if game["phase"] == "voting" and game["turn"] == team:
        bar_pct = int(secs_left / TURN_SECS * 100)
        bar_col = "#4caf50" if secs_left > 8 else "#ffcc44" if secs_left > 4 else "#ff5722"
        st.markdown(f"""
        <div style="margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;color:#aaa;font-size:.8rem;margin-bottom:4px">
            <span>⏱ Time left</span><span style="color:{bar_col};font-weight:700">{int(secs_left)}s</span>
          </div>
          <div style="background:#333;border-radius:8px;height:10px">
            <div style="width:{bar_pct}%;background:{bar_col};height:100%;border-radius:8px;transition:width .5s"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    elif game["phase"] == "voting" and game["turn"] != team:
        other = "RIGHT" if team == "left" else "LEFT"
        st.info(f"It's {other} team's turn right now. Wait for your turn!")

    if st.session_state[voted_key]:
        st.markdown("""<div class="ok">
          <div style="font-size:3rem">✅</div>
          <div style="font-family:'Bangers',cursive;font-size:2rem;color:#4caf50">Vote Submitted!</div>
          <div style="color:#aaa;margin-top:6px">Your vote is counted. Watch the main screen!</div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔄 Vote again (new turn)", use_container_width=True):
            st.session_state[voted_key] = False
            st.rerun()
    else:
        # ── angle slider ──────────────────────────────────────────────────────
        st.markdown('<div class="vb"><div class="pl">🎯 Throw Angle</div>'
                    '<div class="pd">Low = flat, High = lofted arc</div></div>',
                    unsafe_allow_html=True)
        angle = st.slider("Angle", 10, 80, 45, key="vs_angle", label_visibility="collapsed")
        st.markdown(f'<div class="bv">{angle}°</div>', unsafe_allow_html=True)

        # ── trajectory preview SVG ─────────────────────────────────────────────
        # Mini 260×120 preview showing the arc
        pts = compute_trajectory(angle, 55, "left" if team == "left" else "right", 0)
        # scale to 260×110 preview box
        # source coords: x 0-900, y 0-380 → preview 260×110
        def sc(px, py):
            return round(px * 260/900, 1), round(py * 110/380, 1)

        path_d = ""
        for i, (px, py) in enumerate(pts[::3]):  # every 3rd point
            sx, sy = sc(px, py)
            path_d += f"{'M' if i==0 else 'L'}{sx},{sy} "

        # monkey dots
        lx, ly = sc(LMX, LMY)
        rx, ry = sc(RMX, RMY)
        # banana tip
        last = pts[-1]
        bx, by = sc(*last)

        st.markdown(f"""
        <svg viewBox="0 0 260 115" style="width:100%;background:#1a2a3a;border-radius:10px;margin:4px 0 8px">
          <!-- ground -->
          <rect x="0" y="95" width="260" height="20" fill="#3d6128" rx="2"/>
          <!-- buildings hint -->
          <rect x="30" y="55" width="38" height="42" fill="#c0845a" rx="2"/>
          <rect x="192" y="48" width="38" height="49" fill="#8a9bbc" rx="2"/>
          <!-- monkeys -->
          <circle cx="{lx}" cy="{ly}" r="7" fill="#c8822a"/>
          <text x="{lx}" y="{ly+1}" text-anchor="middle" dominant-baseline="middle" font-size="9">🐵</text>
          <circle cx="{rx}" cy="{ry}" r="7" fill="#c8822a"/>
          <text x="{rx}" y="{ry+1}" text-anchor="middle" dominant-baseline="middle" font-size="9">🐵</text>
          <!-- arc -->
          <path d="{path_d}" fill="none" stroke="#f5d020" stroke-width="2"
                stroke-dasharray="5 3" opacity="0.8"/>
          <!-- banana tip -->
          <text x="{bx}" y="{by}" text-anchor="middle" dominant-baseline="middle" font-size="11">🍌</text>
          <text x="130" y="108" text-anchor="middle" fill="#555" font-size="8" font-family="sans-serif">trajectory preview (no wind shown)</text>
        </svg>
        """, unsafe_allow_html=True)

        # ── power slider ──────────────────────────────────────────────────────
        st.markdown('<div class="vb"><div class="pl">💥 Throw Power</div>'
                    '<div class="pd">More power = farther. Don\'t overshoot!</div></div>',
                    unsafe_allow_html=True)
        power = st.slider("Power", 10, 100, 50, key="vs_power", label_visibility="collapsed")

        bw  = int(power * 2.2)
        bc  = "#4caf50" if power < 40 else "#ffcc44" if power < 70 else "#ff5722"
        st.markdown(f"""
        <div style="background:#222;border-radius:8px;height:22px;margin:4px 0 2px;overflow:hidden">
          <div style="width:{bw}px;max-width:220px;height:100%;background:{bc};border-radius:8px"></div>
        </div>
        <div class="bv">{power}</div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🍌 SUBMIT MY VOTE", use_container_width=True, type="primary"):
            st.session_state.votes[team].append({
                "angle": angle, "power": power, "timestamp": time.time()
            })
            save_state()
            st.session_state[voted_key] = True
            st.rerun()

    st.markdown(f"<div style='text-align:center;color:#444;font-size:.7rem;margin-top:24px'>"
                f"Monkey Banana Battle · Team {team.upper()}</div>", unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN GAME SCREEN
# ══════════════════════════════════════════════════════════════════════════════

game  = st.session_state.game
votes = st.session_state.votes

# ── sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Setup")
app_url = st.sidebar.text_input(
    "This app's public URL",
    value="http://localhost:8501",
    help="On Streamlit Cloud use your full URL, e.g. https://your-app.streamlit.app"
)
st.sidebar.markdown("QR codes will link to `<url>?team=left` and `?team=right`")
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Reset Game"):
    st.session_state.game  = _init_game()
    st.session_state.votes = _init_votes()
    save_state()
    st.rerun()

# ── auto-advance when timer expires ──────────────────────────────────────────
now       = time.time()
time_left = max(0.0, TURN_SECS - (now - game.get("turn_start", now)))

if game["phase"] == "voting" and time_left == 0:
    active = game["turn"]
    tvotes = votes[active]
    avg_angle = round(sum(v["angle"] for v in tvotes)/len(tvotes)) if tvotes else 45
    avg_power = round(sum(v["power"] for v in tvotes)/len(tvotes)) if tvotes else 50
    traj    = compute_trajectory(avg_angle, avg_power, active, game["wind"])
    did_hit = check_hit(traj, active)
    if did_hit:
        if active == "left": game["score_left"]  += 1
        else:                game["score_right"] += 1
    game["last_throw"] = {
        "angle": avg_angle, "power": avg_power, "thrower": active,
        "target_side": "right" if active == "left" else "left",
        "hit": did_hit, "trajectory": traj,
    }
    game["phase"] = "result"
    save_state()
    clear_votes()
    st.rerun()

# ── QR codes ──────────────────────────────────────────────────────────────────
left_url  = app_url.rstrip("/") + "?team=left"
right_url = app_url.rstrip("/") + "?team=right"
qr_left   = make_qr(left_url)
qr_right  = make_qr(right_url)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@400;700&display=swap');
html,body,[class*="css"]{font-family:'Nunito',sans-serif}
.title{font-family:'Bangers',cursive;font-size:2.5rem;letter-spacing:3px;text-align:center;
       color:#f5a623;text-shadow:3px 3px 0 #7b3f00;margin-bottom:4px}
.sb{display:flex;justify-content:space-around;align-items:center;
    background:linear-gradient(135deg,#2d5a27,#1a3a16);
    border-radius:16px;padding:10px 32px;margin:6px 0 8px}
.sn{font-family:'Bangers',cursive;font-size:1.2rem;letter-spacing:2px}
.sv{font-family:'Bangers',cursive;font-size:3.2rem;line-height:1}
.lc{color:#ffcc44}.rc{color:#44ccff}
.vs{font-family:'Bangers',cursive;font-size:1.7rem;color:#fff;opacity:.55}
.qp{border-radius:14px;padding:12px;text-align:center}
.lp{background:#2d3a1e;border:2px solid #ffcc44}
.rp{background:#1a2a3a;border:2px solid #44ccff}
.rmsg{font-family:'Bangers',cursive;font-size:1.7rem;letter-spacing:2px;text-align:center;margin:4px 0}
</style>
""", unsafe_allow_html=True)

# ── header ────────────────────────────────────────────────────────────────────
wa = "→" if game["wind"] > 0 else ("←" if game["wind"] < 0 else "—")
st.markdown(f"""
<div class="title">🍌 Monkey Banana Battle 🐵</div>
<div class="sb">
  <div><div class="sn lc">🐵 Team Left</div><div class="sv lc">{game['score_left']}</div></div>
  <div class="vs">VS</div>
  <div><div class="sv rc">{game['score_right']}</div><div class="sn rc">Team Right 🐵</div></div>
</div>
<div style="text-align:center;font-size:.8rem;color:#bbb;margin-bottom:6px">💨 Wind: {game['wind']:+.1f} {wa}</div>
""", unsafe_allow_html=True)

# ── result message ────────────────────────────────────────────────────────────
if game["phase"] == "result" and game.get("last_throw"):
    lt  = game["last_throw"]
    msg = f"💥 HIT! Point for {lt['thrower'].upper()}!" if lt["hit"] else "🍌 Miss! Sailed right past…"
    col = "#ff6b6b" if lt["hit"] else "#aaa"
    st.markdown(f'<div class="rmsg" style="color:{col}">{msg}</div>', unsafe_allow_html=True)

# ── countdown bar (voting phase) ──────────────────────────────────────────────
if game["phase"] == "voting":
    tl_int  = int(time_left)
    pct     = int(time_left / TURN_SECS * 100)
    bc      = "#4caf50" if time_left > 8 else "#ffcc44" if time_left > 4 else "#ff5722"
    tn      = game["turn"].upper()
    tc      = "color:#ffcc44" if game["turn"]=="left" else "color:#44ccff"
    st.markdown(f"""
    <div style="margin:0 0 8px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <span style="font-family:'Bangers',cursive;font-size:1.3rem;{tc}">TEAM {tn} — vote now!</span>
        <span style="font-family:'Bangers',cursive;font-size:1.6rem;color:{bc}">{tl_int}s</span>
      </div>
      <div style="background:#333;border-radius:8px;height:14px">
        <div style="width:{pct}%;background:{bc};height:100%;border-radius:8px;transition:width .4s"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── columns: QR | canvas | QR ────────────────────────────────────────────────
cl, cc, cr = st.columns([1.25, 4.5, 1.25])

lvotes = votes["left"]
rvotes = votes["right"]

with cl:
    vote_lines = "<br>".join(f"🎯{v['angle']}° 💥{v['power']}" for v in lvotes[-4:]) or "No votes yet"
    st.markdown(f"""
    <div class="qp lp">
      <div class="sn lc">🐵 TEAM LEFT</div>
      <div style="color:#ccc;font-size:.75rem;margin:3px 0">Scan to vote</div>
      {qr_tag(qr_left, left_url)}
      <div style="color:#aaa;font-size:.6rem;margin-top:3px;word-break:break-all">{left_url}</div>
      <div style="color:#ffcc44;font-size:.8rem;margin-top:5px">Votes: <b>{len(lvotes)}</b></div>
      <div style="color:#aaa;font-size:.7rem">{vote_lines}</div>
    </div>""", unsafe_allow_html=True)

with cr:
    vote_lines = "<br>".join(f"🎯{v['angle']}° 💥{v['power']}" for v in rvotes[-4:]) or "No votes yet"
    st.markdown(f"""
    <div class="qp rp">
      <div class="sn rc">TEAM RIGHT 🐵</div>
      <div style="color:#ccc;font-size:.75rem;margin:3px 0">Scan to vote</div>
      {qr_tag(qr_right, right_url)}
      <div style="color:#aaa;font-size:.6rem;margin-top:3px;word-break:break-all">{right_url}</div>
      <div style="color:#44ccff;font-size:.8rem;margin-top:5px">Votes: <b>{len(rvotes)}</b></div>
      <div style="color:#aaa;font-size:.7rem">{vote_lines}</div>
    </div>""", unsafe_allow_html=True)

# ── animated canvas ───────────────────────────────────────────────────────────
with cc:
    traj_json = "null"
    hit_js    = "false"
    hit_side  = "null"
    if game["phase"] == "result" and game.get("last_throw"):
        lt        = game["last_throw"]
        traj_json = json.dumps(lt["trajectory"])
        hit_js    = "true" if lt["hit"] else "false"
        hit_side  = f'"{lt["target_side"]}"'

    # Full self-contained canvas animation — no external deps, pure canvas2d
    canvas_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:transparent;overflow:hidden}}
  canvas{{width:100%;display:block;border-radius:14px}}
</style></head><body>
<canvas id="c" width="900" height="340"></canvas>
<script>
const cv = document.getElementById('c');
const cx = cv.getContext('2d');
const W=900, H=340;

const TRAJ     = {traj_json};
const DID_HIT  = {hit_js};
const HIT_SIDE = {hit_side};  // "left" | "right" | null

// ── drawing helpers ──────────────────────────────────────────────────────────
function drawSky(){{
  const g=cx.createLinearGradient(0,0,0,H);
  g.addColorStop(0,'#3a7ac8'); g.addColorStop(1,'#87ceeb');
  cx.fillStyle=g; cx.fillRect(0,0,W,H);
}}
function drawCloud(x,y,rx,ry){{
  cx.fillStyle='rgba(255,255,255,0.82)';
  [[0,0,rx,ry],[-rx*.3,ry*.38,rx*.58,ry*.7],[rx*.35,ry*.32,rx*.52,ry*.65]]
    .forEach(([dx,dy,ex,ey])=>{{
      cx.beginPath(); cx.ellipse(x+dx,y+dy,ex,ey,0,0,Math.PI*2); cx.fill();
    }});
}}
function drawGround(){{
  const g=cx.createLinearGradient(0,H-50,0,H);
  g.addColorStop(0,'#5a8a3c'); g.addColorStop(1,'#3d6128');
  cx.fillStyle=g; cx.fillRect(0,H-50,W,50);
  cx.fillStyle='#6aa84f'; cx.fillRect(0,H-52,W,6);
}}
function drawBuilding(x,y,w,h,col){{
  cx.fillStyle=col;
  cx.beginPath(); cx.roundRect(x,y,w,h,4); cx.fill();
  cx.fillStyle='rgba(0,0,0,.14)'; cx.fillRect(x,y,w,8);
  const wc=['rgba(255,253,231,.88)','rgba(170,212,245,.88)'];
  for(let wy=y+18;wy<y+h-24;wy+=32)
    for(let wx=x+12;wx<x+w-16;wx+=28){{
      cx.fillStyle=wc[Math.random()>.35?0:1];
      cx.beginPath(); cx.roundRect(wx,wy,16,18,2); cx.fill();
    }}
}}
function drawMonkey(mx,my,flash,right){{
  const mc=flash?'#ff3333':'#c8822a';
  const d=right?1:-1;
  cx.fillStyle=mc;
  cx.beginPath(); cx.ellipse(mx,my+10,13,16,0,0,Math.PI*2); cx.fill(); // body
  cx.beginPath(); cx.arc(mx,my-8,14,0,Math.PI*2); cx.fill(); // head
  cx.fillStyle='#e8b87a';
  cx.beginPath(); cx.ellipse(mx,my-5,9,7,0,0,Math.PI*2); cx.fill(); // face
  [[-5,-13],[5,-13]].forEach(([dx,dy])=>{{
    cx.fillStyle='#fff'; cx.beginPath(); cx.arc(mx+dx,my+dy,2.6,0,Math.PI*2); cx.fill();
    cx.fillStyle='#222'; cx.beginPath(); cx.arc(mx+dx+.5*d,my+dy,1.3,0,Math.PI*2); cx.fill();
  }});
  cx.fillStyle=mc;
  cx.beginPath(); cx.arc(mx-14,my-10,5,0,Math.PI*2); cx.fill();
  cx.beginPath(); cx.arc(mx+14,my-10,5,0,Math.PI*2); cx.fill();
  cx.strokeStyle=mc; cx.lineWidth=5; cx.lineCap='round';
  cx.beginPath(); cx.moveTo(mx+d*12,my+8); cx.lineTo(mx+d*26,my+2); cx.stroke();
  cx.strokeStyle='#f5d020'; cx.lineWidth=4;
  cx.beginPath();
  cx.moveTo(mx+d*26,my+2);
  cx.quadraticCurveTo(mx+d*37,my-5,mx+d*33,my-16);
  cx.stroke();
  if(flash){{
    cx.font='20px serif'; cx.textAlign='center';
    cx.fillText('💥',mx,my-32);
  }}
}}

function scene(flashL, flashR){{
  drawSky();
  drawCloud(W*.17,34,55,22); drawCloud(W*.63,28,65,26); drawCloud(W*.41,18,40,15);
  drawGround();
  drawBuilding(52,182,128,138,'#c0845a');
  drawBuilding(720,162,128,158,'#8a9bbc');
  drawMonkey(155,170,flashL,true);
  drawMonkey(745,150,flashR,false);
}}

// ── animation ────────────────────────────────────────────────────────────────
let frame=0, finished=false, flashOn=false;
const SPEED=5;

function draw(){{
  const fL = DID_HIT && HIT_SIDE==='left'  && flashOn;
  const fR = DID_HIT && HIT_SIDE==='right' && flashOn;
  scene(fL, fR);

  if(!TRAJ||finished) return;

  const end=Math.min(frame, TRAJ.length-1);
  if(end>1){{
    cx.strokeStyle='rgba(245,208,32,.62)';
    cx.lineWidth=2.5; cx.setLineDash([7,4]);
    cx.beginPath(); cx.moveTo(TRAJ[0][0],TRAJ[0][1]);
    for(let i=1;i<=end;i++) cx.lineTo(TRAJ[i][0],TRAJ[i][1]);
    cx.stroke(); cx.setLineDash([]);
  }}
  const [bx,by]=TRAJ[end];
  cx.font='17px serif'; cx.textAlign='center';
  cx.fillText('🍌',bx,by);
}}

function tick(){{
  if(!TRAJ){{ scene(false,false); return; }}
  if(frame<TRAJ.length){{
    frame+=SPEED; draw();
    requestAnimationFrame(tick);
  }}else{{
    finished=true;
    let n=0;
    (function flash(){{
      flashOn=!flashOn; draw();
      if(++n<10) setTimeout(flash,160);
    }})();
  }}
}}
tick();
</script>
</body></html>"""

    st.components.v1.html(canvas_html, height=360, scrolling=False)

# ── bottom controls ───────────────────────────────────────────────────────────
st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
bc1, bc2, bc3 = st.columns([2, 2, 2])

active  = game["turn"]
tvotes  = votes[active]
avg_ang = round(sum(v["angle"] for v in tvotes)/len(tvotes)) if tvotes else 45
avg_pwr = round(sum(v["power"] for v in tvotes)/len(tvotes)) if tvotes else 50

with bc1:
    st.markdown("<div style='background:#1a1a1a;border-radius:10px;padding:10px;text-align:center;"
                "font-family:Bangers,cursive;font-size:.95rem;color:#aaa'>Host override</div>",
                unsafe_allow_html=True)
    man_ang = st.slider("Angle (°)", 10, 80, 45, key="ma")
    man_pwr = st.slider("Power",    10,100, 50, key="mp")

with bc2:
    if tvotes:
        st.markdown(f"""<div style='background:#1e2a1e;border-radius:10px;padding:12px;text-align:center'>
          <div style='font-family:Bangers,cursive;color:#7dff7d;font-size:.95rem'>Crowd average</div>
          <div style='font-family:Bangers,cursive;font-size:2rem;color:#fff'>{avg_ang}° · {avg_pwr}</div>
          <div style='color:#aaa;font-size:.78rem'>{len(tvotes)} vote(s)</div>
        </div>""", unsafe_allow_html=True)
    else:
        avg_ang, avg_pwr = man_ang, man_pwr
        st.markdown(f"""<div style='background:#1e1e2a;border-radius:10px;padding:12px;text-align:center'>
          <div style='font-family:Bangers,cursive;color:#aaa;font-size:.95rem'>No votes — using override</div>
          <div style='font-family:Bangers,cursive;font-size:2rem;color:#fff'>{avg_ang}° · {avg_pwr}</div>
        </div>""", unsafe_allow_html=True)

with bc3:
    st.markdown("<br>", unsafe_allow_html=True)
    if game["phase"] == "voting":
        if st.button("🍌 Throw now!", use_container_width=True, type="primary"):
            traj    = compute_trajectory(avg_ang, avg_pwr, active, game["wind"])
            did_hit = check_hit(traj, active)
            if did_hit:
                if active == "left": game["score_left"]  += 1
                else:                game["score_right"] += 1
            game["last_throw"] = {
                "angle": avg_ang, "power": avg_pwr, "thrower": active,
                "target_side": "right" if active == "left" else "left",
                "hit": did_hit, "trajectory": traj,
            }
            game["phase"] = "result"
            save_state(); clear_votes(); st.rerun()
    else:
        if st.button("➡️ Next turn", use_container_width=True, type="primary"):
            game["turn"]       = "right" if game["turn"] == "left" else "left"
            game["phase"]      = "voting"
            game["turn_start"] = time.time()
            game["last_throw"] = None
            game["wind"]       = round(random.uniform(-7, 7), 1)
            save_state(); clear_votes(); st.rerun()

# ── auto-refresh every second during voting ───────────────────────────────────
if game["phase"] == "voting":
    time.sleep(1)
    st.rerun()
