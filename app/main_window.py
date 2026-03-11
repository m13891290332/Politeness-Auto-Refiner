"""
Main settings window for Politeness Auto Refiner.

Provides:
- Model / API key / API base URL configuration.
- Prompt editing with a reset-to-default button.
- System tray icon so the app can live in the background.
- Shows / hides the floating toolbar.
"""
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QPainter
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QGroupBox,
    QSystemTrayIcon,
    QMenu,
    QAction,
    QMessageBox,
    QDoubleSpinBox,
    QSpinBox,
    QFrame,
)

from app.settings_manager import MODEL_PRESETS, DEFAULT_SETTINGS


def _make_tray_icon(size: int = 32) -> QIcon:
    """Create a simple coloured letter icon for the system tray."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    # Background circle
    painter.setBrush(QColor("#0078d4"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    # Letter "礼"
    painter.setPen(QColor("white"))
    font = QFont()
    font.setPixelSize(size * 14 // 32)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(0, 0, size, size, Qt.AlignCenter, "礼")
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    """Main settings window with tray icon support."""

    def __init__(self, settings_manager, floating_window=None):
        super().__init__()
        self.settings = settings_manager
        self.floating_window = floating_window

        self.setWindowTitle("礼貌自动润色器 – 设置")
        self.setMinimumWidth(520)
        self.setMinimumHeight(560)

        self._build_ui()
        self._setup_tray()
        self._load_values()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ── Header ───────────────────────────────────────────────────
        header = QLabel("礼貌自动润色器")
        header.setAlignment(Qt.AlignCenter)
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        sub = QLabel("自动将文字润色为礼貌、正式的表达")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #666;")
        layout.addWidget(sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # ── Model preset selector ─────────────────────────────────────
        model_group = QGroupBox("AI 模型设置")
        model_layout = QGridLayout(model_group)
        model_layout.setVerticalSpacing(10)
        model_layout.setHorizontalSpacing(12)

        model_layout.addWidget(QLabel("模型预设:"), 0, 0)
        self._preset_combo = QComboBox()
        self._preset_combo.addItems(list(MODEL_PRESETS.keys()))
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        model_layout.addWidget(self._preset_combo, 0, 1)

        model_layout.addWidget(QLabel("模型名称:"), 1, 0)
        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("gpt-3.5-turbo")
        model_layout.addWidget(self._model_edit, 1, 1)

        model_layout.addWidget(QLabel("API Key:"), 2, 0)
        self._apikey_edit = QLineEdit()
        self._apikey_edit.setEchoMode(QLineEdit.Password)
        self._apikey_edit.setPlaceholderText("sk-…")
        model_layout.addWidget(self._apikey_edit, 2, 1)

        model_layout.addWidget(QLabel("API 地址:"), 3, 0)
        self._baseurl_edit = QLineEdit()
        self._baseurl_edit.setPlaceholderText("https://api.openai.com/v1")
        model_layout.addWidget(self._baseurl_edit, 3, 1)

        model_layout.addWidget(QLabel("Temperature:"), 4, 0)
        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 2.0)
        self._temp_spin.setSingleStep(0.1)
        self._temp_spin.setDecimals(1)
        model_layout.addWidget(self._temp_spin, 4, 1)

        model_layout.addWidget(QLabel("最大 Token 数:"), 5, 0)
        self._tokens_spin = QSpinBox()
        self._tokens_spin.setRange(100, 8000)
        self._tokens_spin.setSingleStep(100)
        model_layout.addWidget(self._tokens_spin, 5, 1)

        model_layout.setColumnStretch(1, 1)
        layout.addWidget(model_group)

        # ── Prompt editor ─────────────────────────────────────────────
        prompt_group = QGroupBox("润色提示词 (Prompt)")
        prompt_layout = QVBoxLayout(prompt_group)

        self._prompt_edit = QTextEdit()
        self._prompt_edit.setFixedHeight(90)
        self._prompt_edit.setPlaceholderText("请输入发送给 AI 的提示词…")
        prompt_layout.addWidget(self._prompt_edit)

        btn_reset_prompt = QPushButton("恢复默认提示词")
        btn_reset_prompt.setObjectName("secondaryBtn")
        btn_reset_prompt.clicked.connect(self._reset_prompt)
        prompt_layout.addWidget(btn_reset_prompt)

        layout.addWidget(prompt_group)

        # ── Bottom buttons ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_float = QPushButton("显示悬浮窗")
        self._btn_float.setObjectName("primaryBtn")
        self._btn_float.clicked.connect(self._toggle_float)
        btn_row.addWidget(self._btn_float)

        btn_row.addStretch()

        btn_save = QPushButton("保存设置")
        btn_save.setObjectName("saveBtn")
        btn_save.setMinimumWidth(110)
        btn_save.clicked.connect(self._save_settings)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)
        layout.addStretch()

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(
            """
            QMainWindow { background: #f5f5f5; }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 8px;
                margin-top: 8px;
                padding: 10px 10px 10px 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLineEdit, QTextEdit, QComboBox, QDoubleSpinBox, QSpinBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                background: white;
            }
            #primaryBtn {
                background: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            #primaryBtn:hover { background: #1084d8; }
            #saveBtn {
                background: #107c10;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            #saveBtn:hover { background: #138013; }
            #secondaryBtn {
                background: #f0f0f0;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 6px 12px;
            }
            #secondaryBtn:hover { background: #e0e0e0; }
            """
        )

    # ------------------------------------------------------------------
    # System tray
    # ------------------------------------------------------------------

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(_make_tray_icon())
        self._tray.setToolTip("礼貌自动润色器")
        self._tray.activated.connect(self._on_tray_activated)

        menu = QMenu()

        act_show = QAction("打开设置窗口", self)
        act_show.triggered.connect(self._show_main)
        menu.addAction(act_show)

        act_float = QAction("显示/隐藏 悬浮窗", self)
        act_float.triggered.connect(self._toggle_float)
        menu.addAction(act_float)

        menu.addSeparator()

        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self._quit_app)
        menu.addAction(act_quit)

        self._tray.setContextMenu(menu)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_main()

    def _show_main(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_float(self):
        if self.floating_window is None:
            return
        if self.floating_window.isVisible():
            self.floating_window.hide()
            self._btn_float.setText("显示悬浮窗")
        else:
            self.floating_window.show()
            self.floating_window.raise_()
            self._btn_float.setText("隐藏悬浮窗")

    def set_floating_window(self, fw):
        self.floating_window = fw

    # ------------------------------------------------------------------
    # Load / save settings
    # ------------------------------------------------------------------

    def _load_values(self):
        self._model_edit.setText(self.settings.get("model", ""))
        self._apikey_edit.setText(self.settings.get("api_key", ""))
        self._baseurl_edit.setText(self.settings.get("api_base_url", ""))
        self._prompt_edit.setPlainText(self.settings.get("prompt", ""))
        self._temp_spin.setValue(float(self.settings.get("temperature", 0.7)))
        self._tokens_spin.setValue(int(self.settings.get("max_tokens", 1000)))

        # Set preset combo to "自定义" initially; try to match a preset
        current_model = self.settings.get("model", "")
        current_url = self.settings.get("api_base_url", "")
        matched = "自定义"
        for name, vals in MODEL_PRESETS.items():
            if vals.get("model") == current_model and vals.get("api_base_url") == current_url:
                matched = name
                break
        # Block signal so _on_preset_changed does not overwrite the fields
        self._preset_combo.blockSignals(True)
        self._preset_combo.setCurrentText(matched)
        self._preset_combo.blockSignals(False)

    def _on_preset_changed(self, name: str):
        preset = MODEL_PRESETS.get(name, {})
        if preset.get("model"):
            self._model_edit.setText(preset["model"])
        if preset.get("api_base_url"):
            self._baseurl_edit.setText(preset["api_base_url"])

    def _reset_prompt(self):
        self._prompt_edit.setPlainText(DEFAULT_SETTINGS["prompt"])

    def _save_settings(self):
        self.settings.update(
            {
                "model": self._model_edit.text().strip(),
                "api_key": self._apikey_edit.text().strip(),
                "api_base_url": self._baseurl_edit.text().strip(),
                "prompt": self._prompt_edit.toPlainText().strip(),
                "temperature": self._temp_spin.value(),
                "max_tokens": self._tokens_spin.value(),
            }
        )
        QMessageBox.information(self, "已保存", "设置已保存成功。")

    # ------------------------------------------------------------------
    # Window close: minimise to tray instead of quitting
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if self.floating_window:
            self.floating_window.show()
            self._btn_float.setText("隐藏悬浮窗")
        self._tray.showMessage(
            "礼貌自动润色器",
            "程序已最小化到托盘，双击图标可重新打开设置窗口。",
            QSystemTrayIcon.Information,
            2000,
        )

    def _quit_app(self):
        from PyQt5.QtWidgets import QApplication

        QApplication.quit()
