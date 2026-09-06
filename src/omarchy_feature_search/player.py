"""Embedded mpv playback with an external-mpv fallback.

* If ``python-mpv`` is installed, :class:`PlayerWidget` renders the stream
  directly into a Qt widget via the widget's native window id.
* Otherwise :func:`play_external` launches a standalone ``mpv`` window at the
  right timestamp.

Both stream the YouTube segment (``--start``/``--end`` with ``--ytdl``) so no
local video file is required for playback.
"""

from __future__ import annotations

import subprocess

try:
    import mpv as _mpv

    _HAS_MPV_PY = True
except Exception:  # ImportError or OSError (libmpv missing)
    _mpv = None
    _HAS_MPV_PY = False


def has_embedded() -> bool:
    return _HAS_MPV_PY


def play_external(video_url: str, start_s: int, end_s: int | None = None) -> subprocess.Popen:
    """Launch an external mpv window streaming the segment."""
    cmd = [
        "mpv",
        f"--start={int(start_s)}",
        "--ytdl",
        "--ytdl-format=best[height<=720]/best",
        video_url,
    ]
    if end_s is not None and end_s > start_s:
        cmd.insert(2, f"--end={int(end_s)}")
    return subprocess.Popen(cmd)


try:
    from PySide6.QtWidgets import QVBoxLayout, QWidget
    from PySide6.QtCore import Qt

    _HAS_QT = True
except Exception:
    _HAS_QT = False


if _HAS_QT:

    class PlayerWidget(QWidget):
        """A Qt widget hosting an embedded mpv player."""

        def __init__(self, parent: QWidget | None = None):
            super().__init__(parent)
            self.setObjectName("playerFrame")
            self.setMinimumHeight(220)
            self._layout = QVBoxLayout(self)
            self._layout.setContentsMargins(0, 0, 0, 0)
            self._mpv = None

            if _HAS_MPV_PY:
                # Container that mpv renders into via its native window id.
                self._container = QWidget(self)
                self._container.setAttribute(Qt.WA_DontCreateNativeAncestors, True)
                self._container.setAttribute(Qt.WA_NativeWindow, True)
                self._layout.addWidget(self._container)
                self._mpv = _mpv.MPV(
                    wid=str(int(self._container.winId())),
                    vo="gpu",
                    ytdl=True,
                    keep_open=True,
                    log_handler=lambda *a: None,
                )
            else:
                self._container = None

        @property
        def available(self) -> bool:
            return self._mpv is not None

        def play(self, video_url: str, start_s: int, end_s: int | None = None) -> None:
            if not self._mpv:
                return
            self._mpv.play(video_url)
            try:
                self._mpv.wait_until_playing(timeout=10)
            except Exception:
                pass
            try:
                self._mpv.seek(int(start_s), reference="absolute")
            except Exception:
                pass
            if end_s is not None and end_s > start_s:
                try:
                    self._mpv["end"] = str(int(end_s))
                except Exception:
                    pass

        def stop(self) -> None:
            if self._mpv:
                try:
                    self._mpv.terminate()
                except Exception:
                    pass
                self._mpv = None

        def shutdown(self) -> None:
            self.stop()

else:
    PlayerWidget = None  # type: ignore
