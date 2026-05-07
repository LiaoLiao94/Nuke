# -*- coding: utf-8 -*-
"""
Nuke Plugin Installer - 安装 / 卸载 .gizmo / .nk / .py 插件
支持层级菜单、节点位置优化、自动菜单清理
更新：.gizmo 默认在鼠标位置创建节点
"""

import nuke
import nukescripts
import os
import shutil
import re
from pathlib import Path

try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    USE_TK = True
else:
    USE_TK = False


def get_nuke_user_dir():
    home = Path.home()
    nuke_dir = home / ".nuke"
    if not nuke_dir.exists():
        nuke_dir.mkdir(parents=True, exist_ok=True)
    return str(nuke_dir)


# ==================== 卸载对话框 ====================
if not USE_TK:
    class UninstallDialog(QtWidgets.QDialog):
        def __init__(self, target_dir, parent=None):
            super(UninstallDialog, self).__init__(parent)
            self.setWindowTitle("卸载已安装插件")
            self.setMinimumSize(700, 450)
            self.target_dir = Path(target_dir)
            self.plugins = []
            self.init_ui()
            self.scan_installed()

        def init_ui(self):
            layout = QtWidgets.QVBoxLayout(self)

            self.table = QtWidgets.QTableWidget(0, 4)
            self.table.setHorizontalHeaderLabels(["文件名", "类型", "安装路径", "菜单状态"])
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            self.table.horizontalHeader().setStretchLastSection(True)
            self.table.setColumnWidth(0, 150)
            self.table.setColumnWidth(1, 60)
            self.table.setColumnWidth(2, 350)
            layout.addWidget(self.table)

            btn_layout = QtWidgets.QHBoxLayout()
            self.uninstall_btn = QtWidgets.QPushButton("卸载选中")
            self.uninstall_btn.clicked.connect(self.uninstall_selected)
            self.uninstall_btn.setStyleSheet("background-color: #d9534f; color: white;")
            btn_layout.addWidget(self.uninstall_btn)
            self.refresh_btn = QtWidgets.QPushButton("刷新列表")
            self.refresh_btn.clicked.connect(self.scan_installed)
            btn_layout.addWidget(self.refresh_btn)
            layout.addLayout(btn_layout)

            self.status_label = QtWidgets.QLabel("")
            layout.addWidget(self.status_label)

        def scan_installed(self):
            self.plugins.clear()
            self.table.setRowCount(0)

            for ext in ['*.gizmo', '*.py', '*.nk']:
                for file in self.target_dir.glob(ext):
                    if file.is_file():
                        self.plugins.append({
                            'name': file.name,
                            'type': ext[1:],
                            'path': str(file),
                            'rel_path': str(file.relative_to(self.target_dir))
                        })

            menu_entries = self._get_menu_entries()
            for p in self.plugins:
                base_name = os.path.splitext(p['name'])[0]
                has_menu = any(base_name in entry for entry in menu_entries)
                row = self.table.rowCount()
                self.table.insertRow(row)

                name_item = QtWidgets.QTableWidgetItem(p['name'])
                name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row, 0, name_item)

                type_item = QtWidgets.QTableWidgetItem(p['type'])
                type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row, 1, type_item)

                path_item = QtWidgets.QTableWidgetItem(p['path'])
                path_item.setFlags(path_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row, 2, path_item)

                menu_status = "有菜单" if has_menu else "无菜单"
                menu_item = QtWidgets.QTableWidgetItem(menu_status)
                menu_item.setFlags(menu_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.table.setItem(row, 3, menu_item)

            self.status_label.setText(f"共找到 {len(self.plugins)} 个已安装插件")

        def _get_menu_entries(self):
            menu_py = self.target_dir / "menu.py"
            if not menu_py.exists():
                return []
            with open(menu_py, 'r', encoding='utf-8') as f:
                content = f.read()
            marker_start = "# === Nuke Plugin Installer Auto-Generated Menu Items ==="
            marker_end = "# === End Auto-Generated ==="
            pattern = re.escape(marker_start) + r"\n(.*?)" + re.escape(marker_end)
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                return []
            block = match.group(1)
            commands = re.findall(r"addCommand\('(.+?)',\s*'(.+?)'\)", block)
            return [cmd for _, cmd in commands]

        def uninstall_selected(self):
            selected_rows = set()
            for idx in self.table.selectedIndexes():
                selected_rows.add(idx.row())
            if not selected_rows:
                QtWidgets.QMessageBox.warning(self, "提示", "请先选择要卸载的插件")
                return

            reply = QtWidgets.QMessageBox.question(
                self, "确认卸载",
                f"将删除选中的 {len(selected_rows)} 个插件文件并清理菜单，是否继续？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

            removed = []
            for row in sorted(selected_rows, reverse=True):
                plugin = self.plugins[row]
                try:
                    os.remove(plugin['path'])
                    removed.append(plugin)
                except Exception as e:
                    print(f"删除失败 {plugin['path']}: {e}")

            if removed:
                self._clean_menu_entries(removed)

            self.scan_installed()
            QtWidgets.QMessageBox.information(self, "完成", f"已卸载 {len(removed)} 个插件，请重启 Nuke 使更改生效")

        def _clean_menu_entries(self, removed_plugins):
            menu_py = self.target_dir / "menu.py"
            if not menu_py.exists():
                return
            with open(menu_py, 'r', encoding='utf-8') as f:
                content = f.read()

            marker_start = "# === Nuke Plugin Installer Auto-Generated Menu Items ==="
            marker_end = "# === End Auto-Generated ==="
            pattern = re.escape(marker_start) + r"\n(.*?)" + re.escape(marker_end)
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                return

            block = match.group(1)
            lines = block.splitlines(keepends=True)
            new_lines = []
            removed_bases = {os.path.splitext(p['name'])[0] for p in removed_plugins}

            for line in lines:
                keep = True
                for base in removed_bases:
                    if f"createNode('{base}')" in line or f'createNode("{base}")' in line:
                        keep = False
                        break
                    if f"import {base};" in line or f"import {base} " in line:
                        keep = False
                        break
                    if f"scriptReadFile(r" in line and base in line:
                        keep = False
                        break
                if keep:
                    new_lines.append(line)

            if new_lines:
                new_block = "".join(new_lines)
                new_content = content[:match.start(1)] + new_block + content[match.end(1):]
            else:
                new_content = content[:match.start()] + content[match.end():]

            with open(menu_py, 'w', encoding='utf-8') as f:
                f.write(new_content)


# ==================== 安装主界面 ====================
    class PluginInstaller(QtWidgets.QDialog):
        def __init__(self, parent=None):
            try:
                parent = parent or nukescripts.get_main_window()
            except:
                parent = None
            super(PluginInstaller, self).__init__(parent)
            self.setWindowTitle("Nuke 插件安装工具 (自动检测入口)")
            self.setMinimumSize(650, 550)
            self.setAcceptDrops(True)
            self.file_list = []
            self.init_ui()
            self.load_settings()

        def init_ui(self):
            layout = QtWidgets.QVBoxLayout(self)

            dir_layout = QtWidgets.QHBoxLayout()
            dir_layout.addWidget(QtWidgets.QLabel("安装目录:"))
            self.target_dir_edit = QtWidgets.QLineEdit()
            self.target_dir_edit.setText(get_nuke_user_dir())
            self.target_dir_edit.setReadOnly(True)
            dir_layout.addWidget(self.target_dir_edit)
            self.browse_dir_btn = QtWidgets.QPushButton("浏览...")
            self.browse_dir_btn.clicked.connect(self.browse_target_dir)
            dir_layout.addWidget(self.browse_dir_btn)
            layout.addLayout(dir_layout)

            layout.addWidget(QtWidgets.QLabel("要安装的插件文件:"))
            self.file_list_widget = QtWidgets.QListWidget()
            self.file_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            self.file_list_widget.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
            self.file_list_widget.setAcceptDrops(True)
            layout.addWidget(self.file_list_widget)

            btn_layout = QtWidgets.QHBoxLayout()
            self.add_files_btn = QtWidgets.QPushButton("添加文件")
            self.add_files_btn.clicked.connect(self.add_files)
            btn_layout.addWidget(self.add_files_btn)
            self.remove_selected_btn = QtWidgets.QPushButton("移除选中")
            self.remove_selected_btn.clicked.connect(self.remove_selected)
            btn_layout.addWidget(self.remove_selected_btn)
            self.clear_all_btn = QtWidgets.QPushButton("清空列表")
            self.clear_all_btn.clicked.connect(self.clear_all)
            btn_layout.addWidget(self.clear_all_btn)
            layout.addLayout(btn_layout)

            self.menu_group = QtWidgets.QGroupBox("菜单选项")
            menu_layout = QtWidgets.QVBoxLayout(self.menu_group)

            self.generate_menu_cb = QtWidgets.QCheckBox("自动生成菜单项")
            self.generate_menu_cb.setChecked(True)
            menu_layout.addWidget(self.generate_menu_cb)

            location_layout = QtWidgets.QHBoxLayout()
            location_layout.addWidget(QtWidgets.QLabel("菜单位置:"))
            self.menu_location_combo = QtWidgets.QComboBox()
            self.menu_location_combo.addItems(["顶部菜单栏 (Nuke)", "节点工具栏 (Nodes)"])
            self.menu_location_combo.setCurrentIndex(0)
            location_layout.addWidget(self.menu_location_combo)
            menu_layout.addLayout(location_layout)

            cat_layout = QtWidgets.QHBoxLayout()
            cat_layout.addWidget(QtWidgets.QLabel("菜单分类 (子菜单名称):"))
            self.menu_category_edit = QtWidgets.QLineEdit()
            self.menu_category_edit.setPlaceholderText("例如: NK / MyTools / Gizmos")
            cat_layout.addWidget(self.menu_category_edit)
            menu_layout.addLayout(cat_layout)

            name_layout = QtWidgets.QHBoxLayout()
            name_layout.addWidget(QtWidgets.QLabel("菜单项名称 (留空则使用文件名):"))
            self.menu_name_edit = QtWidgets.QLineEdit()
            name_layout.addWidget(self.menu_name_edit)
            menu_layout.addLayout(name_layout)

            layout.addWidget(self.menu_group)

            action_layout = QtWidgets.QHBoxLayout()
            self.install_btn = QtWidgets.QPushButton("安装选中文件")
            self.install_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            self.install_btn.clicked.connect(self.install_selected)
            action_layout.addWidget(self.install_btn)
            self.install_all_btn = QtWidgets.QPushButton("安装全部")
            self.install_all_btn.clicked.connect(self.install_all)
            action_layout.addWidget(self.install_all_btn)
            self.uninstall_btn = QtWidgets.QPushButton("卸载已安装插件")
            self.uninstall_btn.clicked.connect(self.open_uninstaller)
            action_layout.addWidget(self.uninstall_btn)
            layout.addLayout(action_layout)

            self.status_label = QtWidgets.QLabel("就绪")
            layout.addWidget(self.status_label)

            self.setStyleSheet("""
                QGroupBox { font-weight: bold; margin-top: 10px; }
                QListWidget { border: 1px solid #ccc; min-height: 150px; }
                QPushButton { padding: 6px; }
            """)

        def open_uninstaller(self):
            dlg = UninstallDialog(self.target_dir_edit.text(), self)
            dlg.exec_()

        def dragEnterEvent(self, event):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()

        def dropEvent(self, event):
            urls = event.mimeData().urls()
            files = [u.toLocalFile() for u in urls if u.isLocalFile()]
            self.add_files_from_paths(files)

        def add_files(self):
            file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
                self, "选择插件文件", "",
                "插件文件 (*.gizmo *.nk *.py);;所有文件 (*.*)"
            )
            if file_paths:
                self.add_files_from_paths(file_paths)

        def add_files_from_paths(self, paths):
            for p in paths:
                if p not in self.file_list:
                    self.file_list.append(p)
                    self.file_list_widget.addItem(p)
            self.status_label.setText(f"已添加 {len(paths)} 个文件，总计 {len(self.file_list)} 个")

        def remove_selected(self):
            for item in self.file_list_widget.selectedItems():
                path = item.text()
                if path in self.file_list:
                    self.file_list.remove(path)
                self.file_list_widget.takeItem(self.file_list_widget.row(item))
            self.status_label.setText(f"已移除选中，剩余 {len(self.file_list)} 个")

        def clear_all(self):
            self.file_list.clear()
            self.file_list_widget.clear()
            self.status_label.setText("列表已清空")

        def browse_target_dir(self):
            dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择安装目录", self.target_dir_edit.text())
            if dir_path:
                self.target_dir_edit.setText(dir_path)

        def load_settings(self):
            pass

        def save_settings(self):
            pass

        def install_selected(self):
            selected = [item.text() for item in self.file_list_widget.selectedItems()]
            if not selected:
                QtWidgets.QMessageBox.warning(self, "提示", "请先选择要安装的文件")
                return
            self._install_files(selected)

        def install_all(self):
            if not self.file_list:
                QtWidgets.QMessageBox.warning(self, "提示", "文件列表为空")
                return
            self._install_files(self.file_list)

        def _detect_entry_functions(self, file_path):
            candidates = []
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                patterns = [
                    r'^def\s+(show)\s*\(',
                    r'^def\s+(main)\s*\(',
                    r'^def\s+(show_ui)\s*\(',
                    r'^def\s+(open_window)\s*\(',
                    r'^def\s+(launch)\s*\(',
                    r'^def\s+(show_dialog)\s*\(',
                    r'^def\s+(show_repath_dialog)\s*\(',
                ]
                for pat in patterns:
                    matches = re.findall(pat, content, re.MULTILINE)
                    candidates.extend(matches)
            except:
                pass
            return list(set(candidates))

        def _install_files(self, files):
            target_dir = self.target_dir_edit.text().strip()
            if not target_dir:
                QtWidgets.QMessageBox.warning(self, "错误", "请设置有效的安装目录")
                return
            target_path = Path(target_dir)
            if not target_path.exists():
                try:
                    target_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "错误", f"无法创建目录: {e}")
                    return

            success_count = 0
            skipped_count = 0
            error_count = 0
            installed_all = []

            for src in files:
                src_path = Path(src)
                if not src_path.exists():
                    error_count += 1
                    continue

                dst = target_path / src_path.name

                if dst.exists():
                    reply = QtWidgets.QMessageBox.question(
                        self, "文件已存在",
                        f"{dst.name} 已存在，是否覆盖？",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel
                    )
                    if reply == QtWidgets.QMessageBox.Cancel:
                        continue
                    elif reply == QtWidgets.QMessageBox.No:
                        skipped_count += 1
                        continue

                try:
                    shutil.copy2(src, dst)
                    success_count += 1
                    installed_all.append(dst)
                except Exception as e:
                    error_count += 1
                    self.status_label.setText(f"复制失败: {src} -> {e}")

            if self.generate_menu_cb.isChecked() and installed_all:
                self._generate_menu_entries(installed_all, target_dir)

            msg = f"安装完成: 成功 {success_count}, 跳过 {skipped_count}, 失败 {error_count}\n请重启 Nuke 以使菜单生效。"
            self.status_label.setText(msg)
            QtWidgets.QMessageBox.information(self, "完成", msg)

        def _generate_menu_entries(self, installed_files, target_dir):
            menu_py_path = Path(target_dir) / "menu.py"
            category = self.menu_category_edit.text().strip()
            custom_name = self.menu_name_edit.text().strip()
            location = self.menu_location_combo.currentText()
            is_node_menu = "节点工具栏" in location

            entries = []
            for file_path in installed_files:
                ext = file_path.suffix.lower()
                if ext == '.gizmo':
                    node_name = file_path.stem
                    # 修复：添加 inpanel=False 使节点创建在鼠标位置附近
                    command = f"nuke.createNode('{node_name}', inpanel=False)"
                    menu_label = custom_name if custom_name else node_name
                    entries.append((menu_label, command, category, is_node_menu))
                elif ext == '.py':
                    module_name = file_path.stem
                    candidates = self._detect_entry_functions(str(file_path))
                    entry_func = None
                    if candidates:
                        if len(candidates) == 1:
                            entry_func = candidates[0]
                        else:
                            func, ok = QtWidgets.QInputDialog.getItem(
                                self, "选择入口函数", f"插件 {module_name} 有多个可能的入口函数，请选择:",
                                candidates, 0, False
                            )
                            if ok and func:
                                entry_func = func
                    if not entry_func:
                        entry_func, ok = QtWidgets.QInputDialog.getText(
                            self, "入口函数", f"未检测到入口函数，请手动输入 {module_name} 的入口函数名:",
                            text="show"
                        )
                        if not ok or not entry_func:
                            entry_func = "show"
                    command = f'import {module_name}; {module_name}.{entry_func}()'
                    menu_label = custom_name if custom_name else module_name
                    entries.append((menu_label, command, category, is_node_menu))
                elif ext == '.nk':
                    command = f'nuke.scriptReadFile(r"{file_path.as_posix()}")'
                    menu_label = custom_name if custom_name else file_path.stem
                    entries.append((menu_label, command, category, is_node_menu))

            if not entries:
                return

            existing_code = ""
            if menu_py_path.exists():
                with open(menu_py_path, 'r', encoding='utf-8') as f:
                    existing_code = f.read()

            marker_start = "# === Nuke Plugin Installer Auto-Generated Menu Items ===\n"
            marker_end = "# === End Auto-Generated ===\n"

            pattern = re.escape(marker_start) + r".*?" + re.escape(marker_end)
            existing_code = re.sub(pattern, "", existing_code, flags=re.DOTALL)

            new_code = marker_start
            new_code += "import nuke\n"
            if is_node_menu:
                new_code += "toolbar = nuke.menu('Nodes')\n"
            else:
                new_code += "menubar = nuke.menu('Nuke')\n"

            for label, cmd, cat, is_node in entries:
                if cat:
                    menu_path = f"{cat}/{label}"
                else:
                    menu_path = label
                new_code += f"try:\n"
                if is_node:
                    new_code += f"    toolbar.findItem('{menu_path}').delete()\n"
                else:
                    new_code += f"    menubar.findItem('{menu_path}').delete()\n"
                new_code += f"except:\n    pass\n"
                if is_node:
                    new_code += f"toolbar.addCommand('{menu_path}', '{cmd}')\n"
                else:
                    new_code += f"menubar.addCommand('{menu_path}', '{cmd}')\n"
            new_code += marker_end

            final_code = existing_code.rstrip() + "\n\n" + new_code
            with open(menu_py_path, 'w', encoding='utf-8') as f:
                f.write(final_code)

            self.status_label.setText(f"已更新 menu.py: {menu_py_path}")


# ==================== 入口函数 ====================
    def show_installer():
        global _installer_win
        try:
            _installer_win.close()
            _installer_win.deleteLater()
        except:
            pass
        _installer_win = PluginInstaller()
        _installer_win.show()

else:
    def show_installer():
        import tkinter.messagebox as msgbox
        msgbox.showinfo("提示", "PySide2 未安装，请安装 PySide2 后使用本工具。")

def main():
    show_installer()

if __name__ == "__main__":
    main()
