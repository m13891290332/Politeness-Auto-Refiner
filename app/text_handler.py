"""
Text capture and replacement helper.

On Windows: tracks the last external foreground window, then uses clipboard
operations (Ctrl+A / Ctrl+C / Ctrl+V) to capture and replace text without
requiring any special OS permissions or accessibility permissions.

On other platforms (e.g., Linux CI): the class is still importable but the
Win32-specific methods are no-ops and return empty strings / False.
"""
import sys
import time

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import win32clipboard
        import win32con
        import win32gui

        _HAS_WIN32 = True
    except ImportError:
        _HAS_WIN32 = False

    try:
        import pyautogui

        _HAS_PYAUTOGUI = True
    except ImportError:
        _HAS_PYAUTOGUI = False
else:
    _HAS_WIN32 = False
    _HAS_PYAUTOGUI = False


def _clipboard_get() -> str:
    """Return the current clipboard text (Windows only)."""
    if not _HAS_WIN32:
        return ""
    try:
        win32clipboard.OpenClipboard()
        try:
            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        except Exception:
            data = ""
        finally:
            win32clipboard.CloseClipboard()
        return data
    except Exception:
        return ""


def _clipboard_set(text: str) -> None:
    """Set clipboard text (Windows only)."""
    if not _HAS_WIN32:
        return
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        win32clipboard.CloseClipboard()
    except Exception as exc:
        print(f"[TextHandler] clipboard set error: {exc}")


class TextHandler:
    """
    Manages the 'last known external window' and provides helpers for
    capturing and replacing text in that window via clipboard shortcuts.
    """

    def __init__(self):
        self._target_hwnd: int = 0

    # ------------------------------------------------------------------
    # Window tracking
    # ------------------------------------------------------------------

    def record_foreground_window(self, own_hwnd: int = 0) -> None:
        """
        Record the current foreground window as the capture/replace target,
        as long as it is not our own application window.
        """
        if not _HAS_WIN32:
            return
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and hwnd != own_hwnd:
            self._target_hwnd = hwnd

    @property
    def has_target(self) -> bool:
        return bool(self._target_hwnd)

    def target_window_title(self) -> str:
        if not (_HAS_WIN32 and self._target_hwnd):
            return ""
        try:
            return win32gui.GetWindowText(self._target_hwnd)
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    def capture_text(self) -> str:
        """
        Focus the target window, select-all, copy, and return the clipboard text.
        Restores the original clipboard content afterwards.
        """
        if not (_HAS_WIN32 and _HAS_PYAUTOGUI and self._target_hwnd):
            return ""
        original = _clipboard_get()
        try:
            win32gui.SetForegroundWindow(self._target_hwnd)
            time.sleep(0.15)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.15)
            text = _clipboard_get()
        except Exception as exc:
            print(f"[TextHandler] capture error: {exc}")
            text = ""
        finally:
            if original:
                _clipboard_set(original)
        return text

    # ------------------------------------------------------------------
    # Replace
    # ------------------------------------------------------------------

    def replace_text(self, refined: str) -> bool:
        """
        Focus the target window, select-all, then paste the refined text.
        Returns True on success.
        """
        if not (_HAS_WIN32 and _HAS_PYAUTOGUI and self._target_hwnd):
            return False
        try:
            _clipboard_set(refined)
            win32gui.SetForegroundWindow(self._target_hwnd)
            time.sleep(0.15)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.05)
            return True
        except Exception as exc:
            print(f"[TextHandler] replace error: {exc}")
            return False
