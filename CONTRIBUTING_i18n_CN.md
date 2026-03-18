# h3sed 中文本地化实现说明

## 概述

本实现为 h3sed 添加了完整的中文本地化支持，翻译覆盖所有UI元素，包括：
- 主要属性（攻击力、防御力、法术攻击力、法术防御力）
- 技能名称和技能等级
- 生物/军队单位
- 装备/物品
- 法术
- 魔法卷轴（动态翻译）

## 实现方案

### 核心设计：UI层翻译

本实现采用UI层翻译方案，而非修改核心数据结构。这种方案的优势：

1. **保持数据完整性** - 核心游戏数据结构保持不变
2. **关注点分离** - 翻译逻辑独立在单独模块中
3. **易于扩展** - 添加其他语言非常简单
4. **避免循环导入** - i18n模块完全自包含

### 架构设计

```
i18n.py (翻译核心)
    │
    │  ZH_LABELS = {...}  # 翻译字典
    │  zh(text)           # 翻译函数
    │
    ▼
gui.py (UI渲染层)
    │
    │  from .i18n import zh
    │  wx.StaticText(panel, label=zh("Attack"))
    │  c2.SetItems([zh(c) for c in choices])
    │
    ▼
中文界面
```

## 文件变更

### 新增文件
- `h3sed/i18n.py` - 翻译模块，包含 ZH_LABELS 字典和 zh() 函数

### 修改文件
- `gui.py` - 导入 zh() 并应用到所有UI文本元素
- `hero/gui.py` - 导入 zh() 用于标签页标题翻译

## 使用方法

中文翻译自动应用，无需配置。

## 添加其他语言

添加其他语言支持（如俄语）只需：

1. 创建 `i18n_ru.py` 文件：
```python
RU_LABELS = {
    "Attack": "Атака",
    "Defense": "Защита",
    # ... 其他翻译
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

2. 在 `gui.py` 中添加语言选择：
```python
from .i18n import zh    # 中文
from .i18n_ru import ru # 俄文

# 根据配置选择翻译函数
def t(text):
    lang = conf.Settings.get("language", "en")
    if lang == "zh": return zh(text)
    if lang == "ru": return ru(text)
    return text
```

## 翻译覆盖范围

| 类别 | 数量 | 示例 |
|------|------|------|
| UI标签 | 50+ | "Attack" → "攻击力" |
| 技能名称 | 28 | "Archery" → "箭术" |
| 技能等级 | 3 | "Basic" → "基础" |
| 生物名称 | 118 | "Black Dragon" → "黑龙" |
| 法术名称 | 70+ | "Meteor Shower" → "流星火雨" |
| 装备名称 | 120+ | "Angel Wings" → "天使之翼" |
| 魔法卷轴 | 动态 | "Spell Scroll: Fireball" → "魔法卷轴: 火球术" |

## 技术要点

### 动态名称处理

部分物品具有动态名称，如 "Spell Scroll: Fireball"。zh() 函数的处理方式：

```python
def zh(text):
    if text is None:
        return None
    if text in ZH_LABELS:
        return ZH_LABELS[text]
    # 处理动态名称
    if text.startswith("Spell Scroll: "):
        spell_name = text[14:]
        return "魔法卷轴: " + ZH_LABELS.get(spell_name, spell_name)
    return text
```

### 避免循环导入

i18n.py 模块完全自包含，不导入任何其他 h3sed 模块，从而避免循环导入问题。

## 测试方法

1. 打开任意英雄无敌3存档
2. 浏览英雄标签页（主要属性、技能、军队、装备、背包、法术）
3. 所有文本应显示为中文

## 致谢

中文翻译实现由社区贡献。

---

## 给原作者的贡献说明

### 改动摘要

本贡献为 h3sed 添加了完整的中文（简体）本地化支持，采用 UI 层翻译方案，对原有代码侵入性最小。

### 技术方案

**设计理念**：在 UI 渲染层进行翻译，而非修改核心数据结构。

**优势**：
- 核心游戏数据结构保持不变，确保存档读写兼容性
- 翻译逻辑完全独立，便于维护和扩展
- 无循环导入问题，模块依赖清晰

### 文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `h3sed/i18n.py` | 新增 | 翻译模块，包含 400+ 条中文翻译 |
| `gui.py` | 修改 | 导入 zh() 函数，在 build() 中翻译 UI 文本 |
| `hero/gui.py` | 修改 | 导入 zh() 函数，翻译标签页标题 |

### 翻译覆盖

- UI 标签：50+ 条
- 技能名称：28 个
- 技能等级：3 个
- 生物名称：118 个
- 法术名称：70+ 个
- 装备名称：120+ 个
- 魔法卷轴：动态翻译

### 扩展性

此方案易于扩展其他语言。只需：
1. 创建新的翻译模块（如 `i18n_ru.py`）
2. 在配置中添加语言选择逻辑

### 测试验证

已在以下场景测试通过：
- 打开存档文件
- 浏览所有英雄标签页
- 编辑属性、技能、军队、装备、法术等
- 保存存档

### 许可

本贡献遵循项目原有的 MIT 许可证。

---

感谢您开发这个优秀的工具！如果这个功能对项目有帮助，欢迎合并。

---

## Pull Request 模板

**标题**: `feat: Add Chinese (zh-CN) localization support`

**描述**:

```markdown
## 概述

本 PR 为 h3sed 添加了完整的中文（简体）本地化支持。

## 改动内容

- 新增 `h3sed/i18n.py` 翻译模块（400+ 条翻译）
- 修改 `gui.py` 应用 UI 层翻译
- 修改 `hero/gui.py` 翻译标签页标题

## 技术方案

采用 UI 层翻译方案，不修改核心数据结构：
- 保持存档读写兼容性
- 翻译模块完全独立
- 易于扩展其他语言

## 翻译覆盖

- ✅ UI 标签
- ✅ 技能名称和等级
- ✅ 生物名称
- ✅ 法术名称
- ✅ 装备名称
- ✅ 魔法卷轴（动态翻译）

## 测试

- [x] 打开存档正常
- [x] 所有界面显示中文
- [x] 编辑保存正常

## 截图

（可附上翻译效果截图）
```
