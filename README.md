# 🎬 Nuke Plugin Installer

一个轻量但强大的 **Nuke 插件安装工具**，用于快速安装 `.gizmo / .nk / .py` 插件，并自动生成菜单。

---

# ✨ 功能特点

- 📦 支持插件格式：
  - `.gizmo`
  - `.nk`
  - `.py`

- 🖱️ 拖拽安装（Drag & Drop）

- 📁 自动复制到：
  ```
  ~/.nuke/
  ```

- 🧠 自动生成菜单：
  - 顶部菜单（Nuke）
  - 节点工具栏（Nodes）

- 🧩 自定义：
  - 菜单分类
  - 菜单名称

- ⚠️ 自动处理：
  - 文件覆盖提示
  - menu.py 自动更新（不会重复写入）

---

# 📸 界面说明

主界面包含：

- 安装目录（默认 `.nuke`）
- 插件文件列表
- 菜单选项设置
- 安装按钮

---

# 🚀 使用方法

## ✅ 启动工具

在 Nuke Script Editor 或 `menu.py` 中执行：

```python
import plugin_installer
plugin_installer.main()
```

---

## 📦 安装插件

### 方法 1：拖拽

直接把插件文件拖入窗口

---

### 方法 2：手动添加

1. 点击【添加文件】
2. 选择插件文件
3. 点击【安装选中】或【安装全部】

---

## ⚙️ 菜单设置

| 选项 | 说明 |
|------|------|
| 自动生成菜单 | 是否写入 menu.py |
| 菜单位置 | Nuke / Nodes |
| 菜单分类 | 如 `MyTools/FX` |
| 菜单名称 | 可自定义 |

---

# 📁 安装位置

默认目录：

Windows：
```
C:/Users/你的用户名/.nuke/
```

macOS / Linux：
```
/Users/你的用户名/.nuke/
```

---

# 🧠 工作原理

```
选择文件
   ↓
复制到 ~/.nuke
   ↓
更新 menu.py
   ↓
重启 Nuke 生效
```

---

# 🧾 menu.py 自动生成示例

```python
# === Nuke Plugin Installer Auto-Generated Menu Items ===
import nuke
menubar = nuke.menu('Nuke')
menubar.addCommand('MyTools/MyNode', 'nuke.createNode("MyNode")')
# === End Auto-Generated ===
```

---

# ⚠️ 注意事项

- 安装完成后 **必须重启 Nuke**
- `.nk` 文件不会自动生成菜单（仅复制）
- `.py` 插件建议包含：

```python
def show():
    ...
```

否则菜单不会自动弹出 UI

---

# 🧩 支持的菜单行为

| 类型 | 行为 |
|------|------|
| gizmo | 创建节点 |
| py | import + show() |
| nk | 仅复制 |

---

# 🛠️ 依赖

优先使用：

```
PySide2
```

如果没有则自动降级：

```
Tkinter（简化版 UI）
```

---

# 📂 推荐目录结构

```
.nuke/
 ├── plugin_installer.py
 ├── menu.py
 ├── MyTool.gizmo
 └── MyScript.py
```

---

# 🔧 可扩展方向

- 🔄 插件版本管理
- 📦 自动解压 zip 插件
- 🌐 插件仓库（远程下载）
- 🎨 UI 美化（QSS）
- 🔌 插件启用 / 禁用系统

---

# 👤 作者

**LiaoLiao**

---

# 🚀 一句话总结

👉 一个让 Nuke 插件安装从「手动复制」升级为「一键自动化」的工具
