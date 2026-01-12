# Assets Directory

This directory contains assets for the Fisherman gaming dashboard:

## Contents:

### Icons (Future)
- `fish_icon.png` - Fish icon for UI
- `trophy_icon.png` - Trophy for achievements
- `star_icon.png` - Star for ratings
- `clock_icon.png` - Clock for time metrics

### Sounds (Future)
- `catch.wav` - Sound when catching a fish
- `bite.wav` - Sound when fish bites
- `achievement.wav` - Achievement unlocked sound
- `level_up.wav` - Level up sound

### Fonts (Future)
- `game_font.ttf` - Gaming style font

## Note
Currently, the dashboard uses:
- Built-in emoji for icons (🐟, 🏆, ⭐, ⏱️, etc.)
- System beep sounds via winsound module
- Default system fonts

To add custom assets:
1. Place files in this directory
2. Update the respective modules (dashboard.py, sounds.py, ui_theme.py)
3. Update config_ui.json with asset paths
