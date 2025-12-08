# Rugs.fun Game Mechanics

**Purpose**: Comprehensive documentation of Rugs.fun game rules, mechanics, and data formats. Used for bot decision logic and Socket.IO data feed integration.

**Last Updated**: 2025-10-30
**Source**: User gameplay expertise
**Architecture**: Socket.IO feed (100% accurate real-time data) - OCR/vision approach deprecated 2025-10-29

---

## Critical Data Fields (Priority Order)

### 1. Price (CRITICAL)
- **Format**: `X.XXXXx` (multiplier format)
- **Range**: `0.0001x` to `999.9999x` (theoretically)
- **Typical Range**: `1.0x` to `5.0x` (most games rug before 10x)
- **Use**: Primary decision input for buy/sell logic

### 2. Wallet Balance (CRITICAL)
- **Format**: `0.000` (SOL amount)
- **Range**: `0.001` to `99.999` (or higher)
- **Use**: Determines available capital for bets, tracks profit/loss

### 3. Bet Amount (CRITICAL)
- **Format**: `00.000` (always 5 digits with 3 decimal places)
- **Minimum**: `0.001` SOL
- **Maximum**: `99.999` SOL
- **Use**: Position sizing, risk management

---

## Calculated/Derived Fields (Can Be Computed)

### PNL (Profit and Loss)
- **Format**: `+/- 00.000 +/-0000%`
- **Example**: `+0.005 sol +118%` or `-0.002 sol -23380%`

**Calculation**:
```python
# If position is active:
entry_price = price_at_purchase  # e.g., 1.5x
current_price = current_multiplier  # e.g., 2.0x
bet_amount = position_size  # e.g., 0.001 SOL

# SOL profit/loss
pnl_sol = bet_amount * (current_price / entry_price - 1)
# Example: 0.001 * (2.0 / 1.5 - 1) = 0.001 * 0.333 = +0.000333 SOL

# Percentage profit/loss
pnl_percent = (current_price / entry_price - 1) * 100
# Example: (2.0 / 1.5 - 1) * 100 = 33.3%
```

**Important Rules**:
- PNL resets each game (no inter-game positions)
- PNL includes all completed positions in current game
- When position is sold, PNL is reflected in wallet immediately
- When rug occurs, all active positions liquidated (PNL updated, wallet reduced)

### Side Bets
- **Format**: `Bet X.XXX Sol [multiplier] To Win: X.XXX sol`
- **Example**: `Bet 0.001 Sol 4x To Win: 0.005 sol`
- **Example Position**: `Bet 0.001 Sol 4x To Win: 0.005 sol placed at Tick 40. Game is still active at tick 81, side bet is lost. Game rugs between tick 40 and 80, side bet is won. A new side bet cant be entered again in this game until tick 85 due to the 5 tick cooldown between side bets.(There are no limits to the amount of side bets placed in any one game other than the duration of the game, 5 second cooldown between side bets, and only one allowed active at a time.`

**Mechanics**:
- Side bet pays **400%** if rug occurs while bet is active
- Payout calculation: `win_amount = bet_amount * 5`
  - Example: Bet 0.001 → Win 0.005 (400% profit = 5x multiplier)
- Side bets are "insurance" against rug events
- If game doesn't rug before side bet expires, bet is lost
- Only one active side bet is allowed at any given time
- Side bets last for 40 ticks (10 seconds).
- There is a cool down period for a new side bet of 5 ticks.
- A side bet can be entered during the presale phase if you believe the game will rug in the first 40 ticks when it starts. 

## Game Phases and State Transitions

### Phase 1: COOLDOWN
- **Duration**: Fixed cooldown period between games
- **Visible Indicator**: "Next round in: X.XXXs" countdown
- **Actions Available**: None (waiting for next game)

### Phase 2: PRESALE
- **Indicator**: "Presale: Buy a guaranteed position at 1.00x before the round starts"
- **Actions Available**: Buy position at guaranteed 1.00x entry
- **Strategic Advantage**: Enter before price movement begins

### Phase 3: GAME_START
- **Indicator**: Game begins, price starts at 1.00x
- **Actions Available**: Buy, Sell, Adjust Bet, Side Bet

### Phase 4: ACTIVE
- **Indicator**: Price is actively changing
- **Price Behavior**: Multiplier increases over time (1.00x → 2.00x → 3.00x...)
- **Actions Available**: Sell, Adjust Bet (cannot buy after certain point)

### Phase 5: RUG_EVENT
- **Indicator**: "Thanks for playing" message appears
- **Game Over Trigger**: Price crashes to 0x
- **Consequences**:
  - All active bet positions liquidated immediately
  - All active side bets pay out 400% (5x multiplier)
  - Losses/gains reflected instantly in wallet
  - PNL is finalized for this game

---

## OCR Validation Rules (Historical Reference - DEPRECATED 2025-10-29)

⚠️ **NOTE**: These OCR validation rules are preserved for historical reference only. The current architecture (Phase 3.6) uses Socket.IO feed which provides 100% accurate data without need for OCR or validation.

<details>
<summary>Click to expand deprecated OCR validation rules</summary>

Use these rules to validate and correct OCR outputs:

### Price Validation
```python
def validate_price(ocr_text: str) -> str:
    """
    Validate and correct price OCR output.

    Rules:
    - Must end with 'x'
    - Must be numeric before 'x'
    - Replace 'O' with '0' (common OCR error)
    """
    text = ocr_text.strip()

    # Common OCR errors
    text = text.replace('O', '0')  # O → 0
    text = text.replace('o', '0')  # o → 0

    # Must end with 'x'
    if not text.endswith('x'):
        return None  # Invalid

    # Extract numeric part
    numeric = text[:-1]

    try:
        price = float(numeric)
        if price < 0 or price > 1000:
            return None  # Out of reasonable range
        return f"{price:.4f}x"
    except ValueError:
        return None  # Invalid format
```

### Bet Amount Validation
```python
def validate_bet_amount(ocr_text: str) -> str:
    """
    Validate and correct bet amount OCR output.

    Rules:
    - Format: 00.000 (5 digits, 3 decimals)
    - Range: 0.001 to 99.999
    - Replace 'O' with '0', 'o' with '0'
    """
    text = ocr_text.strip()

    # Common OCR errors
    text = text.replace('O', '0')
    text = text.replace('o', '0')

    try:
        amount = float(text)
        if amount < 0.001 or amount > 99.999:
            return None  # Out of valid range
        return f"{amount:.3f}"
    except ValueError:
        return None
```

### Wallet Validation
```python
def validate_wallet(ocr_text: str) -> str:
    """
    Validate and correct wallet balance OCR output.

    Rules:
    - Format: 0.000 (SOL amount)
    - Must be positive
    - Replace 'O' with '0'
    """
    text = ocr_text.strip()

    # Common OCR errors
    text = text.replace('O', '0')
    text = text.replace('o', '0')

    try:
        balance = float(text)
        if balance < 0:
            return None
        return f"{balance:.3f}"
    except ValueError:
        return None
```

</details>

---

## Bot Decision Logic (Socket.IO Architecture)

### Critical Decision Inputs (In Priority Order):
1. **Price** - Primary signal for buy/sell decisions
2. **Wallet Balance** - Determines position sizing capability
3. **Bet Amount** - Current position size

### Derived Calculations:
- PNL can be calculated from (entry_price, current_price, bet_amount)
- Side bet value can be calculated from bet_amount (5x multiplier)
- Win rate can be tracked by bot (not in game UI)

### Example Bot Logic:
```python
# Critical fields from Socket.IO feed (100% accurate)
game_state = socket_io_client.get_game_state()

price = game_state['multiplier']  # e.g., 2.5 (float)
wallet = game_state['balance']  # e.g., 0.045 (float)
bet_amount = game_state['bet_amount']  # e.g., 0.001 (float)
phase = game_state['phase']  # "PRESALE", "ACTIVE", etc.
has_position = len(game_state['positions']) > 0

# Decision logic (no validation needed - data is already accurate)
if price >= 2.0 and has_position:
    action = "SELL"  # Take profit at 2x
elif wallet >= 0.001 and phase == "PRESALE":
    action = "BUY"  # Enter at 1.0x
else:
    action = "WAIT"
```

---

## Training Data Collection Priorities (Historical Reference - DEPRECATED 2025-10-29)

⚠️ **NOTE**: This section described OCR annotation priorities for YOLO training (Phase 3.5). Socket.IO architecture (Phase 3.6) does not require manual annotation or OCR training.

<details>
<summary>Click to expand deprecated training data priorities</summary>

Based on critical fields analysis:

### High Priority (Required for bot):
1. **Price** - Collect 150+ annotations with various multipliers
2. **Wallet** - Collect 150+ annotations (already strong at 99%)
3. **Bet Amount** - Collect 150+ annotations (fix 'O' vs '0' errors)

### Medium Priority (Nice to have):
4. **PNL** - Collect 80+ annotations (can be calculated if needed)
5. **Side Bet** - Collect 50+ annotations (can be calculated)

### Low Priority (For game state detection):
6. **Countdown** - Collect 60+ for phase detection
7. **Presale** - Collect 40+ for phase detection
8. **Rugged** - Collect 30+ for game-over detection

</details>

---

## Known Limitations and Edge Cases

### Game Mechanics Edge Cases:
- Multiple positions in same game (PNL is cumulative)
- Side bets can be placed/removed during active game
- Presale phase may be very short (1-2 seconds)
- Rug can occur at any time (even at 1.01x)

### Wallet Balance Behavior:
- Decreases when buying position (wallet -= bet_amount)
- Increases when selling position (wallet += bet_amount + profit)
- Decreases when rug occurs with active position (wallet -= bet_amount)
- Increases when side bet wins (wallet += side_bet * 5)

---

## Future Bot Architecture Considerations

### Minimum Viable Bot (MVP):
- **Required Fields**: Price, Wallet, Bet Amount
- **Required Logic**: Buy at presale/low price, sell at 2x target
- **Required Actions**: Browser automation (click buy/sell)

### Advanced Bot (v2):
- **Additional Fields**: PNL (validation), Game Phase
- **Advanced Logic**: Dynamic profit targets, stop-loss
- **Risk Management**: Kelly criterion position sizing

### Expert Bot (v3):
- **ML Integration**: Predict rug timing from historical patterns
- **Multi-account**: Parallel gameplay across sessions
- **Profit Optimization**: Maximize expected value over many games

---

**End of Game Mechanics Documentation**

**Related Files**:
- `docs/projects/rugs_fun/GYMNASIUM_DESIGN_SPEC.md` - Socket.IO gymnasium environment (Phase 3.6)
- `core/rugs/game_state_detector.py` - Phase detection implementation
- `core/rugs/pattern_detector.py` - Pattern detection systems (Phase 3.6B)
- `docs/archive/deprecated_yolo/TRAINING_SYSTEM.md` - Deprecated OCR training architecture (archived)
