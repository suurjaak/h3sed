# h3sed 项目架构与翻译修改总结

## 一、项目整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           h3sed 应用层                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  main.py          - 程序入口，负责启动GUI或CLI                           │
│  gui.py           - 主窗口(MainWindow)和存档页面(SavefilePage)          │
│  guibase.py       - GUI基础类，日志处理器                                 │
│  conf.py          - 配置文件                                             │
│  i18n.py          - 国际化翻译模块 (新增)                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           数据层                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  metadata.py      - 游戏数据存储 (Savefile, Store类)                    │
│  templates.py     - HTML/文本模板                                        │
│  version/         - 不同版本(ROE, AB, SOD, HOTA)的数据适配              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           英雄属性层 (hero/)                             │
├─────────────────────────────────────────────────────────────────────────┤
│  hero/__init__.py  - 英雄数据类定义 (Hero, Army, Skills等)              │
│  hero/gui.py       - 英雄插件管理器 (HeroPlugin)                        │
│  hero/profile.py   - 英雄阵营                                           │
│  hero/stats.py     - 英雄主要属性 (攻击/防御/力量/知识)                   │
│  hero/skills.py    - 英雄技能                                           │
│  hero/army.py      - 英雄部队                                           │
│  hero/equipment.py - 英雄装备                                           │
│  hero/inventory.py - 英雄背包                                           │
│  hero/spells.py    - 英雄法术                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           公共库 (lib/)                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  lib/util.py      - 工具函数 (AttrDict, OrderedSet, SlotsDict等)        │
│  lib/controls.py  - 自定义wx控件                                        │
│  lib/wx_accel.py  - 键盘快捷键                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心数据流关系

### 1. UI与数据的关系

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   MainWindow     │ ───▶ │  SavefilePage    │ ───▶ │   HeroPlugin     │
│   (主窗口)       │      │   (存档页面)      │      │   (英雄插件)     │
└──────────────────┘      └──────────────────┘      └──────────────────┘
         │                                                   │
         │                                                   ▼
         │                                        ┌──────────────────────┐
         │                                        │   各个属性插件        │
         │                                        │  - StatsPlugin       │
         │                                        │  - SkillsPlugin      │
         │                                        │  - ArmyPlugin        │
         │                                        │  - EquipmentPlugin   │
         │                                        │  - InventoryPlugin   │
         │                                        │  - SpellsPlugin      │
         │                                        └──────────────────────┘
         │                                                   │
         ▼                                                   ▼
┌──────────────────┐                           ┌──────────────────────┐
│  metadata.Store  │ ◀─────────────────────────│   Hero 数据类        │
│  (游戏数据)      │         读写               │ (Hero/Army/Skills)  │
└──────────────────┘                           └──────────────────────┘
```

### 2. 翻译系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          i18n.py (翻译核心)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  ZH_LABELS = {                                                          │
│      "Attack": "攻击力",                                                 │
│      "Defense": "防御力",                                                │
│      "Spell Power": "法术攻击力",                                        │
│      "Knowledge": "法术防御力",                                          │
│      ... (技能/生物/法术/装备等所有翻译)                                  │
│  }                                                                      │
│                                                                         │
│  def zh(text):                                                          │
│      """翻译函数 - 支持动态名称如 'Spell Scroll: XXX'"""                 │
│      if text in ZH_LABELS: return ZH_LABELS[text]                      │
│      if text.startswith("Spell Scroll: "):                              │
│          return "魔法卷轴: " + ZH_LABELS.get(spell_name, spell_name)    │
│      return text                                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          gui.py (UI渲染层)                               │
├─────────────────────────────────────────────────────────────────────────┤
│  from .i18n import zh                                                   │
│                                                                         │
│  # 所有UI文本都通过 zh() 函数翻译:                                       │
│  wx.StaticText(panel, label=zh("Attack"))                               │
│  wx.CheckBox(panel, label=zh(spell_name))                               │
│  c2.SetItems([zh(c) for c in choices])                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、关键文件说明

| 文件 | 类/函数 | 作用 |
|------|---------|------|
| **main.py** | `MainApp`, `main()` | 程序入口，启动wxPython应用 |
| **gui.py** | `MainWindow` | 主窗口，包含菜单、工具栏、Notebook |
| **gui.py** | `SavefilePage` | 每个存档文件的标签页 |
| **gui.py** | `build()` | **关键**: 根据plugin.props()生成UI控件，调用zh()翻译 |
| **i18n.py** | `ZH_LABELS` | **新增**: 中文翻译字典 |
| **i18n.py** | `zh()` | **新增**: 翻译函数 |
| **metadata.py** | `Savefile` | 读取/解析存档文件 |
| **metadata.py** | `Store` | 游戏数据存储(技能/生物/法术/装备列表) |
| **hero/__init__.py** | `Hero` | 英雄数据容器 |
| **hero/gui.py** | `HeroPlugin` | 英雄UI插件管理器 |
| **hero/stats.py** | `StatsPlugin` | 攻击/防御/力量/知识属性插件 |

---

## 四、UI构建流程

```
1. MainWindow 创建 SavefilePage
2. SavefilePage 加载 hero/gui.py 的 HeroPlugin
3. HeroPlugin.build() 为每个属性创建插件:
   - 调用 h3sed.hero.PROPERTIES 中的每个模块
   - 每个模块的 props() 返回标签列表
   - 每个模块的 factory() 创建插件实例
   
