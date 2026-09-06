"""PySide6 main window for Omarchy Feature Search — master/detail layout.

Left: a browsable list of *all* features (group, name, command, thumbnail),
visible by default and reduced by the search box. Right: a detail panel for the
clicked item showing its name, summary, command(s) and an in-app video player.

Video playback downloads just the segment (the feature's timestamp range) as a
≤480p MP4 with AAC audio, then plays it in-app via ``QMediaPlayer``. First
click per segment takes ~20s (one-time download); subsequent clicks are instant.
Search runs in a background ``QThread`` so the UI never blocks.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
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
    QStackedLayout,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget

    _HAS_QT_MEDIA = True
except Exception:
    _HAS_QT_MEDIA = False

from omarchy_feature_search import data as data_mod
from omarchy_feature_search import player as player_mod
from omarchy_feature_search.search import Result, SearchEngine, results_from_doc
from omarchy_feature_search.theme import Theme, stylesheet

_LIST_THUMB_W, _LIST_THUMB_H = 104, 58
_VIDEO_W, _VIDEO_H = 420, 236

_FUN_PHRASES = [
    "Cleaning the lugnuts...",
    "Tweaking the pipes...",
    "Twisting the taps...",
    "Ungreasing the monkeys...",
    "Feeding the seagulls...",
    "Reading 1984...",
    "Learning how to yoyo...",
    "Fixing the hulahoops...",
    "Calibrating the flux capacitor...",
    "Warming up the hamsters...",
    "Polishing the doorknobs...",
    "Herding the cats...",
    "Untangling the spaghetti...",
    "Charging the crystals...",
]


def _load_pixmap(rel: str, w: int, h: int) -> QPixmap | None:
    p = data_mod.thumbnail_path(rel)
    if p is None:
        return None
    pix = QPixmap(str(p))
    if pix.isNull():
        return None
    return pix.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)


def _video_id(url: str) -> str:
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    return ""


def _format_summary(result: Result) -> str:
    """Build a rich-text informative summary of the feature in the Omarchy context."""
    # Clean up the transcript (strip repetitive auto-caption fragments)
    transcript = (result.transcript_summary or "").strip()
    # Take the first meaningful sentence as the description
    desc = transcript.split(".")[0].strip() if transcript else ""
    if len(desc) > 180:
        desc = desc[:177] + "..."

    # Build a YouTube search URL for more info about this command + omarchy
    vid = _video_id(result.video_url)
    search_q = f"omarchy {result.feature} {result.how_to}"
    search_url = (
        f"https://www.youtube.com/results?search_query="
        + search_q.replace(" ", "+")
    )

    parts = []
    if desc:
        parts.append(f"{desc}.")
    parts.append(f"<br><br><b>How to use:</b> {result.how_to}")
    parts.append(f"<br><b>Category:</b> {result.feature_group}")
    parts.append(f"<br><b>Timestamp:</b> {result.start_fmt} - {result.end_fmt}")
    parts.append(
        f'<br><br><a href="{search_url}">Search for more info on YouTube</a>'
    )
    return "".join(parts)


# --------------------------------------------------------------------------- #
# background threads
# --------------------------------------------------------------------------- #
class SearchWorker(QThread):
    resultsReady = Signal(object)

    def __init__(self, engine: SearchEngine, query: str, top_k: int):
        super().__init__()
        self._engine = engine
        self._query = query
        self._top_k = top_k

    def run(self) -> None:
        try:
            res = self._engine.search(self._query, top_k=self._top_k)
        except Exception:
            res = []
        self.resultsReady.emit(res)


class DownloadWorker(QThread):
    """Download just the segment to a cache file."""
    ready = Signal(object)  # str (local path) | None

    def __init__(self, video_id: str, start_s: int, end_s: int, video_url: str):
        super().__init__()
        self._id = video_id
        self._start = start_s
        self._end = end_s
        self._url = video_url

    def run(self) -> None:
        path = player_mod.ensure_segment_cached(self._id, self._start, self._end, self._url)
        self.ready.emit(str(path) if path else None)


class PreloadWorker(QThread):
    """Preload the semantic search model in the background so the first
    search is instant instead of a ~30s freeze."""
    ready = Signal(bool)

    def __init__(self, engine: SearchEngine):
        super().__init__()
        self._engine = engine

    def run(self) -> None:
        try:
            ok = self._engine.preload_semantic()
        except Exception:
            ok = False
        self.ready.emit(ok)


# --------------------------------------------------------------------------- #
# list row
# --------------------------------------------------------------------------- #
class ListItem(QFrame):
    selected = Signal(object)

    def __init__(self, result: Result, searching: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self._result = result
        self.setObjectName("listItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(74)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(12)

        thumb = QLabel(self)
        thumb.setFixedSize(_LIST_THUMB_W, _LIST_THUMB_H)
        thumb.setAlignment(Qt.AlignCenter)
        pix = _load_pixmap(result.thumbnail, _LIST_THUMB_W, _LIST_THUMB_H)
        if pix is not None:
            thumb.setPixmap(pix)
        else:
            thumb.setText(">")
            thumb.setStyleSheet("color: palette(mid);")
        row.addWidget(thumb, alignment=Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.setSpacing(8)
        group = QLabel(result.feature_group.upper(), self)
        group.setObjectName("listGroup")
        top.addWidget(group)
        ts = QLabel(f"{result.start_fmt}-{result.end_fmt}", self)
        ts.setObjectName("detailTimestamp")
        top.addWidget(ts)
        if searching:
            pct = QLabel(f"{result.confidence:.0f}%", self)
            pct.setObjectName("matchPct")
            top.addWidget(pct)
        top.addStretch(1)
        col.addLayout(top)

        name = QLabel(result.feature, self)
        name.setObjectName("listName")
        col.addWidget(name)

        cmd = QLabel(result.how_to, self)
        cmd.setObjectName("listCommand")
        col.addWidget(cmd)
        row.addLayout(col, 1)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.selected.emit(self._result)
        super().mousePressEvent(event)

    def set_selected(self, on: bool) -> None:
        self.setObjectName("listItemSelected" if on else "listItem")
        self.setStyle(self.style())


# --------------------------------------------------------------------------- #
# detail panel with in-app video player
# --------------------------------------------------------------------------- #
class DetailPanel(QFrame):
    playRequested = Signal(object)

    def __init__(self, theme: Theme, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("detailPanel")
        self._result: Result | None = None
        self._media_player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None
        self._downloader: DownloadWorker | None = None
        self._play_end_ms = 0

        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)

        # name + group/timestamp
        self.name = QLabel("", self)
        self.name.setObjectName("detailName")
        self.name.setWordWrap(True)
        v.addWidget(self.name)

        meta = QHBoxLayout()
        meta.setSpacing(10)
        self.group = QLabel("", self)
        self.group.setObjectName("detailGroup")
        meta.addWidget(self.group)
        self.timestamp = QLabel("", self)
        self.timestamp.setObjectName("detailTimestamp")
        meta.addWidget(self.timestamp)
        meta.addStretch(1)
        v.addLayout(meta)

        # summary
        self.sum_label = QLabel("SUMMARY", self)
        self.sum_label.setObjectName("sectionLabel")
        v.addWidget(self.sum_label)
        self.summary = QLabel("", self)
        self.summary.setObjectName("detailSummary")
        self.summary.setWordWrap(True)
        v.addWidget(self.summary)

        # command(s)
        self.cmd_label = QLabel("COMMAND(S)", self)
        self.cmd_label.setObjectName("sectionLabel")
        v.addWidget(self.cmd_label)
        block = QFrame(self)
        block.setObjectName("commandBlock")
        bl = QVBoxLayout(block)
        bl.setContentsMargins(12, 10, 12, 10)
        self.command = QLabel("", self)
        self.command.setObjectName("commandText")
        self.command.setWordWrap(True)
        self.command.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bl.addWidget(self.command)
        v.addWidget(block)

        # video area — stacked: page 0 = play button, page 1 = video widget
        self.vid_label = QLabel("VIDEO  -  click to play this segment", self)
        self.vid_label.setObjectName("sectionLabel")
        v.addWidget(self.vid_label)

        self._video_container = QFrame(self)
        self._video_container.setObjectName("commandBlock")
        self._video_container.setFixedSize(_VIDEO_W, _VIDEO_H)
        sl = QStackedLayout(self._video_container)

        self.play_btn = QPushButton(">  Play segment", self._video_container)
        self.play_btn.setObjectName("detailThumb")
        self.play_btn.setFixedSize(_VIDEO_W, _VIDEO_H)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.clicked.connect(self._on_play)
        sl.addWidget(self.play_btn)  # page 0

        if _HAS_QT_MEDIA:
            self.video_widget = QVideoWidget(self._video_container)
            self.video_widget.setFixedSize(_VIDEO_W, _VIDEO_H)
            sl.addWidget(self.video_widget)  # page 1
            self._media_player = QMediaPlayer(self)
            self._media_player.setVideoOutput(self.video_widget)
            # Qt6 requires an explicit QAudioOutput for sound
            self._audio_output = QAudioOutput(self)
            self._audio_output.setVolume(1.0)
            self._media_player.setAudioOutput(self._audio_output)
            self._video_page = 1
        else:
            self._video_page = -1

        # page 2: fun progress overlay with rotating tech phrases
        self._progress_page = 2
        self._progress_frame = QFrame(self._video_container)
        self._progress_frame.setObjectName("commandBlock")
        pl = QVBoxLayout(self._progress_frame)
        pl.setAlignment(Qt.AlignCenter)
        self._progress_phrase = QLabel(_FUN_PHRASES[0], self._progress_frame)
        self._progress_phrase.setObjectName("detailSummary")
        self._progress_phrase.setAlignment(Qt.AlignCenter)
        self._progress_phrase.setWordWrap(True)
        pl.addWidget(self._progress_phrase)
        sl.addWidget(self._progress_frame)
        # Timer that rotates the fun phrases
        self._phrase_timer = QTimer(self)
        self._phrase_timer.setInterval(1500)
        self._phrase_timer.timeout.connect(self._rotate_phrase)
        self._phrase_idx = 0

        v.addWidget(self._video_container)
        self.status_label = QLabel("", self)
        self.status_label.setObjectName("detailTimestamp")
        self.status_label.setAlignment(Qt.AlignCenter)
        v.addWidget(self.status_label)

        v.addStretch(1)
        self._show_placeholder()

    def _on_play(self) -> None:
        if self._result is not None:
            self.playRequested.emit(self._result)

    def _rotate_phrase(self) -> None:
        self._phrase_idx = (self._phrase_idx + 1) % len(_FUN_PHRASES)
        self._progress_phrase.setText(_FUN_PHRASES[self._phrase_idx])

    def _show_placeholder(self) -> None:
        self._result = None
        self.name.setText("")
        self.name.setObjectName("placeholder")
        self.group.setText("")
        self.timestamp.setText("")
        self.summary.setPixmap(QPixmap())
        self.summary.setText("Select a feature from the list to begin.")
        self.summary.setAlignment(Qt.AlignLeft)
        self.command.setText("")
        self.play_btn.setText(">  Play segment")
        self.play_btn.setIcon(QIcon())
        self.play_btn.show()
        self._video_container.layout().setCurrentIndex(0)
        self.status_label.setText("")

    def show_item(self, result: Result) -> None:
        self._result = result
        if self._media_player is not None:
            try:
                self._media_player.positionChanged.disconnect(self._on_position_changed)
            except Exception:
                pass
            self._media_player.stop()
        self._play_end_ms = 0
        self._video_container.layout().setCurrentIndex(0)
        self.play_btn.show()
        self.name.setText(result.feature)
        self.name.setObjectName("detailName")
        self.group.setText(result.feature_group.upper())
        self.timestamp.setText(f"{result.start_fmt} - {result.end_fmt}")
        # Clear any logo and show an informative summary
        self.summary.setPixmap(QPixmap())
        self.summary.setAlignment(Qt.AlignLeft)
        self.summary.setText(_format_summary(result))
        self.summary.setTextFormat(Qt.RichText)
        self.summary.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.summary.setOpenExternalLinks(True)
        self.command.setText(result.how_to)
        pix = _load_pixmap(result.thumbnail, _VIDEO_W, _VIDEO_H)
        if pix is not None:
            self.play_btn.setIcon(QIcon(pix))
            self.play_btn.setIconSize(self.play_btn.size())
            self.play_btn.setText("")
        else:
            self.play_btn.setIcon(QIcon())
            self.play_btn.setText(f">  Play  {result.start_fmt}")
        self.play_btn.show()
        self.status_label.setText("")

    def start_playback(self, result: Result) -> None:
        """Download segment (once), then play in-app via QMediaPlayer."""
        if not _HAS_QT_MEDIA or self._media_player is None:
            self.status_label.setText("Qt Multimedia unavailable.")
            return

        vid = _video_id(result.video_url)
        if not vid:
            self.status_label.setText("Could not parse video ID.")
            return

        # Check cache first — instant if already downloaded
        cpath = player_mod.segment_cache_path(vid, result.start_s, result.end_s)
        if cpath.exists() and cpath.stat().st_size > 50_000:
            self._play_local(str(cpath), result)
            return

        # Download in background thread with fun progress overlay
        self._video_container.layout().setCurrentIndex(self._progress_page)
        self._phrase_idx = 0
        self._progress_phrase.setText(_FUN_PHRASES[0])
        self._phrase_timer.start()
        self._downloader = DownloadWorker(vid, result.start_s, result.end_s, result.video_url)
        self._downloader.ready.connect(lambda path, r=result: self._on_downloaded(path, r))
        self._downloader.finished.connect(self._downloader.deleteLater)
        self._downloader.start()

    def _on_downloaded(self, local_path: str | None, result: Result) -> None:
        self._phrase_timer.stop()
        if local_path:
            self._play_local(local_path, result)
        else:
            self._video_container.layout().setCurrentIndex(0)
            self.play_btn.show()
            self.status_label.setText("Download failed. Try again or check network.")

    def _play_local(self, local_path: str, result: Result) -> None:
        """Play a local segment file in-app. The file is already just the
        segment, so we play from the start (no seeking needed)."""
        self._video_container.layout().setCurrentIndex(self._video_page)
        self.play_btn.hide()
        self._play_end_ms = int(result.end_s - result.start_s) * 1000
        try:
            self._media_player.setSource(QUrl.fromLocalFile(local_path))
            self._media_player.play()
            self._media_player.positionChanged.connect(self._on_position_changed)
            self.status_label.setText("Playing segment")
        except Exception:
            self.status_label.setText("Playback error.")

    def _on_position_changed(self, position: int) -> None:
        """Pause when we reach the clip's end."""
        if self._play_end_ms > 0 and position >= self._play_end_ms:
            if self._media_player is not None:
                try:
                    self._media_player.positionChanged.disconnect(self._on_position_changed)
                except Exception:
                    pass
                self._media_player.pause()
                self.status_label.setText("Reached end of segment")

    def shutdown(self) -> None:
        if self._media_player is not None:
            self._media_player.stop()
        if self._downloader is not None and self._downloader.isRunning():
            self._downloader.quit()
            self._downloader.wait(2000)


