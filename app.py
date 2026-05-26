import streamlit as st
import math, json, time, os, io, base64, random

st.set_page_config(page_title="🍌 Monkey Banana Battle", layout="wide",
                   initial_sidebar_state="collapsed")

VOTES_FILE      = "votes.json"
GAME_STATE_FILE = "game_state.json"
TURN_DURATION   = 15   # seconds per voting round

# ── persistence helpers ───────────────────────────────────────────────────────
def load_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE) as f: return json.load(f)
    return {"left": [], "right": []}

def save_votes(v):
    with open(VOTES_FILE, "w") as f: json.dump(v, f)

def clear_votes():
    save_votes({"left": [], "right": []})

def load_game():
    if os.path.exists(GAME_STATE_FILE):
        with open(GAME_STATE_FILE) as f: return json.load(f)
    return default_game()

def default_game():
    return {"score_left": 0, "score_right": 0,
            "phase": "voting",          # voting | result
            "turn": "left",
            "turn_start": time.time(),
            "last_throw": None,
            "wind": round(random.uniform(-8, 8), 1)}

def save_game(g):
    with open(GAME_STATE_FILE, "w") as f: json.dump(g, f)

# ── physics (server-side, mirrored in JS) ────────────────────────────────────
# Canvas is 900 × 380.  Left monkey top-centre ≈ (155, 170), right ≈ (745, 150)
LMX, LMY = 155, 170
RMX, RMY = 745, 150
HIT_R = 38          # pixels radius counts as hit

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
        pts.append([round(x, 1), round(y, 1)])
        vx += we; vy += g; x += vx; y += vy
        if y > 400: break
    return pts

def check_hit(pts, direction):
    tx, ty = (RMX, RMY) if direction == "left" else (LMX, LMY)
    for px, py in pts:
        if (px - tx)**2 + (py - ty)**2 < HIT_R**2:
            return True
    return False

# ── QR code helper ────────────────────────────────────────────────────────────
def make_qr(url: str) -> str:
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(url); qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""

# ─────────────────────────────────────────────────────────────────────────────
# Load state
# ─────────────────────────────────────────────────────────────────────────────
game  = load_game()
votes = load_votes()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Setup")
base_url = st.sidebar.text_input(
    "Voter page base URL",
    value="http://localhost:8502",
    help="Set to your LAN IP so phones can reach voter.py, e.g. http://192.168.1.42:8502")
st.sidebar.markdown("**Run voter app:**")
st.sidebar.code("streamlit run voter.py --server.port 8502")
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Reset Game"):
    save_game(default_game()); clear_votes(); st.rerun()

# ── Auto-advance: when voting timer expires, trigger throw ────────────────────
now = time.time()
time_left = max(0, TURN_DURATION - (now - game.get("turn_start", now)))

if game["phase"] == "voting" and time_left == 0:
    active = game["turn"]
    tvotes = votes[active]
    avg_angle = round(sum(v["angle"] for v in tvotes) / len(tvotes)) if tvotes else 45
    avg_power = round(sum(v["power"] for v in tvotes) / len(tvotes)) if tvotes else 50
    traj    = compute_trajectory(avg_angle, avg_power, active, game["wind"])
    did_hit = check_hit(traj, active)
    if did_hit:
        if active == "left":  game["score_left"]  += 1
        else:                 game["score_right"] += 1
    game["last_throw"] = {
        "angle": avg_angle, "power": avg_power,
        "thrower": active,
        "target_side": "right" if active == "left" else "left",
        "hit": did_hit,
        "trajectory": traj,
    }
    game["phase"] = "result"
    save_game(game); clear_votes(); st.rerun()

# ── QR codes ──────────────────────────────────────────────────────────────────
left_url  = base_url.rstrip("/") + "?team=left"
right_url = base_url.rstrip("/") + "?team=right"
qr_left   = make_qr(left_url)
qr_right  = make_qr(right_url)

def qr_img(b64, url):
    if b64:
        return f"<img src='data:image/png;base64,{b64}' style='width:120px;border-radius:6px;'/>"
    return f"<div style='font-size:0.7rem;color:#aaa;word-break:break-all'>{url}</div>"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@400;700&display=swap');
