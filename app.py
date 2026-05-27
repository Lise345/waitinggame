"""
Breaking Down the Building Blocks — PhD Defence Waiting Game
?team=left  → human-hand voter page
?team=right → robot-hand voter page
(no param)  → main game screen

Images (humanhand.png, robothand.png) are loaded from the same folder.
"""
import streamlit as st
import math, json, time, os, io, base64, random
from contextlib import contextmanager

st.set_page_config(page_title="Breaking Down the Building Blocks",
                   layout="wide", initial_sidebar_state="collapsed")

# ── constants ─────────────────────────────────────────────────────────────────
VOTES_FILE  = "votes.json"
GAME_FILE   = "game_state.json"
TURN_SECS   = 15
RESULT_SECS = 6

LMX, LMY = 155, 165
RMX, RMY = 745, 145
HIT_R    = 42
SCALE    = 0.16
GRAV     = 0.12

# Thesis palette
C_BLUE = "#4A6FE3"
C_PINK = "#E8857A"
C_RED  = "#E84040"

# ── load hand images from disk, encode as base64 for embedding in HTML/CSS ────
def _img_b64(filename):
    """Load image file next to app.py and return base64 string."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, filename)
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

HUMAN_B64 = _img_b64("humanhand.png")
ROBOT_B64 = _img_b64("robothand.png")

# ── file locking ──────────────────────────────────────────────────────────────
if os.name == "nt":
    import msvcrt
else:
    import fcntl

@contextmanager
def locked_open(path, mode):
    f = open(path, mode)
    try:
        if os.name == "nt":
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield f
    finally:
        try:
            if os.name == "nt":
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        f.close()

# ── state helpers ─────────────────────────────────────────────────────────────
def _new_game():
    return {"score_left": 0, "score_right": 0,
            "phase": "voting",
            "turn": "left",
            "turn_start": time.time(),
            "result_start": None,
            "last_throw": None,
            "wind": round(random.uniform(-5, 5), 1),
            "last_avg_left":  {"angle": 45, "power": 62},
            "last_avg_right": {"angle": 45, "power": 62}}

def _new_votes():
    return {"left": [], "right": []}

def load_game():
    try:
        if os.path.exists(GAME_FILE):
            with open(GAME_FILE) as f: return json.load(f)
    except Exception: pass
    return _new_game()

def load_votes():
    try:
        if os.path.exists(VOTES_FILE):
            with open(VOTES_FILE) as f: return json.load(f)
    except Exception: pass
    return _new_votes()

def save_game(g):
    with locked_open(GAME_FILE, "w") as f: json.dump(g, f)

def save_votes(v):
    with locked_open(VOTES_FILE, "w") as f: json.dump(v, f)

def persist(g, v): save_game(g); save_votes(v)

if not os.path.exists(GAME_FILE):  save_game(_new_game())
if not os.path.exists(VOTES_FILE): save_votes(_new_votes())

# ── physics ───────────────────────────────────────────────────────────────────
def trajectory(angle_deg, power, direction, wind):
    if direction == "left":
        x, y = LMX, LMY
        rad = math.radians(angle_deg)
    else:
        x, y = RMX, RMY
        rad = math.radians(180 - angle_deg)
    vx =  math.cos(rad) * power * SCALE
    vy = -math.sin(rad) * power * SCALE
    pts = []
    for _ in range(600):
        pts.append([round(x, 1), round(y, 1)])
        vx += wind * 0.01; vy += GRAV; x += vx; y += vy
        if y > 360 or x < -50 or x > 960: break
    return pts

def hits(pts, direction):
    tx, ty = (RMX, RMY) if direction == "left" else (LMX, LMY)
    return any((p[0]-tx)**2 + (p[1]-ty)**2 < HIT_R**2 for p in pts)

# ── QR helper ─────────────────────────────────────────────────────────────────
def make_qr(url):
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(url); qr.make(fit=True)
        img = qr.make_image(fill_color="#1a1a2e", back_color="white")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception: return ""

# ── routing ───────────────────────────────────────────────────────────────────
team_param = st.query_params.get("team", "")

# ═════════════════════════════════════════════════════════════════════════════
# VOTER PAGE
# ═════════════════════════════════════════════════════════════════════════════
if team_param in ("left", "right"):
    team    = team_param
    is_left = team == "left"
    tc       = C_PINK if is_left else C_BLUE
    tbg      = "#2a1a1a" if is_left else "#1a1a2a"
    hand_b64 = HUMAN_B64 if is_left else ROBOT_B64
    label    = "Human Hand 🧬" if is_left else "Robot Hand 🤖"

    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;700&family=DM+Serif+Display&display=swap');
html,body,[class*="css"]{{font-family:'DM Sans',sans-serif;background:#0d0d1a;color:#eee}}
.vh{{background:{tbg};border-left:4px solid {tc};border-radius:0 12px 12px 0;
     padding:16px 18px;margin-bottom:16px;display:flex;align-items:center;gap:14px}}
.vt{{font-family:'DM Serif Display',serif;font-size:1.8rem;color:{tc};margin:0}}
.vs2{{color:#888;font-size:.82rem;margin:3px 0 0}}
.bv{{font-family:'DM Serif Display',serif;font-size:2.8rem;text-align:center;color:{tc};margin:2px 0}}
.ok{{background:linear-gradient(135deg,#1a2a1a,#0d0d1a);border:2px solid #4caf50;
     border-radius:14px;padding:22px;text-align:center;margin-top:10px}}
</style>
<div class="vh">
  <img src="data:image/png;base64,{hand_b64}"
       style="height:60px;width:auto;object-fit:contain"/>
  <div>
    <p class="vt">{label}</p>
    <p class="vs2">Choose your molecule throw for this round</p>
  </div>
</div>""", unsafe_allow_html=True)

    game = load_game()
    now  = time.time()
    secs_left  = max(0.0, TURN_SECS - (now - game.get("turn_start", now)))
    is_my_turn = game["phase"] == "voting" and game["turn"] == team

    if is_my_turn:
        pct = int(secs_left / TURN_SECS * 100)
        bc  = "#4caf50" if secs_left > 8 else "#ffcc44" if secs_left > 4 else C_RED
        st.markdown(f"""
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;font-size:.8rem;
                      color:#888;margin-bottom:4px">
            <span>⏱ Time to vote</span>
            <span style="color:{bc};font-weight:600">{int(secs_left)}s</span>
          </div>
          <div style="background:#222;border-radius:5px;height:8px">
            <div style="width:{pct}%;background:{bc};height:100%;border-radius:5px"></div>
          </div>
        </div>""", unsafe_allow_html=True)
    elif game["phase"] == "voting":
        other = "Robot Hand" if is_left else "Human Hand"
        st.info(f"It's {other}'s turn. Wait for yours!")

    vk = f"voted_{team}"
    if vk not in st.session_state: st.session_state[vk] = False

    if st.session_state[vk]:
        st.markdown("""<div class="ok">
          <div style="font-size:2.4rem">⚗️</div>
          <div style="font-family:'DM Serif Display',serif;font-size:1.7rem;
                      color:#4caf50;margin:5px 0">Vote submitted!</div>
          <div style="color:#888;font-size:.84rem">Watch the main screen!</div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔄 Vote again (new turn)", use_container_width=True):
            st.session_state[vk] = False; st.rerun()
    else:
        st.markdown(f"<div style='font-size:.84rem;color:#aaa;margin:0 0 4px'>"
                    f"🎯 <b style='color:{tc}'>Throw angle</b> — low = flat, high = lofted</div>",
                    unsafe_allow_html=True)
        angle = st.slider("Angle", 10, 80, 45, key="va", label_visibility="collapsed")
        st.markdown(f'<div class="bv">{angle}°</div>', unsafe_allow_html=True)

        # live arc preview SVG
        pts = trajectory(angle, 62, team, 0)
        def sc(px, py, W=260, H=100):
            return round(px*W/900, 1), round(py*H/340, 1)
        path_d = " ".join(
            ("M" if i==0 else "L") + f"{sc(px,py)[0]},{sc(px,py)[1]}"
            for i,(px,py) in enumerate(pts[::4])
        )
        lx, ly = sc(LMX, LMY); rx, ry = sc(RMX, RMY); ex, ey = sc(*pts[-1])
        st.markdown(f"""
        <svg viewBox="0 0 260 105"
             style="width:100%;background:linear-gradient(135deg,#1a1a3e,#0d0d1a);
                    border-radius:10px;margin:4px 0 12px;border:1px solid #2a2a4e">
          <rect x="0" y="90" width="260" height="15" fill="#0a0a18"/>
          <rect x="22" y="52" width="36" height="40" fill="#1a1a3e" rx="2"/>
          <rect x="22" y="50" width="36" height="4" fill="{C_PINK}" rx="1"/>
          <rect x="202" y="44" width="36" height="48" fill="#1a1a3e" rx="2"/>
          <rect x="202" y="42" width="36" height="4" fill="{C_BLUE}" rx="1"/>
          <circle cx="{lx}" cy="{ly}" r="7" fill="{C_RED}" opacity=".7"/>
          <circle cx="{rx}" cy="{ry}" r="7" fill="{C_RED}" opacity=".7"/>
          <path d="{path_d}" fill="none" stroke="{C_RED}" stroke-width="2"
                stroke-dasharray="5 3" opacity=".8"/>
          <circle cx="{ex}" cy="{ey}" r="4" fill="{C_RED}" opacity=".85"/>
          <text x="130" y="102" text-anchor="middle" fill="#333"
                font-size="7" font-family="DM Sans,sans-serif">trajectory preview (no wind)</text>
        </svg>""", unsafe_allow_html=True)

        st.markdown(f"<div style='font-size:.84rem;color:#aaa;margin:0 0 4px'>"
                    f"💥 <b style='color:{tc}'>Throw power</b> — more = farther, don't overshoot!</div>",
                    unsafe_allow_html=True)
        power = st.slider("Power", 10, 100, 62, key="vp", label_visibility="collapsed")
        bw  = int(power * 2.1)
        bc2 = "#4caf50" if power < 45 else "#ffcc44" if power < 72 else C_RED
        st.markdown(f"""
        <div style="background:#1a1a2e;border-radius:5px;height:16px;margin:3px 0 2px;overflow:hidden">
          <div style="width:{min(bw,220)}px;height:100%;background:{bc2};border-radius:5px"></div>
        </div>
        <div class="bv">{power}</div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚗️ Submit vote", use_container_width=True, type="primary"):
            v = load_votes()
            v[team].append({"angle": angle, "power": power, "ts": time.time()})
            save_votes(v)
            st.session_state[vk] = True; st.rerun()

    st.markdown("<div style='text-align:center;color:#333;font-size:.66rem;margin-top:22px'>"
                "Breaking Down the Building Blocks · Lise Vermeersch · VUB</div>",
                unsafe_allow_html=True)
    time.sleep(1)
    st.rerun()
    st.stop()

# ═════════════════════════════════════════════════════════════════════════════
# MAIN GAME SCREEN
# ═════════════════════════════════════════════════════════════════════════════
game  = load_game()
votes = load_votes()
now   = time.time()

# ── phase transitions (fully automatic) ──────────────────────────────────────
if game["phase"] == "voting":
    time_left = max(0.0, TURN_SECS - (now - game.get("turn_start", now)))
    if time_left == 0:
        active = game["turn"]
        tv     = votes[active]
        if tv:
            ang = round(sum(v["angle"] for v in tv) / len(tv))
            pwr = round(sum(v["power"] for v in tv) / len(tv))
            game[f"last_avg_{active}"] = {"angle": ang, "power": pwr}
        else:
            prev = game.get(f"last_avg_{active}", {"angle": 45, "power": 62})
            ang  = prev["angle"]
            pwr  = prev["power"]
        traj    = trajectory(ang, pwr, active, game["wind"])
        did_hit = hits(traj, active)
        if did_hit:
            if active == "left": game["score_left"]  += 1
            else:                game["score_right"] += 1
        game["last_throw"] = {"angle": ang, "power": pwr, "thrower": active,
                              "target_side": "right" if active == "left" else "left",
                              "hit": did_hit, "trajectory": traj}
        game["phase"]        = "result"
        game["result_start"] = now
        persist(game, _new_votes()); st.rerun()

elif game["phase"] == "result":
    result_age = now - (game.get("result_start") or now)
    if result_age >= RESULT_SECS:
        game["turn"]         = "right" if game["turn"] == "left" else "left"
        game["phase"]        = "voting"
        game["turn_start"]   = now
        game["result_start"] = None
        game["last_throw"]   = None
        game["wind"]         = round(random.uniform(-5, 5), 1)
        persist(game, votes); st.rerun()

# ── auto-detect host URL ──────────────────────────────────────────────────────
def _detect_url():
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        host = headers.get("Host", "")
        if host and "localhost" not in host and "127.0.0.1" not in host:
            proto = "https" if "streamlit.app" in host else "http"
            return f"{proto}://{host}"
    except Exception: pass
    try:
        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx and hasattr(ctx, "request") and ctx.request:
            host = ctx.request.headers.get("host", "")
            if host and "localhost" not in host:
                proto = "https" if "streamlit.app" in host else "http"
                return f"{proto}://{host}"
    except Exception: pass
    return ""

if "detected_url" not in st.session_state:
    st.session_state.detected_url = _detect_url()

# ── sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Setup")
default_url = st.session_state.detected_url or "https://waitinggame-jbyqzggvgecpqpuxie5jtt.streamlit.app"
app_url = st.sidebar.text_input("This app's public URL (for QR codes)", value=default_url)
st.sidebar.success("✅ QR codes point to this URL")
st.sidebar.caption("Voters scan → `?team=left` or `?team=right`")
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Reset game"):
    persist(_new_game(), _new_votes()); st.rerun()

# ── QR codes ──────────────────────────────────────────────────────────────────
left_url  = app_url.rstrip("/") + "?team=left"
right_url = app_url.rstrip("/") + "?team=right"
qr_l = make_qr(left_url)
qr_r = make_qr(right_url)
def qrtag(b64, url):
    if b64: return f"<img src='data:image/png;base64,{b64}' style='width:115px;border-radius:5px'/>"
    return f"<div style='font-size:.6rem;color:#aaa;word-break:break-all'>{url}</div>"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;700&family=DM+Serif+Display&display=swap');
html,body,[class*="css"]{{font-family:'DM Sans',sans-serif;background:#0d0d1a;color:#eee}}
#MainMenu,footer,header{{visibility:hidden}}
.block-container{{padding-top:1rem!important}}
.title-main{{font-family:'DM Serif Display',serif;font-size:1.55rem;text-align:center;
             color:#fff;letter-spacing:.3px;margin-bottom:1px}}
.title-sub{{font-size:.72rem;text-align:center;color:#666;letter-spacing:2px;
            text-transform:uppercase;margin-bottom:7px}}
.sb{{display:flex;justify-content:space-around;align-items:center;
     background:linear-gradient(135deg,#12122a,#0d0d1a);
     border:1px solid #252540;border-radius:12px;padding:8px 20px;margin:5px 0 7px}}
.sn{{font-size:.95rem;font-weight:500;letter-spacing:.3px}}
.sv{{font-family:'DM Serif Display',serif;font-size:2.8rem;line-height:1}}
.lc{{color:{C_PINK}}}.rc{{color:{C_BLUE}}}
.vs{{font-family:'DM Serif Display',serif;font-size:1.3rem;color:#333}}
.qp{{border-radius:12px;padding:11px;text-align:center;height:100%}}
.lp{{background:#1c1014;border:1px solid {C_PINK}}}
.rp{{background:#10141c;border:1px solid {C_BLUE}}}
.rmsg{{font-family:'DM Serif Display',serif;font-size:1.45rem;
       letter-spacing:.3px;text-align:center;margin:2px 0 3px}}
</style>""", unsafe_allow_html=True)

# ── header + wind ─────────────────────────────────────────────────────────────
w      = game["wind"]
w_pct  = abs(w) / 5 * 50
w_col  = "#4fc3f7" if abs(w) < 2 else "#ffcc44" if abs(w) < 4 else C_RED
arrow  = "➡️" if w > 0 else ("⬅️" if w < 0 else "—")
w_str  = "Calm" if abs(w)<1 else "Light" if abs(w)<2.5 else "Moderate" if abs(w)<4 else "Strong"
w_label = f"{arrow} {w_str} ({w:+.1f})"

st.markdown(f"""
<div class="title-main">Breaking Down the Building Blocks</div>
<div class="title-sub">PhD Defence Waiting Game · Lise Vermeersch · VUB</div>
<div class="sb">
  <div><div class="sn lc">🧬 Human Hand</div><div class="sv lc">{game['score_left']}</div></div>
  <div class="vs">vs</div>
  <div><div class="sv rc">{game['score_right']}</div><div class="sn rc">Robot Hand 🤖</div></div>
</div>
<div style="background:#0c0c1c;border:1px solid #252540;border-radius:10px;
            padding:8px 16px;margin:0 0 6px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">
    <span style="font-size:.78rem;color:#666;letter-spacing:1px;text-transform:uppercase">💨 Wind</span>
    <span style="font-family:'DM Serif Display',serif;font-size:1.15rem;color:{w_col}">{w_label}</span>
    <span style="font-size:.72rem;color:#444">affects molecule arc</span>
  </div>
  <div style="position:relative;background:#1a1a2e;border-radius:6px;height:14px">
    <div style="position:absolute;left:50%;top:0;width:2px;height:100%;background:#2a2a4e"></div>
    <div style="position:absolute;left:{'50%' if w>=0 else str(round(50-w_pct,1))+'%'};
                width:{w_pct:.1f}%;height:100%;background:{w_col};border-radius:6px;opacity:.85"></div>
    <div style="position:absolute;{'left' if w>0 else 'right'}:{round(100-50-w_pct,1)}%;
                top:-3px;font-size:1.1rem;line-height:1">
      {'▶' if w>0 else ('◀' if w<0 else '')}</div>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:.62rem;color:#333;
              margin-top:2px;padding:0 2px">
    <span>← Left</span><span>No wind</span><span>Right →</span>
  </div>
</div>""", unsafe_allow_html=True)

# ── countdown / result banner ─────────────────────────────────────────────────
if game["phase"] == "voting":
    time_left = max(0.0, TURN_SECS - (now - game.get("turn_start", now)))
    pct = int(time_left / TURN_SECS * 100)
    bc  = "#4caf50" if time_left>8 else "#ffcc44" if time_left>4 else C_RED
    tn  = "🧬 Human Hand" if game["turn"]=="left" else "🤖 Robot Hand"
    tc2 = C_PINK if game["turn"]=="left" else C_BLUE
    st.markdown(f"""
    <div style="margin:0 0 6px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">
        <span style="font-family:'DM Serif Display',serif;font-size:1.2rem;color:{tc2}">
          {tn} — vote now!</span>
        <span style="font-family:'DM Serif Display',serif;font-size:1.45rem;color:{bc}">{int(time_left)}s</span>
      </div>
      <div style="background:#1a1a2e;border-radius:7px;height:12px">
        <div style="width:{pct}%;background:{bc};height:100%;border-radius:7px;transition:width .4s"></div>
      </div>
    </div>""", unsafe_allow_html=True)
else:
    lt  = game.get("last_throw") or {}
    thr = "🧬 Human Hand" if lt.get("thrower")=="left" else "🤖 Robot Hand"
    msg = f"💥 Direct hit — point for {thr}!" if lt.get("hit") else "⚗️ Near miss — molecule sailed past…"
    col = C_RED if lt.get("hit") else "#888"
    result_age = now - (game.get("result_start") or now)
    remaining  = max(0, RESULT_SECS - result_age)
    st.markdown(f"""
    <div class="rmsg" style="color:{col}">{msg}</div>
    <div style="text-align:center;color:#555;font-size:.8rem;margin-bottom:5px">
      Next round in {int(remaining)}s…</div>""", unsafe_allow_html=True)

# ── columns ───────────────────────────────────────────────────────────────────
cl, cc, cr = st.columns([1.2, 4.6, 1.2])
lv = votes["left"]; rv = votes["right"]

with cl:
    vl = "<br>".join(f"∠{v['angle']}° · {v['power']}" for v in lv[-4:]) or "No votes yet"
    st.markdown(f"""
    <div class="qp lp">
      <div class="sn lc" style="margin-bottom:4px">🧬 Human</div>
      <div style="color:#666;font-size:.7rem;margin:2px 0">Scan to vote</div>
      {qrtag(qr_l, left_url)}
      <div style="color:#333;font-size:.56rem;margin-top:3px;word-break:break-all">{left_url}</div>
      <div style="color:{C_PINK};font-size:.76rem;margin-top:4px">Votes: <b>{len(lv)}</b></div>
      <div style="color:#555;font-size:.66rem;margin-top:2px">{vl}</div>
    </div>""", unsafe_allow_html=True)

with cr:
    vr = "<br>".join(f"∠{v['angle']}° · {v['power']}" for v in rv[-4:]) or "No votes yet"
    st.markdown(f"""
    <div class="qp rp">
      <div class="sn rc" style="margin-bottom:4px">Robot 🤖</div>
      <div style="color:#666;font-size:.7rem;margin:2px 0">Scan to vote</div>
      {qrtag(qr_r, right_url)}
      <div style="color:#333;font-size:.56rem;margin-top:3px;word-break:break-all">{right_url}</div>
      <div style="color:{C_BLUE};font-size:.76rem;margin-top:4px">Votes: <b>{len(rv)}</b></div>
      <div style="color:#555;font-size:.66rem;margin-top:2px">{vr}</div>
    </div>""", unsafe_allow_html=True)

# ── canvas ────────────────────────────────────────────────────────────────────
with cc:
    phase    = game["phase"]
    lt       = game.get("last_throw") or {}
    traj_js  = json.dumps(lt.get("trajectory") or [])
    did_hit  = "true" if lt.get("hit") else "false"
    hit_side = f'"{lt.get("target_side","")}"'
    res_age  = (now - (game.get("result_start") or now)) if phase=="result" else 0

    # Preview trajectory for voting phase
    preview_traj = []
    if phase == "voting":
        active_votes = votes[game["turn"]]
        if active_votes:
            pa = round(sum(v["angle"] for v in active_votes) / len(active_votes))
            pp = round(sum(v["power"] for v in active_votes) / len(active_votes))
        else:
            prev = game.get(f"last_avg_{game['turn']}", {"angle": 45, "power": 62})
            pa, pp = prev["angle"], prev["power"]
        preview_traj = trajectory(pa, pp, game["turn"], game["wind"])
    preview_js = json.dumps(preview_traj)

    # Pass image data safely as JS variables — not inside f-string JS
    human_b64_js = HUMAN_B64
    robot_b64_js = ROBOT_B64

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;overflow:hidden}}
canvas{{width:100%;display:block;border-radius:13px}}</style></head><body>
<canvas id="c" width="900" height="320"></canvas>
<script>
const cv=document.getElementById('c'),cx=cv.getContext('2d'),W=900,H=320;
const LMX=155,LMY=165,RMX=745,RMY=145;
const PHASE="{phase}";
const TRAJ={traj_js};
const DID_HIT={did_hit};
const HIT_SIDE={hit_side};
const RES_AGE={res_age:.2f};
const ANIM_DUR=2.5;
const PREVIEW={preview_js};

// images loaded from data URIs
const humanImg=new Image(), robotImg=new Image();
humanImg.src='data:image/png;base64,{human_b64_js}';
robotImg.src='data:image/png;base64,{robot_b64_js}';
let ready=0;
humanImg.onload=robotImg.onload=()=>{{if(++ready===2)start();}};
setTimeout(()=>{{if(ready<2){{ready=2;start();}}}},900);

function bg(){{
  const g=cx.createLinearGradient(0,0,W,H);
  g.addColorStop(0,'#3558d4');g.addColorStop(.55,'#8060b8');g.addColorStop(1,'#e07a72');
  cx.fillStyle=g;cx.fillRect(0,0,W,H);
  cx.fillStyle='rgba(255,255,255,.03)';
  for(let x=0;x<W;x+=18)for(let y=0;y<H;y+=18)
    {{cx.beginPath();cx.arc(x,y,1,0,Math.PI*2);cx.fill();}}
}}
function arch(){{
  cx.strokeStyle='rgba(255,255,255,.2)';cx.lineWidth=1.5;
  cx.beginPath();cx.arc(W*.5,H*.6,H*.72,-Math.PI*.62,Math.PI*.08);cx.stroke();
}}
function redcircle(x,y,r,a){{
  cx.fillStyle=`rgba(232,64,64,${{a}})`;
  cx.beginPath();cx.arc(x,y,r,0,Math.PI*2);cx.fill();
  cx.strokeStyle=`rgba(255,160,140,${{a*.35}})`;cx.lineWidth=1.5;
  cx.beginPath();cx.arc(x,y,r*.72,0,Math.PI*2);cx.stroke();
}}
function drawHand(img,x,y,w,h,flip,flash){{
  cx.save();
  if(flash){{cx.shadowColor='#E84040';cx.shadowBlur=28;}}
  if(flip){{cx.translate(x+w/2,y+h/2);cx.scale(-1,1);cx.drawImage(img,-w/2,-h/2,w,h);}}
  else cx.drawImage(img,x,y,w,h);
  cx.restore();
  if(flash){{
    cx.fillStyle='rgba(232,64,64,.28)';
    cx.beginPath();cx.arc(x+w/2,y+h*.25,44,0,Math.PI*2);cx.fill();
  }}
}}
function molecule(x,y,r,col){{
  cx.fillStyle=col;cx.beginPath();cx.arc(x,y,r,0,Math.PI*2);cx.fill();
  cx.strokeStyle=col;cx.lineWidth=2;
  [[-r*1.9,-r*1.1],[r*1.9,-r*.8],[0,-r*2.1]].forEach(([dx,dy])=>{{
    cx.beginPath();cx.moveTo(x,y);cx.lineTo(x+dx,y+dy);cx.stroke();
    cx.fillStyle=col;cx.beginPath();cx.arc(x+dx,y+dy,r*.6,0,Math.PI*2);cx.fill();
  }});
}}
function scene(fL,fR){{
  bg(); arch();
  redcircle(W*.11,H*.54,85,.82);
  redcircle(W*.87,H*.28,42,.72);
  redcircle(W*.73,H*.78,18,.62);
  drawHand(humanImg, LMX-88, H-230, 155, 245, false, fL);
  drawHand(robotImg,  RMX-70, H-225, 155, 245, true,  fR);
  molecule(LMX,LMY-6,8,fL?'#ff6666':'#E84040');
  molecule(RMX,RMY-6,8,fR?'#ff6666':'#E84040');
  cx.fillStyle='rgba(255,255,255,.35)';
  cx.font='10px "DM Sans",sans-serif';cx.textAlign='center';
  cx.fillText('Breaking Down the Building Blocks · PhD Defence · Lise Vermeersch · VUB',W/2,H-7);
}}

function start(){{
  if(PHASE!=='result'||!TRAJ||!TRAJ.length){{
    scene(false,false);
    if(PREVIEW&&PREVIEW.length>1){{
      cx.strokeStyle='rgba(255,255,255,.4)';cx.lineWidth=2.5;cx.setLineDash([10,6]);
      cx.beginPath();cx.moveTo(PREVIEW[0][0],PREVIEW[0][1]);
      for(let i=1;i<PREVIEW.length;i+=3)cx.lineTo(PREVIEW[i][0],PREVIEW[i][1]);
      cx.stroke();cx.setLineDash([]);
      const end=PREVIEW[PREVIEW.length-1];
      molecule(end[0],end[1],5,'rgba(255,255,255,.5)');
      cx.fillStyle='rgba(255,255,255,.6)';
      cx.font='12px "DM Sans",sans-serif';cx.textAlign='center';
      cx.fillText('Predicted landing',end[0],end[1]-18);
    }}
  }} else {{
    const total=TRAJ.length,steps=Math.round(ANIM_DUR*60),skip=total/steps;
    const sf=Math.min(RES_AGE/ANIM_DUR,1.0);
    let idx=Math.floor(sf*total),flashing=sf>=1.0,flashN=0,flashOn=DID_HIT&&flashing;
    function frame(){{
      if(!flashing){{
        idx=Math.min(idx+skip,total-1);
        scene(false,false);
        if(idx>1){{
          cx.strokeStyle='rgba(255,255,255,.55)';cx.lineWidth=2.5;cx.setLineDash([7,4]);
          cx.beginPath();cx.moveTo(TRAJ[0][0],TRAJ[0][1]);
          for(let i=1;i<=Math.floor(idx);i++)cx.lineTo(TRAJ[i][0],TRAJ[i][1]);
          cx.stroke();cx.setLineDash([]);
        }}
        const ti=Math.floor(idx);
        molecule(TRAJ[ti][0],TRAJ[ti][1],6,'#ff9966');
        if(idx>=total-1)flashing=true; else requestAnimationFrame(frame);
      }} else {{
        flashOn=!flashOn;
        scene(DID_HIT&&HIT_SIDE==='left'&&flashOn, DID_HIT&&HIT_SIDE==='right'&&flashOn);
        cx.strokeStyle='rgba(255,255,255,.25)';cx.lineWidth=1.5;cx.setLineDash([6,4]);
        cx.beginPath();cx.moveTo(TRAJ[0][0],TRAJ[0][1]);
        TRAJ.forEach(([x,y])=>cx.lineTo(x,y));cx.stroke();cx.setLineDash([]);
        if(++flashN<12)setTimeout(()=>requestAnimationFrame(frame),180);
      }}
    }}
    requestAnimationFrame(frame);
  }}
}}
</script></body></html>"""

    st.components.v1.html(html, height=340, scrolling=False)

# ── bottom: crowd average + manual override ───────────────────────────────────
st.markdown("<div style='height:3px'></div>", unsafe_allow_html=True)
b1, b2, b3 = st.columns([2, 2, 2])

active = game["turn"]
tv     = votes[active]
avg_a  = round(sum(v["angle"] for v in tv)/len(tv)) if tv else 45
avg_p  = round(sum(v["power"] for v in tv)/len(tv)) if tv else 62

with b1:
    st.markdown("<div style='background:#0c0c1c;border:1px solid #252540;border-radius:8px;"
                "padding:9px;text-align:center;font-size:.82rem;color:#555;"
                "margin-bottom:6px'>Host override</div>", unsafe_allow_html=True)
    man_a = st.slider("Angle (°)", 10, 80, 45, key="ma")
    man_p = st.slider("Power",    10,100, 62, key="mp")

with b2:
    if tv:
        st.markdown(f"""<div style='background:#0c1a0c;border:1px solid #1a3a1a;
                    border-radius:8px;padding:11px;text-align:center'>
          <div style='font-size:.8rem;color:#4caf50;letter-spacing:1px;text-transform:uppercase'>
            Crowd average</div>
          <div style='font-family:"DM Serif Display",serif;font-size:2rem;
                      color:#fff;margin:2px 0'>{avg_a}° · {avg_p}</div>
          <div style='color:#555;font-size:.75rem'>{len(tv)} vote(s) received</div>
        </div>""", unsafe_allow_html=True)
    else:
        avg_a, avg_p = man_a, man_p
        st.markdown(f"""<div style='background:#0c0c1c;border:1px solid #252540;
                    border-radius:8px;padding:11px;text-align:center'>
          <div style='font-size:.8rem;color:#444;letter-spacing:1px;text-transform:uppercase'>
            No votes — host override</div>
          <div style='font-family:"DM Serif Display",serif;font-size:2rem;
                      color:#fff;margin:2px 0'>{avg_a}° · {avg_p}</div>
        </div>""", unsafe_allow_html=True)

with b3:
    st.markdown("<br>", unsafe_allow_html=True)
    if game["phase"] == "voting":
        if st.button("⚗️ Throw now! (skip timer)", use_container_width=True, type="primary"):
            traj    = trajectory(avg_a, avg_p, active, game["wind"])
            did_hit = hits(traj, active)
            if did_hit:
                if active=="left": game["score_left"]  += 1
                else:              game["score_right"] += 1
            game["last_throw"]   = {"angle": avg_a, "power": avg_p, "thrower": active,
                                    "target_side": "right" if active=="left" else "left",
                                    "hit": did_hit, "trajectory": traj}
            game["phase"]        = "result"
            game["result_start"] = now
            persist(game, _new_votes()); st.rerun()
    else:
        if st.button("➡️ Next round now", use_container_width=True):
            game["turn"]         = "right" if game["turn"]=="left" else "left"
            game["phase"]        = "voting"
            game["turn_start"]   = now
            game["result_start"] = None
            game["last_throw"]   = None
            game["wind"]         = round(random.uniform(-5, 5), 1)
            persist(game, votes); st.rerun()

# ── auto-rerun every second ───────────────────────────────────────────────────
time.sleep(1)
st.rerun()
