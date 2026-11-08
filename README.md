# SME FinancePilot — 3D Business Survival Simulator

An educational Malaysian SME simulation prototype combining an isometric 3D business world, deterministic Python financial calculations, and an Ollama-powered agentic advisor.

## Features

- Five clickable specialist buildings and a central Finance Core in the 3D HQ.
- Three-round business survival game: rising supplier costs, delayed customer payment, and an expansion decision.
- Owner confirmation before a simulated decision changes game state.
- Separate profitability and cash-flow calculations.
- Receivables, payables, simulated debt and capital expenditure tracking.
- Finance Core: goal interpretation, dynamic allow-listed tool selection, Python tool execution, evaluation, one bounded replanning pass, and a learning-focused recommendation.
- Final score, decision history and downloadable JSON report.

## Requirements

- Windows 10/11
- Python 3.10 or later (recommended: Python 3.11–3.13)
- Internet connection for the Three.js CDN used by the 3D scene
- Optional: Ollama with a local chat model, e.g. `qwen3:4b`

## Run on Windows

1. Extract the ZIP file.
2. Open the extracted `SME-FinancePilot-Optimized` folder.
3. Click the address bar in File Explorer, type `cmd`, and press Enter.
4. Create a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```

5. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. Start the game:

   ```powershell
   streamlit run app.py
   ```

7. Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Enable local AI (optional)

1. Install and open Ollama.
2. In PowerShell run:

   ```powershell
   ollama pull qwen3:4b
   ollama run qwen3:4b
   ```

3. Keep Ollama running. In the FinancePilot sidebar, set the model name to the exact model shown by `ollama list`.
4. Open **Finance Core AI** or **Play Simulation** and run an analysis.

If Ollama is unavailable, the game still runs using a clearly labelled rule-based fallback. The fallback is not presented as an LLM-generated plan.

## Game flow

1. Start or reset a game from the sidebar settings.
2. Explore the 3D Business World.
3. Open Play Simulation and read the current event.
4. Choose A, B or C. Optionally ask Finance Core to analyse the event.
5. Review the simulated financial outcome.
6. Approve to commit the decision, or reject to leave the game state unchanged.
7. Complete all three rounds and open Final Report.

## Important notes

- All figures, thresholds and event assumptions are illustrative educational game data, not real market forecasts or financial advice.
- No bank accounts, real personal data, payments or external business systems are connected.
- Python performs financial calculations. The AI is not allowed to invent calculation results.
- The Agent workflow is bounded to one additional replanning pass to keep local inference predictable.
- The 3D scene loads Three.js from a CDN. If the scene is blank, check internet access or replace the CDN imports with locally hosted Three.js assets.
- Streamlit Community Cloud does not automatically provide access to a player's local Ollama server. The local AI workflow is intended for local demonstration unless a separately secured hosted inference endpoint is configured.

## Project structure

```text
SME-FinancePilot-Optimized/
├── app.py
├── agent_core.py
├── game_engine.py
├── requirements.txt
├── README.md
├── .streamlit/config.toml
└── components/hq_scene.html
```
