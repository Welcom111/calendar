import json
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import caldav
import keyring
from PySide6.QtCore import QDate, QObject, QPoint, QRunnable, QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap, QPolygon
from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QCalendarWidget, QComboBox, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
    QStackedWidget, QSystemTrayIcon, QToolButton, QVBoxLayout, QWidget,
)


APP_NAME = "Календарь CalDAV"
SERVICE_NAME = "QuickCalendarCalDAV"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = (Path(os.environ.get("APPDATA", Path.home())) / "QuickCalendar"
            if getattr(sys, "frozen", False) else BASE_DIR)
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "settings.json"

WEEKDAYS = ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье")
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря")


def app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#246bfd"))
    p.drawRoundedRect(6, 8, 52, 50, 9, 9)
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(12, 19, 40, 32, 4, 4)
    p.setBrush(QColor("#246bfd"))
    for x in (18, 29, 40):
        p.drawEllipse(x, 27, 6, 6)
        p.drawEllipse(x, 38, 6, 6)
    p.end()
    return QIcon(pixmap)


def chevron_icon(points) -> QIcon:
    """Create a blue calendar arrow independent of the Windows icon theme."""
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = painter.pen()
    pen.setColor(QColor("#246bfd"))
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline(QPolygon(points))
    painter.end()
    return QIcon(pixmap)


STYLE = """
QWidget { font-family: "Segoe UI Variable", "Segoe UI"; font-size: 13px; color: #172033; }
#panel { background: #f8fafc; border: 1px solid #e5eaf1; border-radius: 22px; }
#clockPanel { background: #246bfd; border: 1px solid #1857db; border-radius: 16px; }
QLabel#eyebrow { color: #708096; font-size: 11px; font-weight: 700; }
QLabel#title { color: #172033; font-size: 23px; font-weight: 700; }
QLabel#sectionTitle { color: #172033; font-size: 16px; font-weight: 700; }
QLabel#fieldLabel { color: #536176; font-size: 12px; font-weight: 600; }
QLabel#helperText { color: #708096; font-size: 11px; }
QLabel#clock { color: #ffffff; font-size: 24px; font-weight: 700; }
QLabel#clockDate { color: #dce8ff; font-size: 12px; }
QLabel#status { color: #708096; background: #ffffff; border: 1px dashed #d7dee9;
    border-radius: 12px; padding: 14px; }
QFrame#settingsCard { background: #ffffff; border: 1px solid #e5eaf1; border-radius: 16px; }
QFrame#eventCard { background: #ffffff; border: 1px solid #e5eaf1; border-radius: 12px; }
QFrame#eventAccent { background: #246bfd; border: none; border-radius: 2px; }
QLabel#eventTime { color: #246bfd; font-size: 11px; font-weight: 700; }
QLabel#eventTitle { color: #172033; font-size: 14px; font-weight: 600; }
QLabel#eventMeta { color: #708096; font-size: 11px; }
QLineEdit, QComboBox { min-height: 22px; background: #f8fafc; color: #172033;
    border: 1px solid #d7dee9; border-radius: 10px; padding: 8px 11px;
    selection-background-color: #246bfd; }
QLineEdit:hover, QComboBox:hover { border-color: #aebbd0; }
QLineEdit:focus, QComboBox:focus { background: #ffffff; border: 2px solid #246bfd; padding: 7px 10px; }
QPushButton { border: none; background: #edf2f8; color: #344258; border-radius: 10px;
    padding: 9px 13px; font-weight: 600; }
QPushButton:hover { background: #e2e9f3; }
QPushButton:pressed { background: #d6dfec; }
QPushButton#iconButton { font-size: 17px; padding: 0; }
QPushButton#primary { background: #246bfd; color: white; }
QPushButton#primary:hover { background: #1857db; }
QListWidget { border: none; background: transparent; outline: none; }
QListWidget::item { background: transparent; border: none; padding: 3px 0; }
QCalendarWidget { background: #ffffff; border: 1px solid #e5eaf1; border-radius: 16px; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: #ffffff; border-bottom: 1px solid #edf1f6; }
QCalendarWidget QAbstractItemView { background: #ffffff; color: #344258; border: none;
    selection-background-color: #246bfd; selection-color: white; outline: none; }
QCalendarWidget QToolButton { color: #344258; background: transparent; border-radius: 8px;
    padding: 6px; font-weight: 600; }
QCalendarWidget QToolButton:hover { background: #edf2f8; }
QCalendarWidget QMenu { background: #ffffff; color: #172033; border: 1px solid #d7dee9; }
QScrollBar:vertical { width: 7px; background: transparent; margin: 2px 0; }
QScrollBar::handle:vertical { background: #c7d1df; border-radius: 3px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QMessageBox { background: #f8fafc; }
QMessageBox QLabel { color: #172033; min-width: 260px; }
QMessageBox QPushButton { background: #246bfd; color: white; min-width: 82px; }
"""


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class Worker(QRunnable):
    def __init__(self, operation):
        super().__init__()
        self.operation = operation
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.finished.emit(self.operation())
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class ClockWidget(QFrame):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("clockPanel")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(245, 68)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 5, 14, 6)
        layout.setSpacing(0)
        self.clock = QLabel()
        self.clock.setObjectName("clock")
        self.clock_date = QLabel()
        self.clock_date.setObjectName("clockDate")
        layout.addWidget(self.clock)
        layout.addWidget(self.clock_date)
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(250)
        self.update_time()

    def update_time(self):
        now = datetime.now()
        self.clock.setText(now.strftime("%H:%M:%S"))
        self.clock_date.setText(
            f"{WEEKDAYS[now.weekday()]}, {now.day:02d}.{now.month:02d}.{now.year}"
        )

    def place_near_taskbar(self):
        area = QApplication.primaryScreen().availableGeometry()
        self.move(area.right() - self.width() - 10, area.bottom() - self.height() - 6)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class EventCard(QFrame):
    def __init__(self, event):
        super().__init__()
        self.setObjectName("eventCard")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 9, 12, 9)
        row.setSpacing(11)

        accent = QFrame()
        accent.setObjectName("eventAccent")
        accent.setFixedWidth(4)
        row.addWidget(accent)

        content = QVBoxLayout()
        content.setSpacing(2)
        when = event["when"]
        time_text = when.strftime("%d.%m") + ("  ·  весь день" if event["all_day"] else when.strftime("  ·  %H:%M"))
        time_label = QLabel(time_text.upper())
        time_label.setObjectName("eventTime")
        title = QLabel(event["summary"])
        title.setObjectName("eventTitle")
        title.setWordWrap(True)
        content.addWidget(time_label)
        content.addWidget(title)
        meta_parts = [part for part in (event["location"], event["calendar"]) if part]
        if meta_parts:
            meta = QLabel("  ·  ".join(meta_parts))
            meta.setObjectName("eventMeta")
            meta.setWordWrap(True)
            content.addWidget(meta)
        row.addLayout(content, 1)


class CalendarWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.config = self.load_config()
        self.pool = QThreadPool.globalInstance()
        self.workers = set()
        self.generation = 0
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(470, 700)
        self.setStyleSheet(STYLE)
        self.build_ui()

    @staticmethod
    def load_config():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def password(self, url=None, user=None):
        key = f"{url or self.config.get('url', '')}|{user or self.config.get('user', '')}"
        try:
            return keyring.get_password(SERVICE_NAME, key) or ""
        except keyring.errors.KeyringError:
            return ""

    def build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        panel = QFrame()
        panel.setObjectName("panel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(22, 32, 51, 45))
        panel.setGraphicsEffect(shadow)
        outer.addWidget(panel)
        root = QVBoxLayout(panel)
        root.setContentsMargins(20, 20, 20, 20)
        self.pages = QStackedWidget()
        root.addWidget(self.pages)
        self.pages.addWidget(self.build_calendar_page())
        self.pages.addWidget(self.build_settings_page())

    def build_calendar_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(1)
        eyebrow = QLabel("CALDAV · МОИ СОБЫТИЯ")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Календарь")
        title.setObjectName("title")
        settings = QPushButton("⚙")
        settings.setObjectName("iconButton")
        settings.setToolTip("Настройки CalDAV")
        settings.setFixedSize(40, 40)
        settings.clicked.connect(self.open_settings)
        heading.addWidget(eyebrow)
        heading.addWidget(title)
        header.addLayout(heading)
        header.addStretch()
        header.addWidget(settings)
        layout.addLayout(header)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar.setFixedHeight(285)
        previous = self.calendar.findChild(QToolButton, "qt_calendar_prevmonth")
        following = self.calendar.findChild(QToolButton, "qt_calendar_nextmonth")
        if previous:
            previous.setIcon(chevron_icon([QPoint(12, 5), QPoint(7, 10), QPoint(12, 15)]))
            previous.setIconSize(QSize(20, 20))
        if following:
            following.setIcon(chevron_icon([QPoint(8, 5), QPoint(13, 10), QPoint(8, 15)]))
            following.setIconSize(QSize(20, 20))
        self.calendar.currentPageChanged.connect(self.month_changed)
        layout.addWidget(self.calendar)
        self.range_label = QLabel()
        self.range_label.setObjectName("sectionTitle")
        layout.addSpacing(6)
        layout.addWidget(self.range_label)
        self.status = QLabel()
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.events = QListWidget()
        self.events.setSpacing(2)
        self.events.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        layout.addWidget(self.events, 1)
        return page

    def build_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        back = QPushButton("← Назад")
        back.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        title = QLabel("CalDAV")
        title.setObjectName("title")
        header.addWidget(back)
        header.addStretch()
        header.addWidget(title)
        layout.addLayout(header)
        layout.addSpacing(18)
        card = QFrame()
        card.setObjectName("settingsCard")
        form = QVBoxLayout(card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(7)
        intro = QLabel("Подключение к календарю")
        intro.setObjectName("sectionTitle")
        form.addWidget(intro)
        hint = QLabel("Данные хранятся локально, пароль — в защищённом хранилище Windows.")
        hint.setObjectName("helperText")
        hint.setWordWrap(True)
        form.addWidget(hint)
        field = QLabel("URL CalDAV")
        field.setObjectName("fieldLabel")
        form.addWidget(field)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://cloud.example.com/remote.php/dav")
        form.addWidget(self.url_input)
        field = QLabel("Имя пользователя")
        field.setObjectName("fieldLabel")
        form.addWidget(field)
        self.user_input = QLineEdit()
        form.addWidget(self.user_input)
        field = QLabel("Пароль приложения")
        field.setObjectName("fieldLabel")
        form.addWidget(field)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Оставьте пустым, чтобы не менять")
        form.addWidget(self.password_input)
        field = QLabel("Название календаря (необязательно)")
        field.setObjectName("fieldLabel")
        form.addWidget(field)
        self.calendar_input = QLineEdit()
        self.calendar_input.setPlaceholderText("Пусто — показывать все календари")
        form.addWidget(self.calendar_input)
        layout.addWidget(card)
        test = QPushButton("Проверить подключение")
        test.clicked.connect(self.test_connection)
        layout.addWidget(test)
        save = QPushButton("Сохранить настройки")
        save.setObjectName("primary")
        save.clicked.connect(self.save_settings)
        layout.addWidget(save)
        layout.addStretch()
        return page

    def open_settings(self):
        self.url_input.setText(self.config.get("url", ""))
        self.user_input.setText(self.config.get("user", ""))
        self.calendar_input.setText(self.config.get("calendar", ""))
        self.password_input.clear()
        self.pages.setCurrentIndex(1)

    def credentials_from_form(self):
        url = self.url_input.text().strip().rstrip("/") + "/"
        user = self.user_input.text().strip()
        password = self.password_input.text() or self.password(url, user)
        return url, user, password

    def test_connection(self):
        url, user, password = self.credentials_from_form()
        if not url.startswith(("http://", "https://")) or not user or not password:
            QMessageBox.information(self, APP_NAME, "Заполните URL, логин и пароль приложения.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            with caldav.get_davclient(url=url, username=user, password=password) as client:
                count = len(client.principal().get_calendars())
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Подключиться не удалось:\n{exc}")
        else:
            QMessageBox.information(self, APP_NAME, f"Подключение установлено. Календарей: {count}.")
        finally:
            QApplication.restoreOverrideCursor()

    def save_settings(self):
        url, user, password = self.credentials_from_form()
        if not url.startswith(("http://", "https://")) or not user or not password:
            QMessageBox.information(self, APP_NAME, "Заполните URL, логин и пароль приложения.")
            return
        try:
            keyring.set_password(SERVICE_NAME, f"{url}|{user}", password)
            self.config = {"url": url, "user": user, "calendar": self.calendar_input.text().strip()}
            CONFIG_FILE.write_text(json.dumps(self.config, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, keyring.errors.KeyringError) as exc:
            QMessageBox.warning(self, APP_NAME, f"Не удалось сохранить настройки:\n{exc}")
            return
        self.pages.setCurrentIndex(0)
        self.load_default_range()

    def show_near_tray(self):
        area = QApplication.primaryScreen().availableGeometry()
        x = area.right() - self.width() - 10
        y = area.bottom() - self.height() - 10
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def load_default_range(self):
        today = date.today()
        self.calendar.blockSignals(True)
        self.calendar.setSelectedDate(QDate(today.year, today.month, today.day))
        self.calendar.setCurrentPage(today.year, today.month)
        self.calendar.blockSignals(False)
        self.load_month(today.year, today.month)

    def month_changed(self, year: int, month: int):
        self.load_month(year, month)

    def load_month(self, year: int, month: int):
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        label = f"{MONTHS[month - 1].capitalize()} {year}"
        self.load_events(start, end, label)

    def load_events(self, start: date, end: date, label: str):
        self.generation += 1
        generation = self.generation
        self.events.clear()
        self.range_label.setText(label)
        self.status.setText("Загрузка событий…")
        self.status.show()
        url, user = self.config.get("url", ""), self.config.get("user", "")
        password = self.password()
        if not url or not user or not password:
            self.status.setText("Откройте настройки ⚙ и укажите подключение CalDAV.")
            return
        calendar_name = self.config.get("calendar", "")
        worker = Worker(lambda: self.fetch_events(url, user, password, calendar_name, start, end))
        self.workers.add(worker)
        worker.signals.finished.connect(lambda data, w=worker, g=generation: self.events_loaded(w, g, data))
        worker.signals.failed.connect(lambda error, w=worker, g=generation: self.events_failed(w, g, error))
        self.pool.start(worker)

    @staticmethod
    def fetch_events(url, user, password, calendar_name, start, end):
        result = []
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.min)
        with caldav.get_davclient(url=url, username=user, password=password) as client:
            calendars = client.principal().get_calendars()
            if calendar_name:
                calendars = [c for c in calendars if (c.name or "").casefold() == calendar_name.casefold()]
            for calendar in calendars:
                for event in calendar.search(start=start_dt, end=end_dt, event=True, expand=True):
                    instance = event.vobject_instance
                    component = getattr(instance, "vevent", None) if instance else None
                    if component is None or not hasattr(component, "dtstart"):
                        continue
                    begins = component.dtstart.value
                    summary = getattr(getattr(component, "summary", None), "value", "Без названия")
                    location = getattr(getattr(component, "location", None), "value", "")
                    all_day = isinstance(begins, date) and not isinstance(begins, datetime)
                    when = datetime.combine(begins, time.min) if all_day else begins
                    if isinstance(when, datetime) and when.tzinfo:
                        when = when.astimezone()
                    result.append({"when": when, "all_day": all_day, "summary": str(summary),
                                   "location": str(location), "calendar": calendar.name or "Календарь"})
        return sorted(result, key=lambda item: item["when"].replace(tzinfo=None))

    def events_loaded(self, worker, generation, data):
        self.workers.discard(worker)
        if generation != self.generation:
            return
        self.status.setText("Событий нет" if not data else "")
        self.status.setVisible(not data)
        for event in data:
            card = EventCard(event)
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, card.sizeHint().height() + 6))
            item.setToolTip(event["calendar"])
            self.events.addItem(item)
            self.events.setItemWidget(item, card)

    def events_failed(self, worker, generation, error):
        self.workers.discard(worker)
        if generation != self.generation:
            return
        self.status.setText(f"Не удалось загрузить события:\n{error}")
        self.status.show()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.pages.currentIndex() == 1:
                self.pages.setCurrentIndex(0)
            else:
                self.hide()
            return
        super().keyPressEvent(event)


class CalendarApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(APP_NAME)
        self.app.setQuitOnLastWindowClosed(False)
        self.window = CalendarWindow()
        self.tray = QSystemTrayIcon(app_icon(), self.app)
        menu = QMenu()
        open_action = QAction("Открыть календарь", menu)
        open_action.triggered.connect(self.toggle_window)
        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self.app.quit)
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.toggle_window()
                                    if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tooltip_timer = QTimer(self.app)
        self.tooltip_timer.timeout.connect(self.update_tray_tooltip)
        self.tooltip_timer.start(1000)
        self.update_tray_tooltip()

    def update_tray_tooltip(self):
        now = datetime.now()
        self.tray.setToolTip(
            f"{now:%H:%M:%S}\n"
            f"{WEEKDAYS[now.weekday()]}, {now.day:02d}.{now.month:02d}.{now.year}"
        )

    def toggle_window(self):
        if self.window.isVisible():
            self.window.hide()
        else:
            self.window.show_near_tray()
            self.window.load_default_range()

    def run(self):
        self.tray.show()
        return self.app.exec()


if __name__ == "__main__":
    raise SystemExit(CalendarApp().run())
