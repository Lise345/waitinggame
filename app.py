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
TURN_SECS   = 25
RESULT_SECS = 7

# Canvas 900×400. Pivot points at base of each hand (centre of launcher disk)
# Hands sit on hills at bottom corners.
LPX, LPY = 150, 360   # left pivot  (arm base / disk centre)
RPX, RPY = 750, 360   # right pivot
HIT_R    = 38          # hit-detection radius around pivot of the TARGET hand

SCALE    = 0.16
GRAV     = 0.12
C_BLUE   = "#4A6FE3"
C_PINK   = "#E8857A"
C_RED    = "#E84040"

# ── load images ────────────────────────────────────────────────────────────────
def _img_data(filename):
    here = os.path.dirname(os.path.abspath(__file__))
    for fname in [filename, filename.replace(".png","_final.png"),
                  filename.replace(".png","_crop.jpg")]:
        path = os.path.join(here, fname)
        if os.path.exists(path):
            with open(path, "rb") as f: data = f.read()
            b64  = base64.b64encode(data).decode()
            mime = "image/jpeg" if data[:3] == b'\xff\xd8\xff' else "image/png"
            return b64, mime
    return "", "image/png"

HUMAN_B64, HUMAN_MIME = _img_data("humanhand_final.png")
ROBOT_B64, ROBOT_MIME = _img_data("robothand_final.png")

# ── file locking ──────────────────────────────────────────────────────────────
if os.name != "nt":
    import fcntl

@contextmanager
def locked_open(path, mode):
    f = open(path, mode)
    try:
        if os.name != "nt": fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield f
    finally:
        try:
            if os.name != "nt": fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception: pass
        f.close()

