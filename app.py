"""
Breaking Down the Building Blocks — PhD Defence Waiting Game
?team=left  → human-hand voter page
?team=right → robot-hand voter page
(no param)  → main game screen
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
C_BLUE   = "#4A6FE3"
C_PINK   = "#E8857A"
C_RED    = "#E84040"

# ── load images — detect actual format ───────────────────────────────────────
def _img_data(filename):
    """Return (base64_str, mime_type) for an image file."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, filename)
    try:
        with open(path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        mime = "image/jpeg" if data[:3] == b'\xff\xd8\xff' else "image/png"
        return b64, mime
    except Exception:
        return "", "image/png"

HUMAN_B64, HUMAN_MIME = _img_data("humanhand.png")
ROBOT_B64, ROBOT_MIME = _img_data("robothand.png")

# ── file locking ──────────────────────────────────────────────────────────────
if os.name != "nt":
    import fcntl

@contextmanager
def locked_open(path, mode):
    f = open(path, mode)
    try:
        if os.name != "nt":
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield f
    finally:
        try:
            if os.name != "nt":
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        f.close()

# ── state ─────────────────────────────────────────────────────────────────────
def _new_game():
    return {"score_left": 0, "score_right": 0,
            "phase": "voting", "turn": "left",
            "turn_start": time.time(), "result_start": None,
            "last_throw": None,
            "wind": round(random.uniform(-5, 5), 1),
            "last_avg_left":  {"angle": 45, "power": 62},
            "last_avg_right": {"angle": 45, "power": 62}}

def _new_votes(): return {"left": [], "right": []}

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
        x, y, rad = LMX, LMY, math.radians(angle_deg)
    else:
        x, y, rad = RMX, RMY, math.radians(180 - angle_deg)
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

# ── QR ────────────────────────────────────────────────────────────────────────
def make_qr(url):
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(url); qr.make(fit=True)
        img = qr.make_image(fill_color="#1a1a2e", back_color="white")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception: return ""

def qrtag(b64, url, w=115):
    if b64: return f"<img src='data:image/png;base64,{b64}' style='width:{w}px;border-radius:4px'/>"
    return f"<div style='font-size:.6rem;color:#aaa;word-break:break-all'>{url}</div>"

# ── routing ───────────────────────────────────────────────────────────────────
team_param = st.query_params.get("team", "")

# ═════════════════════════════════════════════════════════════════════════════
# VOTER PAGE
# ═════════════════════════════════════════════════════════════════════════════
if team_param in ("left", "right"):
    team    = team_param
    is_left = team == "left"
    tc       = C_PINK if is_left else C_BLUE
    hand_b64 = HUMAN_B64 if is_left else ROBOT_B64
    hand_mime = HUMAN_MIME if is_left else ROBOT_MIME
    label    = "Human Hand 🧬" if is_left else "Robot Hand 🤖"

    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;700&family=DM+Serif+Display&display=swap');
html,body,[class*="css"]{{font-family:'DM Sans',sans-serif;
  background:linear-gradient(160deg,#3558d4 0%,#8060b8 55%,#e07a72 100%);
  min-height:100vh;color:#eee}}
.vcard{{background:rgba(0,0,0,.55);backdrop-filter:blur(6px);
        border-left:4px solid {tc};border-radius:0 14px 14px 0;
        padding:16px 18px;margin-bottom:16px;display:flex;align-items:center;gap:14px}}
.vt{{font-family:'DM Serif Display',serif;font-size:1.8rem;color:{tc};margin:0}}
.vs2{{color:#ccc;font-size:.82rem;margin:3px 0 0}}
.bv{{font-family:'DM Serif Display',serif;font-size:2.8rem;text-align:center;color:{tc};margin:2px 0}}
.ok{{background:rgba(0,40,0,.6);border:2px solid #4caf50;
     border-radius:14px;padding:22px;text-align:center;margin-top:10px}}
</style>
<div class="vcard">
  <img src="data:image/{hand_mime};base64,{hand_b64}"
       style="height:64px;width:auto;object-fit:contain"/>
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
                      color:#ccc;margin-bottom:4px">
            <span>⏱ Time to vote</span>
            <span style="color:{bc};font-weight:700">{int(secs_left)}s</span>
          </div>
          <div style="background:rgba(0,0,0,.4);border-radius:5px;height:8px">
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
          <div style="color:#ccc;font-size:.84rem">Watch the main screen!</div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔄 Vote again (new turn)", use_container_width=True):
            st.session_state[vk] = False; st.rerun()
    else:
        st.markdown(f"<div style='font-size:.84rem;color:#ddd;margin:0 0 4px'>"
                    f"🎯 <b style='color:{tc}'>Throw angle</b> — low = flat, high = lofted</div>",
                    unsafe_allow_html=True)
        angle = st.slider("Angle", 10, 80, 45, key="va", label_visibility="collapsed")
        st.markdown(f'<div class="bv">{angle}°</div>', unsafe_allow_html=True)

        pts = trajectory(angle, 62, team, 0)
        def sc(px, py, W=260, H=100):
            return round(px*W/900, 1), round(py*H/340, 1)
        path_d = " ".join(("M" if i==0 else "L")+f"{sc(px,py)[0]},{sc(px,py)[1]}"
                          for i,(px,py) in enumerate(pts[::4]))
        lx,ly=sc(LMX,LMY); rx,ry=sc(RMX,RMY); ex,ey=sc(*pts[-1])
        st.markdown(f"""
        <svg viewBox="0 0 260 105"
             style="width:100%;background:rgba(0,0,0,.4);border-radius:10px;
                    margin:4px 0 12px;border:1px solid rgba(255,255,255,.15)">
          <rect x="0" y="90" width="260" height="15" fill="rgba(0,0,0,.3)"/>
          <rect x="22" y="52" width="36" height="40" fill="rgba(74,111,227,.4)" rx="2"/>
          <rect x="22" y="50" width="36" height="4" fill="{C_PINK}" rx="1"/>
          <rect x="202" y="44" width="36" height="48" fill="rgba(74,111,227,.4)" rx="2"/>
          <rect x="202" y="42" width="36" height="4" fill="{C_BLUE}" rx="1"/>
          <circle cx="{lx}" cy="{ly}" r="7" fill="{C_RED}" opacity=".8"/>
          <circle cx="{rx}" cy="{ry}" r="7" fill="{C_RED}" opacity=".8"/>
          <path d="{path_d}" fill="none" stroke="white" stroke-width="2"
                stroke-dasharray="5 3" opacity=".7"/>
          <circle cx="{ex}" cy="{ey}" r="4" fill="white" opacity=".8"/>
          <text x="130" y="102" text-anchor="middle" fill="rgba(255,255,255,.4)"
                font-size="7" font-family="DM Sans,sans-serif">trajectory preview (no wind)</text>
        </svg>""", unsafe_allow_html=True)

        st.markdown(f"<div style='font-size:.84rem;color:#ddd;margin:0 0 4px'>"
                    f"💥 <b style='color:{tc}'>Throw power</b></div>", unsafe_allow_html=True)
        power = st.slider("Power", 10, 100, 62, key="vp", label_visibility="collapsed")
        bw  = int(power * 2.1)
        bc2 = "#4caf50" if power < 45 else "#ffcc44" if power < 72 else C_RED
        st.markdown(f"""
        <div style="background:rgba(0,0,0,.4);border-radius:5px;height:16px;
                    margin:3px 0 2px;overflow:hidden">
          <div style="width:{min(bw,220)}px;height:100%;background:{bc2};border-radius:5px"></div>
        </div>
        <div class="bv">{power}</div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚗️ Submit vote", use_container_width=True, type="primary"):
            v = load_votes()
            v[team].append({"angle": angle, "power": power, "ts": time.time()})
            save_votes(v)
            st.session_state[vk] = True; st.rerun()

    st.markdown("<div style='text-align:center;color:rgba(255,255,255,.3);font-size:.66rem;"
                "margin-top:22px'>Breaking Down the Building Blocks · Lise Vermeersch · VUB</div>",
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
            ang, pwr = prev["angle"], prev["power"]
        traj    = trajectory(ang, pwr, active, game["wind"])
        did_hit = hits(traj, active)
        if did_hit:
            if active == "left": game["score_left"]  += 1
            else:                game["score_right"] += 1
        game["last_throw"] = {"angle": ang, "power": pwr, "thrower": active,
                              "target_side": "right" if active=="left" else "left",
                              "hit": did_hit, "trajectory": traj}
        game["phase"]        = "result"
        game["result_start"] = now
        persist(game, _new_votes()); st.rerun()

elif game["phase"] == "result":
    ra = now - (game.get("result_start") or now)
    if ra >= RESULT_SECS:
        game["turn"]         = "right" if game["turn"] == "left" else "left"
        game["phase"]        = "voting"
        game["turn_start"]   = now
        game["result_start"] = None
        game["last_throw"]   = None
        game["wind"]         = round(random.uniform(-5, 5), 1)
        persist(game, votes); st.rerun()

# ── sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Setup")
if "detected_url" not in st.session_state: st.session_state.detected_url = ""
app_url = st.sidebar.text_input("App URL (for QR codes)",
    value=st.session_state.detected_url or "https://waitinggame-jbyqzggvgecpqpuxie5jtt.streamlit.app")
st.sidebar.success("✅ QR codes use this URL")
st.sidebar.caption("Voters scan → `?team=left` or `?team=right`")
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Reset game"): persist(_new_game(), _new_votes()); st.rerun()

left_url  = app_url.rstrip("/") + "?team=left"
right_url = app_url.rstrip("/") + "?team=right"
qr_l = make_qr(left_url)
qr_r = make_qr(right_url)

# ── global CSS — gradient background on the page itself ──────────────────────
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;700&family=DM+Serif+Display&display=swap');
html,body,[class*="css"],
.stApp,.main,.block-container {{
    font-family:'DM Sans',sans-serif;
    background:transparent;
    color:#eee;
}}
.stApp {{
    background: linear-gradient(160deg,#3558d4 0%,#8060b8 55%,#e07a72 100%) !important;
    min-height:100vh;
}}
#MainMenu,footer,header{{visibility:hidden}}
.block-container{{padding-top:.75rem!important;max-width:100%!important;padding-left:1.5rem!important;padding-right:1.5rem!important}}
/* frosted glass card */
.card{{
    background:rgba(0,0,0,.45);
    backdrop-filter:blur(4px);
    -webkit-backdrop-filter:blur(4px);
    border-radius:12px;
    border:1px solid rgba(255,255,255,.12);
    padding:10px 14px;
    margin-bottom:6px;
}}
.lc{{color:{C_PINK}}} .rc{{color:{C_BLUE}}}
</style>""", unsafe_allow_html=True)

# ── title (large, on gradient) ────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:10px 0 6px">
  <div style="font-family:'DM Serif Display',serif;font-size:2.6rem;
              font-weight:400;color:#fff;letter-spacing:.5px;
              text-shadow:0 2px 12px rgba(0,0,0,.4)">
    Breaking Down the Building Blocks
  </div>
  <div style="font-size:.75rem;color:rgba(255,255,255,.6);letter-spacing:2px;
              text-transform:uppercase;margin-top:3px">
    PhD Defence Waiting Game &nbsp;·&nbsp; Lise Vermeersch &nbsp;·&nbsp; VUB
  </div>
</div>""", unsafe_allow_html=True)

# ── top row: score + wind in one compact card ─────────────────────────────────
w      = game["wind"]
w_pct  = abs(w) / 5 * 50
w_col  = "#4fc3f7" if abs(w) < 2 else "#ffcc44" if abs(w) < 4 else C_RED
w_arr  = "➡️" if w > 0 else ("⬅️" if w < 0 else "—")
w_str  = "Calm" if abs(w)<1 else "Light" if abs(w)<2.5 else "Moderate" if abs(w)<4 else "Strong"

st.markdown(f"""
<div class="card" style="display:flex;align-items:center;gap:0;padding:8px 16px">
  <!-- left score -->
  <div style="flex:1;text-align:center">
    <div style="font-size:.85rem;font-weight:600;color:{C_PINK}">🧬 Human Hand</div>
    <div style="font-family:'DM Serif Display',serif;font-size:3rem;
                line-height:1.1;color:{C_PINK}">{game['score_left']}</div>
  </div>
  <!-- wind centre -->
  <div style="flex:2;padding:0 16px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
      <span style="font-size:.72rem;color:rgba(255,255,255,.5);text-transform:uppercase;
                   letter-spacing:1px">💨 Wind</span>
      <span style="font-family:'DM Serif Display',serif;font-size:1rem;color:{w_col}">
        {w_arr} {w_str} ({w:+.1f})</span>
      <span style="font-size:.68rem;color:rgba(255,255,255,.35)">affects arc</span>
    </div>
    <div style="position:relative;background:rgba(0,0,0,.35);border-radius:4px;height:10px">
      <div style="position:absolute;left:50%;top:0;width:1px;height:100%;
                  background:rgba(255,255,255,.2)"></div>
      <div style="position:absolute;
                  left:{'50%' if w>=0 else str(round(50-w_pct,1))+'%'};
                  width:{w_pct:.1f}%;height:100%;background:{w_col};
                  border-radius:4px;opacity:.85"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:.58rem;
                color:rgba(255,255,255,.25);margin-top:2px">
      <span>← Left</span><span>No wind</span><span>Right →</span>
    </div>
  </div>
  <!-- right score -->
  <div style="flex:1;text-align:center">
    <div style="font-size:.85rem;font-weight:600;color:{C_BLUE}">Robot Hand 🤖</div>
    <div style="font-family:'DM Serif Display',serif;font-size:3rem;
                line-height:1.1;color:{C_BLUE}">{game['score_right']}</div>
  </div>
</div>""", unsafe_allow_html=True)

# ── countdown / result banner ─────────────────────────────────────────────────
if game["phase"] == "voting":
    tl  = max(0.0, TURN_SECS - (now - game.get("turn_start", now)))
    pct = int(tl / TURN_SECS * 100)
    bc  = "#4caf50" if tl>8 else "#ffcc44" if tl>4 else C_RED
    tn  = "🧬 Human Hand" if game["turn"]=="left" else "🤖 Robot Hand"
    tc2 = C_PINK if game["turn"]=="left" else C_BLUE
    st.markdown(f"""
    <div class="card" style="padding:8px 14px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <span style="font-family:'DM Serif Display',serif;font-size:1.2rem;color:{tc2}">
          {tn} — vote now!</span>
        <span style="font-family:'DM Serif Display',serif;font-size:1.4rem;color:{bc}">{int(tl)}s</span>
      </div>
      <div style="background:rgba(0,0,0,.35);border-radius:5px;height:10px">
        <div style="width:{pct}%;background:{bc};height:100%;border-radius:5px;
                    transition:width .4s"></div>
      </div>
    </div>""", unsafe_allow_html=True)
else:
    lt  = game.get("last_throw") or {}
    thr = "🧬 Human Hand" if lt.get("thrower")=="left" else "🤖 Robot Hand"
    msg = f"💥 Direct hit — point for {thr}!" if lt.get("hit") else "⚗️ Near miss — molecule sailed past…"
    col = C_RED if lt.get("hit") else "rgba(255,255,255,.7)"
    ra  = now - (game.get("result_start") or now)
    rem = max(0, RESULT_SECS - ra)
    st.markdown(f"""
    <div class="card" style="text-align:center;padding:8px 14px">
      <div style="font-family:'DM Serif Display',serif;font-size:1.5rem;
                  color:{col}">{msg}</div>
      <div style="color:rgba(255,255,255,.45);font-size:.8rem;margin-top:2px">
        Next round in {int(rem)}s…</div>
    </div>""", unsafe_allow_html=True)

# ── main row: QR left | canvas | QR right ────────────────────────────────────
lv = votes["left"]; rv = votes["right"]
col_l, col_c, col_r = st.columns([1, 4, 1])

with col_l:
    vl = "<br>".join(f"∠{v['angle']}° · {v['power']}" for v in lv[-4:]) or "No votes yet"
    st.markdown(f"""
    <div class="card" style="text-align:center;border-color:{C_PINK}40">
      <div style="font-weight:600;color:{C_PINK};margin-bottom:5px">🧬 Human</div>
      <div style="color:rgba(255,255,255,.55);font-size:.7rem;margin-bottom:5px">Scan to vote</div>
      {qrtag(qr_l, left_url)}
      <div style="color:rgba(255,255,255,.25);font-size:.55rem;margin-top:4px;
                  word-break:break-all">{left_url}</div>
      <div style="color:{C_PINK};font-size:.76rem;margin-top:6px">
        Votes: <b>{len(lv)}</b></div>
      <div style="color:rgba(255,255,255,.45);font-size:.65rem;margin-top:2px">{vl}</div>
    </div>""", unsafe_allow_html=True)

with col_r:
    vr = "<br>".join(f"∠{v['angle']}° · {v['power']}" for v in rv[-4:]) or "No votes yet"
    st.markdown(f"""
    <div class="card" style="text-align:center;border-color:{C_BLUE}40">
      <div style="font-weight:600;color:{C_BLUE};margin-bottom:5px">Robot 🤖</div>
      <div style="color:rgba(255,255,255,.55);font-size:.7rem;margin-bottom:5px">Scan to vote</div>
      {qrtag(qr_r, right_url)}
      <div style="color:rgba(255,255,255,.25);font-size:.55rem;margin-top:4px;
                  word-break:break-all">{right_url}</div>
      <div style="color:{C_BLUE};font-size:.76rem;margin-top:6px">
        Votes: <b>{len(rv)}</b></div>
      <div style="color:rgba(255,255,255,.45);font-size:.65rem;margin-top:2px">{vr}</div>
    </div>""", unsafe_allow_html=True)

# ── canvas ────────────────────────────────────────────────────────────────────
with col_c:
    phase    = game["phase"]
    lt       = game.get("last_throw") or {}
    traj_js  = json.dumps(lt.get("trajectory") or [])
    did_hit  = "true" if lt.get("hit") else "false"
    hit_side = f'"{lt.get("target_side","")}"'
    res_age  = (now - (game.get("result_start") or now)) if phase=="result" else 0

    preview_traj = []
    if phase == "voting":
        av = votes[game["turn"]]
        if av:
            pa = round(sum(v["angle"] for v in av)/len(av))
            pp = round(sum(v["power"] for v in av)/len(av))
        else:
            prev = game.get(f"last_avg_{game['turn']}", {"angle": 45, "power": 62})
            pa, pp = prev["angle"], prev["power"]
        preview_traj = trajectory(pa, pp, game["turn"], game["wind"])
    preview_js = json.dumps(preview_traj)

    # Build image data URIs with correct MIME type
    human_uri = f"data:{HUMAN_MIME};base64,{HUMAN_B64}"
    robot_uri = f"data:{ROBOT_MIME};base64,{ROBOT_B64}"

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;overflow:hidden}}
canvas{{width:100%;display:block;border-radius:12px}}</style></head><body>
<canvas id="c" width="900" height="380"></canvas>
<script>
const cv=document.getElementById('c'),cx=cv.getContext('2d'),W=900,H=380;
const LMX=155,LMY=210,RMX=745,RMY=190;
const PHASE="{phase}",TRAJ={traj_js},DID_HIT={did_hit},HIT_SIDE={hit_side};
const RES_AGE={res_age:.2f},ANIM_DUR=2.5,PREVIEW={preview_js};

// Load images with correct MIME types
const humanImg=new Image(), robotImg=new Image();
humanImg.src='{human_uri}';
robotImg.src='{robot_uri}';
let ready=0;
function onLoad(){{ if(++ready===2) start(); }}
humanImg.onload=onLoad; robotImg.onload=onLoad;
humanImg.onerror=e=>{{ console.error('human img error',e); onLoad(); }};
robotImg.onerror=e=>{{ console.error('robot img error',e); onLoad(); }};
setTimeout(()=>{{if(ready<2){{ready=2;start();}}}},1200);

function bg(){{
  // Simple clean gradient — no circles to avoid glitching
  const g=cx.createLinearGradient(0,0,W,H);
  g.addColorStop(0,'#3558d4');
  g.addColorStop(.55,'#8060b8');
  g.addColorStop(1,'#e07a72');
  cx.fillStyle=g; cx.fillRect(0,0,W,H);
}}

function drawHand(img,x,y,w,h,flip,flash){{
  if(!img.complete||img.naturalWidth===0) return;
  cx.save();
  if(flash){{ cx.shadowColor='#E84040'; cx.shadowBlur=30; }}
  if(flip){{
    cx.translate(x+w/2, y+h/2);
    cx.scale(-1,1);
    cx.drawImage(img,-w/2,-h/2,w,h);
  }} else {{
    cx.drawImage(img,x,y,w,h);
  }}
  cx.restore();
  if(flash){{
    cx.fillStyle='rgba(232,64,64,.25)';
    cx.beginPath(); cx.arc(x+w/2, y+h*.2, 50, 0, Math.PI*2); cx.fill();
  }}
}}

function molecule(x,y,r,col){{
  cx.fillStyle=col; cx.beginPath(); cx.arc(x,y,r,0,Math.PI*2); cx.fill();
  cx.strokeStyle=col; cx.lineWidth=2.5;
  [[-r*1.9,-r*1.1],[r*1.9,-r*.8],[0,-r*2.2]].forEach(([dx,dy])=>{{
    cx.beginPath(); cx.moveTo(x,y); cx.lineTo(x+dx,y+dy); cx.stroke();
    cx.fillStyle=col; cx.beginPath(); cx.arc(x+dx,y+dy,r*.6,0,Math.PI*2); cx.fill();
  }});
}}

function scene(fL,fR){{
  bg();
  // Human hand: left side, rises from bottom, NOT flipped
  drawHand(humanImg, LMX-100, H-310, 185, 300, false, fL);
  // Robot hand: right side, mirrored
  drawHand(robotImg,  RMX-85,  H-305, 185, 300, true,  fR);
  // Molecules at fingertip positions
  molecule(LMX, LMY-8, 9, fL?'#ff8888':'#E84040');
  molecule(RMX, RMY-8, 9, fR?'#ff8888':'#E84040');
}}

function start(){{
  if(PHASE!=='result'||!TRAJ||!TRAJ.length){{
    scene(false,false);
    if(PREVIEW&&PREVIEW.length>1){{
      cx.strokeStyle='rgba(255,255,255,.45)';
      cx.lineWidth=2.5; cx.setLineDash([10,6]);
      cx.beginPath(); cx.moveTo(PREVIEW[0][0],PREVIEW[0][1]);
      for(let i=1;i<PREVIEW.length;i+=3) cx.lineTo(PREVIEW[i][0],PREVIEW[i][1]);
      cx.stroke(); cx.setLineDash([]);
      const e=PREVIEW[PREVIEW.length-1];
      molecule(e[0],e[1],5,'rgba(255,255,255,.55)');
      cx.fillStyle='rgba(255,255,255,.65)';
      cx.font='12px "DM Sans",sans-serif'; cx.textAlign='center';
      cx.fillText('Predicted landing',e[0],e[1]-18);
    }}
  }} else {{
    const total=TRAJ.length, steps=Math.round(ANIM_DUR*60), skip=total/steps;
    const sf=Math.min(RES_AGE/ANIM_DUR,1.0);
    let idx=Math.floor(sf*total), flashing=sf>=1.0, flashN=0, flashOn=DID_HIT&&flashing;
    function frame(){{
      if(!flashing){{
        idx=Math.min(idx+skip,total-1);
        scene(false,false);
        if(idx>1){{
          cx.strokeStyle='rgba(255,255,255,.6)';
          cx.lineWidth=2.5; cx.setLineDash([7,4]);
          cx.beginPath(); cx.moveTo(TRAJ[0][0],TRAJ[0][1]);
          for(let i=1;i<=Math.floor(idx);i++) cx.lineTo(TRAJ[i][0],TRAJ[i][1]);
          cx.stroke(); cx.setLineDash([]);
        }}
        const ti=Math.floor(idx);
        molecule(TRAJ[ti][0],TRAJ[ti][1],7,'#ffaa88');
        if(idx>=total-1) flashing=true;
        else requestAnimationFrame(frame);
      }} else {{
        flashOn=!flashOn;
        scene(DID_HIT&&HIT_SIDE==='left'&&flashOn, DID_HIT&&HIT_SIDE==='right'&&flashOn);
        cx.strokeStyle='rgba(255,255,255,.2)';
        cx.lineWidth=1.5; cx.setLineDash([6,4]);
        cx.beginPath(); cx.moveTo(TRAJ[0][0],TRAJ[0][1]);
        TRAJ.forEach(([x,y])=>cx.lineTo(x,y)); cx.stroke(); cx.setLineDash([]);
        if(++flashN<12) setTimeout(()=>requestAnimationFrame(frame),180);
      }}
    }}
    requestAnimationFrame(frame);
  }}
}}
</script></body></html>"""

    st.components.v1.html(html, height=400, scrolling=False)

# ── bottom controls ───────────────────────────────────────────────────────────
st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
b1, b2, b3 = st.columns([2, 2, 2])
active = game["turn"]
tv     = votes[active]
avg_a  = round(sum(v["angle"] for v in tv)/len(tv)) if tv else 45
avg_p  = round(sum(v["power"] for v in tv)/len(tv)) if tv else 62

with b1:
    st.markdown("<div class='card' style='text-align:center;font-size:.8rem;"
                "color:rgba(255,255,255,.4);margin-bottom:5px'>Host override</div>",
                unsafe_allow_html=True)
    man_a = st.slider("Angle (°)", 10, 80, 45, key="ma")
    man_p = st.slider("Power",    10,100, 62, key="mp")

with b2:
    if tv:
        st.markdown(f"""<div class='card' style='text-align:center;
                    border-color:rgba(76,175,80,.4)'>
          <div style='font-size:.78rem;color:#4caf50;letter-spacing:1px;
                      text-transform:uppercase'>Crowd average</div>
          <div style='font-family:"DM Serif Display",serif;font-size:2rem;
                      color:#fff;margin:2px 0'>{avg_a}° · {avg_p}</div>
          <div style='color:rgba(255,255,255,.4);font-size:.73rem'>
            {len(tv)} vote(s) received</div>
        </div>""", unsafe_allow_html=True)
    else:
        avg_a, avg_p = man_a, man_p
        st.markdown(f"""<div class='card' style='text-align:center'>
          <div style='font-size:.78rem;color:rgba(255,255,255,.35);letter-spacing:1px;
                      text-transform:uppercase'>No votes — host override</div>
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
            game["last_throw"]   = {"angle":avg_a,"power":avg_p,"thrower":active,
                                    "target_side":"right" if active=="left" else "left",
                                    "hit":did_hit,"trajectory":traj}
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
            game["wind"]         = round(random.uniform(-5,5),1)
            persist(game, votes); st.rerun()

time.sleep(1)
st.rerun()
