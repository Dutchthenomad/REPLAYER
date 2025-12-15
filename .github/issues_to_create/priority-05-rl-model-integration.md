---
title: "[Priority 5] RL Model Integration Framework"
labels: enhancement, ml, rl, priority-high, phase-12
assignees: ""
---

## Goal
Integrate trained RL models from rugs-rl-bot for live trading decisions.

## Context
RL models exist in `/home/nomad/Desktop/rugs-rl-bot/` but are not yet wired into REPLAYER for live inference.

## Tasks
### Model Inference Pipeline
- [ ] Design model inference pipeline (load models, feature extraction, action selection)
- [ ] Load trained RL models (PPO/DQN)
- [ ] Feature extraction from live game state
- [ ] Action selection (buy/sell/hold/sidebet)
- [ ] Confidence scoring

### RLStrategyAdapter
- [ ] Create `RLStrategyAdapter` class (implements `TradingStrategy` ABC)
- [ ] Wrap RL model inference
- [ ] Handle feature preprocessing
- [ ] Apply risk limits (max position, stop loss)

### UI Integration
- [ ] Add model selection dropdown in UI
- [ ] Display model performance metrics
- [ ] Live inference confidence visualization
- [ ] Integration tests with backtesting

## Success Criteria
- RL models load successfully at startup
- Model can generate trade decisions in <100ms
- Bot executes RL-recommended actions in BACKEND mode
- Performance metrics tracked (win rate, avg PnL, Sharpe ratio)
- Zero inference errors during 100-game test

## Dependencies
- Priority 3 complete (training data available)

## Related Files
- `/home/nomad/Desktop/rugs-rl-bot/` - RL training project
- `src/bot/strategies/` - Existing strategy framework
- `src/ml/` - ML symlinks
- `src/bot/controller.py` - Bot orchestration

## Estimated Effort
8-10 hours
