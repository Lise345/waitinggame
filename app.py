"""
Monkey Banana Battle — single Streamlit file.
?team=left / ?team=right  → voter page
(no param)                → main game screen
"""
import streamlit as st
import math, json, time, os, io, base64, random
from contextlib import contextmanager

st.set_page_config(page_title="🍌 Monkey Banana Battle",
                   layout="wide", initial_sidebar_state="collapsed")

# ── constants ─────────────────────────────────────────────────────────────────
VOTES_FILE  = "votes.json"
GAME_FILE   = "game_state.json"
TURN_SECS   = 15          # seconds players have to vote
RESULT_SECS = 6           # seconds result is shown before next turn starts

# Canvas 900×340. Buildings and monkey positions must match JS exactly.
LMX, LMY = 155, 165       # left monkey centre (top of left building)
RMX, RMY = 745, 145       # right monkey centre (top of right building)
HIT_R     = 42            # hit radius in px

# Physics: scale=0.16, gravity=0.12 gives hits at angle≈30-60°, power≈54-70
SCALE = 0.16
GRAV  = 0.12

# ── file locking ─────────────────────────────────────────────────────────────
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
            "phase": "voting",        # voting | result
            "turn": "left",
            "turn_start": time.time(),
            "result_start": None,
            "last_throw": None,
            "wind": round(random.uniform(-5, 5), 1),
            "last_avg_left":  {"angle": 45, "power": 62},
            "last_avg_right": {"angle": 45, "power": 62}}

def _new_votes():
    return {"left": [], "right": []}

