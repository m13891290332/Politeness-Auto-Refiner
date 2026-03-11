"""
Floating toolbar window – always on top, frameless, draggable.

Resembles the floating bar used by input-method editors (IMEs) on Windows.
The user positions it near any input field and uses it to:
  1. Capture the text currently in that input field (Ctrl+A / Ctrl+C trick).
  2. Send the captured text to the AI polishing engine.
  3. One-click replace the original text with the refined result.
"""
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel,
    QSizeGrip,
    QFrame,
    QApplication,
    QMessageBox,
)


class FloatingWindow(QWidget):
    """Compact always-on-top floating toolbar for text polishing."""

    # Emitted when the user wants to open the main settings window
    open_settings_requested = pyqtSignal()

    def __init__(self, ai_client, text_handler, settings_manager):
        super().__init__()
        self.ai_client = ai_client
        self.text_handler = text_handler
        self.settings = settings_manager

        self._drag_pos: QPoint | None = None
        self._polishing = False

        self._build_ui()
        self._apply_style()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(380)
        self.setMinimumHeight(260)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        container = QFrame(self)
        container.setObjectName("container")
        root.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(8)

        # ── Title bar ────────────────────────────────────────────────
        title_bar = QHBoxLayout()
        title_bar.setSpacing(6)

        drag_hint = QLabel("⠿")
        drag_hint.setObjectName("dragHint")
        drag_hint.setToolTip("拖动此处移动窗口")
        title_bar.addWidget(drag_hint)

        title = QLabel("礼貌润色器")
        title.setObjectName("titleLabel")
        title_bar.addWidget(title)

        title_bar.addStretch()

        self._target_label = QLabel("未锁定输入框")
        self._target_label.setObjectName("targetLabel")
        title_bar.addWidget(self._target_label)

        btn_settings = QPushButton("⚙")
        btn_settings.setObjectName("iconBtn")
        btn_settings.setToolTip("打开设置")
        btn_settings.setFixedSize(24, 24)
        btn_settings.clicked.connect(self.open_settings_requested)
        title_bar.addWidget(btn_settings)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("iconBtn")
        btn_close.setToolTip("隐藏悬浮框")
        btn_close.setFixedSize(24, 24)
        btn_close.clicked.connect(self.hide)
        title_bar.addWidget(btn_close)

        layout.addLayout(title_bar)

        # ── Source text area ─────────────────────────────────────────
        src_label = QLabel("原始文本")
        src_label.setObjectName("sectionLabel")
        layout.addWidget(src_label)

        self._src_edit = QTextEdit()
        self._src_edit.setObjectName("srcEdit")
        self._src_edit.setPlaceholderText("在此粘贴或由「捕获」按钮自动读取…")
        self._src_edit.setFixedHeight(80)
        layout.addWidget(self._src_edit)

        # ── Source action buttons ─────────────────────────────────────
        src_btns = QHBoxLayout()
        src_btns.setSpacing(6)

        self._btn_capture = QPushButton("📋  捕获输入框文本")
        self._btn_capture.setObjectName("primaryBtn")
        self._btn_capture.setToolTip(
            "记录当前输入框，并读取其中全部文本\n"
            "（请先点击目标输入框，再点此按钮）"
        )
        self._btn_capture.clicked.connect(self._on_capture)
        src_btns.addWidget(self._btn_capture)

        btn_clear_src = QPushButton("清空")
        btn_clear_src.setObjectName("secondaryBtn")
        btn_clear_src.clicked.connect(self._src_edit.clear)
        src_btns.addWidget(btn_clear_src)

        layout.addLayout(src_btns)

        # ── Polish button ─────────────────────────────────────────────
        self._btn_polish = QPushButton("✨  AI 礼貌润色")
        self._btn_polish.setObjectName("polishBtn")
        self._btn_polish.setToolTip("将上方文本发送给 AI 进行礼貌性润色")
        self._btn_polish.clicked.connect(self._on_polish)
        layout.addWidget(self._btn_polish)

        # ── Refined text area ─────────────────────────────────────────
        dst_label = QLabel("润色结果")
        dst_label.setObjectName("sectionLabel")
        layout.addWidget(dst_label)

        self._dst_edit = QTextEdit()
        self._dst_edit.setObjectName("dstEdit")
        self._dst_edit.setPlaceholderText("润色后的文本将显示在此处…")
        self._dst_edit.setFixedHeight(80)
        layout.addWidget(self._dst_edit)

        # ── Destination action buttons ────────────────────────────────
        dst_btns = QHBoxLayout()
        dst_btns.setSpacing(6)

        self._btn_replace = QPushButton("↩  一键替换")
        self._btn_replace.setObjectName("primaryBtn")
        self._btn_replace.setToolTip("用润色后的文本替换原始输入框的内容")
        self._btn_replace.clicked.connect(self._on_replace)
        dst_btns.addWidget(self._btn_replace)

        btn_copy = QPushButton("复制")
        btn_copy.setObjectName("secondaryBtn")
        btn_copy.setToolTip("复制润色结果到剪贴板")
        btn_copy.clicked.connect(self._on_copy)
        dst_btns.addWidget(btn_copy)

        btn_clear_dst = QPushButton("清空")
        btn_clear_dst.setObjectName("secondaryBtn")
        btn_clear_dst.clicked.connect(self._dst_edit.clear)
        dst_btns.addWidget(btn_clear_dst)

        layout.addLayout(dst_btns)

        # Resize grip
        grip_row = QHBoxLayout()
        grip_row.addStretch()
        grip = QSizeGrip(self)
        grip.setFixedSize(14, 14)
        grip_row.addWidget(grip)
        layout.addLayout(grip_row)

    def _apply_style(self):
        self.setStyleSheet(
            """
            #container {
                background: #2b2b2b;
                border: 1px solid #555;
                border-radius: 10px;
            }
            #titleLabel {
                color: #e0e0e0;
                font-size: 13px;
                font-weight: bold;
            }
            #dragHint {
                color: #888;
                font-size: 16px;
            }
            #targetLabel {
                color: #aaa;
                font-size: 11px;
                padding: 2px 6px;
                background: #383838;
                border-radius: 4px;
            }
            #sectionLabel {
                color: #aaa;
                font-size: 11px;
            }
            QTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #444;
                border-radius: 6px;
                font-size: 12px;
                padding: 4px;
            }
            #iconBtn {
                background: transparent;
                color: #aaa;
                border: none;
                font-size: 13px;
            }
            #iconBtn:hover {
                color: #fff;
                background: #444;
                border-radius: 4px;
            }
            #primaryBtn {
                background: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            #primaryBtn:hover { background: #1084d8; }
            #primaryBtn:disabled { background: #555; color: #888; }
            #polishBtn {
                background: #107c10;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            #polishBtn:hover { background: #138013; }
            #polishBtn:disabled { background: #555; color: #888; }
            #secondaryBtn {
                background: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            #secondaryBtn:hover { background: #4a4a4a; }
            """
        )

    # ------------------------------------------------------------------
    # Drag to move (frameless window)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_capture(self):
        """
        Record the last external foreground window and capture its text.
        The user must have clicked in the target input field BEFORE pressing
        this button; the window tracks the last focused non-app window.
        """
        own_hwnd = int(self.winId()) if hasattr(self, "winId") else 0
        self.text_handler.record_foreground_window(own_hwnd)

        text = self.text_handler.capture_text()
        if text:
            self._src_edit.setPlainText(text)
            title = self.text_handler.target_window_title()
            self._target_label.setText(f"已锁定: {title[:20]}" if title else "已锁定")
        else:
            # Fall back: try to read directly from the clipboard
            try:
                import pyperclip

                clip = pyperclip.paste()
                if clip:
                    self._src_edit.setPlainText(clip)
                    self._target_label.setText("来自剪贴板")
                else:
                    QMessageBox.information(
                        self,
                        "提示",
                        "未能捕获文本。\n\n"
                        "请先在目标输入框中单击（确保输入框已激活），\n"
                        "然后再点击「捕获输入框文本」按钮。",
                    )
            except Exception:
                QMessageBox.information(
                    self,
                    "提示",
                    "未能捕获文本，请手动粘贴到上方文本框。",
                )

    def _on_polish(self):
        src = self._src_edit.toPlainText().strip()
        if not src:
            QMessageBox.warning(self, "提示", "请先在「原始文本」框中输入或捕获要润色的文字。")
            return

        api_key = self.settings.get("api_key", "").strip()
        if not api_key:
            QMessageBox.warning(
                self,
                "未设置 API Key",
                "请先在主设置窗口中填写 API Key。\n点击右上角 ⚙ 按钮打开设置。",
            )
            return

        self._set_polishing(True)
        self._dst_edit.setPlainText("正在润色中，请稍候…")

        def _on_success(result: str):
            self._dst_edit.setPlainText(result)
            self._set_polishing(False)

        def _on_error(msg: str):
            self._dst_edit.setPlainText(f"[错误] {msg}")
            self._set_polishing(False)

        self.ai_client.polish_text(src, _on_success, _on_error)

    def _on_replace(self):
        refined = self._dst_edit.toPlainText().strip()
        if not refined:
            QMessageBox.warning(self, "提示", "润色结果为空，无法替换。")
            return

        if not self.text_handler.has_target:
            # No recorded window – copy to clipboard instead
            try:
                import pyperclip

                pyperclip.copy(refined)
                QMessageBox.information(
                    self,
                    "已复制",
                    "未检测到锁定的输入框，润色结果已复制到剪贴板。\n"
                    "请手动粘贴（Ctrl+V）到目标位置。",
                )
            except Exception:
                QMessageBox.information(self, "提示", "请手动复制上方润色结果并粘贴。")
            return

        ok = self.text_handler.replace_text(refined)
        if not ok:
            # Fallback: copy to clipboard
            try:
                import pyperclip

                pyperclip.copy(refined)
            except Exception:
                pass
            QMessageBox.information(
                self,
                "已复制到剪贴板",
                "替换操作未能完成（可能目标窗口不支持），\n"
                "润色结果已复制到剪贴板，请手动粘贴。",
            )

    def _on_copy(self):
        text = self._dst_edit.toPlainText().strip()
        if not text:
            return
        try:
            import pyperclip

            pyperclip.copy(text)
        except Exception:
            QApplication.clipboard().setText(text)

    def _set_polishing(self, polishing: bool):
        self._polishing = polishing
        self._btn_polish.setEnabled(not polishing)
        self._btn_capture.setEnabled(not polishing)
        if polishing:
            self._btn_polish.setText("润色中…")
        else:
            self._btn_polish.setText("✨  AI 礼貌润色")