# ── state ─────────────────────────────────────────────────────────────────────
def _new_game():
    return {"score_left": 0, "score_right": 0,
            "phase": "voting", "turn": "left",
            "turn_start": time.time(), "result_start": None,
            "last_throw": None,
            "wind": round(random.uniform(-5, 5), 1),
            # persist last crowd average per side across rounds
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
    """
    Molecule is launched from the FINGERTIP of each hand.
    The hand (length 110px on canvas) points at angle_deg from vertical.
    Left hand: 0°=straight up, positive angle tilts right (toward target).
    """
    hand_len = 115  # pixels from pivot to fingertip — must match JS HAND_LEN=115
    if direction == "left":
        # angle from vertical, tilting right
        tip_x = LPX + math.sin(math.radians(angle_deg)) * hand_len
        tip_y = LPY - math.cos(math.radians(angle_deg)) * hand_len
        rad   = math.radians(angle_deg)          # launch direction = hand angle
        vx    =  math.cos(rad) * power * SCALE  # wait — launch along hand direction
        vy    = -math.sin(math.radians(90 - angle_deg)) * power * SCALE
        # Simpler: launch in hand-pointing direction
        vx =  math.sin(math.radians(angle_deg)) * power * SCALE
        vy = -math.cos(math.radians(angle_deg)) * power * SCALE
    else:
        tip_x = RPX - math.sin(math.radians(angle_deg)) * hand_len
        tip_y = RPY - math.cos(math.radians(angle_deg)) * hand_len
        vx = -math.sin(math.radians(angle_deg)) * power * SCALE
        vy = -math.cos(math.radians(angle_deg)) * power * SCALE
    x, y = tip_x, tip_y
    pts = []
    for _ in range(600):
        pts.append([round(x,1), round(y,1)])
        vx += wind * 0.01; vy += GRAV; x += vx; y += vy
        if y > 420 or x < -60 or x > 960: break
    return pts

def hits(pts, direction):
    # Target is the PIVOT of the opposing hand (centre of launcher disk)
    tx, ty = (RPX, RPY) if direction == "left" else (LPX, LPY)
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
    team     = team_param
    is_left  = team == "left"
    tc       = C_PINK if is_left else C_BLUE
    hand_b64 = HUMAN_B64 if is_left else ROBOT_B64
    hand_mime = HUMAN_MIME if is_left else ROBOT_MIME
    label    = "Human Hand 🧬" if is_left else "Robot Hand 🤖"

    st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;700&family=DM+Serif+Display&display=swap');
html,body,[class*="css"]{{font-family:'DM Sans',sans-serif;
  background:linear-gradient(160deg,#3558d4 0%,#8060b8 55%,#e07a72 100%);
  min-height:100vh;color:#eee}}
.vcard{{background:rgba(0,0,0,.5);backdrop-filter:blur(6px);
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
       style="height:72px;width:auto;object-fit:contain"/>
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
        # Show last average as hint
        last = game.get(f"last_avg_{team}", {"angle": 45, "power": 62})
        st.markdown(f"<div style='font-size:.84rem;color:#ddd;margin:0 0 4px'>"
                    f"🎯 <b style='color:{tc}'>Throw angle</b> "
                    f"<span style='color:rgba(255,255,255,.4);font-size:.75rem'>"
                    f"(last round: {last['angle']}°)</span></div>", unsafe_allow_html=True)
        angle = st.slider("Angle", 10, 80, int(last["angle"]), key="va",
                          label_visibility="collapsed")
        st.markdown(f'<div class="bv">{angle}°</div>', unsafe_allow_html=True)

        # Live arc preview SVG
        pts = trajectory(angle, 62, team, 0)
        def sc(px, py, W=260, H=120):
            return round(px*W/900,1), round(py*H/420,1)
        path_d = " ".join(("M" if i==0 else "L")+f"{sc(px,py)[0]},{sc(px,py)[1]}"
                          for i,(px,py) in enumerate(pts[::4]))
        lx,ly = sc(LPX,LPY); rx,ry = sc(RPX,RPY); ex,ey = sc(*pts[-1])
        # hand line preview
        hl  = 28  # hand length in preview
        if team == "left":
            htx = lx + math.sin(math.radians(angle))*hl
            hty = ly - math.cos(math.radians(angle))*hl
        else:
            htx = rx - math.sin(math.radians(angle))*hl
            hty = ry - math.cos(math.radians(angle))*hl
        st.markdown(f"""
        <svg viewBox="0 0 260 125"
             style="width:100%;background:rgba(0,0,0,.4);border-radius:10px;
                    margin:4px 0 12px;border:1px solid rgba(255,255,255,.12)">
          <!-- hills -->
          <ellipse cx="{lx}" cy="{ly+4}" rx="22" ry="10" fill="rgba(255,255,255,.15)"/>
          <ellipse cx="{rx}" cy="{ry+4}" rx="22" ry="10" fill="rgba(255,255,255,.15)"/>
          <!-- disks -->
          <ellipse cx="{lx}" cy="{ly}" rx="10" ry="4" fill="{C_PINK}" opacity=".8"/>
          <ellipse cx="{rx}" cy="{ry}" rx="10" ry="4" fill="{C_BLUE}" opacity=".8"/>
          <!-- hand lines -->
          <line x1="{lx}" y1="{ly}" x2="{htx}" y2="{hty}"
                stroke="{C_PINK}" stroke-width="3" stroke-linecap="round"/>
          <line x1="{rx}" y1="{ry}" x2="{rx - math.sin(math.radians(angle))*hl:.1f}"
                y2="{ry - math.cos(math.radians(angle))*hl:.1f}"
                stroke="{C_BLUE}" stroke-width="3" stroke-linecap="round"/>
          <!-- arc -->
          <path d="{path_d}" fill="none" stroke="white" stroke-width="2"
                stroke-dasharray="5 3" opacity=".65"/>
          <!-- tip -->
          <circle cx="{ex}" cy="{ey}" r="4" fill="white" opacity=".75"/>
          <text x="130" y="122" text-anchor="middle" fill="rgba(255,255,255,.3)"
                font-size="7" font-family="DM Sans,sans-serif">trajectory preview (no wind)</text>
        </svg>""", unsafe_allow_html=True)

        st.markdown(f"<div style='font-size:.84rem;color:#ddd;margin:0 0 4px'>"
                    f"💥 <b style='color:{tc}'>Throw power</b> "
                    f"<span style='color:rgba(255,255,255,.4);font-size:.75rem'>"
                    f"(last round: {last['power']})</span></div>", unsafe_allow_html=True)
        power = st.slider("Power", 10, 100, int(last["power"]), key="vp",
                          label_visibility="collapsed")
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

    st.markdown("<div style='text-align:center;color:rgba(255,255,255,.25);font-size:.66rem;"
                "margin-top:22px'>Breaking Down the Building Blocks · Lise Vermeersch · VUB</div>",
                unsafe_allow_html=True)
    time.sleep(1); st.rerun(); st.stop()

# ═════════════════════════════════════════════════════════════════════════════
# MAIN GAME SCREEN
# ═════════════════════════════════════════════════════════════════════════════
game  = load_game()
votes = load_votes()
now   = time.time()

# ── phase transitions ─────────────────────────────────────────────────────────
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
    value=st.session_state.detected_url or
          "https://waitinggame-jbyqzggvgecpqpuxie5jtt.streamlit.app")
st.sidebar.success("✅ QR codes use this URL")
st.sidebar.caption("Voters scan → `?team=left` or `?team=right`")
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Reset game"): persist(_new_game(), _new_votes()); st.rerun()

left_url  = app_url.rstrip("/") + "?team=left"
right_url = app_url.rstrip("/") + "?team=right"
qr_l = make_qr(left_url); qr_r = make_qr(right_url)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;700&family=DM+Serif+Display&display=swap');
html,body,[class*="css"],
.stApp,.main,.block-container{{font-family:'DM Sans',sans-serif;background:transparent;color:#eee}}
.stApp{{background:linear-gradient(160deg,#3558d4 0%,#8060b8 55%,#e07a72 100%)!important;min-height:100vh}}
#MainMenu,footer,header{{visibility:hidden}}
.block-container{{padding-top:.75rem!important;max-width:100%!important;
                  padding-left:1.5rem!important;padding-right:1.5rem!important}}
.card{{background:rgba(0,0,0,.45);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);
       border-radius:12px;border:1px solid rgba(255,255,255,.12);padding:10px 14px;margin-bottom:6px}}
.lc{{color:{C_PINK}}}.rc{{color:{C_BLUE}}}
</style>""", unsafe_allow_html=True)

# ── title + fullscreen ────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:8px 0 5px;position:relative">
  <div style="font-family:'DM Serif Display',serif;font-size:2.6rem;
              font-weight:400;color:#fff;text-shadow:0 2px 12px rgba(0,0,0,.4)">
    Breaking Down the Building Blocks
  </div>
  <div style="font-size:.74rem;color:rgba(255,255,255,.55);letter-spacing:2px;
              text-transform:uppercase;margin-top:2px">
    PhD Defence Waiting Game &nbsp;·&nbsp; Lise Vermeersch &nbsp;·&nbsp; VUB
  </div>
  <button onclick="toggleFS()" id="fsBtn"
    style="position:absolute;top:8px;right:0;background:rgba(0,0,0,.4);
           border:1px solid rgba(255,255,255,.25);border-radius:8px;
           color:rgba(255,255,255,.7);font-size:.8rem;padding:5px 10px;
           cursor:pointer;font-family:'DM Sans',sans-serif;letter-spacing:.5px"
    title="Fullscreen (F)">⛶ Fullscreen</button>
</div>
<script>
function toggleFS(){
  if(!document.fullscreenElement){
    document.documentElement.requestFullscreen().catch(()=>{});
    document.getElementById('fsBtn').textContent='\u2715 Exit fullscreen';
  } else {
    document.exitFullscreen();
    document.getElementById('fsBtn').textContent='\u26f6 Fullscreen';
  }
}
document.addEventListener('keydown', e=>{
  if(e.key==='f'||e.key==='F') toggleFS();
});
document.addEventListener('fullscreenchange', ()=>{
  const btn=document.getElementById('fsBtn');
  if(btn) btn.textContent = document.fullscreenElement ? '\u2715 Exit fullscreen' : '\u26f6 Fullscreen';
});
</script>""", unsafe_allow_html=True)

# ── score + wind card ─────────────────────────────────────────────────────────
w     = game["wind"]
w_pct = abs(w) / 5 * 50
w_col = "#4fc3f7" if abs(w)<2 else "#ffcc44" if abs(w)<4 else C_RED
w_arr = "➡️" if w>0 else ("⬅️" if w<0 else "—")
w_str = "Calm" if abs(w)<1 else "Light" if abs(w)<2.5 else "Moderate" if abs(w)<4 else "Strong"

st.markdown(f"""
<div class="card" style="display:flex;align-items:center;padding:8px 16px;gap:0">
  <div style="flex:1;text-align:center">
    <div style="font-size:.85rem;font-weight:600;color:{C_PINK}">🧬 Human Hand</div>
    <div style="font-family:'DM Serif Display',serif;font-size:3rem;
                line-height:1.1;color:{C_PINK}">{game['score_left']}</div>
  </div>
  <div style="flex:2;padding:0 16px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
      <span style="font-size:.72rem;color:rgba(255,255,255,.45);text-transform:uppercase;
                   letter-spacing:1px">💨 Wind</span>
      <span style="font-family:'DM Serif Display',serif;font-size:1rem;color:{w_col}">
        {w_arr} {w_str} ({w:+.1f})</span>
      <span style="font-size:.68rem;color:rgba(255,255,255,.3)">affects arc</span>
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
                color:rgba(255,255,255,.22);margin-top:2px">
      <span>← Left</span><span>No wind</span><span>Right →</span>
    </div>
  </div>
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
    msg = f"💥 Direct hit — point for {thr}!" if lt.get("hit") else \
          "⚗️ Near miss — molecule sailed past…"
    col = C_RED if lt.get("hit") else "rgba(255,255,255,.75)"
    ra  = now - (game.get("result_start") or now)
    rem = max(0, RESULT_SECS - ra)
    st.markdown(f"""
    <div class="card" style="text-align:center;padding:8px 14px">
      <div style="font-family:'DM Serif Display',serif;font-size:1.5rem;color:{col}">{msg}</div>
      <div style="color:rgba(255,255,255,.4);font-size:.8rem;margin-top:2px">
        Next round in {int(rem)}s…</div>
    </div>""", unsafe_allow_html=True)

# ── main layout: QR | canvas | QR ────────────────────────────────────────────
lv = votes["left"]; rv = votes["right"]
col_l, col_c, col_r = st.columns([1, 4, 1])

with col_l:
    vl = "<br>".join(f"∠{v['angle']}° · {v['power']}" for v in lv[-4:]) or "No votes yet"
    st.markdown(f"""
    <div class="card" style="text-align:center;border-color:{C_PINK}50">
      <div style="font-weight:600;color:{C_PINK};margin-bottom:5px">🧬 Human</div>
      <div style="color:rgba(255,255,255,.5);font-size:.7rem;margin-bottom:5px">Scan to vote</div>
      {qrtag(qr_l, left_url)}
      <div style="color:rgba(255,255,255,.22);font-size:.52rem;margin-top:4px;
                  word-break:break-all">{left_url}</div>
      <div style="color:{C_PINK};font-size:.76rem;margin-top:6px">Votes: <b>{len(lv)}</b></div>
      <div style="color:rgba(255,255,255,.45);font-size:.65rem;margin-top:2px">{vl}</div>
    </div>""", unsafe_allow_html=True)

with col_r:
    vr = "<br>".join(f"∠{v['angle']}° · {v['power']}" for v in rv[-4:]) or "No votes yet"
    st.markdown(f"""
    <div class="card" style="text-align:center;border-color:{C_BLUE}50">
      <div style="font-weight:600;color:{C_BLUE};margin-bottom:5px">Robot 🤖</div>
      <div style="color:rgba(255,255,255,.5);font-size:.7rem;margin-bottom:5px">Scan to vote</div>
      {qrtag(qr_r, right_url)}
      <div style="color:rgba(255,255,255,.22);font-size:.52rem;margin-top:4px;
                  word-break:break-all">{right_url}</div>
      <div style="color:{C_BLUE};font-size:.76rem;margin-top:6px">Votes: <b>{len(rv)}</b></div>
      <div style="color:rgba(255,255,255,.45);font-size:.65rem;margin-top:2px">{vr}</div>
    </div>""", unsafe_allow_html=True)

# ── canvas ────────────────────────────────────────────────────────────────────
with col_c:
    phase    = game["phase"]
    lt       = game.get("last_throw") or {}
    traj_js  = json.dumps(lt.get("trajectory") or [])
    did_hit  = "true" if lt.get("hit") else "false"
    hit_side = f'"{lt.get("target_side","")}"'
    thrower  = f'"{lt.get("thrower","")}"'
    res_age  = (now - (game.get("result_start") or now)) if phase=="result" else 0
    throw_angle = lt.get("angle", 45) if phase=="result" else 45

    # Current voting averages for each side (for aim preview + hand display)
    def _avg(side):
        tv = votes[side]
        if tv:
            return (round(sum(v["angle"] for v in tv)/len(tv)),
                    round(sum(v["power"] for v in tv)/len(tv)))
        prev = game.get(f"last_avg_{side}", {"angle": 45, "power": 62})
        return prev["angle"], prev["power"]

    l_ang, l_pwr = _avg("left")
    r_ang, r_pwr = _avg("right")
    active_turn  = game["turn"]
    wind_val     = game["wind"]

    # Preview trajectory for the active side
    if phase == "voting":
        pa, pp = (l_ang, l_pwr) if active_turn=="left" else (r_ang, r_pwr)
        preview_traj = trajectory(pa, pp, active_turn, game["wind"])
    else:
        preview_traj = []
    preview_js = json.dumps(preview_traj)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;overflow:hidden}}
canvas{{width:100%;display:block;border-radius:12px}}</style></head><body>
<canvas id="c" width="900" height="400"></canvas>
<script>
const cv=document.getElementById('c'),cx=cv.getContext('2d'),W=900,H=400;
const LPX={LPX},LPY={LPY},RPX={RPX},RPY={RPY};
const HAND_LEN=115;  // pivot-to-fingertip distance on canvas

const PHASE="{phase}";
const TRAJ={traj_js};
const DID_HIT={did_hit};
const HIT_SIDE={hit_side};
const THROWER={thrower};
const RES_AGE={res_age:.2f};
const ANIM_DUR=2.0;
const PREVIEW={preview_js};
const ACTIVE_TURN="{active_turn}";

// Aim angles in degrees — how far the hand tilts BACK (away from target).
// Left hand tilts left (negative canvas rotation), right hand tilts right.
// 0° = perfectly vertical (at rest / just released).
const L_AIM={l_ang};
const R_AIM={r_ang};
const THROW_ANG={throw_angle};

// Images
const humanImg=new Image(), robotImg=new Image();
humanImg.src='data:{HUMAN_MIME};base64,{HUMAN_B64}';
robotImg.src='data:{ROBOT_MIME};base64,{ROBOT_B64}';
let ready=0;
const onLoad=()=>{{if(++ready>=2) start();}};
humanImg.onload=onLoad; robotImg.onload=onLoad;
humanImg.onerror=onLoad; robotImg.onerror=onLoad;
setTimeout(()=>{{if(ready<2){{ready=2; start();}}}}, 1200);

// ── helpers ───────────────────────────────────────────────────────────────────
function bg(){{
  const g=cx.createLinearGradient(0,0,W,H);
  g.addColorStop(0,'#3558d4'); g.addColorStop(.55,'#8060b8'); g.addColorStop(1,'#e07a72');
  cx.fillStyle=g; cx.fillRect(0,0,W,H);
}}

function hills(){{
  cx.fillStyle='rgba(255,255,255,.18)';
  cx.beginPath(); cx.ellipse(LPX,H,120,58,0,Math.PI,0); cx.fill();
  cx.beginPath(); cx.ellipse(RPX,H,120,58,0,Math.PI,0); cx.fill();
  cx.fillStyle='rgba(255,255,255,.09)';
  cx.beginPath(); cx.ellipse(LPX,H-2,85,40,0,Math.PI,0); cx.fill();
  cx.beginPath(); cx.ellipse(RPX,H-2,85,40,0,Math.PI,0); cx.fill();
}}

function disk(px,py,col){{
  cx.fillStyle='rgba(0,0,0,.28)';
  cx.beginPath(); cx.ellipse(px,py+4,30,11,0,0,Math.PI*2); cx.fill();
  const g=cx.createLinearGradient(px-30,py-10,px+30,py+10);
  g.addColorStop(0,'rgba(255,255,255,.3)'); g.addColorStop(.5,col); g.addColorStop(1,'rgba(0,0,0,.35)');
  cx.fillStyle=g;
  cx.beginPath(); cx.ellipse(px,py,30,11,0,0,Math.PI*2); cx.fill();
  cx.strokeStyle='rgba(255,255,255,.45)'; cx.lineWidth=1.5;
  cx.beginPath(); cx.ellipse(px,py-1,22,6,0,Math.PI,0); cx.stroke();
}}

/**
 * drawHand:
 *   px,py   = pivot point (arm base, centre of launcher disk)
 *   tiltDeg = degrees the hand tilts BACK from vertical
 *             Left hand: positive tilt = arm leans LEFT  (away from target)
 *             Right hand: positive tilt = arm leans RIGHT (away from target)
 *   isRight = true for the right (robot) hand
 *   flash   = hit flash effect
 */
function drawHand(img, px, py, tiltDeg, isRight, flash){{
  if(!img.complete || img.naturalWidth===0) return;

  // Rotation: left leans left = negative radians, right leans right = positive
  const sign   = isRight ? 1 : -1;
  const rad    = sign * tiltDeg * Math.PI / 180;
  const IW=72, IH=175;  // drawn size

  cx.save();
  cx.translate(px, py);   // pivot at arm base
  cx.rotate(rad);

  if(flash){{ cx.shadowColor='#E84040'; cx.shadowBlur=28; }}

  if(isRight){{
    // Mirror robot hand so it faces left (toward centre)
    cx.scale(-1, 1);
  }}

  // Draw image so bottom-centre aligns with pivot (0,0 after translate)
  cx.drawImage(img, -IW/2, -IH, IW, IH);
  cx.restore();
}}

/** Fingertip world position — must match Python trajectory() tip calculation exactly.
 *  Python left:  tip_x = LPX + sin(angle)*hand_len  (tilts toward centre = right)
 *  Python right: tip_x = RPX - sin(angle)*hand_len  (tilts toward centre = left)
 *  JS drawHand rotation: left hand sign=-1 so rad=-angle → sin(rad)=-sin(angle)
 *    → we need to NEGATE the JS rotation sign here to match Python.
 */
function tipPos(px, py, tiltDeg, isRight){{
  const rad = tiltDeg * Math.PI / 180;  // always positive, direction handled below
  if(isRight){{
    // right hand tip moves LEFT toward centre
    return [ px - Math.sin(rad)*HAND_LEN,
             py - Math.cos(rad)*HAND_LEN ];
  }} else {{
    // left hand tip moves RIGHT toward centre  (matches Python: LPX + sin*len)
    return [ px + Math.sin(rad)*HAND_LEN,
             py - Math.cos(rad)*HAND_LEN ];
  }}
}}

function molecule(x,y,r,col,alpha){{
  cx.globalAlpha = (alpha===undefined) ? 1 : alpha;
  cx.fillStyle=col; cx.beginPath(); cx.arc(x,y,r,0,Math.PI*2); cx.fill();
  cx.strokeStyle=col; cx.lineWidth=2.2;
  [[-r*1.9,-r*1.1],[r*1.9,-r*.8],[0,-r*2.2]].forEach(([dx,dy])=>{{
    cx.beginPath(); cx.moveTo(x,y); cx.lineTo(x+dx,y+dy); cx.stroke();
    cx.fillStyle=col; cx.beginPath(); cx.arc(x+dx,y+dy,r*.6,0,Math.PI*2); cx.fill();
  }});
  cx.globalAlpha=1;
}}

/**
 * Full scene draw.
 * lTilt / rTilt = current tilt angles for left/right hand
 * lHit / rHit   = flash the target hand red
 * showMoleculeL / showMoleculeR = show held molecule at fingertip
 */
function scene(lTilt, rTilt, lHit, rHit, showMoleculeL, showMoleculeR){{
  bg(); hills();
  drawHand(humanImg, LPX, LPY, lTilt, false, lHit);
  drawHand(robotImg,  RPX, RPY, rTilt, true,  rHit);
  disk(LPX, LPY, '{C_PINK}');
  disk(RPX, RPY, '{C_BLUE}');
  if(showMoleculeL){{
    const [tx,ty]=tipPos(LPX,LPY,lTilt,false);
    molecule(tx,ty,12,'#ffaa88');
  }}
  if(showMoleculeR){{
    const [tx,ty]=tipPos(RPX,RPY,rTilt,true);
    molecule(tx,ty,12,'#ffaa88');
  }}
}}

// ── easing ────────────────────────────────────────────────────────────────────
function easeOut(t){{ return 1-(1-t)*(1-t); }}
function easeInOut(t){{ return t<.5 ? 2*t*t : 1-Math.pow(-2*t+2,2)/2; }}
function lerp(a,b,t){{ return a+(b-a)*t; }}

// ── main ──────────────────────────────────────────────────────────────────────
function start(){{

  if(PHASE==='voting'){{
    // Show both hands: ACTIVE hand tilted back at aim angle, other hand vertical
    const lTilt = (ACTIVE_TURN==='left')  ? L_AIM : 0;
    const rTilt = (ACTIVE_TURN==='right') ? R_AIM : 0;
    scene(lTilt, rTilt, false, false,
          ACTIVE_TURN==='left',
          ACTIVE_TURN==='right');

    // Wind indicator
    const windVal = {wind_val:.1f};
    const windStr = windVal===0 ? 'No wind' :
                    (windVal>0 ? '→ ' : '← ') +
                    (Math.abs(windVal)<2 ? 'Light' : Math.abs(windVal)<4 ? 'Moderate' : 'Strong') +
                    ' wind (' + (windVal>0?'+':'') + windVal.toFixed(1) + ')';
    const windCol = Math.abs(windVal)<2 ? '#4fc3f7' : Math.abs(windVal)<4 ? '#ffcc44' : '#E84040';
    // Bar background
    cx.fillStyle='rgba(0,0,0,.35)';
    cx.beginPath(); cx.roundRect(W/2-120, 12, 240, 28, 6); cx.fill();
    // Bar fill
    const barMax=100, barW=Math.abs(windVal)/5*barMax;
    const barX = windVal>=0 ? W/2 : W/2-barW;
    cx.fillStyle=windCol; cx.globalAlpha=0.7;
    cx.beginPath(); cx.roundRect(barX, 17, barW, 18, 3); cx.fill();
    cx.globalAlpha=1;
    // Centre tick
    cx.strokeStyle='rgba(255,255,255,.4)'; cx.lineWidth=1;
    cx.beginPath(); cx.moveTo(W/2,14); cx.lineTo(W/2,38); cx.stroke();
    // Label
    cx.fillStyle=windCol; cx.font='bold 12px "DM Sans",sans-serif';
    cx.textAlign='center'; cx.fillText('💨 ' + windStr, W/2, 56);

    // Preview arc from tip of active hand
    if(PREVIEW && PREVIEW.length>1){{
      cx.strokeStyle='rgba(255,255,255,.45)';
      cx.lineWidth=2.5; cx.setLineDash([10,6]);
      cx.beginPath(); cx.moveTo(PREVIEW[0][0],PREVIEW[0][1]);
      for(let i=1;i<PREVIEW.length;i+=3) cx.lineTo(PREVIEW[i][0],PREVIEW[i][1]);
      cx.stroke(); cx.setLineDash([]);
      const e=PREVIEW[PREVIEW.length-1];
      molecule(e[0],e[1],9,'rgba(255,255,255,.5)',0.55);
      cx.fillStyle='rgba(255,255,255,.6)';
      cx.font='12px "DM Sans",sans-serif'; cx.textAlign='center';
      cx.fillText('Predicted landing', e[0], e[1]-18);
    }}
    return;
  }}

  // ── RESULT PHASE ─────────────────────────────────────────────────────────────
  // Timeline:
  //   0 → ANIM_DUR s    : throw animation — hand swings from THROW_ANG tilt → 0° vertical
  //                        while molecule flies along trajectory
  //   ANIM_DUR → +1.8 s : hit flash (if hit)
  //   after flash        : both hands rest at 0°

  if(!TRAJ || !TRAJ.length){{ scene(0,0,false,false,false,false); return; }}

  const total      = TRAJ.length;
  const flyFrames  = Math.round(ANIM_DUR * 60);
  const flySkip    = total / flyFrames;

  const sf         = Math.min(RES_AGE / ANIM_DUR, 1.0);
  let   flyIdx     = Math.floor(sf * total);
  const skipToFlash= sf >= 1.0;
  const skipToRest = RES_AGE > (ANIM_DUR + 2.0);

  // Non-throwing hand always at 0
  // Throwing hand: starts at THROW_ANG tilt, sweeps to 0 as molecule flies
  function getThrowerTilt(progress){{
    // progress 0→1 over ANIM_DUR; ease the swing from tilt→0
    return lerp(THROW_ANG, 0, easeOut(progress));
  }}

  function drawFly(){{
    const progress = flyIdx / total;
    const tilt     = getThrowerTilt(progress);
    const lT = THROWER==='left'  ? tilt : 0;
    const rT = THROWER==='right' ? tilt : 0;
    scene(lT, rT, false, false, false, false);

    // Trail from launch point (fingertip) to current molecule position
    if(flyIdx >= 1){{
      cx.strokeStyle='rgba(255,255,255,.6)';
      cx.lineWidth=2.5; cx.setLineDash([7,4]);
      cx.beginPath(); cx.moveTo(TRAJ[0][0],TRAJ[0][1]);
      for(let i=1;i<=Math.floor(flyIdx);i++) cx.lineTo(TRAJ[i][0],TRAJ[i][1]);
      cx.stroke(); cx.setLineDash([]);
    }}
    const ti = Math.floor(Math.min(flyIdx, total-1));
    molecule(TRAJ[ti][0], TRAJ[ti][1], 12, '#ffaa88');
  }}

  function doFly(){{
    flyIdx = Math.min(flyIdx + flySkip, total-1);
    drawFly();
    if(flyIdx < total-1) requestAnimationFrame(doFly);
    else setTimeout(doFlash, 80);
  }}

  let flashN=0, flashOn=false;
  function doFlash(){{
    flashOn = !flashOn; flashN++;
    const lH = DID_HIT && HIT_SIDE==='left'  && flashOn;
    const rH = DID_HIT && HIT_SIDE==='right' && flashOn;
    scene(0, 0, lH, rH, false, false);
    // keep trail
    cx.strokeStyle='rgba(255,255,255,.2)'; cx.lineWidth=1.5; cx.setLineDash([6,4]);
    cx.beginPath(); cx.moveTo(TRAJ[0][0],TRAJ[0][1]);
    TRAJ.forEach(([x,y])=>cx.lineTo(x,y)); cx.stroke(); cx.setLineDash([]);
    if(flashN < 10) setTimeout(doFlash, 160);
    else scene(0, 0, false, false, false, false);
  }}

  if(skipToRest)      {{ scene(0,0,false,false,false,false); }}
  else if(skipToFlash) {{ doFlash(); }}
  else                 {{ drawFly(); requestAnimationFrame(doFly); }}
}}
</script></body></html>"""

    st.components.v1.html(html, height=420, scrolling=False)

# ── bottom controls ───────────────────────────────────────────────────────────
st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
b1, b2, b3 = st.columns([2, 2, 2])
active = game["turn"]
tv     = votes[active]
avg_a  = round(sum(v["angle"] for v in tv)/len(tv)) if tv else \
         game.get(f"last_avg_{active}", {"angle":45})["angle"]
avg_p  = round(sum(v["power"] for v in tv)/len(tv)) if tv else \
         game.get(f"last_avg_{active}", {"power":62})["power"]

with b1:
    st.markdown("<div class='card' style='text-align:center;font-size:.8rem;"
                "color:rgba(255,255,255,.35);margin-bottom:5px'>Host override</div>",
                unsafe_allow_html=True)
    man_a = st.slider("Angle (°)", 10, 80, int(avg_a), key="ma")
    man_p = st.slider("Power",    10,100, int(avg_p),  key="mp")

with b2:
    if tv:
        st.markdown(f"""<div class='card' style='text-align:center;
                    border-color:rgba(76,175,80,.4)'>
          <div style='font-size:.78rem;color:#4caf50;letter-spacing:1px;
                      text-transform:uppercase'>Crowd average</div>
          <div style='font-family:"DM Serif Display",serif;font-size:2rem;
                      color:#fff;margin:2px 0'>{avg_a}° · {avg_p}</div>
          <div style='color:rgba(255,255,255,.35);font-size:.73rem'>
            {len(tv)} vote(s)</div>
        </div>""", unsafe_allow_html=True)
    else:
        avg_a, avg_p = man_a, man_p
        st.markdown(f"""<div class='card' style='text-align:center'>
          <div style='font-size:.78rem;color:rgba(255,255,255,.3);letter-spacing:1px;
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
            game[f"last_avg_{active}"] = {"angle": avg_a, "power": avg_p}
            game["last_throw"] = {"angle":avg_a,"power":avg_p,"thrower":active,
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
