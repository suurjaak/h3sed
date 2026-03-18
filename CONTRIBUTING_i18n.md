# Chinese Localization (i18n) Implementation

## Overview

This implementation adds full Chinese localization support to h3sed, translating all UI elements including:
- Main attributes (Attack, Defense, Spell Power, Knowledge)
- Skills and skill levels
- Creatures/Army units
- Artifacts/Equipment
- Spells
- Spell Scrolls (dynamic translation)

## Implementation Approach

### Key Design Decision: UI-Layer Translation

Instead of modifying core data structures, this implementation translates text at the UI rendering layer. This approach:

1. **Preserves data integrity** - Core game data structures remain unchanged
2. **Separates concerns** - Translation logic is isolated in a single module
3. **Easy to extend** - Adding other languages is straightforward
4. **No circular imports** - The i18n module is self-contained

### Architecture

```
i18n.py (Translation Core)
    │
    │  ZH_LABELS = {...}  # Translation dictionary
    │  zh(text)           # Translation function
    │
    ▼
gui.py (UI Layer)
    │
    │  from .i18n import zh
    │  wx.StaticText(panel, label=zh("Attack"))
    │  c2.SetItems([zh(c) for c in choices])
    │
    ▼
Chinese UI
```

## Files Changed

### New Files
- `h3sed/i18n.py` - Translation module with ZH_LABELS dictionary and zh() function

### Modified Files
- `gui.py` - Import zh() and apply to all UI text elements
- `hero/gui.py` - Import zh() for tab title translation

## Usage

The Chinese translation is applied automatically. No configuration needed.

## Adding Other Languages

To add support for another language (e.g., Russian):

1. Create `i18n_ru.py` with:
```python
RU_LABELS = {
    "Attack": "Атака",
    "Defense": "Защита",
    # ... other translations
}

def ru(text):
    if text is None:
        return None
    if text in RU_LABELS:
        return RU_LABELS[text]
    if text.startswith("Spell Scroll: "):
        spell_name = text[14:]
        return "Свиток заклинания: " + RU_LABELS.get(spell_name, spell_name)
    return text
```

2. In `gui.py`, add language selection:
```python
from .i18n import zh    # Chinese
from .i18n_ru import ru # Russian

# Select translation function based on config
def t(text):
    lang = conf.Settings.get("language", "en")
    if lang == "zh": return zh(text)
    if lang == "ru": return ru(text)
    return text
```

## Translation Coverage

| Category | Count | Example |
|----------|-------|---------|
| UI Labels | 50+ | "Attack" → "攻击力" |
| Skills | 28 | "Archery" → "箭术" |
| Skill Levels | 3 | "Basic" → "基础" |
| Creatures | 118 | "Black Dragon" → "黑龙" |
| Spells | 70+ | "Meteor Shower" → "流星火雨" |
| Artifacts | 120+ | "Angel Wings" → "天使之翼" |
| Spell Scrolls | Dynamic | "Spell Scroll: Fireball" → "魔法卷轴: 火球术" |

## Technical Notes

### Dynamic Name Handling

Some items have dynamic names like "Spell Scroll: Fireball". The zh() function handles these:

```python
def zh(text):
    if text is None:
        return None
    if text in ZH_LABELS:
        return ZH_LABELS[text]
    # Handle dynamic names
    if text.startswith("Spell Scroll: "):
        spell_name = text[14:]
        return "魔法卷轴: " + ZH_LABELS.get(spell_name, spell_name)
    return text
```

### No Circular Imports

The i18n.py module is completely self-contained with no imports from other h3sed modules, avoiding circular import issues.

## Testing

1. Open any Heroes3 savegame
2. Navigate to hero tabs (Main attributes, Skills, Army, Equipment, Inventory, Spells)
3. All text should display in Chinese

## Credits

Chinese translation implementation by community contribution.

---

## 给原作者的说明 (Note for Original Author)

这个实现采用了UI层翻译的方案，不修改核心数据结构，对原有代码侵入性最小。主要改动：

1. 新增 `i18n.py` 模块，包含翻译字典和翻译函数
2. 在 `gui.py` 的 `build()` 函数中调用 `zh()` 翻译所有UI文本
3. 在 `hero/gui.py` 中翻译标签页标题

这种设计便于扩展其他语言，只需创建新的翻译模块并在配置中选择即可。

如果这个功能对项目有帮助，欢迎合并到主分支。感谢您开发这个优秀的工具！
