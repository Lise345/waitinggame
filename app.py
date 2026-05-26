
import streamlit as st
import math, json, time, os, io, base64, random
from contextlib import contextmanager

st.set_page_config(
    page_title="The PhD Public Defense Waiting Game",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── assets ─────────────────────────────────────────────────────
HUMAN_HAND = "Breaking Down the Building Blocks-2.png"
ROBOT_HAND = "robothand.png"

# ── constants ──────────────────────────────────────────────────
VOTES_FILE = "votes.json"
GAME_FILE = "game_state.json"

TURN_SECS = 15
RESULT_SECS = 6

W = 900
H = 420

LEFT_X, LEFT_Y = 180, 280
RIGHT_X, RIGHT_Y = 720, 150
HIT_R = 45

SCALE = 0.16
GRAV = 0.12

# ── locking ────────────────────────────────────────────────────
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
        except:
            pass
        f.close()

# ── state ──────────────────────────────────────────────────────
def new_game():
    return {
        "score_left": 0,
        "score_right": 0,
        "phase": "voting",
        "turn": "left",
        "turn_start": time.time(),
        "result_start": None,
        "last_throw": None,
        "wind": round(random.uniform(-5, 5), 1),
        "last_avg_left": {"angle": 45, "power": 60},
        "last_avg_right": {"angle": 45, "power": 60},
    }

def new_votes():
    return {"left": [], "right": []}

def load_json(path, fallback):
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    except:
        pass
    return fallback

def save_json(path, data):
    with locked_open(path, "w") as f:
        json.dump(data, f)

def load_game():
    return load_json(GAME_FILE, new_game())

def load_votes():
    return load_json(VOTES_FILE, new_votes())

def save_game(g):
    save_json(GAME_FILE, g)

def save_votes(v):
    save_json(VOTES_FILE, v)

if not os.path.exists(GAME_FILE):
    save_game(new_game())

if not os.path.exists(VOTES_FILE):
    save_votes(new_votes())

# ── helpers ────────────────────────────────────────────────────
def trajectory(angle_deg, power, direction, wind):
    if direction == "left":
        x, y = LEFT_X, LEFT_Y
        rad = math.radians(angle_deg)
    else:
        x, y = RIGHT_X, RIGHT_Y
        rad = math.radians(180 - angle_deg)

    vx = math.cos(rad) * power * SCALE
    vy = -math.sin(rad) * power * SCALE

    pts = []

    for _ in range(600):
        pts.append([round(x, 1), round(y, 1)])
        vx += wind * 0.01
        vy += GRAV
        x += vx
        y += vy

        if y > H + 30 or x < -40 or x > W + 40:
            break

    return pts

def hits(pts, direction):
    tx, ty = (RIGHT_X, RIGHT_Y) if direction == "left" else (LEFT_X, LEFT_Y)
    return any((p[0]-tx)**2 + (p[1]-ty)**2 < HIT_R**2 for p in pts)

def make_qr(url):
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=6, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except:
        return ""

def img64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

human_b64 = img64(HUMAN_HAND)
robot_b64 = img64(ROBOT_HAND)

# ── styling ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

.stApp {
    background: linear-gradient(180deg,#0d5bdd 0%,#7d9fd9 50%,#e7a2a0 100%);
}

.block-container {
    padding-top: 1rem;
    max-width: 100%;
}

.panel {
    background: rgba(255,255,255,.08);
    border: 1px solid rgba(255,255,255,.16);
    backdrop-filter: blur(12px);
    border-radius: 24px;
    padding: 20px;
    color: white;
}

.title {
    color: white;
    text-align: center;
    font-size: 52px;
    font-weight: 700;
    letter-spacing: -2px;
    margin-bottom: 0;
}

.subtitle {
    color: rgba(255,255,255,.8);
    text-align: center;
    margin-top: 0;
    margin-bottom: 24px;
}

.metric {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 16px;
}

.label {
    text-transform: uppercase;
    opacity: .7;
    letter-spacing: 2px;
    font-size: 11px;
}

.stSlider label {
    color: white !important;
}

button {
    border-radius: 14px !important;
}
</style>
""", unsafe_allow_html=True)

# ── routing ────────────────────────────────────────────────────
team = st.query_params.get("team", "")

# ── voter page ────────────────────────────────────────────────
if team in ("left", "right"):

    game = load_game()
    votes = load_votes()

    active = game["turn"] == team and game["phase"] == "voting"

    st.markdown(f"""
    <div class='title' style='font-size:36px'>
    {'Humanity' if team=='left' else 'AI'} Voting Console
    </div>
    """, unsafe_allow_html=True)

    if not active:
        st.info("Waiting for your team's turn...")
        time.sleep(1)
        st.rerun()

    angle = st.slider("Launch Angle", 10, 80, 45)
    power = st.slider("Propulsion Strength", 20, 100, 60)

    if st.button("Submit Vote", use_container_width=True):
        votes = load_votes()

        votes[team].append({
            "angle": angle,
            "power": power,
            "ts": time.time()
        })

        save_votes(votes)

        st.success("Vote submitted")

        time.sleep(1)
        st.rerun()

    time.sleep(1)
    st.rerun()

# ── main screen ───────────────────────────────────────────────
game = load_game()
votes = load_votes()

phase = game["phase"]
turn = game["turn"]

now = time.time()

if phase == "voting":
    elapsed = now - game["turn_start"]

    if elapsed >= TURN_SECS:

        tv = votes[turn]

        if tv:
            ang = round(sum(v["angle"] for v in tv) / len(tv))
            pwr = round(sum(v["power"] for v in tv) / len(tv))

            game[f"last_avg_{turn}"] = {
                "angle": ang,
                "power": pwr
            }
        else:
            prev = game[f"last_avg_{turn}"]
            ang = prev["angle"]
            pwr = prev["power"]

        traj = trajectory(ang, pwr, turn, game["wind"])
        did_hit = hits(traj, turn)

        if did_hit:
            if turn == "left":
                game["score_left"] += 1
            else:
                game["score_right"] += 1

        game["last_throw"] = {
            "angle": ang,
            "power": pwr,
            "traj": traj,
            "hit": did_hit,
            "side": "right" if turn == "left" else "left"
        }

        game["phase"] = "result"
        game["result_start"] = time.time()

        save_game(game)

elif phase == "result":

    if now - game["result_start"] >= RESULT_SECS:

        game["phase"] = "voting"
        game["turn"] = "right" if turn == "left" else "left"
        game["turn_start"] = time.time()
        game["wind"] = round(random.uniform(-5, 5), 1)

        votes = new_votes()

        save_game(game)
        save_votes(votes)

# ── ui ────────────────────────────────────────────────────────
st.markdown("""
<div class='title'>
The PhD Public Defense Waiting Game
</div>
<div class='subtitle'>
Audience-controlled molecular combat between humanity and AI
</div>
""", unsafe_allow_html=True)

left, center, right = st.columns([1.1, 3, 1.1])

with left:

    st.markdown("<div class='panel'>", unsafe_allow_html=True)

    st.markdown("<div class='label'>Round State</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric'>{game['phase'].upper()}</div>", unsafe_allow_html=True)

    st.markdown("<div class='label'>Current Turn</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric'>{game['turn'].upper()}</div>", unsafe_allow_html=True)

    st.markdown("<div class='label'>Field Drift</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric'>{game['wind']}</div>", unsafe_allow_html=True)

    st.markdown("<div class='label'>Votes</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='metric'>L {len(votes['left'])} / R {len(votes['right'])}</div>",
        unsafe_allow_html=True
    )

    st.markdown("</div>", unsafe_allow_html=True)

with right:

    base = st.context.headers.get("Host", "localhost:8501")
    scheme = "https"

    url = f"{scheme}://{base}?team={game['turn']}"

    qr = make_qr(url)

    st.markdown("<div class='panel'>", unsafe_allow_html=True)

    st.markdown("<h2>Join the experiment</h2>", unsafe_allow_html=True)

    if qr:
        st.image(f"data:image/png;base64,{qr}", width=220)

    st.markdown(
        f"Scan to vote for the {game['turn']} team.",
        unsafe_allow_html=True
    )

    st.markdown("</div>", unsafe_allow_html=True)

with center:

    preview = []

    if game["phase"] == "voting":

        active_votes = votes[game["turn"]]

        if active_votes:
            pa = round(sum(v["angle"] for v in active_votes) / len(active_votes))
            pp = round(sum(v["power"] for v in active_votes) / len(active_votes))
        else:
            prev = game[f"last_avg_{game['turn']}"]
            pa = prev["angle"]
            pp = prev["power"]

        preview = trajectory(pa, pp, game["turn"], game["wind"])

    preview_js = json.dumps(preview)

    throw = game.get("last_throw") or {}

    traj_js = json.dumps(throw.get("traj", []))

    html = f"""
    <canvas id='c' width='{W}' height='{H}' style='width:100%;border-radius:24px'></canvas>

    <script>

    const W = {W};
    const H = {H};

    const TURN = "{game['turn']}";
    const PHASE = "{game['phase']}";

    const LS = {game['score_left']};
    const RS = {game['score_right']};

    const WIND = {game['wind']};

    const TRAJ = {traj_js};
    const PREVIEW = {preview_js};

    const DID_HIT = {str(throw.get("hit", False)).lower()};
    const HIT_SIDE = "{throw.get('side', '')}";

    const canvas = document.getElementById('c');
    const cx = canvas.getContext('2d');

    const humanImg = new Image();
    humanImg.src = "data:image/png;base64,{human_b64}";

    const robotImg = new Image();
    robotImg.src = "data:image/png;base64,{robot_b64}";

    function bg(){{
      const g = cx.createLinearGradient(0,0,0,H);
      g.addColorStop(0,'#0d5bdd');
      g.addColorStop(.5,'#7d9fd9');
      g.addColorStop(1,'#e7a2a0');
      cx.fillStyle=g;
      cx.fillRect(0,0,W,H);
    }}

    function circles(){{
      cx.strokeStyle='rgba(255,255,255,.7)';
      cx.lineWidth=4;

      cx.beginPath();
      cx.arc(210,260,140,0,Math.PI*2);
      cx.stroke();

      cx.beginPath();
      cx.arc(690,170,140,0,Math.PI*2);
      cx.stroke();
    }}

    function floating(){{
      const nodes = [
        [120,220,60],
        [260,330,26],
        [760,160,52],
        [820,260,22]
      ];

      nodes.forEach(n=>{{
        cx.fillStyle='rgba(255,80,70,.95)';
        cx.beginPath();
        cx.arc(n[0],n[1],n[2],0,Math.PI*2);
        cx.fill();

        cx.strokeStyle='rgba(255,255,255,.3)';
        cx.beginPath();
        cx.arc(n[0]+8,n[1]+4,n[2],0,Math.PI*2);
        cx.stroke();
      }});
    }}

    function molecule(x,y,s=1){{
      cx.save();
      cx.translate(x,y);
      cx.scale(s,s);

      cx.strokeStyle='rgba(255,255,255,.9)';
      cx.fillStyle='rgba(255,80,70,.95)';
      cx.lineWidth=2;

      const pts=[[0,0],[18,-12],[-16,-10],[12,18]];

      cx.beginPath();
      pts.forEach((p,i)=>{{
        if(i===0)return;
        cx.moveTo(0,0);
        cx.lineTo(p[0],p[1]);
      }});
      cx.stroke();

      pts.forEach(p=>{{
        cx.beginPath();
        cx.arc(p[0],p[1],6,0,Math.PI*2);
        cx.fill();
      }});

      cx.restore();
    }}

    function scene(){{
      bg();
      circles();
      floating();

      cx.drawImage(humanImg, 520, -10, 320, 260);
      cx.drawImage(robotImg, 550, 230, 230, 190);

      cx.fillStyle='white';
      cx.font='700 34px Space Grotesk';
      cx.textAlign='center';
      cx.fillText(`${{LS}} : ${{RS}}`, W/2, 60);

      cx.font='18px Space Grotesk';
      cx.fillText(TURN === 'left' ? 'Humanity Turn' : 'AI Turn', W/2, 90);

      cx.fillStyle='rgba(255,255,255,.7)';
      cx.fillText(`Field Drift ${{WIND}}`, W/2, 118);
    }}

    function animate(){{
      scene();

      if(PHASE === 'voting'){{
        if(PREVIEW.length > 1){{
          cx.strokeStyle='rgba(255,255,255,.7)';
          cx.lineWidth=3;
          cx.setLineDash([8,6]);

          cx.beginPath();
          cx.moveTo(PREVIEW[0][0], PREVIEW[0][1]);

          for(let i=1;i<PREVIEW.length;i+=3){{
            cx.lineTo(PREVIEW[i][0], PREVIEW[i][1]);
          }}

          cx.stroke();
          cx.setLineDash([]);

          const end = PREVIEW[PREVIEW.length-1];
          molecule(end[0], end[1], .8);
        }}
      }}

      if(PHASE === 'result' && TRAJ.length > 0){{
        cx.strokeStyle='rgba(255,255,255,.75)';
        cx.lineWidth=3;

        cx.beginPath();
        cx.moveTo(TRAJ[0][0], TRAJ[0][1]);

        TRAJ.forEach(p=>cx.lineTo(p[0],p[1]));
        cx.stroke();

        const tip = TRAJ[TRAJ.length-1];
        molecule(tip[0], tip[1], 1);

        if(DID_HIT){{
          cx.fillStyle='white';
          cx.font='700 32px Space Grotesk';
          cx.fillText('DIRECT HIT', W/2, H-40);
        }}
      }}
    }}

    humanImg.onload = animate;
    robotImg.onload = animate;

    </script>
    """

    st.components.v1.html(html, height=H+10)

time.sleep(1)
st.rerun()
