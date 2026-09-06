"""PySide6 main window for Omarchy Feature Search."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from omarchy_feature_search import data as data_mod
from omarchy_feature_search import player as player_mod
from omarchy_feature_search.search import Result, SearchEngine
from omarchy_feature_search.theme import Theme, stylesheet

_THUMB_W = 176
_THUMB_H = 99


class ResultCard(QFrame):
    playRequested = Signal(object)  # emits a Result

    def __init__(self, result: Result, theme: Theme, parent: QWidget | None = None):
        super().__init__(parent)
        self._result = result
        self.setObjectName("resultCard")
        self.setMinimumHeight(116)
        self.setFixedWidth(0)  # let layout expand via size policy
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 12, 12, 12)
        row.setSpacing(14)

        # Thumbnail / play button
        self.thumb = QPushButton("▶", self)
        self.thumb.setObjectName("thumbButton")
        self.thumb.setFixedSize(_THUMB_W, _THUMB_H)
        self.thumb.setCursor(Qt.PointingHandCursor)
        self._load_thumb(result.thumbnail)
        self.thumb.clicked.connect(lambda: self.playRequested.emit(self._result))
        row.addWidget(self.thumb, alignment=Qt.AlignTop)

        # Right column
        col = QVBoxLayout()
        col.setSpacing(4)
        col.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        top.setSpacing(8)
        group = QLabel(result.feature_group.upper(), self)
        group.setObjectName("featureGroup")
        top.addWidget(group)
        badge = QLabel(f"{result.confidence:.0f}%", self)
        badge.setObjectName("confidence")
        top.addWidget(badge)
        ts = QLabel(f"{result.start_fmt} – {result.end_fmt}", self)
        ts.setObjectName("timestamp")
        top.addWidget(ts)
        top.addStretch(1)
        col.addLayout(top)

        name = QLabel(result.feature, self)
        name.setObjectName("featureName")
        name.setWordWrap(True)
        col.addWidget(name)

        how = QLabel(result.how_to, self)
        how.setObjectName("howTo")
        how.setWordWrap(True)
        col.addWidget(how)

        summary = QLabel(result.transcript_summary or "Transcript not built yet — run the data pipeline.")
        summary.setObjectName("summary")
        summary.setWordWrap(True)
        summary.setMaximumHeight(48)
        col.addWidget(summary)
        col.addStretch(1)

        row.addLayout(col, 1)

    def _load_thumb(self, rel: str) -> None:
        p = data_mod.thumbnail_path(rel)
        if p is not None:
            pix = QPixmap(str(p))
            if not pix.isNull():
                self.thumb.setIcon(QIcon(pix.scaled(_THUMB_W, _THUMB_H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)))
                self.thumb.setIconSize(self.thumb.size())
                self.thumb.setText("")
                return
        # Placeholder
        self.thumb.setText(f"▶  {self._result.start_fmt}")
        self.thumb.setIcon(QIcon())


class MainWindow(QMainWindow):
    def __init__(self, theme: Theme | None = None, features_doc: dict | None = None):
        super().__init__()
        self.theme = theme if theme is not None else __import__(
            "omarchy_feature_search.theme", fromlist=["load_theme"]
        ).load_theme()
        self.setWindowTitle("Omarchy Feature Search")
        self.resize(1180, 760)
        if data_mod.icon_path().exists():
            self.setWindowIcon(QIcon(str(data_mod.icon_path())))

        self.setStyleSheet(stylesheet(self.theme))

        self.engine = SearchEngine(features_doc)
        self._external_proc = None

        central = QWidget(self)
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(16, 16, 16, 12)
        outer.setSpacing(12)

        outer.addLayout(self._build_header())

        self.splitter = QSplitter(Qt.Horizontal, self)
        outer.addWidget(self.splitter, 1)

        self.splitter.addWidget(self._build_results_pane())
        self.splitter.addWidget(self._build_player_pane())
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([680, 420])

        self.status = QLabel(f"backend: {self.engine.backend}  •  {len(self.engine.features)} features", self)
        self.status.setObjectName("statusBar")
        outer.addWidget(self.status)

        # Debounced search
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(220)
        self._timer.timeout.connect(self._do_search)
        self.search_box.textChanged.connect(self._timer.start)

        self._show_empty_state()

    # ------------------------------------------------------------------ #
    # header
    # ------------------------------------------------------------------ #
    def _build_header(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setSpacing(12)
        logo_path = data_mod.logo_path()
        if logo_path.exists():
            logo = QLabel(self)
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                logo.setPixmap(pix.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            h.addWidget(logo, alignment=Qt.AlignVCenter)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("Omarchy Feature Search", self)
        title.setObjectName("headerTitle")
        titles.addWidget(title)
        sub = QLabel("NetworkChuck · searchable feature knowledge base", self)
        sub.setObjectName("headerSub")
        titles.addWidget(sub)
        h.addLayout(titles)
        h.addStretch(1)

        self.search_box = QLineEdit(self)
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("Search how to do something…  e.g. screenshot, install package, workspace")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setMinimumHeight(46)
        self.search_box.returnPressed.connect(self._do_search)
        h.addWidget(self.search_box, 3)
        return h

    # ------------------------------------------------------------------ #
    # results pane
    # ------------------------------------------------------------------ #
    def _build_results_pane(self) -> QWidget:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget(scroll)
        self.results_layout = QVBoxLayout(container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(10)
        self.results_layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    def _clear_results(self) -> None:
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _show_empty_state(self) -> None:
        self._clear_results()
        hint = QLabel("Type a query above to search the Omarchy feature database.\n\nTry: “screenshot”, “clipboard”, “install”, “workspace”, “night light”.", self)
        hint.setObjectName("summary")
        hint.setWordWrap(True)
        self.results_layout.insertWidget(0, hint)

    # ------------------------------------------------------------------ #
    # player pane
    # ------------------------------------------------------------------ #
    def _build_player_pane(self) -> QWidget:
        pane = QWidget(self)
        v = QVBoxLayout(pane)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        if player_mod.has_embedded() and player_mod.PlayerWidget is not None:
            self.player = player_mod.PlayerWidget(pane)
            self.player.setObjectName("playerFrame")
            v.addWidget(self.player, 1)
        else:
            self.player = None
            frame = QFrame(pane)
            frame.setObjectName("playerFrame")
            fl = QVBoxLayout(frame)
            fl.setAlignment(Qt.AlignCenter)
            msg = QLabel("Embedded player unavailable.\nClick a thumbnail to open the segment in mpv.\n\nInstall python-mpv for in-app playback.", frame)
            msg.setObjectName("summary")
            msg.setWordWrap(True)
            msg.setAlignment(Qt.AlignCenter)
            fl.addWidget(msg)
            v.addWidget(frame, 1)

        self.now_title = QLabel("No segment selected", pane)
        self.now_title.setObjectName("featureName")
        self.now_title.setWordWrap(True)
        v.addWidget(self.now_title)
        self.now_how = QLabel("", pane)
        self.now_how.setObjectName("howTo")
        self.now_how.setWordWrap(True)
        v.addWidget(self.now_how)
        return pane

    # ------------------------------------------------------------------ #
    # search + render
    # ------------------------------------------------------------------ #
    def _do_search(self) -> None:
        q = self.search_box.text().strip()
        if not q:
            self._show_empty_state()
            self.status.setText(f"backend: {self.engine.backend}  •  {len(self.engine.features)} features")
            return
        results = self.engine.search(q, top_k=12)
        self._clear_results()
        if not results:
            none = QLabel("No matches. Try different keywords.", self)
            none.setObjectName("summary")
            self.results_layout.insertWidget(0, none)
            self.status.setText(f"backend: {self.engine.backend}  •  0 matches for “{q}”")
            return
        for r in results:
            card = ResultCard(r, self.theme, self)
            card.playRequested.connect(self._play)
            self.results_layout.insertWidget(self.results_layout.count() - 1, card)
        self.status.setText(f"backend: {self.engine.backend}  •  {len(results)} matches for “{q}”")

    # ------------------------------------------------------------------ #
    # playback
    # ------------------------------------------------------------------ #
    def _play(self, result: Result) -> None:
        self.now_title.setText(f"{result.feature}  ·  {result.start_fmt}–{result.end_fmt}")
        self.now_how.setText(result.how_to)
        url = result.video_url
        if self.player is not None and self.player.available:
            self.player.play(url, result.start_s, result.end_s)
        else:
            self._external_proc = player_mod.play_external(url, result.start_s, result.end_s)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if self.player is not None:
            self.player.shutdown()
        super().closeEvent(event)