# ── shared state helpers ────────────────────────────────────────────────────
def load_game():
    try:
        if os.path.exists(GAME_FILE):
            with open(GAME_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return _new_game()


def load_votes():
    try:
        if os.path.exists(VOTES_FILE):
            with open(VOTES_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return _new_votes()


def save_game(game):
    with locked_open(GAME_FILE, "w") as f:
        json.dump(game, f)


def save_votes(votes):
    with locked_open(VOTES_FILE, "w") as f:
        json.dump(votes, f)


def persist(game, votes):
    save_game(game)
    save_votes(votes)


# initialize shared files if missing
if not os.path.exists(GAME_FILE):
    save_game(_new_game())

if not os.path.exists(VOTES_FILE):
    save_votes(_new_votes())

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
        vx += wind * 0.01
        vy += GRAV
        x  += vx
        y  += vy
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
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception: return ""

# ── routing ───────────────────────────────────────────────────────────────────
team_param = st.query_params.get("team", "")

# ═════════════════════════════════════════════════════════════════════════════
# VOTER PAGE
# ═════════════════════════════════════════════════════════════════════════════
if team_param in ("left", "right"):
    team = team_param
    tc  = "#ffcc44" if team == "left" else "#44ccff"
    tbg = "#1e2a14" if team == "left" else "#141e2a"
    tbr = tc

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@400;700&display=swap');
    html,body,[class*="css"]{{font-family:'Nunito',sans-serif;background:#111}}
    .th{{background:{tbg};border:3px solid {tbr};border-radius:18px;
         padding:18px;text-align:center;margin-bottom:14px}}
    .tn{{font-family:'Bangers',cursive;font-size:2.2rem;color:{tc};letter-spacing:3px;margin:0}}
    .bv{{font-family:'Bangers',cursive;font-size:2.6rem;text-align:center;color:{tc};margin:2px 0}}
    .ok{{background:#1a3a1a;border:2px solid #4caf50;border-radius:16px;
         padding:20px;text-align:center;margin-top:12px}}
    </style>
    <div class="th">
      <p class="tn">TEAM {'LEFT 🟡' if team=='left' else 'RIGHT 🔵'}</p>
      <p style="color:#aaa;font-size:.85rem;margin:3px 0 0">🍌 Choose your throw!</p>
    </div>""", unsafe_allow_html=True)

    game = load_game()
    votes = load_votes()
    now  = time.time()
    secs_left = max(0.0, TURN_SECS - (now - game.get("turn_start", now)))
    is_my_turn = game["phase"] == "voting" and game["turn"] == team

    # countdown bar
    if is_my_turn:
        pct = int(secs_left / TURN_SECS * 100)
        bc  = "#4caf50" if secs_left > 8 else "#ffcc44" if secs_left > 4 else "#ff5722"
        st.markdown(f"""
        <div style="margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;color:#aaa;
                      font-size:.8rem;margin-bottom:4px">
            <span>⏱ Time to vote</span>
            <span style="color:{bc};font-weight:700">{int(secs_left)}s</span>
          </div>
          <div style="background:#333;border-radius:6px;height:10px">
            <div style="width:{pct}%;background:{bc};height:100%;border-radius:6px"></div>
          </div>
        </div>""", unsafe_allow_html=True)
    elif game["phase"] == "voting":
        other = "RIGHT" if team == "left" else "LEFT"
        st.info(f"It's {other} team's turn. Wait for yours!")

    vk = f"voted_{team}"
    if vk not in st.session_state: st.session_state[vk] = False

    if st.session_state[vk]:
        st.markdown("""<div class="ok">
          <div style="font-size:2.8rem">✅</div>
          <div style="font-family:'Bangers',cursive;font-size:1.9rem;color:#4caf50">Vote counted!</div>
          <div style="color:#aaa;margin-top:5px;font-size:.88rem">Watch the main screen!</div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔄 Vote again (new turn)", use_container_width=True):
            st.session_state[vk] = False; st.rerun()
    else:
        angle = st.slider("🎯 Throw Angle", 10, 80, 45, key="va")
        st.markdown(f'<div class="bv">{angle}°</div>', unsafe_allow_html=True)

        # live arc preview
        pts = trajectory(angle, 62, team, 0)
        def sc(px, py, W=260, H=110):
            return round(px*W/900, 1), round(py*H/340, 1)
        path_d = " ".join(
            ("M" if i==0 else "L") + f"{sc(px,py)[0]},{sc(px,py)[1]}"
            for i,(px,py) in enumerate(pts[::4])
        )
        lx,ly = sc(LMX,LMY); rx,ry = sc(RMX,RMY)
        ex,ey = sc(*pts[-1])
        st.markdown(f"""
        <svg viewBox="0 0 260 115"
             style="width:100%;background:#1a2535;border-radius:10px;margin:2px 0 10px">
          <rect x="0" y="93" width="260" height="22" fill="#3d6128" rx="2"/>
          <rect x="28" y="55" width="36" height="40" fill="#a0704a" rx="2"/>
          <rect x="196" y="48" width="36" height="47" fill="#7a8aaa" rx="2"/>
          <text x="{lx}" y="{ly+4}" text-anchor="middle" font-size="11">🐵</text>
          <text x="{rx}" y="{ry+4}" text-anchor="middle" font-size="11">🐵</text>
          <path d="{path_d}" fill="none" stroke="#f5d020" stroke-width="2"
                stroke-dasharray="5 3" opacity=".85"/>
          <text x="{ex}" y="{ey+4}" text-anchor="middle" font-size="10">🍌</text>
        </svg>""", unsafe_allow_html=True)

        power = st.slider("💥 Power", 10, 100, 62, key="vp")
        bw = int(power * 2.1); bc = "#4caf50" if power<45 else "#ffcc44" if power<72 else "#ff5722"
        st.markdown(f"""
        <div style="background:#222;border-radius:7px;height:20px;margin:3px 0 2px;overflow:hidden">
          <div style="width:{min(bw,220)}px;height:100%;background:{bc};border-radius:7px"></div>
        </div>
        <div class="bv">{power}</div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🍌 SUBMIT VOTE", use_container_width=True, type="primary"):
            votes = load_votes()

            votes[team].append({
                "angle": angle,
                "power": power,
                "ts": time.time()
            })
            
            save_votes(votes)
            st.session_state[vk] = True; st.rerun()

    st.markdown(f"<div style='text-align:center;color:#333;font-size:.68rem;margin-top:20px'>"
                f"Monkey Banana Battle · Team {team.upper()}</div>", unsafe_allow_html=True)
    time.sleep(1)
    st.rerun()
    st.stop()

# ═════════════════════════════════════════════════════════════════════════════
# MAIN GAME SCREEN
# ═════════════════════════════════════════════════════════════════════════════
game = load_game()
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
        
            game[f"last_avg_{active}"] = {
                "angle": ang,
                "power": pwr
            }
        else:
            prev = game.get(
                f"last_avg_{active}",
                {"angle": 45, "power": 62}
            )
        
            ang = prev["angle"]
            pwr = prev["power"]
        traj   = trajectory(ang, pwr, active, game["wind"])
        did_hit = hits(traj, active)
        if did_hit:
            if active == "left": game["score_left"]  += 1
            else:                game["score_right"] += 1
        game["last_throw"] = {
            "angle": ang, "power": pwr, "thrower": active,
            "target_side": "right" if active == "left" else "left",
            "hit": did_hit, "trajectory": traj}
        game["phase"]        = "result"
        game["result_start"] = now
        votes = _new_votes()
        persist(game, votes)
        st.rerun()

elif game["phase"] == "result":
    result_age = now - (game.get("result_start") or now)
    if result_age >= RESULT_SECS:
        game["turn"]       = "right" if game["turn"] == "left" else "left"
        game["phase"]      = "voting"
        game["turn_start"] = now
        game["result_start"] = None
        game["last_throw"] = None
        game["wind"]       = round(random.uniform(-5, 5), 1)
        persist(game, votes)
        st.rerun()

# ── auto-detect host URL ──────────────────────────────────────────────────────
def _detect_url():
    """Try to get the real public URL from Streamlit's runtime headers."""
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        host = headers.get("Host", "")
        if host and "localhost" not in host and "127.0.0.1" not in host:
            proto = "https" if "streamlit.app" in host else "http"
            return f"{proto}://{host}"
    except Exception:
        pass
    try:
        # Streamlit >= 1.30 exposes this cleanly
        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx and hasattr(ctx, "request") and ctx.request:
            host = ctx.request.headers.get("host", "")
            if host and "localhost" not in host:
                proto = "https" if "streamlit.app" in host else "http"
                return f"{proto}://{host}"
    except Exception:
        pass
    return ""

if "detected_url" not in st.session_state:
    st.session_state.detected_url = _detect_url()

# ── sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Setup")

default_url = st.session_state.detected_url or "https://waitinggame-jbyqzggvgecpqpuxie5jtt.streamlit.app"
app_url = st.sidebar.text_input(
    "This app's public URL (for QR codes)",
    value=default_url,
    help="Update this if you redeploy to a different URL.")
st.sidebar.success(f"✅ QR codes point to this URL")

st.sidebar.caption("QR codes link to `<url>?team=left` and `?team=right`")
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Reset game"):
    game  = _new_game()
    votes = _new_votes()
    persist(game, votes); st.rerun()

# ── QR codes ─────────────────────────────────────────────────────────────────
left_url  = app_url.rstrip("/") + "?team=left"
right_url = app_url.rstrip("/") + "?team=right"
qr_l = make_qr(left_url)
qr_r = make_qr(right_url)
def qrtag(b64, url):
    if b64: return f"<img src='data:image/png;base64,{b64}' style='width:115px;border-radius:5px'/>"
    return f"<div style='font-size:.6rem;color:#aaa;word-break:break-all'>{url}</div>"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@400;700&display=swap');
html,body,[class*="css"]{font-family:'Nunito',sans-serif}
.title{font-family:'Bangers',cursive;font-size:2.4rem;letter-spacing:3px;
       text-align:center;color:#f5a623;text-shadow:3px 3px 0 #7b3f00;margin-bottom:4px}
.sb{display:flex;justify-content:space-around;align-items:center;
    background:linear-gradient(135deg,#2d5a27,#1a3a16);
    border-radius:14px;padding:8px 28px;margin:5px 0 7px}
.sn{font-family:'Bangers',cursive;font-size:1.15rem;letter-spacing:2px}
.sv{font-family:'Bangers',cursive;font-size:3rem;line-height:1}
.lc{color:#ffcc44}.rc{color:#44ccff}
.vs{font-family:'Bangers',cursive;font-size:1.5rem;color:#fff;opacity:.5}
.qp{border-radius:13px;padding:11px;text-align:center;height:100%}
.lp{background:#1e2a14;border:2px solid #ffcc44}
.rp{background:#141e2a;border:2px solid #44ccff}
.rmsg{font-family:'Bangers',cursive;font-size:1.6rem;letter-spacing:2px;
      text-align:center;margin:3px 0 5px}
</style>""", unsafe_allow_html=True)

# ── header ────────────────────────────────────────────────────────────────────
w = game["wind"]
# Wind bar: centre=0, range -5..+5. Arrow points in wind direction.
# Bar fills from centre outward; colour = strength
w_pct      = abs(w) / 5 * 50        # 0-50% of half-bar
w_left     = (50 - w_pct) if w < 0 else 50   # left edge of filled segment
w_width    = w_pct
w_col      = "#4fc3f7" if abs(w) < 2 else "#ffcc44" if abs(w) < 4 else "#ff5722"
arrow      = "➡️" if w > 0 else ("⬅️" if w < 0 else "⬆️")
strength   = "Calm" if abs(w)<1 else "Light" if abs(w)<2.5 else "Moderate" if abs(w)<4 else "Strong"
w_label    = f"{arrow} {strength} wind ({w:+.1f})"

st.markdown(f"""
<div class="title">🍌 Monkey Banana Battle 🐵</div>
<div class="sb">
  <div><div class="sn lc">🐵 Team Left</div><div class="sv lc">{game['score_left']}</div></div>
  <div class="vs">VS</div>
  <div><div class="sv rc">{game['score_right']}</div><div class="sn rc">Team Right 🐵</div></div>
</div>
<div style="background:#1a1a2e;border-radius:10px;padding:8px 16px;margin:6px 0 6px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">
    <span style="font-family:'Bangers',cursive;font-size:1.1rem;color:#aaa;letter-spacing:1px">💨 WIND</span>
    <span style="font-family:'Bangers',cursive;font-size:1.2rem;color:{w_col}">{w_label}</span>
    <span style="font-family:'Bangers',cursive;font-size:1.1rem;color:#aaa;letter-spacing:1px">affects banana!</span>
  </div>
  <div style="position:relative;background:#333;border-radius:6px;height:14px">
    <!-- centre tick -->
    <div style="position:absolute;left:50%;top:0;width:2px;height:100%;background:#555"></div>
    <!-- filled segment -->
    <div style="position:absolute;left:{50 if w>=0 else 50-w_pct:.1f}%;
                width:{w_pct:.1f}%;height:100%;background:{w_col};border-radius:6px;
                opacity:.85"></div>
    <!-- arrow head at tip -->
    <div style="position:absolute;
                {'left' if w>0 else 'right'}:{100-50-w_pct if w>0 else 100-50-w_pct:.1f}%;
                top:-3px;font-size:1.1rem;line-height:1;transform:translateX({'- ' if w>0 else ''}50%)">
      {'▶' if w>0 else ('◀' if w<0 else '')}</div>
  </div>
  <div style="display:flex;justify-content:space-between;
              font-size:.65rem;color:#555;margin-top:2px;padding:0 2px">
    <span>← Left</span><span>No wind</span><span>Right →</span>
  </div>
</div>""", unsafe_allow_html=True)

# ── countdown / result banner ─────────────────────────────────────────────────
if game["phase"] == "voting":
    time_left = max(0.0, TURN_SECS - (now - game.get("turn_start", now)))
    pct = int(time_left / TURN_SECS * 100)
    bc  = "#4caf50" if time_left>8 else "#ffcc44" if time_left>4 else "#ff5722"
    tn  = game["turn"].upper()
    tc  = "#ffcc44" if game["turn"]=="left" else "#44ccff"
    st.markdown(f"""
    <div style="margin:0 0 6px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">
        <span style="font-family:'Bangers',cursive;font-size:1.25rem;color:{tc}">
          TEAM {tn} — vote now!</span>
        <span style="font-family:'Bangers',cursive;font-size:1.5rem;color:{bc}">{int(time_left)}s</span>
      </div>
      <div style="background:#333;border-radius:7px;height:12px">
        <div style="width:{pct}%;background:{bc};height:100%;border-radius:7px;transition:width .4s"></div>
      </div>
    </div>""", unsafe_allow_html=True)
else:
    lt  = game.get("last_throw") or {}
    msg = f"💥 HIT! Point for {lt.get('thrower','').upper()}!" if lt.get("hit") else "🍌 Miss! Sailed past…"
    col = "#ff6b6b" if lt.get("hit") else "#aaa"
    result_age = now - (game.get("result_start") or now)
    remaining  = max(0, RESULT_SECS - result_age)
    st.markdown(f"""
    <div class="rmsg" style="color:{col}">{msg}</div>
    <div style="text-align:center;color:#666;font-size:.8rem;margin-bottom:5px">
      Next turn in {int(remaining)}s…</div>""", unsafe_allow_html=True)

# ── columns ───────────────────────────────────────────────────────────────────
cl, cc, cr = st.columns([1.2, 4.6, 1.2])

lv = votes["left"]; rv = votes["right"]

with cl:
    vl = "<br>".join(f"🎯{v['angle']}° 💥{v['power']}" for v in lv[-4:]) or "No votes yet"
    st.markdown(f"""
    <div class="qp lp">
      <div class="sn lc">🐵 LEFT</div>
      <div style="color:#ccc;font-size:.72rem;margin:3px 0">Scan to vote</div>
      {qrtag(qr_l, left_url)}
      <div style="color:#555;font-size:.58rem;margin-top:3px;word-break:break-all">{left_url}</div>
      <div style="color:#ffcc44;font-size:.78rem;margin-top:5px">Votes: <b>{len(lv)}</b></div>
      <div style="color:#aaa;font-size:.68rem;margin-top:2px">{vl}</div>
    </div>""", unsafe_allow_html=True)

with cr:
    vr = "<br>".join(f"🎯{v['angle']}° 💥{v['power']}" for v in rv[-4:]) or "No votes yet"
    st.markdown(f"""
    <div class="qp rp">
      <div class="sn rc">RIGHT 🐵</div>
      <div style="color:#ccc;font-size:.72rem;margin:3px 0">Scan to vote</div>
      {qrtag(qr_r, right_url)}
      <div style="color:#555;font-size:.58rem;margin-top:3px;word-break:break-all">{right_url}</div>
      <div style="color:#44ccff;font-size:.78rem;margin-top:5px">Votes: <b>{len(rv)}</b></div>
      <div style="color:#aaa;font-size:.68rem;margin-top:2px">{vr}</div>
    </div>""", unsafe_allow_html=True)

# ── canvas (animation handled entirely in JS) ─────────────────────────────────
with cc:
    phase     = game["phase"]
    lt        = game.get("last_throw") or {}
    traj_js   = json.dumps(lt.get("trajectory") or [])
    did_hit   = "true" if lt.get("hit") else "false"
    hit_side  = f'"{lt.get("target_side","")}"'
    # How long the result has been shown (so JS can pick up where it left off)
    res_age   = (now - (game.get("result_start") or now)) if phase=="result" else 0

    preview_traj = []
    
    if phase == "voting":
        active_votes = votes[game["turn"]]
    
        if active_votes:
            pa = round(sum(v["angle"] for v in active_votes) / len(active_votes))
            pp = round(sum(v["power"] for v in active_votes) / len(active_votes))
        else:
            prev = game.get(
                f"last_avg_{game['turn']}",
                {"angle": 45, "power": 62}
            )
    
            pa = prev["angle"]
            pp = prev["power"]
    
        preview_traj = trajectory(
            pa,
            pp,
            game["turn"],
            game["wind"]
        )
    
    preview_js = json.dumps(preview_traj)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;overflow:hidden}}
canvas{{width:100%;display:block;border-radius:13px}}</style></head><body>
<canvas id="c" width="900" height="320"></canvas>
<script>
const cv=document.getElementById('c');
const cx=cv.getContext('2d');
const W=900,H=320;

// ── positions (must match Python constants) ──────────────────────────────────
const LMX=155,LMY=165,RMX=745,RMY=145;

const PHASE    = "{phase}";
const TRAJ     = {traj_js};
const DID_HIT  = {did_hit};
const HIT_SIDE = {hit_side};
const RES_AGE  = {res_age:.2f};   // seconds already elapsed in result phase
const ANIM_DUR = 2.5;             // seconds for banana to fly across
const PREVIEW = {preview_js};

// ── draw helpers ─────────────────────────────────────────────────────────────
function sky(){{
  const g=cx.createLinearGradient(0,0,0,H);
  g.addColorStop(0,'#3a7ac8');g.addColorStop(1,'#87ceeb');
  cx.fillStyle=g;cx.fillRect(0,0,W,H);
}}
function cloud(x,y,rx,ry){{
  cx.fillStyle='rgba(255,255,255,.82)';
  [[0,0,rx,ry],[-rx*.3,ry*.38,rx*.58,ry*.7],[rx*.35,ry*.32,rx*.52,ry*.65]]
    .forEach(([dx,dy,ex,ey])=>{{
      cx.beginPath();cx.ellipse(x+dx,y+dy,ex,ey,0,0,Math.PI*2);cx.fill();
    }});
}}
function ground(){{
  const g=cx.createLinearGradient(0,H-48,0,H);
  g.addColorStop(0,'#5a8a3c');g.addColorStop(1,'#3d6128');
  cx.fillStyle=g;cx.fillRect(0,H-48,W,48);
  cx.fillStyle='#6aa84f';cx.fillRect(0,H-50,W,6);
}}
function building(x,y,w,h,col){{
  // pre-seed window pattern so it doesn't flicker on every frame
  if(!building.cache) building.cache={{}};
  const key=x+','+y;
  if(!building.cache[key]){{
    const wins=[];
    for(let wy=y+18;wy<y+h-22;wy+=30)
      for(let wx=x+11;wx<x+w-14;wx+=26)
        wins.push([wx,wy,Math.random()>.35?'rgba(255,253,231,.88)':'rgba(170,212,245,.88)']);
    building.cache[key]=wins;
  }}
  cx.fillStyle=col;cx.beginPath();cx.roundRect(x,y,w,h,4);cx.fill();
  cx.fillStyle='rgba(0,0,0,.13)';cx.fillRect(x,y,w,8);
  building.cache[key].forEach(([wx,wy,wc])=>{{
    cx.fillStyle=wc;cx.beginPath();cx.roundRect(wx,wy,15,17,2);cx.fill();
  }});
}}
function monkey(mx,my,flash,right){{
  const mc=flash?'#ff3333':'#c8822a',d=right?1:-1;
  cx.fillStyle=mc;
  cx.beginPath();cx.ellipse(mx,my+10,13,15,0,0,Math.PI*2);cx.fill();
  cx.beginPath();cx.arc(mx,my-8,13,0,Math.PI*2);cx.fill();
  cx.fillStyle='#e8b87a';cx.beginPath();cx.ellipse(mx,my-5,9,7,0,0,Math.PI*2);cx.fill();
  [[-5,-12],[5,-12]].forEach(([dx,dy])=>{{
    cx.fillStyle='#fff';cx.beginPath();cx.arc(mx+dx,my+dy,2.5,0,Math.PI*2);cx.fill();
    cx.fillStyle='#222';cx.beginPath();cx.arc(mx+dx+.5*d,my+dy,1.2,0,Math.PI*2);cx.fill();
  }});
  cx.fillStyle=mc;
  cx.beginPath();cx.arc(mx-13,my-10,5,0,Math.PI*2);cx.fill();
  cx.beginPath();cx.arc(mx+13,my-10,5,0,Math.PI*2);cx.fill();
  cx.strokeStyle=mc;cx.lineWidth=5;cx.lineCap='round';
  cx.beginPath();cx.moveTo(mx+d*12,my+8);cx.lineTo(mx+d*25,my+2);cx.stroke();
  cx.strokeStyle='#f5d020';cx.lineWidth=4;
  cx.beginPath();cx.moveTo(mx+d*25,my+2);
  cx.quadraticCurveTo(mx+d*36,my-5,mx+d*32,my-15);cx.stroke();
  if(flash){{cx.font='19px serif';cx.textAlign='center';cx.fillText('💥',mx,my-30);}}
}}
function scene(fL,fR){{
  sky();
  cloud(W*.17,32,54,21);cloud(W*.63,26,64,25);cloud(W*.41,16,39,14);
  ground();
  building(50,175,130,130,'#c0845a');   // left building
  building(720,155,130,150,'#8a9bbc');  // right building
  monkey(LMX,LMY,fL,true);
  monkey(RMX,RMY,fR,false);
}}

// ── animation ─────────────────────────────────────────────────────────────────
// In "result" phase: animate banana fly, then flash on hit.
// In "voting" phase: just draw static scene.

if(PHASE !== 'result' || !TRAJ || TRAJ.length===0){

  scene(false,false);

  // live aiming preview
  if(PREVIEW && PREVIEW.length > 1){

    cx.strokeStyle = 'rgba(245,208,32,.7)';
    cx.lineWidth = 3;
    cx.setLineDash([10,6]);

    cx.beginPath();
    cx.moveTo(PREVIEW[0][0], PREVIEW[0][1]);

    for(let i=1;i<PREVIEW.length;i+=3){
      cx.lineTo(PREVIEW[i][0], PREVIEW[i][1]);
    }

    cx.stroke();
    cx.setLineDash([]);

    // landing marker
    const end = PREVIEW[PREVIEW.length - 1];

    cx.font = '20px serif';
    cx.textAlign = 'center';
    cx.fillText('🍌', end[0], end[1]);

    // target indicator
    cx.fillStyle = 'rgba(255,255,255,.85)';
    cx.font = '15px Bangers';
    cx.fillText('Predicted throw', end[0], end[1] - 18);
  }
}} else {{
  const total = TRAJ.length;
  const FPS   = 60;
  const steps = Math.round(ANIM_DUR * FPS);  // frames for full flight
  const skip  = total / steps;               // traj points per frame

  // If result has already been shown for a while (page reloaded mid-result),
  // jump ahead in the animation proportionally.
  const startFrac = Math.min(RES_AGE / ANIM_DUR, 1.0);
  let   idx       = Math.floor(startFrac * total);
  let   flashing  = startFrac >= 1.0;
  let   flashN    = 0;
  let   flashOn   = DID_HIT && flashing;

  function frame(){{
    if(!flashing){{
      idx = Math.min(idx + skip, total-1);
      const fL = false, fR = false;
      scene(fL, fR);
      // draw trail
      if(idx>1){{
        cx.strokeStyle='rgba(245,208,32,.65)';
        cx.lineWidth=2.5;cx.setLineDash([7,4]);
        cx.beginPath();cx.moveTo(TRAJ[0][0],TRAJ[0][1]);
        for(let i=1;i<=Math.floor(idx);i++) cx.lineTo(TRAJ[i][0],TRAJ[i][1]);
        cx.stroke();cx.setLineDash([]);
      }}
      // banana tip
      const ti=Math.floor(idx);
      cx.font='17px serif';cx.textAlign='center';
      cx.fillText('🍌',TRAJ[ti][0],TRAJ[ti][1]);

      if(idx >= total-1){{ flashing=true; }}
      else requestAnimationFrame(frame);
    }} else {{
      // flash hit monkey
      flashOn=!flashOn;
      const fL=DID_HIT&&HIT_SIDE==='left' &&flashOn;
      const fR=DID_HIT&&HIT_SIDE==='right'&&flashOn;
      scene(fL,fR);
      // keep trail visible
      cx.strokeStyle='rgba(245,208,32,.4)';
      cx.lineWidth=2;cx.setLineDash([7,4]);
      cx.beginPath();cx.moveTo(TRAJ[0][0],TRAJ[0][1]);
      TRAJ.forEach(([x,y])=>cx.lineTo(x,y));
      cx.stroke();cx.setLineDash([]);
      if(++flashN < 12) setTimeout(()=>requestAnimationFrame(frame), 180);
    }}
  }}
  requestAnimationFrame(frame);
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
    st.markdown("<div style='background:#1a1a1a;border-radius:9px;padding:9px;"
                "text-align:center;font-family:Bangers,cursive;font-size:.9rem;"
                "color:#888;margin-bottom:6px'>Host override</div>", unsafe_allow_html=True)
    man_a = st.slider("Angle (°)", 10, 80, 45, key="ma")
    man_p = st.slider("Power",    10,100, 62, key="mp")

with b2:
    if tv:
        st.markdown(f"""<div style='background:#1e2a1e;border-radius:9px;padding:11px;text-align:center'>
          <div style='font-family:Bangers,cursive;color:#7dff7d;font-size:.9rem'>Crowd average</div>
          <div style='font-family:Bangers,cursive;font-size:1.9rem;color:#fff'>{avg_a}° · {avg_p}</div>
          <div style='color:#aaa;font-size:.75rem'>{len(tv)} vote(s)</div>
        </div>""", unsafe_allow_html=True)
    else:
        avg_a, avg_p = man_a, man_p
        st.markdown(f"""<div style='background:#1e1e2a;border-radius:9px;padding:11px;text-align:center'>
          <div style='font-family:Bangers,cursive;color:#666;font-size:.9rem'>No votes — using host override</div>
          <div style='font-family:Bangers,cursive;font-size:1.9rem;color:#fff'>{avg_a}° · {avg_p}</div>
        </div>""", unsafe_allow_html=True)

with b3:
    st.markdown("<br>", unsafe_allow_html=True)
    if game["phase"] == "voting":
        if st.button("🍌 Throw now! (skip timer)", use_container_width=True, type="primary"):
            traj    = trajectory(avg_a, avg_p, active, game["wind"])
            did_hit = hits(traj, active)
            if did_hit:
                if active=="left": game["score_left"]  += 1
                else:              game["score_right"] += 1
            game["last_throw"]   = {
                "angle": avg_a, "power": avg_p, "thrower": active,
                "target_side": "right" if active=="left" else "left",
                "hit": did_hit, "trajectory": traj}
            game["phase"]        = "result"
            game["result_start"] = now
            votes = _new_votes()
            persist(game, votes); st.rerun()
    else:
        # Manual skip button during result phase too
        if st.button("➡️ Next turn now", use_container_width=True):
            game["turn"]         = "right" if game["turn"]=="left" else "left"
            game["phase"]        = "voting"
            game["turn_start"]   = now
            game["result_start"] = None
            game["last_throw"]   = None
            game["wind"]         = round(random.uniform(-5,5),1)
            persist(game, votes); st.rerun()

# ── auto-rerun ────────────────────────────────────────────────────────────────
# During voting: rerun every second to tick countdown.
# During result: rerun every second to count down to auto-next-turn.
time.sleep(1)
st.rerun()
