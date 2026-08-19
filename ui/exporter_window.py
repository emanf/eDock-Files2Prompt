import os
import json
from html import escape

from core import paths

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QLineEdit,
    QTextEdit,
    QGroupBox,
    QSplitter,
    QFrame,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QMenu,
)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QGuiApplication

from core.ui.base_ui import eD_UIBase
from core.ui.dialogs.message_dialog import MessageDialog


class ExporterWindow(QMainWindow, eD_UIBase):
    def __init__(self, app_ref=None, parent=None):
        super().__init__(parent)
        self._init_ui_base(app=app_ref, context=getattr(app_ref, "context", None))

        self.setWindowTitle("Files2Prompt")
        self.setMinimumSize(980, 680)

        self.root_path = None
        self._all_files = []
        self._file_checks = {}
        self._filter_text = ""
        self._source_text = ""
        self._preview_parts = []
        self._preview_part_index = 0

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_backup = None
        self._status_style_backup = ""
        self._status_timer.timeout.connect(self._restore_preview_info)

        self._build_ui()
        self._apply_ui_style()
        self._load_last_root()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        central.setLayout(layout)

        header = QFrame()
        header.setObjectName("header")
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(8)
        header.setLayout(header_layout)

        title_row = QHBoxLayout()
        title = QLabel("Files2Prompt")
        title.setObjectName("titleLabel")

        self.lbl_root = QLabel("No root folder selected")
        self.lbl_root.setObjectName("rootLabel")
        self.lbl_root.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_root.setTextInteractionFlags(Qt.TextSelectableByMouse)

        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.lbl_root, 1)
        header_layout.addLayout(title_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.btn_select = QPushButton("Select Root Folder")
        self.btn_select.clicked.connect(self.select_root)

        self.btn_scan = QPushButton("Scan Root")
        self.btn_scan.clicked.connect(self.scan_root)

        self.btn_export = QPushButton("Export")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.clicked.connect(self.export_selected)

        action_row.addWidget(self.btn_select)
        action_row.addWidget(self.btn_scan)
        action_row.addStretch()
        action_row.addWidget(self.btn_export)
        header_layout.addLayout(action_row)

        layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)
        left_panel.setLayout(left_layout)

        files_group = QGroupBox("Files under root")
        files_layout = QVBoxLayout()
        files_layout.setContentsMargins(10, 12, 10, 10)
        files_layout.setSpacing(8)
        files_group.setLayout(files_layout)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter files...")
        self.search_input.textChanged.connect(self.on_search_change)

        self.btn_check_visible = QPushButton("Check Visible")
        self.btn_check_visible.clicked.connect(self.check_visible_files)

        self.btn_uncheck_visible = QPushButton("Uncheck Visible")
        self.btn_uncheck_visible.clicked.connect(self.uncheck_visible_files)

        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.btn_check_visible)
        search_row.addWidget(self.btn_uncheck_visible)
        files_layout.addLayout(search_row)

        self.files_stats = QLabel("Files: 0   Checked: 0")
        self.files_stats.setObjectName("metaLabel")
        files_layout.addWidget(self.files_stats)

        self.files_list = QListWidget()
        self.files_list.setSelectionMode(QListWidget.SingleSelection)
        self.files_list.itemChanged.connect(self._on_item_changed)
        self.files_list.itemDoubleClicked.connect(self._on_file_double_clicked)
        files_layout.addWidget(self.files_list, 1)

        left_layout.addWidget(files_group, 1)

        export_group = QGroupBox("Export List")
        export_layout = QVBoxLayout()
        export_layout.setContentsMargins(10, 12, 10, 10)
        export_layout.setSpacing(8)
        export_group.setLayout(export_layout)

        export_top = QHBoxLayout()

        self.export_stats = QLabel("Entries: 0")
        self.export_stats.setObjectName("metaLabel")

        self.btn_add = QPushButton("Add Checked")
        self.btn_add.clicked.connect(self.add_selected)

        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.clicked.connect(self.remove_selected)

        self.btn_clear_export = QPushButton("Clear")
        self.btn_clear_export.clicked.connect(self.clear_export_list)

        export_top.addWidget(self.export_stats)
        export_top.addStretch()
        export_top.addWidget(self.btn_add)
        export_top.addWidget(self.btn_remove)
        export_top.addWidget(self.btn_clear_export)
        export_layout.addLayout(export_top)

        self.export_list = QListWidget()
        self.export_list.setSelectionMode(QListWidget.MultiSelection)
        export_layout.addWidget(self.export_list, 1)

        left_layout.addWidget(export_group, 1)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)
        right_panel.setLayout(right_layout)

        preview_group = QGroupBox("Export Preview")
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(10, 12, 10, 10)
        preview_layout.setSpacing(8)
        preview_group.setLayout(preview_layout)

        split_row = QHBoxLayout()
        split_row.setSpacing(8)

        self.split_enabled = QCheckBox("Split large output")
        self.split_enabled.setChecked(True)
        self.split_enabled.toggled.connect(self._on_split_settings_changed)

        self.split_mode = QComboBox()
        self.split_mode.addItems(["Characters", "Lines"])
        self.split_mode.currentTextChanged.connect(
            self._on_split_settings_changed
        )

        self.split_limit = QSpinBox()
        self.split_limit.setRange(1, 10000000)
        self.split_limit.setValue(45000)
        self.split_limit.valueChanged.connect(
            self._on_split_settings_changed
        )
        self.split_limit.setToolTip(
            "Maximum characters or lines per copy part"
        )

        self.split_limit_label = QLabel("max characters")
        self.split_limit_label.setObjectName("metaLabel")

        split_row.addWidget(self.split_enabled)
        split_row.addWidget(self.split_mode)
        split_row.addWidget(self.split_limit)
        split_row.addWidget(self.split_limit_label)
        split_row.addStretch()
        preview_layout.addLayout(split_row)

        preview_controls = QHBoxLayout()

        self.btn_preview = QPushButton("Preview")
        self.btn_preview.clicked.connect(self.preview_export)

        self.btn_copy_all = QPushButton("Copy All")
        self.btn_copy_all.clicked.connect(self.copy_all_export)

        self.btn_copy = QPushButton("Copy Part")
        self.btn_copy.clicked.connect(self.show_copy_parts_menu)

        self.preview_info = QLabel("")
        self.preview_info.setObjectName("metaLabel")
        self.preview_info.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        preview_controls.addWidget(self.btn_preview)
        preview_controls.addWidget(self.btn_copy_all)
        preview_controls.addWidget(self.btn_copy)
        preview_controls.addStretch()
        preview_controls.addWidget(self.preview_info)
        preview_layout.addLayout(preview_controls)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Preview will appear here...")
        preview_layout.addWidget(self.preview, 1)

        right_layout.addWidget(preview_group, 1)
        splitter.addWidget(right_panel)

        splitter.setSizes([420, 560])

        self._update_split_controls()
        self._update_part_buttons()

    def _apply_ui_style(self):
        assets_dir = paths.get_assets_dir()
        chevron_down = (
            assets_dir / "chevron_down.svg"
        ).resolve().as_posix()
        chevron_up = (
            assets_dir / "chevron_up.svg"
        ).resolve().as_posix()

        style = """
            QMainWindow {
                background: #111318;
            }
            QWidget {
                color: #e8eaed;
                font-size: 13px;
            }
            QFrame#header {
                background: #191c22;
                border: 1px solid #2a2f3a;
                border-radius: 12px;
            }
            QLabel#titleLabel {
                font-size: 18px;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel#rootLabel {
                color: #aab2c0;
            }
            QLabel#metaLabel {
                color: #8f98a8;
                font-size: 12px;
            }
            QGroupBox {
                background: #191c22;
                border: 1px solid #2a2f3a;
                border-radius: 12px;
                margin-top: 10px;
                font-weight: 600;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 10px;
            }
            QLineEdit,
            QTextEdit,
            QListWidget,
            QComboBox,
            QSpinBox {
                background: #101217;
                border: 1px solid #2a2f3a;
                border-radius: 9px;
                padding: 8px;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
            }
            QListWidget {
                outline: none;
            }
            QListWidget::item {
                padding: 6px;
                margin: 1px 0;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background: #202633;
            }
            QListWidget::item:selected {
                background: #263244;
                color: #ffffff;
            }
            QCheckBox::indicator,
            QListWidget::indicator {
                width: 16px;
                height: 16px;
                border-radius: 5px;
                border: 1px solid #46516a;
                background: #151922;
            }
            QCheckBox::indicator:hover,
            QListWidget::indicator:hover {
                border-color: #60a5fa;
                background: #1d2635;
            }
            QCheckBox::indicator:checked,
            QListWidget::indicator:checked {
                border: 1px solid #3b82f6;
                background: #2563eb;
                image: none;
            }
            QCheckBox::indicator:checked:hover,
            QListWidget::indicator:checked:hover {
                border-color: #60a5fa;
                background: #1d4ed8;
            }
            QCheckBox::indicator:disabled,
            QListWidget::indicator:disabled {
                border-color: #2a2f3a;
                background: #111318;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 4px 2px 4px 2px;
            }
            QScrollBar::handle:vertical {
                background: #343b4d;
                border-radius: 5px;
                min-height: 28px;
            }
            QScrollBar::handle:vertical:hover {
                background: #46516a;
            }
            QScrollBar::handle:vertical:pressed {
                background: #5b6b89;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
                background: transparent;
                border: none;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 10px;
                margin: 2px 4px 2px 4px;
            }
            QScrollBar::handle:horizontal {
                background: #343b4d;
                border-radius: 5px;
                min-width: 28px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #46516a;
            }
            QScrollBar::handle:horizontal:pressed {
                background: #5b6b89;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0;
                background: transparent;
                border: none;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            QPushButton {
                background: #242936;
                border: 1px solid #343b4d;
                border-radius: 8px;
                padding: 8px 12px;
                color: #eef2ff;
            }
            QPushButton:hover {
                background: #2d3444;
                border-color: #46516a;
            }
            QPushButton:pressed {
                background: #1d2330;
            }
            QPushButton:disabled {
                background: #1a1e27;
                border-color: #272d39;
                color: #626b7b;
            }
            QPushButton#primaryButton {
                background: #2563eb;
                border-color: #3b82f6;
                color: #ffffff;
                font-weight: 700;
            }
            QPushButton#primaryButton:hover {
                background: #1d4ed8;
            }
            QSplitter::handle {
                background: transparent;
            }
            QComboBox {
                background-color: #101217;
                color: #e8eaed;
                border: 1px solid #2a2f3a;
                border-radius: 9px;
                padding: 8px 32px 8px 8px;
            }
            QComboBox:hover {
                border-color: #46516a;
                background-color: #151922;
            }
            QComboBox:focus {
                border-color: #3b82f6;
            }
            QComboBox:disabled {
                background-color: #111318;
                color: #5f6878;
                border-color: #242936;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                background-color: #242936;
                border: none;
                border-left: 1px solid #343b4d;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QComboBox::drop-down:hover {
                background-color: #2d3444;
            }
            QComboBox::down-arrow {
                image: url("__CHEVRON_DOWN__");
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #17191f;
                color: #e8eaed;
                border: 1px solid #343b4d;
                border-radius: 8px;
                padding: 4px;
                outline: none;
                selection-background-color: #263244;
                selection-color: #ffffff;
            }
            QComboBox QAbstractItemView::item {
                min-height: 30px;
                padding: 4px 8px;
                background-color: #17191f;
                color: #e8eaed;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #202633;
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #263244;
                color: #ffffff;
            }
            QSpinBox {
                background-color: #101217;
                color: #e8eaed;
                border: 1px solid #2a2f3a;
                border-radius: 9px;
                padding: 8px 30px 8px 8px;
            }
            QSpinBox:hover {
                border-color: #46516a;
                background-color: #151922;
            }
            QSpinBox:focus {
                border-color: #3b82f6;
            }
            QSpinBox:disabled {
                background-color: #111318;
                color: #5f6878;
                border-color: #242936;
            }
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 26px;
                height: 18px;
                background-color: #242936;
                border: none;
                border-left: 1px solid #343b4d;
                border-bottom: 1px solid #343b4d;
                border-top-right-radius: 8px;
            }
            QSpinBox::up-button:hover {
                background-color: #2d3444;
            }
            QSpinBox::up-button:pressed {
                background-color: #1d2330;
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 26px;
                height: 18px;
                background-color: #242936;
                border: none;
                border-left: 1px solid #343b4d;
                border-bottom-right-radius: 8px;
            }
            QSpinBox::down-button:hover {
                background-color: #2d3444;
            }
            QSpinBox::down-button:pressed {
                background-color: #1d2330;
            }
            QSpinBox::up-arrow {
                image: url("__CHEVRON_UP__");
                width: 12px;
                height: 12px;
            }
            QSpinBox::down-arrow {
                image: url("__CHEVRON_DOWN__");
                width: 12px;
                height: 12px;
            }
            QMenu {
                background-color: #17191f;
                color: #e8eaed;
                border: 1px solid #343b4d;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                min-width: 240px;
                min-height: 30px;
                padding: 5px 12px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #263244;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #343b4d;
                margin: 5px 8px;
            }
        """

        style = style.replace("__CHEVRON_DOWN__", chevron_down)
        style = style.replace("__CHEVRON_UP__", chevron_up)
        self.setStyleSheet(style)

    def _load_last_root(self):
        try:
            cfg = self._load_cache_config() or {}
            saved = cfg.get("last_root", "")

            if saved and os.path.isdir(saved):
                self.root_path = saved
                self.lbl_root.setText(saved)
                self.scan_root()
        except Exception:
            pass

    def select_root(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Root Folder",
        )

        if path:
            self.root_path = path
            self.lbl_root.setText(path)

            try:
                self._save_cache_config({"last_root": path})
            except Exception:
                pass

            self.scan_root()

    def scan_root(self):
        self._all_files = []
        self._file_checks = {}

        if not self.root_path or not os.path.isdir(self.root_path):
            MessageDialog.warning(
                self,
                "No root",
                "Please select a valid root folder first.",
            )
            self._update_stats()
            return

        for dirpath, _, filenames in os.walk(self.root_path):
            for filename in filenames:
                full = os.path.join(dirpath, filename)
                rel = os.path.relpath(full, self.root_path)
                self._all_files.append(rel)
                self._file_checks[rel] = False

        self._all_files.sort(key=lambda value: value.lower())
        self.refresh_files_view()
        self._show_temp_status(
            "Scan complete",
            color="#22c55e",
        )

    def refresh_files_view(self):
        self.files_list.blockSignals(True)

        try:
            self.files_list.clear()
            filter_text = (self._filter_text or "").lower()

            for rel in self._all_files:
                if filter_text and filter_text not in rel.lower():
                    continue

                item = QListWidgetItem(rel)
                item.setFlags(
                    item.flags()
                    | Qt.ItemIsUserCheckable
                    | Qt.ItemIsEnabled
                    | Qt.ItemIsSelectable
                )
                item.setCheckState(
                    Qt.Checked
                    if self._file_checks.get(rel, False)
                    else Qt.Unchecked
                )
                self.files_list.addItem(item)
        finally:
            self.files_list.blockSignals(False)

        self._update_stats()

    def _add_export_item(self, rel: str):
        existing = {
            self.export_list.item(index).text()
            for index in range(self.export_list.count())
        }

        if rel in existing:
            self._show_temp_status(
                "Already in export list",
                color="#f59e0b",
            )
            return False

        self.export_list.addItem(rel)
        self._invalidate_preview()
        self._update_stats()
        self._show_temp_status(
            "Added 1 file",
            color="#22c55e",
        )
        return True

    def add_selected(self):
        items = [
            path
            for path in self._all_files
            if self._file_checks.get(path)
        ]

        if not items:
            MessageDialog.info(
                self,
                "No selection",
                "No checked files to add.",
            )
            return

        existing = {
            self.export_list.item(index).text()
            for index in range(self.export_list.count())
        }

        added = 0

        for path in items:
            if path in existing:
                continue

            self.export_list.addItem(path)
            existing.add(path)
            added += 1

        if added:
            self._invalidate_preview()

        self._update_stats()

        if added:
            self._show_temp_status(
                f"Added {added} file(s)",
                color="#22c55e",
            )
        else:
            self._show_temp_status(
                "Already in export list",
                color="#f59e0b",
            )

    def remove_selected(self):
        removed = False

        for item in self.export_list.selectedItems():
            row = self.export_list.row(item)
            self.export_list.takeItem(row)
            removed = True

        if removed:
            self._invalidate_preview()

        self._update_stats()

    def clear_export_list(self):
        if self.export_list.count() == 0:
            return

        self.export_list.clear()
        self._invalidate_preview()
        self._update_stats()
        self._show_temp_status(
            "Export list cleared",
            color="#f59e0b",
        )

    def export_selected(self):
        if self.export_list.count() == 0:
            MessageDialog.info(
                self,
                "No files",
                "Export list is empty.",
            )
            return

        if not self.root_path:
            MessageDialog.warning(
                self,
                "No root",
                "Root folder is not set.",
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Export",
            filter="Text files (*.txt);;All files (*)",
        )

        if not filename:
            return

        try:
            self._refresh_export_content()

            with open(filename, "w", encoding="utf-8") as output:
                output.write(self._source_text)

            MessageDialog.info(
                self,
                "Exported",
                (
                    f"Exported {self.export_list.count()} "
                    f"entries to {filename}"
                ),
            )
        except Exception as error:
            MessageDialog.error(
                self,
                "Error",
                f"Failed to write export: {error}",
            )

    def on_search_change(self, text: str):
        self._filter_text = text or ""
        self.refresh_files_view()

    def check_visible_files(self):
        for index in range(self.files_list.count()):
            item = self.files_list.item(index)
            self._file_checks[item.text()] = True

        self.refresh_files_view()

    def uncheck_visible_files(self):
        for index in range(self.files_list.count()):
            item = self.files_list.item(index)
            self._file_checks[item.text()] = False

        self.refresh_files_view()

    def _on_item_changed(self, item: QListWidgetItem):
        rel = item.text()
        self._file_checks[rel] = (
            item.checkState() == Qt.Checked
        )
        self._update_stats()

    def _on_file_double_clicked(self, item: QListWidgetItem):
        rel = item.text()

        if rel not in self._all_files:
            return

        self._add_export_item(rel)

    def _read_export_files(self):
        files = []

        for index in range(self.export_list.count()):
            rel = self.export_list.item(index).text()
            full = os.path.join(self.root_path or "", rel)

            try:
                with open(
                    full,
                    "r",
                    encoding="utf-8",
                    errors="replace",
                ) as file:
                    content = file.read()
            except Exception as error:
                content = f"<file_read_error>{error}</file_read_error>"

            files.append((rel, content))

        return files

    def build_export_text(self) -> str:
        files = self._read_export_files()
        return self._build_full_export_text(files)

    def preview_export(self):
        if self.export_list.count() == 0:
            MessageDialog.info(
                self,
                "No files",
                "Export list is empty.",
            )
            return

        self._refresh_export_content()
        self._display_full_preview()

    def copy_all_export(self):
        if self.export_list.count() == 0:
            MessageDialog.info(
                self,
                "No content",
                "Nothing to copy.",
            )
            return

        self._refresh_export_content()

        if not self._source_text:
            MessageDialog.info(
                self,
                "No content",
                "Nothing to copy.",
            )
            return

        QGuiApplication.clipboard().setText(self._source_text)
        self._show_temp_status(
            "Copied all content",
            color="#22c55e",
        )

    def show_copy_parts_menu(self):
        if self.export_list.count() == 0:
            MessageDialog.info(
                self,
                "No content",
                "Nothing to copy.",
            )
            return

        self._refresh_export_content()

        if not self._preview_parts:
            MessageDialog.info(
                self,
                "No content",
                "Nothing to copy.",
            )
            return

        menu = QMenu(self)

        for index, part in enumerate(self._preview_parts):
            line_count = self._count_lines(part)
            character_count = len(part)

            action = menu.addAction(
                (
                    f"Part {index + 1}/{len(self._preview_parts)}  "
                    f"({character_count:,} characters, "
                    f"{line_count:,} lines)"
                )
            )
            action.triggered.connect(
                lambda checked=False, part_index=index:
                self.copy_preview_part(part_index)
            )

        button_position = self.btn_copy.mapToGlobal(
            QPoint(0, self.btn_copy.height() + 4)
        )
        menu.exec(button_position)

    def copy_preview_part(self, index: int):
        if index < 0 or index >= len(self._preview_parts):
            return

        self._preview_part_index = index
        text = self._preview_parts[index]

        QGuiApplication.clipboard().setText(text)

        self._show_temp_status(
            (
                f"Copied part {index + 1}/"
                f"{len(self._preview_parts)}"
            ),
            color="#22c55e",
        )

    def _refresh_export_content(self):
        self._cancel_temp_status()

        files = self._read_export_files()
        self._source_text = self._build_full_export_text(files)

        if self.split_enabled.isChecked():
            self._preview_parts = self._create_export_parts()
        else:
            self._preview_parts = (
                [self._source_text]
                if self._source_text
                else []
            )

        self._preview_part_index = 0
        self._update_part_buttons()

    def _build_full_export_text(self, files):
        blocks = []

        for rel, content in files:
            blocks.append(
                self._format_file_content(
                    rel,
                    content,
                    1,
                    1,
                    False,
                )
            )

        return "\n\n".join(blocks)

    def _split_export_text(self, text):
        if not text:
            return []

        limit = self.split_limit.value()

        if self.split_mode.currentText() == "Lines":
            return self._split_by_lines(text, limit)

        return self._split_by_characters(text, limit)

    def _create_export_parts(self):
        files = self._read_export_files()

        if not files:
            return []

        if not self.split_enabled.isChecked():
            return [
                self._build_full_export_text(files)
            ]

        limit = self.split_limit.value()
        split_by_lines = (
            self.split_mode.currentText() == "Lines"
        )
        file_blocks = []

        for rel, content in files:
            if split_by_lines:
                content_parts = self._split_by_lines(
                    content,
                    limit,
                )
            else:
                content_parts = self._split_by_characters(
                    content,
                    limit,
                )

            if not content_parts:
                content_parts = [""]

            total_parts = len(content_parts)

            for index, content_part in enumerate(content_parts):
                file_blocks.append(
                    self._format_file_content(
                        rel,
                        content_part,
                        index + 1,
                        total_parts,
                        index + 1 < total_parts,
                    )
                )

        packed_parts = []
        current_blocks = []
        current_size = 0

        for block in file_blocks:
            block_size = (
                self._count_lines(block)
                if split_by_lines
                else len(block)
            )

            if current_blocks:
                candidate_size = current_size + 2 + block_size

                if candidate_size > limit:
                    packed_parts.append(
                        "\n\n".join(current_blocks)
                    )
                    current_blocks = []
                    current_size = 0

            current_blocks.append(block)

            if current_size:
                current_size += 2

            current_size += block_size

        if current_blocks:
            packed_parts.append(
                "\n\n".join(current_blocks)
            )

        return packed_parts

    def _format_file_content(
        self,
        rel: str,
        content: str,
        part_number: int,
        total_parts: int,
        has_more: bool,
    ):
        safe_name = escape(rel, quote=True)
        more_value = "true" if has_more else "false"
        character_count = len(content)
        line_count = self._count_lines(content)

        opening = (
            f'<file_content name="{safe_name}" '
            f'part="{part_number}/{total_parts}" '
            f'has_more_parts="{more_value}" '
            f'characters="{character_count}" '
            f'lines="{line_count}">'
        )

        if content:
            return (
                f"{opening}\n"
                f"{content}\n"
                f"</file_content>"
            )

        return (
            f"{opening}\n"
            f"</file_content>"
        )

    def _pack_export_blocks(
        self,
        blocks,
        limit: int,
        split_by_lines: bool,
    ):
        if not blocks:
            return []

        packed_parts = []
        current_blocks = []
        current_size = 0

        for block in blocks:
            block_size = (
                self._count_lines(block)
                if split_by_lines
                else len(block)
            )
            separator_size = (
                2 if split_by_lines else 2
            )

            candidate_size = block_size

            if current_blocks:
                candidate_size += current_size + separator_size

            if (
                current_blocks
                and candidate_size > limit
            ):
                packed_parts.append(
                    "\n\n".join(current_blocks)
                )
                current_blocks = [block]
                current_size = block_size
            else:
                current_blocks.append(block)

                if len(current_blocks) == 1:
                    current_size = block_size
                else:
                    current_size += separator_size + block_size

        if current_blocks:
            packed_parts.append(
                "\n\n".join(current_blocks)
            )

        return packed_parts

    def _split_by_characters(self, text: str, limit: int):
        if limit <= 0 or len(text) <= limit:
            return [text]

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            target = min(start + limit, text_length)

            if target >= text_length:
                end = text_length
            else:
                previous_newline = text.rfind(
                    "\n",
                    start,
                    target + 1,
                )

                if previous_newline > start:
                    end = previous_newline + 1
                else:
                    next_newline = text.find("\n", target)

                    if next_newline == -1:
                        end = text_length
                    else:
                        end = next_newline + 1

            if end <= start:
                end = min(start + limit, text_length)

            chunks.append(text[start:end])
            start = end

        return chunks

    def _split_by_lines(self, text: str, limit: int):
        lines = text.splitlines(keepends=True)

        if not lines:
            return [""]

        if limit <= 0 or len(lines) <= limit:
            return [text]

        chunks = []

        for start in range(0, len(lines), limit):
            chunks.append(
                "".join(lines[start:start + limit])
            )

        return chunks

    def _display_full_preview(self):
        self.preview.setPlainText(self._source_text)
        self._update_preview_info(self._source_text)
        self._update_part_buttons()

    def _display_current_preview_part(self):
        self._display_full_preview()

    def _update_part_buttons(self):
        has_content = bool(self._source_text)

        self.btn_copy.setEnabled(
            self.export_list.count() > 0
            and bool(self._preview_parts)
        )
        self.btn_copy_all.setEnabled(
            self.export_list.count() > 0
            and has_content
        )

        if not has_content:
            self.preview_info.setText("")

    def _invalidate_preview(self):
        self._cancel_temp_status()
        self._source_text = ""
        self._preview_parts = []
        self._preview_part_index = 0
        self.preview.clear()
        self._update_preview_info("")
        self._update_part_buttons()

    def _on_split_settings_changed(self):
        self._update_split_controls()

        if self._source_text and self.export_list.count() > 0:
            self._refresh_export_content()
            self._display_full_preview()

    def _update_split_controls(self):
        is_lines = (
            self.split_mode.currentText() == "Lines"
        )

        self.split_limit_label.setText(
            "max lines"
            if is_lines
            else "max characters"
        )

        enabled = self.split_enabled.isChecked()
        self.split_mode.setEnabled(enabled)
        self.split_limit.setEnabled(enabled)

    def _count_lines(self, text: str):
        if not text:
            return 0

        return text.count("\n") + (
            0 if text.endswith("\n") else 1
        )

    def closeEvent(self, event):
        try:
            if self.root_path:
                self._save_cache_config(
                    {"last_root": self.root_path}
                )
        except Exception:
            pass

        try:
            super().closeEvent(event)
        except Exception:
            event.accept()

    def showEvent(self, event):
        try:
            try:
                QTimer.singleShot(200, self._do_center)
            except Exception:
                screen = (
                    self.screen()
                    or QGuiApplication.primaryScreen()
                )

                if screen is not None:
                    center_point = (
                        screen.availableGeometry().center()
                    )
                    frame_geometry = self.frameGeometry()
                    frame_geometry.moveCenter(center_point)
                    self.move(frame_geometry.topLeft())
        except Exception:
            pass

        try:
            super().showEvent(event)
        except Exception:
            pass

    def _do_center(self):
        try:
            screen = (
                self.screen()
                or QGuiApplication.primaryScreen()
            )

            if screen is not None:
                center_point = (
                    screen.availableGeometry().center()
                )
                frame_geometry = self.frameGeometry()
                frame_geometry.moveCenter(center_point)
                self.move(frame_geometry.topLeft())

                try:
                    if hasattr(self, "raise_"):
                        self.raise_()

                    if hasattr(self, "activateWindow"):
                        self.activateWindow()
                except Exception:
                    pass
        except Exception:
            pass

    def _do_center_and_mark(self):
        try:
            self._do_center()
        except Exception:
            pass

    def _cache_config_path(self):
        try:
            app_id = (
                getattr(self.app, "id", None)
                or getattr(
                    self.app,
                    "manifest",
                    {},
                ).get("id", "")
            )
            paths.ensure_app_cache_dir(app_id)
            return (
                paths.get_app_cache_dir(app_id)
                / "config.json"
            )
        except Exception:
            return None

    def _load_cache_config(self):
        config_path = self._cache_config_path()

        if not config_path:
            return {}

        try:
            if config_path.exists():
                return json.loads(
                    config_path.read_text(
                        encoding="utf-8"
                    )
                )
        except Exception:
            pass

        return {}

    def _save_cache_config(self, updates: dict):
        config_path = self._cache_config_path()

        if not config_path:
            return False

        try:
            data = {}

            if config_path.exists():
                try:
                    data = json.loads(
                        config_path.read_text(
                            encoding="utf-8"
                        )
                    )
                except Exception:
                    data = {}

            data.update(updates or {})
            config_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            config_path.write_text(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return True
        except Exception:
            return False

    def _update_stats(self):
        checked = sum(
            1
            for value in self._file_checks.values()
            if value
        )
        visible = (
            self.files_list.count()
            if hasattr(self, "files_list")
            else 0
        )
        total = len(self._all_files)
        export_count = (
            self.export_list.count()
            if hasattr(self, "export_list")
            else 0
        )

        if hasattr(self, "files_stats"):
            self.files_stats.setText(
                (
                    f"Files: {total}   "
                    f"Visible: {visible}   "
                    f"Checked: {checked}"
                )
            )

        if hasattr(self, "export_stats"):
            self.export_stats.setText(
                f"Entries: {export_count}"
            )

        if hasattr(self, "btn_copy"):
            self._update_part_buttons()

    def _update_preview_info(self, text: str):
        if text is None:
            self.preview_info.setText("")
            return

        lines = self._count_lines(text)
        characters = len(text)

        if text:
            self.preview_info.setText(
                (
                    f"Lines: {lines:,}, "
                    f"Characters: {characters:,}"
                )
            )
        else:
            self.preview_info.setText("")
    
    def _cancel_temp_status(self):
        try:
            if self._status_timer.isActive():
                self._status_timer.stop()

            self.preview_info.setStyleSheet(
                self._status_style_backup or ""
            )
        except Exception:
            pass

        self._status_backup = None
        self._status_style_backup = ""

    def _show_temp_status(
        self,
        message: str,
        color: str = None,
        seconds: float = 2.0,
    ):
        try:
            was_active = self._status_timer.isActive()

            if was_active:
                self._status_timer.stop()

            if not was_active:
                try:
                    self._status_backup = (
                        self.preview_info.text()
                    )
                except Exception:
                    self._status_backup = ""

                try:
                    self._status_style_backup = (
                        self.preview_info.styleSheet()
                    )
                except Exception:
                    self._status_style_backup = ""

            try:
                if color:
                    self.preview_info.setStyleSheet(
                        f"color: {color};"
                    )
                else:
                    self.preview_info.setStyleSheet(
                        self._status_style_backup or ""
                    )
            except Exception:
                pass

            self.preview_info.setText(message)
            self._status_timer.start(
                int(
                    max(0.0, float(seconds))
                    * 1000
                )
            )
        except Exception:
            pass

    def _restore_preview_info(self):
        try:
            self.preview_info.setStyleSheet(
                self._status_style_backup or ""
            )
        except Exception:
            pass

        self._status_backup = None
        self._status_style_backup = ""

        try:
            self._update_preview_info(
                self.preview.toPlainText()
            )
        except Exception:
            pass