# --------------------------------------------------------------------------- #
# main window
# --------------------------------------------------------------------------- #
class MainWindow(QMainWindow):
    def __init__(self, theme: Theme | None = None, features_doc: dict | None = None):
        super().__init__()
        from omarchy_feature_search.theme import load_theme

        self.theme = theme if theme is not None else load_theme()
        self.setWindowTitle("Omarchy Feature Search")
        self.resize(1240, 800)
        if data_mod.icon_path().exists():
            self.setWindowIcon(QIcon(str(data_mod.icon_path())))
        self.setStyleSheet(stylesheet(self.theme))

        self.engine = SearchEngine(features_doc)
        self._all_results: list[Result] = results_from_doc(self.engine.doc)
        self._current: Result | None = None
        self._workers: list[SearchWorker] = []
        self._search_seq = 0

        central = QWidget(self)
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(16, 14, 16, 12)
        outer.setSpacing(10)

        outer.addLayout(self._build_header())

        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.addWidget(self._build_list_pane())
        self.detail = DetailPanel(self.theme, self)
        self.detail.playRequested.connect(self._play)
        self.splitter.addWidget(self.detail)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([700, 500])
        outer.addWidget(self.splitter, 1)

        self.status = QLabel("", self)
        self.status.setObjectName("statusBar")
        outer.addWidget(self.status)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._on_search_due)
        self.search_box.textChanged.connect(self._timer.start)

        self._populate(self._all_results, searching=False)
        self._update_status()

        # Preload the semantic model in the background so the first search
        # is instant (keyword) and switches to semantic once ready.
        self._preload_worker = PreloadWorker(self.engine)
        self._preload_worker.ready.connect(self._on_semantic_ready)
        self._preload_worker.finished.connect(self._preload_worker.deleteLater)
        self._preload_worker.start()

    def _on_semantic_ready(self, ok: bool) -> None:
        if ok:
            self._update_status()

    def _build_header(self) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setSpacing(12)
        logo_path = data_mod.logo_path()
        if logo_path.exists():
            logo = QLabel(self)
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                logo.setPixmap(pix.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            h.addWidget(logo, alignment=Qt.AlignVCenter)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("Omarchy Feature Search", self)
        title.setObjectName("headerTitle")
        titles.addWidget(title)
        sub = QLabel("NetworkChuck - searchable feature knowledge base", self)
        sub.setObjectName("headerSub")
        titles.addWidget(sub)
        h.addLayout(titles)
        h.addStretch(1)

        self.search_box = QLineEdit(self)
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("Search to filter...  e.g. screenshot, install package, workspace, night light")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setMinimumHeight(44)
        self.search_box.returnPressed.connect(self._on_search_due)
        h.addWidget(self.search_box, 3)
        return h

    def _build_list_pane(self) -> QWidget:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget(scroll)
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0, 0, 6, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    def _clear_list(self) -> None:
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _populate(self, results: list[Result], searching: bool) -> None:
        self._clear_list()
        for r in results:
            it = ListItem(r, searching, self)
            it.selected.connect(self._on_select)
            self.list_layout.insertWidget(self.list_layout.count() - 1, it)
        if self._current is not None:
            self._highlight_current()

    def _on_search_due(self) -> None:
        q = self.search_box.text().strip()
        if not q:
            self._populate(self._all_results, searching=False)
            self._update_status()
            return
        self._search_seq += 1
        seq = self._search_seq
        self.status.setText(f"searching '{q}'...  (backend: {self.engine.backend})")
        worker = SearchWorker(self.engine, q, top_k=40)
        worker.resultsReady.connect(lambda res, s=seq: self._on_results(res, s))
        worker.finished.connect(worker.deleteLater)
        self._workers.append(worker)
        worker.start()

    def _on_results(self, results: list[Result], seq: int) -> None:
        if seq != self._search_seq:
            return
        if not results:
            self._clear_list()
            none = QLabel("No matches. Try different keywords.", self)
            none.setObjectName("placeholder")
            none.setWordWrap(True)
            self.list_layout.insertWidget(0, none)
        else:
            self._populate(results, searching=True)
        self._update_status(match_count=len(results))

    def _on_select(self, result: Result) -> None:
        self._current = result
        self.detail.show_item(result)
        self._highlight_current()
        self._update_status()

    def _highlight_current(self) -> None:
        for i in range(self.list_layout.count() - 1):
            w = self.list_layout.itemAt(i).widget()
            if isinstance(w, ListItem):
                w.set_selected(w._result is self._current)

    def _play(self, result: Result) -> None:
        self.detail.start_playback(result)
        self.status.setText(f"playing: {result.feature}  -  {result.start_fmt}-{result.end_fmt}")

    def _update_status(self, match_count: int | None = None) -> None:
        q = self.search_box.text().strip()
        if q:
            n = 0 if match_count is None else match_count
            txt = f"backend: {self.engine.backend}  |  {n} matches for '{q}'"
        else:
            txt = f"backend: {self.engine.backend}  |  {len(self._all_results)} features  |  type to filter"
        if self._current is not None:
            txt += f"  |  selected: {self._current.feature}"
        self.status.setText(txt)

    def closeEvent(self, event) -> None:
        self.detail.shutdown()
        for w in self._workers:
            if w.isRunning():
                w.quit()
                w.wait(2000)
        super().closeEvent(event)