html,body,[class*="css"]{font-family:'Nunito',sans-serif}
.title{font-family:'Bangers',cursive;font-size:2.6rem;letter-spacing:3px;text-align:center;
       color:#f5a623;text-shadow:3px 3px 0 #7b3f00;margin-bottom:4px}
.scoreboard{display:flex;justify-content:space-around;align-items:center;
            background:linear-gradient(135deg,#2d5a27,#1a3a16);
            border-radius:16px;padding:10px 32px;margin:6px 0 10px}
.s-name{font-family:'Bangers',cursive;font-size:1.3rem;letter-spacing:2px}
.s-num{font-family:'Bangers',cursive;font-size:3.4rem;line-height:1}
.lc{color:#ffcc44}.rc{color:#44ccff}
.vs{font-family:'Bangers',cursive;font-size:1.8rem;color:#fff;opacity:.6}
.wind-row{text-align:center;font-size:.82rem;color:#ccc;margin-bottom:6px}
.phase-tag{font-family:'Bangers',cursive;font-size:1.5rem;letter-spacing:2px;
           text-align:center;margin:4px 0 8px}
.turn-left{color:#ffcc44}.turn-right{color:#44ccff}
.qr-panel{border-radius:14px;padding:14px;text-align:center}
.lp{background:#2d3a1e;border:2px solid #ffcc44}
.rp{background:#1a2a3a;border:2px solid #44ccff}
.result-msg{font-family:'Bangers',cursive;font-size:1.8rem;letter-spacing:2px;
            text-align:center;margin-top:6px}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
wind_arrow = "→" if game["wind"] > 0 else ("←" if game["wind"] < 0 else "—")
st.markdown(f"""
<div class="title">🍌 Monkey Banana Battle 🐵</div>
<div class="scoreboard">
  <div class="s-name lc">🐵 Team Left</div>
  <div class="s-num  lc">{game['score_left']}</div>
  <div class="vs">VS</div>
  <div class="s-num  rc">{game['score_right']}</div>
  <div class="s-name rc">Team Right 🐵</div>
</div>
<div class="wind-row">💨 Wind: {game['wind']:+.1f} {wind_arrow}</div>
""", unsafe_allow_html=True)

# ── Turn / countdown label ────────────────────────────────────────────────────
if game["phase"] == "voting":
    tc = "turn-left" if game["turn"] == "left" else "turn-right"
    tl = game["turn"].upper()
    st.markdown(f'<div class="phase-tag {tc}">TEAM {tl} — vote now! ⏱ {int(time_left)}s left</div>',
                unsafe_allow_html=True)
else:
    lt = game["last_throw"]
    scorer = lt["thrower"].upper() if lt["hit"] else None
    msg = f"💥 HIT! Point for {scorer}!" if lt["hit"] else "🍌 Miss! Banana sailed past…"
    col = "#ff6b6b" if lt["hit"] else "#aaa"
    st.markdown(f'<div class="result-msg" style="color:{col}">{msg}</div>', unsafe_allow_html=True)

# ── Main layout ───────────────────────────────────────────────────────────────
col_l, col_c, col_r = st.columns([1.3, 4.2, 1.3])

with col_l:
    lvotes = votes["left"]
    st.markdown(f"""
    <div class="qr-panel lp">
      <div class="s-name lc">🐵 TEAM LEFT</div>
      <div style="color:#ccc;font-size:.78rem;margin:4px 0">Scan to vote</div>
      {qr_img(qr_left, left_url)}
      <div style="color:#aaa;font-size:.65rem;margin-top:4px;word-break:break-all">{left_url}</div>
      <div style="color:#ffcc44;font-size:.82rem;margin-top:6px">Votes: <b>{len(lvotes)}</b></div>
      <div style="color:#aaa;font-size:.72rem">{'<br>'.join(f"🎯{v['angle']}° 💥{v['power']}" for v in lvotes[-4:]) or 'No votes yet'}</div>
    </div>""", unsafe_allow_html=True)

with col_r:
    rvotes = votes["right"]
    st.markdown(f"""
    <div class="qr-panel rp">
      <div class="s-name rc">TEAM RIGHT 🐵</div>
      <div style="color:#ccc;font-size:.78rem;margin:4px 0">Scan to vote</div>
      {qr_img(qr_right, right_url)}
      <div style="color:#aaa;font-size:.65rem;margin-top:4px;word-break:break-all">{right_url}</div>
      <div style="color:#44ccff;font-size:.82rem;margin-top:6px">Votes: <b>{len(rvotes)}</b></div>
      <div style="color:#aaa;font-size:.72rem">{'<br>'.join(f"🎯{v['angle']}° 💥{v['power']}" for v in rvotes[-4:]) or 'No votes yet'}</div>
    </div>""", unsafe_allow_html=True)

# ── Canvas – full JS animation ────────────────────────────────────────────────
with col_c:
    # Pass trajectory (if any) as JSON into the JS
    traj_json = "null"
    hit_json  = "false"
    hit_side  = "null"
    if game["phase"] == "result" and game.get("last_throw"):
        lt = game["last_throw"]
        traj_json = json.dumps(lt["trajectory"])
        hit_json  = "true" if lt["hit"] else "false"
        hit_side  = f'"{lt["target_side"]}"'

    canvas_html = f"""
<canvas id="gc" style="width:100%;border-radius:14px;display:block"
        width="900" height="380"></canvas>
<script>
(function(){{
const C  = document.getElementById('gc');
const cx = C.getContext('2d');
const W  = 900, H = 380;

// ── scene constants ──────────────────────────────────────────────────────────
const LMX=155, LMY=170, RMX=745, RMY=150;

// ── trajectory from Python ───────────────────────────────────────────────────
const TRAJ    = {traj_json};
const HIT     = {hit_json};
const HIT_SIDE= {hit_side};

// ── helpers ──────────────────────────────────────────────────────────────────
function sky(){{
  const g=cx.createLinearGradient(0,0,0,H);
  g.addColorStop(0,'#3a7ac8'); g.addColorStop(1,'#87ceeb');
  cx.fillStyle=g; cx.fillRect(0,0,W,H);
}}
function cloud(x,y,rx,ry){{
  cx.fillStyle='rgba(255,255,255,0.82)';
  cx.beginPath(); cx.ellipse(x,y,rx,ry,0,0,Math.PI*2); cx.fill();
  cx.beginPath(); cx.ellipse(x-rx*.3,y+ry*.4,rx*.6,ry*.7,0,0,Math.PI*2); cx.fill();
  cx.beginPath(); cx.ellipse(x+rx*.35,y+ry*.3,rx*.55,ry*.65,0,0,Math.PI*2); cx.fill();
}}
function ground(){{
  const g=cx.createLinearGradient(0,H-55,0,H);
  g.addColorStop(0,'#5a8a3c'); g.addColorStop(1,'#3d6128');
  cx.fillStyle=g; cx.fillRect(0,H-55,W,55);
  cx.fillStyle='#6aa84f'; cx.fillRect(0,H-57,W,7);
}}
function building(x,y,w,h,col){{
  cx.fillStyle=col;
  cx.beginPath(); cx.roundRect(x,y,w,h,4); cx.fill();
  cx.fillStyle='rgba(0,0,0,.15)'; cx.fillRect(x,y,w,8);
  const wcolors=['rgba(255,253,231,.9)','rgba(170,212,245,.9)'];
  for(let wy=y+18;wy<y+h-26;wy+=34)
    for(let wx=x+13;wx<x+w-18;wx+=30){{
      cx.fillStyle=wcolors[Math.random()>.35?0:1];
      cx.beginPath(); cx.roundRect(wx,wy,18,20,2); cx.fill();
    }}
}}
function monkey(mx,my,highlighted,facingRight){{
  const mc = highlighted ? '#ff3333' : '#c8822a';
  const d  = facingRight ? 1 : -1;
  // body
  cx.fillStyle=mc;
  cx.beginPath(); cx.ellipse(mx,my+10,14,17,0,0,Math.PI*2); cx.fill();
  // head
  cx.beginPath(); cx.arc(mx,my-9,15,0,Math.PI*2); cx.fill();
  // face
  cx.fillStyle='#e8b87a';
  cx.beginPath(); cx.ellipse(mx,my-6,10,8,0,0,Math.PI*2); cx.fill();
  // eyes
  [[-5,-14],[5,-14]].forEach(([dx,dy])=>{{
    cx.fillStyle='#fff'; cx.beginPath(); cx.arc(mx+dx,my+dy,2.8,0,Math.PI*2); cx.fill();
    cx.fillStyle='#222'; cx.beginPath(); cx.arc(mx+dx+.6*d,my+dy,1.4,0,Math.PI*2); cx.fill();
  }});
  // ears
  cx.fillStyle=mc;
  cx.beginPath(); cx.arc(mx-15,my-11,5.5,0,Math.PI*2); cx.fill();
  cx.beginPath(); cx.arc(mx+15,my-11,5.5,0,Math.PI*2); cx.fill();
  // arm
  cx.strokeStyle=mc; cx.lineWidth=5.5; cx.lineCap='round';
  cx.beginPath(); cx.moveTo(mx+d*13,my+9); cx.lineTo(mx+d*27,my+3); cx.stroke();
  // banana held by monkey
  cx.strokeStyle='#f5d020'; cx.lineWidth=4.5;
  cx.beginPath();
  cx.moveTo(mx+d*27,my+3);
  cx.quadraticCurveTo(mx+d*38,my-6,mx+d*34,my-17);
  cx.stroke();
  // explosion
  if(highlighted){{
    cx.font='22px serif'; cx.textAlign='center';
    cx.fillText('💥',mx,my-34);
  }}
}}

function drawStatic(hitL, hitR){{
  sky();
  cloud(W*.17,36,58,23); cloud(W*.64,30,68,27); cloud(W*.42,20,42,16);
  ground();
  building( 55, 190, 130, 145, '#c0845a');
  building(715, 170, 130, 165, '#8a9bbc');
  monkey(LMX,LMY,hitL,true);
  monkey(RMX,RMY,hitR,false);
}}

// ── animation state ───────────────────────────────────────────────────────────
let frame=0, done=false, flashOn=false;
const STEP=4;   // points per frame (speed)

function drawFrame(){{
  const hitL = HIT && HIT_SIDE==='left'  && flashOn;
  const hitR = HIT && HIT_SIDE==='right' && flashOn;
  drawStatic(hitL, hitR);

  if(!TRAJ || done) return;

  const end = Math.min(frame, TRAJ.length-1);

  // dashed trail
  if(end>1){{
    cx.strokeStyle='rgba(245,208,32,.65)';
    cx.lineWidth=2.5; cx.setLineDash([7,5]);
    cx.beginPath(); cx.moveTo(TRAJ[0][0],TRAJ[0][1]);
    for(let i=1;i<=end;i++) cx.lineTo(TRAJ[i][0],TRAJ[i][1]);
    cx.stroke(); cx.setLineDash([]);
  }}

  // banana emoji at current tip
  const [bx,by]=TRAJ[end];
  cx.font='18px serif'; cx.textAlign='center';
  cx.fillText('🍌',bx,by);
}}

function tick(){{
  if(!TRAJ){{ drawStatic(false,false); return; }}
  if(frame < TRAJ.length){{
    frame+=STEP;
    drawFrame();
    requestAnimationFrame(tick);
  }} else {{
    // banana has landed – show result
    done=true;
    let flashes=0;
    function flash(){{
      flashOn=!flashOn; drawFrame();
      if(++flashes<8) setTimeout(flash,180);
    }}
    flash();
  }}
}}
tick();
}})();
</script>
"""
    st.components.v1.html(canvas_html, height=400)

# ── Bottom controls ───────────────────────────────────────────────────────────
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
b1, b2, b3 = st.columns([2, 2, 2])

active = game["turn"]
tvotes = votes[active]
avg_angle = round(sum(v["angle"] for v in tvotes)/len(tvotes)) if tvotes else 45
avg_power = round(sum(v["power"] for v in tvotes)/len(tvotes)) if tvotes else 50

with b1:
    st.markdown("""<div style='background:#1a1a1a;border-radius:10px;padding:12px;
                   text-align:center;font-family:Bangers,cursive;font-size:1rem;color:#fff'>
                   Host override</div>""", unsafe_allow_html=True)
    manual_angle = st.slider("Angle (°)", 10, 80, 45, key="ma")
    manual_power = st.slider("Power",     10,100, 50, key="mp")

with b2:
    if tvotes:
        st.markdown(f"""<div style='background:#1e2a1e;border-radius:10px;padding:14px;
                    text-align:center'>
            <div style='font-family:Bangers,cursive;color:#7dff7d;font-size:1rem'>Crowd average</div>
            <div style='font-family:Bangers,cursive;font-size:2.2rem;color:#fff'>{avg_angle}° · {avg_power}</div>
            <div style='color:#aaa;font-size:.8rem'>{len(tvotes)} vote(s)</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style='background:#1e1e2a;border-radius:10px;padding:14px;
                    text-align:center'>
            <div style='font-family:Bangers,cursive;color:#aaa;font-size:1rem'>No votes yet – using override</div>
            <div style='font-family:Bangers,cursive;font-size:2.2rem;color:#fff'>{manual_angle}° · {manual_power}</div>
        </div>""", unsafe_allow_html=True)
        avg_angle, avg_power = manual_angle, manual_power

with b3:
    st.markdown("<br>", unsafe_allow_html=True)
    if game["phase"] == "voting":
        if st.button(f"🍌 Throw now! (skip timer)", use_container_width=True, type="primary"):
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
            save_game(game); clear_votes(); st.rerun()
    else:
        if st.button("➡️ Next turn", use_container_width=True, type="primary"):
            game["turn"]       = "right" if game["turn"] == "left" else "left"
            game["phase"]      = "voting"
            game["turn_start"] = time.time()
            game["last_throw"] = None
            game["wind"]       = round(random.uniform(-8, 8), 1)
            save_game(game); clear_votes(); st.rerun()

    if game["phase"] == "voting":
        # Auto-refresh every second during voting countdown
        st.markdown(f"""
        <div style='text-align:center;color:#aaa;font-size:.8rem;margin-top:8px'>
          ⏱ Auto-throws in <b>{int(time_left)}s</b>
        </div>
        <script>setTimeout(()=>window.location.reload(), 1000);</script>
        """, unsafe_allow_html=True)
    else:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

st.markdown("""<div style='text-align:center;color:#444;font-size:.72rem;margin-top:18px'>
Scan QR → vote angle & power → banana auto-launches after 15 s · wind changes each turn
</div>""", unsafe_allow_html=True)
