"""
voter.py — Mobile voting page for Monkey Banana Battle.
Run separately: streamlit run voter.py --server.port 8502

Players scan the QR code from the main game screen to reach this page,
where they choose their angle and power for the current throw.
"""

import streamlit as st
import json
import os
import time

st.set_page_config(
    page_title="🍌 Vote!",
    layout="centered",
    initial_sidebar_state="collapsed",
)

VOTES_FILE = "votes.json"

def load_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE) as f:
            return json.load(f)
    return {"left": [], "right": []}

def save_votes(votes):
    with open(VOTES_FILE, "w") as f:
        json.dump(votes, f)

# Detect team from query param
params = st.query_params
team = params.get("team", "left")
if team not in ("left", "right"):
    team = "left"

team_label = "LEFT 🟡" if team == "left" else "RIGHT 🔵"
team_color = "#ffcc44" if team == "left" else "#44ccff"
team_bg = "#2d3a1e" if team == "left" else "#1a2a3a"
team_border = "#ffcc44" if team == "left" else "#44ccff"

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@400;700&display=swap');
  html, body, [class*="css"] {{ font-family: 'Nunito', sans-serif; background: #111 !important; }}
  .team-header {{
    background: {team_bg};
    border: 3px solid {team_border};
    border-radius: 20px;
    padding: 20px;
    text-align: center;
    margin-bottom: 20px;
  }}
  .team-name {{
    font-family: 'Bangers', cursive;
    font-size: 2.5rem;
    color: {team_color};
    letter-spacing: 3px;
    margin: 0;
  }}
  .sub {{
    color: #aaa;
    font-size: 0.9rem;
    margin-top: 4px;
  }}
  .vote-box {{
    background: #1a1a1a;
    border-radius: 16px;
    padding: 20px;
    margin: 16px 0;
    border: 1px solid #333;
  }}
  .param-label {{
    font-family: 'Bangers', cursive;
    font-size: 1.3rem;
    color: #fff;
    margin-bottom: 8px;
    letter-spacing: 1px;
  }}
  .param-desc {{
    color: #888;
    font-size: 0.8rem;
    margin-bottom: 12px;
  }}
  .big-val {{
    font-family: 'Bangers', cursive;
    font-size: 3rem;
    text-align: center;
    color: {team_color};
    margin: 8px 0;
  }}
  .voted-msg {{
    background: #1a3a1a;
    border: 2px solid #4caf50;
    border-radius: 16px;
    padding: 24px;
    text-align: center;
  }}
</style>

<div class="team-header">
  <p class="team-name">TEAM {team_label}</p>
  <p class="sub">🍌 Vote for this turn's throw!</p>
</div>
""", unsafe_allow_html=True)

# Check if this session already voted
session_key = f"voted_{team}"
if session_key not in st.session_state:
    st.session_state[session_key] = False

if st.session_state[session_key]:
    st.markdown(f"""
    <div class="voted-msg">
      <div style="font-size:3rem">✅</div>
      <div style="font-family:'Bangers',cursive;font-size:2rem;color:#4caf50;">Vote Submitted!</div>
      <div style="color:#aaa;margin-top:8px;">Your vote has been counted. Watch the main screen!</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Vote again (new turn)", use_container_width=True):
        st.session_state[session_key] = False
        st.rerun()

else:
    # Angle input
    st.markdown("""
    <div class="vote-box">
      <div class="param-label">🎯 Throw Angle</div>
      <div class="param-desc">Low angle = flat throw. High angle = lofted arc.</div>
    </div>
    """, unsafe_allow_html=True)

    angle = st.slider(
        "Angle (degrees)",
        min_value=10,
        max_value=80,
        value=45,
        step=1,
        key="angle_slider",
        label_visibility="collapsed",
    )
    st.markdown(f'<div class="big-val">{angle}°</div>', unsafe_allow_html=True)

    # Visual angle hint
    import math
    tip_x = 30 + math.cos(math.radians(angle)) * 40
    tip_y = 30 - math.sin(math.radians(angle)) * 40
    st.markdown(f"""
    <svg width="100%" viewBox="0 0 200 80" style="margin:-8px 0 4px 0;">
      <line x1="30" y1="50" x2="170" y2="50" stroke="#444" stroke-width="1.5"/>
      <line x1="30" y1="50" x2="{10 + tip_x * 1.8}" y2="{50 - (tip_y - 30) * 0.9}"
            stroke="{team_color}" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="30" cy="50" r="4" fill="{team_color}"/>
      <text x="100" y="70" text-anchor="middle" fill="#666" font-size="11"
            font-family="Nunito, sans-serif">trajectory angle</text>
    </svg>
    """, unsafe_allow_html=True)

    # Power input
    st.markdown("""
    <div class="vote-box">
      <div class="param-label">💥 Throw Power</div>
      <div class="param-desc">More power = farther throw. Be careful of overshooting!</div>
    </div>
    """, unsafe_allow_html=True)

    power = st.slider(
        "Power",
        min_value=10,
        max_value=100,
        value=50,
        step=1,
        key="power_slider",
        label_visibility="collapsed",
    )

    bar_width = int(power * 1.6)
    bar_color = "#4caf50" if power < 40 else "#ffcc44" if power < 70 else "#ff5722"
    st.markdown(f"""
    <div style="background:#222;border-radius:10px;height:28px;margin:4px 0 8px 0;overflow:hidden;">
      <div style="width:{bar_width}px;max-width:100%;height:100%;background:{bar_color};
                  border-radius:10px;transition:width 0.2s;"></div>
    </div>
    <div class="big-val">{power}</div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button(f"🍌 SUBMIT MY VOTE", use_container_width=True, type="primary"):
        votes = load_votes()
        votes[team].append({
            "angle": angle,
            "power": power,
            "timestamp": time.time(),
        })
        save_votes(votes)
        st.session_state[session_key] = True
        st.rerun()

st.markdown(f"""
<div style="text-align:center;color:#444;font-size:0.75rem;margin-top:32px;">
  Monkey Banana Battle · Team {team.upper()} voter
</div>
""", unsafe_allow_html=True)
