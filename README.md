# 🍌 Monkey Banana Battle

A multiplayer crowd-voting banana-throwing game! Two monkeys on buildings try to hit each other with bananas. Players vote on angle and power by scanning QR codes on their phones.

## Setup

```bash
pip install -r requirements.txt
```

## Running

You need **two terminal windows** (or tabs):

**Terminal 1 — Main game display (show on TV/projector):**
```bash
streamlit run app.py --server.port 8501
```

**Terminal 2 — Mobile voter page (players scan QR to reach this):**
```bash
streamlit run voter.py --server.port 8502
```

## Configuration

1. Open the main game at `http://localhost:8501`
2. In the sidebar, set the **Voter page URL** to your machine's local IP address, e.g.:
   ```
   http://192.168.1.42:8502
   ```
   (Find your IP with `ipconfig` on Windows or `ifconfig`/`ip addr` on Linux/Mac)
3. This URL is encoded into the QR codes shown on screen.

## How to Play

1. Show `app.py` on a big screen
2. Players scan the **left** or **right** QR code with their phone
3. Each player picks their **angle** (10–80°) and **power** (10–100) and submits
4. The host clicks **THROW!** — the game averages all votes and launches the banana
5. If the banana hits the opposing monkey, that team scores a point!
6. Wind changes each turn, making each throw unique
7. Click **Next Turn** to switch sides and start voting again

## Files

- `app.py` — Main game display (scoreboard, canvas, QR codes, controls)
- `voter.py` — Mobile voting page served separately
- `votes.json` — Shared vote storage (auto-created)
- `game_state.json` — Game state (auto-created)
