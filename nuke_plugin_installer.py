# -*- coding: utf-8 -*-
"""
Nuke Plugin Installer - 安装 .gizmo / .nk / .py 插件到 Nuke 用户目录
支持添加到顶部菜单或节点工具栏
修复：自动检测 .py 插件的入口函数，无需手动填写
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


# ==================== PySide 版本 ====================
if not USE_TK:
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

            # 目标目录
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

            # 文件列表
            layout.addWidget(QtWidgets.QLabel("要安装的插件文件:"))
            self.file_list_widget = QtWidgets.QListWidget()
            self.file_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            self.file_list_widget.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
            self.file_list_widget.setAcceptDrops(True)
            layout.addWidget(self.file_list_widget)

            # 按钮行
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

            # 菜单选项
            self.menu_group = QtWidgets.QGroupBox("菜单选项")
            menu_layout = QtWidgets.QVBoxLayout(self.menu_group)

            self.generate_menu_cb = QtWidgets.QCheckBox("自动生成菜单项")
            self.generate_menu_cb.setChecked(True)
            menu_layout.addWidget(self.generate_menu_cb)

            # 菜单位置选择
            location_layout = QtWidgets.QHBoxLayout()
            location_layout.addWidget(QtWidgets.QLabel("菜单位置:"))
            self.menu_location_combo = QtWidgets.QComboBox()
            self.menu_location_combo.addItems(["顶部菜单栏 (Nuke)", "节点工具栏 (Nodes)"])
            self.menu_location_combo.setCurrentIndex(0)
            location_layout.addWidget(self.menu_location_combo)
            menu_layout.addLayout(location_layout)

            # 分类和名称
            cat_layout = QtWidgets.QHBoxLayout()
            cat_layout.addWidget(QtWidgets.QLabel("菜单分类:"))
            self.menu_category_edit = QtWidgets.QLineEdit()
            self.menu_category_edit.setPlaceholderText("例如: MyTools / AOV / ...")
            cat_layout.addWidget(self.menu_category_edit)
            menu_layout.addLayout(cat_layout)

            name_layout = QtWidgets.QHBoxLayout()
            name_layout.addWidget(QtWidgets.QLabel("菜单项名称 (留空则使用文件名):"))
            self.menu_name_edit = QtWidgets.QLineEdit()
            name_layout.addWidget(self.menu_name_edit)
            menu_layout.addLayout(name_layout)

            layout.addWidget(self.menu_group)

            # 操作按钮
            action_layout = QtWidgets.QHBoxLayout()
            self.install_btn = QtWidgets.QPushButton("安装选中文件")
            self.install_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            self.install_btn.clicked.connect(self.install_selected)
            action_layout.addWidget(self.install_btn)
            self.install_all_btn = QtWidgets.QPushButton("安装全部")
            self.install_all_btn.clicked.connect(self.install_all)
            action_layout.addWidget(self.install_all_btn)
            layout.addLayout(action_layout)

            # 状态栏
            self.status_label = QtWidgets.QLabel("就绪")
            layout.addWidget(self.status_label)

            self.setStyleSheet("""
                QGroupBox { font-weight: bold; margin-top: 10px; }
                QListWidget { border: 1px solid #ccc; min-height: 150px; }
                QPushButton { padding: 6px; }
            """)

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
            """检测 Python 文件中可能作为入口的函数名"""
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
            installed_files = []

            for src in files:
                src_path = Path(src)
                if not src_path.exists():
                    error_count += 1
                    self.status_label.setText(f"文件不存在: {src}")
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
                    installed_files.append(dst)
                except Exception as e:
                    error_count += 1
                    self.status_label.setText(f"复制失败: {src} -> {e}")

            if self.generate_menu_cb.isChecked():
                self._generate_menu_entries(installed_files, target_dir)

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
                    command = f"nuke.createNode('{node_name}')"
                    menu_label = custom_name if custom_name else node_name
                    entries.append((menu_label, command, category, is_node_menu))
                elif ext == '.py':
                    module_name = file_path.stem
                    # 自动检测入口函数
                    candidates = self._detect_entry_functions(str(file_path))
                    entry_func = None
                    if candidates:
                        if len(candidates) == 1:
                            entry_func = candidates[0]
                        else:
                            # 多个候选，弹出选择对话框
                            func, ok = QtWidgets.QInputDialog.getItem(
                                self, "选择入口函数", f"插件 {module_name} 有多个可能的入口函数，请选择:",
                                candidates, 0, False
                            )
                            if ok and func:
                                entry_func = func
                    if not entry_func:
                        # 如果没检测到，让用户手动输入
                        entry_func, ok = QtWidgets.QInputDialog.getText(
                            self, "入口函数", f"未检测到入口函数，请手动输入 {module_name} 的入口函数名:",
                            text="show"
                        )
                        if not ok or not entry_func:
                            entry_func = "show"
                    # 使用双引号外部，单引号内部，避免语法错误
                    command = f'import {module_name}; {module_name}.{entry_func}()'
                    menu_label = custom_name if custom_name else module_name
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
                # 先尝试删除旧菜单项（避免重复）
                new_code += f"try:\n"
                if is_node:
                    new_code += f"    toolbar.findItem('{menu_path}').delete()\n"
                else:
                    new_code += f"    menubar.findItem('{menu_path}').delete()\n"
                new_code += f"except:\n    pass\n"
                # 添加新命令
                if is_node:
                    new_code += f"toolbar.addCommand('{menu_path}', '{cmd}')\n"
                else:
                    new_code += f"menubar.addCommand('{menu_path}', '{cmd}')\n"
            new_code += marker_end

            final_code = existing_code.rstrip() + "\n\n" + new_code
            with open(menu_py_path, 'w', encoding='utf-8') as f:
                f.write(final_code)

            self.status_label.setText(f"已更新 menu.py: {menu_py_path}")

    def show_installer():
        global _installer_win
        try:
            _installer_win.close()
            _installer_win.deleteLater()
        except:
            pass
        _installer_win = PluginInstaller()
        _installer_win.show()

# ==================== Tkinter 版本（简略） ====================
else:
    def show_installer():
        import tkinter.messagebox as msgbox
        msgbox.showinfo("提示", "PySide2 未安装，请安装 PySide2 后使用本工具。")

def main():
    show_installer()

if __name__ == "__main__":
    main()
