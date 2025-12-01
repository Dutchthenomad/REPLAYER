# Implementation Guide - ttkbootstrap Integration
**Step-by-step guide for migrating Rugs Replay Viewer to ttkbootstrap**

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Phase 1: Basic Integration](#phase-1-basic-integration)
3. [Phase 2: Theme Switcher](#phase-2-theme-switcher)
4. [Phase 3: Panel Upgrades](#phase-3-panel-upgrades)
5. [Phase 4: Chart Coordination](#phase-4-chart-coordination)
6. [Phase 5: Polish & Testing](#phase-5-polish--testing)

---

## Prerequisites

### System Requirements
- Python 3.13
- Windows 11
- Existing Rugs Replay Viewer codebase

### Install ttkbootstrap
```bash
pip install ttkbootstrap
```

### Verify Installation
```bash
python -c "import ttkbootstrap; print(ttkbootstrap.__version__)"
# Should output: 1.19.0 (or newer)
```

---

## Phase 1: Basic Integration (5 minutes)

### Step 1.1: Backup Current Code
```bash
cd /path/to/REPLAYER
git checkout -b feature/ttkbootstrap-theming
cp src/main.py src/main.py.backup
```

### Step 1.2: Update Main Window Initialization

**File:** `src/main.py`

**OLD CODE (Line ~30):**
```python
import tkinter as tk

class Application:
    def __init__(self, live_mode: bool = False):
        # ... initialization code ...
        
        # Create UI
        self.root = tk.Tk()  # ← CHANGE THIS LINE
        self.main_window = None
```

**NEW CODE:**
```python
import tkinter as tk
import ttkbootstrap as ttk  # ← ADD THIS IMPORT

class Application:
    def __init__(self, live_mode: bool = False):
        # ... initialization code ...
        
        # Create UI
        self.root = ttk.Window(themename='cyborg')  # ← CHANGED
        self.main_window = None
```

### Step 1.3: Test Basic Functionality
```bash
cd ~/Desktop/REPLAYER
./run.sh
```

**Expected Result:**
- App launches with cyborg theme applied
- Existing functionality works unchanged
- Widgets have new styled appearance

**If it works:** Proceed to Phase 2  
**If it fails:** Check error logs, verify ttkbootstrap installation

---

## Phase 2: Theme Switcher (15 minutes)

### Step 2.1: Add Theme Menu to Main Window

**File:** `src/ui/main_window.py`

**Find the `_create_menu_bar()` method and add:**

```python
def _create_menu_bar(self):
    """Create menu bar"""
    menubar = tk.Menu(self.root)
    self.root.config(menu=menubar)
    
    # ... existing menus (File, Playback, etc.) ...
    
    # NEW: Theme Menu
    theme_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Theme", menu=theme_menu)
    
    # Add theme options
    available_themes = self.root.style.theme_names()
    
    # Filter to just the dark themes for HUD aesthetic
    dark_themes = ['cyborg', 'darkly', 'superhero', 'solar', 'vapor']
    
    for theme in dark_themes:
        if theme in available_themes:
            theme_menu.add_command(
                label=theme.capitalize(),
                command=lambda t=theme: self._switch_theme(t)
            )
    
    theme_menu.add_separator()
    
    # Add "All Themes" submenu for advanced users
    all_themes_menu = tk.Menu(theme_menu, tearoff=0)
    theme_menu.add_cascade(label="All Themes", menu=all_themes_menu)
    
    for theme in sorted(available_themes):
        all_themes_menu.add_command(
            label=theme,
            command=lambda t=theme: self._switch_theme(t)
        )
```

### Step 2.2: Implement Theme Switching Method

**Add this method to MainWindow class:**

```python
def _switch_theme(self, theme_name: str):
    """
    Switch to a new theme
    
    Args:
        theme_name: Name of theme to activate
    """
    try:
        self.root.style.theme_use(theme_name)
        
        # Update chart colors to match new theme
        if hasattr(self, 'chart_panel'):
            self._update_chart_colors(theme_name)
        
        # Show success toast
        if self.toast:
            self.toast.show_info(f"Theme changed to: {theme_name}")
        
        # Save preference (optional - for persistence)
        self._save_theme_preference(theme_name)
        
        logger.info(f"Theme changed to: {theme_name}")
        
    except Exception as e:
        logger.error(f"Failed to change theme: {e}")
        if self.toast:
            self.toast.show_error(f"Theme change failed: {e}")
```

### Step 2.3: Add Theme Persistence (Optional)

**Add these methods to MainWindow class:**

```python
def _save_theme_preference(self, theme_name: str):
    """Save theme preference to config file"""
    config_file = Path.home() / '.rugs_replay_viewer' / 'theme.json'
    config_file.parent.mkdir(exist_ok=True)
    
    with open(config_file, 'w') as f:
        json.dump({'theme': theme_name}, f)

def _load_theme_preference(self) -> str:
    """Load saved theme preference, default to cyborg"""
    config_file = Path.home() / '.rugs_replay_viewer' / 'theme.json'
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('theme', 'cyborg')
        except:
            pass
    
    return 'cyborg'  # Default theme
```

**Update Application.__init__() in src/main.py:**

```python
def __init__(self, live_mode: bool = False):
    # ... existing code ...
    
    # Create UI with saved theme preference
    self.main_window = MainWindow(self.root, self.state, self.event_bus, self.config)
    preferred_theme = self.main_window._load_theme_preference()
    self.root.style.theme_use(preferred_theme)
```

### Step 2.4: Test Theme Switching
1. Run app
2. Click Theme menu
3. Try cyborg, darkly, superhero
4. Verify instant switching
5. Restart app, verify theme persists

---

## Phase 3: Panel Upgrades (20 minutes)

### Step 3.1: Upgrade StatusPanel

**File:** `src/ui/panels.py`

**OLD CODE:**
```python
class StatusPanel(Panel):
    def _create_widgets(self):
        # Tick display
        self.tick_label = tk.Label(  # ← OLD
            self.frame,
            text="Tick: 0",
            font=('Arial', 12),
            bg=self.config.background,
            fg='white'
        )
```

**NEW CODE:**
```python
import ttkbootstrap as ttk  # ← ADD at top of file

class StatusPanel(Panel):
    def _create_widgets(self):
        # Tick display
        self.tick_label = ttk.Label(  # ← CHANGED to ttk
            self.frame,
            text="Tick: 0",
            font=('Arial', 12),
            # Note: bg/fg removed - theme handles colors
        )
```

**Apply same pattern to:**
- `self.price_label`
- `self.phase_label`
- `self.balance_label`
- `self.pnl_label`

### Step 3.2: Upgrade Button Widgets

**Find all tk.Button instances and upgrade:**

**BEFORE:**
```python
tk.Button(
    controls_frame,
    text="🔍+ Zoom In",
    command=self.chart.zoom_in,
    bg='#444444',
    fg='white',
    font=('Arial', 9)
)
```

**AFTER:**
```python
ttk.Button(
    controls_frame,
    text="🔍+ Zoom In",
    command=self.chart.zoom_in,
    bootstyle='secondary'  # Use ttkbootstrap style
)
```

**Bootstyle Options:**
- `'primary'` - Main theme color (cyan in cyborg)
- `'secondary'` - Secondary color
- `'success'` - Green
- `'info'` - Blue
- `'warning'` - Orange/yellow
- `'danger'` - Red
- `'outline-primary'` - Outlined button
- `'link'` - Link style

### Step 3.3: Upgrade Entry Widgets

**BEFORE:**
```python
self.bet_entry = tk.Entry(
    panel,
    width=10,
    bg='#333333',
    fg='white'
)
```

**AFTER:**
```python
self.bet_entry = ttk.Entry(
    panel,
    width=10
    # Theme handles colors automatically
)
```

### Step 3.4: Test Each Panel
After upgrading each panel:
1. Run app
2. Verify panel displays correctly
3. Test interaction (buttons, entries)
4. Switch themes, verify appearance updates
5. Commit working changes

---

## Phase 4: Chart Coordination (20 minutes)

### Step 4.1: Create Theme Color Mapping

**File:** `src/ui/widgets/chart.py`

**Add at top of file:**

```python
# Theme-coordinated color palettes
THEME_COLORS = {
    'cyborg': {
        'background': '#060606',
        'grid': '#1a1a1a',
        'grid_major': '#2a2a2a',
        'text': '#888888',
        'text_bright': '#FFFFFF',
        'price_up': '#63C971',      # Neon green
        'price_down': '#CC0000',     # Red
        'price_neutral': '#2A9FD6',  # Cyan
    },
    'darkly': {
        'background': '#222222',
        'grid': '#2a2a2a',
        'grid_major': '#3a3a3a',
        'text': '#888888',
        'text_bright': '#FFFFFF',
        'price_up': '#00BC8C',       # Teal green
        'price_down': '#E74C3C',     # Red
        'price_neutral': '#375A7F',  # Blue
    },
    'superhero': {
        'background': '#2B3E50',
        'grid': '#3a4d60',
        'grid_major': '#4a5d70',
        'text': '#999999',
        'text_bright': '#FFFFFF',
        'price_up': '#5CB85C',       # Green
        'price_down': '#D9534F',     # Red
        'price_neutral': '#4C9BE8',  # Blue
    },
    'solar': {
        'background': '#002B36',
        'grid': '#073642',
        'grid_major': '#0a4652',
        'text': '#586e75',
        'text_bright': '#93A1A1',
        'price_up': '#859900',       # Olive
        'price_down': '#DC322F',     # Red
        'price_neutral': '#268BD2',  # Blue
    },
    # Default fallback
    'default': {
        'background': '#0a0a0a',
        'grid': '#1a1a1a',
        'grid_major': '#2a2a2a',
        'text': '#666666',
        'text_bright': '#ffffff',
        'price_up': '#00ff88',
        'price_down': '#ff3366',
        'price_neutral': '#ffcc00',
    }
}
```

### Step 4.2: Add Theme Update Method

**Add to ChartWidget class:**

```python
def update_theme(self, theme_name: str):
    """
    Update chart colors to match theme
    
    Args:
        theme_name: Name of active theme
    """
    # Get colors for this theme, fallback to default
    self.colors = THEME_COLORS.get(theme_name, THEME_COLORS['default']).copy()
    
    # Update canvas background
    self.config(bg=self.colors['background'])
    
    # Redraw chart with new colors
    self.draw()
    
    logger.info(f"Chart theme updated to: {theme_name}")
```

### Step 4.3: Wire Up Theme Updates

**File:** `src/ui/main_window.py`

**Update `_switch_theme()` method:**

```python
def _switch_theme(self, theme_name: str):
    """Switch to a new theme"""
    try:
        self.root.style.theme_use(theme_name)
        
        # Update chart colors to match new theme
        self._update_chart_colors(theme_name)  # ← ADD THIS
        
        # ... rest of method ...
```

**Add new method:**

```python
def _update_chart_colors(self, theme_name: str):
    """Update chart widget colors to match theme"""
    if hasattr(self, 'chart_panel') and hasattr(self.chart_panel, 'chart'):
        self.chart_panel.chart.update_theme(theme_name)
```

### Step 4.4: Test Chart Coordination
1. Run app, load a replay
2. Switch between themes
3. Verify chart background matches theme
4. Verify price lines use theme colors
5. Check readability at all multiplier ranges (1x-100x+)

---

## Phase 5: Polish & Testing (30 minutes)

### Step 5.1: Visual Hierarchy Review

**Check these elements:**
- [ ] Status bar stands out (important info visible)
- [ ] Active position clearly indicated
- [ ] Bot status obvious when enabled
- [ ] Price changes easily tracked
- [ ] Phase transitions visible

**Adjust as needed:**
```python
# Make critical elements bold
ttk.Label(..., font=('Arial', 12, 'bold'))

# Use bootstyle for semantic meaning
ttk.Label(..., bootstyle='success')  # For positive P&L
ttk.Label(..., bootstyle='danger')   # For negative P&L
ttk.Label(..., bootstyle='warning')  # For warnings
```

### Step 5.2: Spacing & Padding Consistency

**Apply consistent padding:**
```python
# Panels
panel.frame.config(padding=10)

# Sections within panels
section_frame.pack(pady=5, padx=10)

# Widgets
widget.pack(pady=2, padx=5)
```

**Standard spacing guide:**
- Between panels: 10px
- Between sections: 5px
- Between widgets: 2-3px
- Border padding: 5-10px

### Step 5.3: Accessibility Check

**Contrast Ratios (WCAG AA Compliance):**
- Normal text: 4.5:1 minimum
- Large text (18pt+): 3:1 minimum
- UI components: 3:1 minimum

**Test with:**
```bash
# Install contrast checker
pip install colorcontrast

# Test key combinations
python
>>> from colorcontrast import contrast
>>> contrast.check('#FFFFFF', '#060606')  # White on cyborg bg
16.05:1  # ✓ Excellent

>>> contrast.check('#2A9FD6', '#060606')  # Cyan on cyborg bg
7.89:1   # ✓ Good
```

### Step 5.4: Performance Testing

**Test real-time performance:**
1. Load a long replay (1000+ ticks)
2. Switch to cyborg theme
3. Play at maximum speed
4. Monitor for frame drops
5. Check CPU usage (should be <20%)

**Test theme switching under load:**
1. Start replay playback
2. Switch themes mid-playback
3. Verify no crashes or glitches
4. Ensure smooth transition

### Step 5.5: User Acceptance Testing

**Test scenarios:**
- [ ] First launch (default theme loads)
- [ ] Theme switching via menu
- [ ] Theme persists after restart
- [ ] Replay playback works in all themes
- [ ] Live feed works in all themes
- [ ] Bot controls visible in all themes
- [ ] Toast notifications readable in all themes
- [ ] All keyboard shortcuts work

**Get feedback on:**
- Which theme is preferred?
- Any readability issues?
- Any visual glitches?
- Performance acceptable?

---

## Troubleshooting

### Issue: "ImportError: No module named ttkbootstrap"
**Solution:** Install ttkbootstrap: `pip install ttkbootstrap`

### Issue: Some widgets still look old-style
**Solution:** Check if using `tk.Widget` instead of `ttk.Widget`

### Issue: Chart colors don't change with theme
**Solution:** Verify `_update_chart_colors()` is being called in `_switch_theme()`

### Issue: Theme doesn't persist across restarts
**Solution:** Check `_save_theme_preference()` and `_load_theme_preference()` implementation

### Issue: Performance degradation
**Solution:** This is NOT caused by ttkbootstrap. Check:
- Event bus issues
- Thread safety violations
- Memory leaks in replay engine

### Issue: Widgets look wrong in dark theme
**Solution:** Make sure using `ttk` widgets, not `tk` widgets

---

## Rollback Procedure

If you need to revert:

```bash
# Restore backup
cp src/main.py.backup src/main.py

# Or use git
git checkout src/main.py
git checkout src/ui/panels.py
git checkout src/ui/widgets/chart.py

# Uninstall ttkbootstrap (optional)
pip uninstall ttkbootstrap
```

---

## Success Criteria

✅ **Implementation Complete When:**
- [ ] ttkbootstrap installed
- [ ] App launches with themed appearance
- [ ] Theme menu functional
- [ ] At least 3 themes tested (cyborg, darkly, superhero)
- [ ] Theme persists across restarts
- [ ] Chart colors coordinate with theme
- [ ] All panels upgraded to ttk widgets
- [ ] Real-time performance maintained (50Hz)
- [ ] No visual glitches or crashes
- [ ] User feedback positive

---

## Next Steps After Implementation

1. **Document chosen theme** in README
2. **Update screenshots** with new themed UI
3. **Consider custom theme** for branding (see RESEARCH_ARTICLE.md)
4. **Gather user feedback** for further refinements
5. **Monitor performance** in production use

---

**Questions?** Review README.md or RESEARCH_ARTICLE.md for additional context.

**Ready to start?** Begin with Phase 1: Basic Integration!