4. GUI build() 函数根据 props() 生成控件:
   - 所有 label 通过 zh() 函数翻译
   - 所有 choices 列表通过 zh() 翻译
   - 所有 value 通过 zh() 翻译
```

---

## 五、中文翻译实现方案

### 核心思路：UI层翻译

**不修改核心数据结构**，而是在UI渲染时进行翻译：

```python
# gui.py 中的翻译应用

# 1. 静态标签翻译
c1 = wx.StaticText(panel, label=zh(prop.get("label", prop["name"])))

# 2. 下拉选项翻译
choices_zh = [zh(c) if isinstance(c, str) else c for c in choices]
c2.SetItems(choices_zh)

# 3. 复选框列表翻译
for value in prop["choices"]:
    c = wx.CheckBox(panel, label=zh(value))

# 4. 列表项标签翻译
v = zh(v)  # 翻译显示值

# 5. 动态名称翻译 (如 "Spell Scroll: Air Shield")
if text.startswith("Spell Scroll: "):
    return "魔法卷轴: " + ZH_LABELS.get(spell_name, spell_name)
```

### 翻译覆盖范围

| 类别 | 数量 | 示例 |
|------|------|------|
| UI标签 | 50+ | "Attack"→"攻击力", "Skills"→"技能" |
| 技能名称 | 28 | "Archery"→"箭术", "Necromancy"→"招魂术" |
| 技能等级 | 3 | "Basic"→"基础", "Advanced"→"高级", "Expert"→"专家" |
| 生物名称 | 118 | "Black Dragon"→"黑龙", "Titan"→"泰坦" |
| 法术名称 | 70+ | "Meteor Shower"→"流星火雨", "Armageddon"→"末日审判" |
| 装备名称 | 120+ | "Angel Wings"→"天使之翼", "Titan's Cuirass"→"泰坦胸甲" |
| 魔法卷轴 | 动态 | "Spell Scroll: Fireball"→"魔法卷轴: 火球术" |

---

## 六、修改文件清单

### 新增文件

| 文件 | 作用 |
|------|------|
| `h3sed/i18n.py` | 国际化翻译模块，包含所有中文翻译和zh()函数 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `gui.py` | 导入zh函数，在build()中翻译所有UI文本 |
| `hero/gui.py` | 导入zh函数，翻译标签页标题 |
| `hero/stats.py` | 移除硬编码中文，使用翻译系统 |
| `hero/inventory.py` | 移除不需要的导入 |

### gui.py 具体修改位置

| 行号 | 修改内容 |
|------|----------|
| 导入区 | `from .i18n import zh` |
| ~1896 | itemlist 的 label 翻译: `v = zh(v)` |
| ~1901-1908 | itemlist 的 combo 翻译: choices 和 value |
| ~1971 | addable 的 choices 翻译 |
| ~1989 | checklist 的 label 翻译 |
| ~2037-2039 | combo 类型的 choices 和 value 翻译 |

---

## 七、翻译效果

### 主要属性界面
- Attack → 攻击力
- Defense → 防御力
- Spell Power → 法术攻击力
- Knowledge → 法术防御力
- Experience → 经验值
- Level → 等级

### 技能界面
- 技能名称全部翻译 (如: Archery→箭术, Wisdom→智慧)
- 技能等级翻译 (Basic→基础, Advanced→高级, Expert→专家)

### 军队界面
- 所有生物名称翻译 (如: Black Dragon→黑龙, Angel→天使)

### 装备界面
- 所有装备槽位翻译 (如: Helm slot→头盔槽)
- 所有装备名称翻译 (如: Angel Wings→天使之翼)

### 背包界面
- 所有物品名称翻译
- 魔法卷轴动态翻译 (Spell Scroll: XXX→魔法卷轴: XXX中文)

### 法术界面
- 所有法术名称翻译 (如: Meteor Shower→流星火雨, Armageddon→末日审判)

---

## 八、技术要点

### 1. 避免循环导入
使用独立的 `i18n.py` 模块，不依赖其他模块，避免循环导入问题。

### 2. 动态名称处理
```python
# 处理 "Spell Scroll: XXX" 格式的动态名称
if text.startswith("Spell Scroll: "):
    spell_name = text[14:]
    return "魔法卷轴: " + ZH_LABELS.get(spell_name, spell_name)
```

### 3. UI层翻译优势
- 不修改核心数据结构，保持数据完整性
- 翻译与业务逻辑分离
- 便于扩展其他语言

### 4. 翻译函数设计
```python
def zh(text):
    """Translate text to Chinese if available."""
    if text is None:
        return None
    if text in ZH_LABELS:
        return ZH_LABELS[text]
    # 处理动态名称
    if text.startswith("Spell Scroll: "):
        spell_name = text[14:]
        return "魔法卷轴: " + ZH_LABELS.get(spell_name, spell_name)
    return text  # 未找到翻译则返回原文
```

---

## 九、后续扩展建议

1. **添加其他语言**: 创建 `i18n_en.py`, `i18n_ru.py` 等，在 `zh()` 函数中根据配置选择字典

2. **翻译管理**: 可以将翻译数据移至外部JSON文件，便于维护

3. **英雄名称翻译**: 当前英雄名称来自存档数据，如需翻译可扩展 `zh()` 函数

4. **地图名称翻译**: 同上，可根据需要扩展
