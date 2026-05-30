import sys
import sqlite3
import hashlib
import time
from datetime import datetime

from PyQt6 import uic
from PyQt6.QtWidgets import (  # Виджеты интерфейса
    QApplication, QWidget, QMessageBox, QTableWidgetItem,
    QLabel, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPixmap

from styles import ROSNEFT_STYLES
from user_tabs import UserTabsWidget

DB_PATH = "users.db"
MAX_HOURS_SCALE = 12.0

def hash_password(password: str) -> str:
    """
    Хэширует пароль с использованием алгоритма SHA-256

    Args:
        password (str): Исходный пароль в виде строки

    Returns:
        str: Хэшированный пароль в виде 64-символьной hex-строки

    Пример:
        >>> hash_password("mypassword123")
        'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def ensure_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Создаем таблицу пользователей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Уникальный ID
            name TEXT,                              -- Имя
            surname TEXT,                           -- Фамилия
            patronymic TEXT,                        -- Отчество
            email TEXT UNIQUE,                      -- Email (уникальный, для входа)
            phone TEXT,                             -- Телефон
            password TEXT,                          -- Хэш пароля (SHA-256)
            position TEXT                           -- Должность
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usage_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,   -- Уникальный ID
            user_id INTEGER,                        -- ID пользователя (внешний ключ)
            day INTEGER,                            -- День недели (0-6, где 0=Пн)
            hours REAL,                             -- Количество часов (дробное число)
            UNIQUE(user_id, day),                   -- Один пользователь = один день
            FOREIGN KEY(user_id) REFERENCES users(id)  -- Связь с таблицей users
        )
    """)

    conn.commit()
    conn.close()


def create_empty_usage_for_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for d in range(7):
        # INSERT OR IGNORE - вставляет только если записи еще нет
        cur.execute(
            "INSERT OR IGNORE INTO usage_hours (user_id, day, hours) VALUES (?, ?, ?)",
            (user_id, d, 0.0)
        )

    conn.commit()  # Сохраняем изменения
    conn.close()  # Закрываем соединение


def color_for_hours(hours):
    maxh = MAX_HOURS_SCALE
    ratio = min(hours / maxh, 1.0)  # Нормализуем значение в диапазон 0-1

    if ratio < 0.5:
        local_ratio = ratio * 2  # Масштабируем 0-0.5 в 0-1
        r1, g1, b1 = 255, 255, 255  # RGB белого цвета
        r2, g2, b2 = 253, 210, 0
        r = int(r1 + (r2 - r1) * local_ratio)
        g = int(g1 + (g2 - g1) * local_ratio)
        b = int(b1 + (b2 - b1) * local_ratio)
    else:
        local_ratio = (ratio - 0.5) * 2  # Масштабируем 0.5-1 в 0-1
        r1, g1, b1 = 253, 210, 0  # RGB желтого
        r2, g2, b2 = 0, 0, 0  # RGB черного
        r = int(r1 + (r2 - r1) * local_ratio)
        g = int(g1 + (g2 - g1) * local_ratio)
        b = int(b1 + (b2 - b1) * local_ratio)

    return QColor(r, g, b)


class MainApp(QWidget):
    def __init__(self):
        super().__init__()

        # Загружаем интерфейс из файла Qt Designer
        uic.loadUi("interface_1.ui", self)

        self.setStyleSheet(ROSNEFT_STYLES)

        ensure_db()
        self.stacked = self.findChild(QWidget, "stackedWidget")
        self.page_login = self.findChild(QWidget, "page_login")  # Страница входа
        self.page_register = self.findChild(QWidget, "page_register")  # Страница регистрации
        self.page_main = self.findChild(QWidget, "page_main")  # Главная страница

        self.le_login_email = self.findChild(type(self.le_login_email if hasattr(self, 'le_login_email') else None),
                                             "le_login_email")  # Поле Email
        self.le_login_password = self.findChild(
            type(self.le_login_password if hasattr(self, 'le_login_password') else None),
            "le_login_password")  # Поле пароля
        self.btn_login = self.findChild(type(self.btn_login if hasattr(self, 'btn_login') else None),
                                        "btn_login")  # Кнопка "Войти"
        self.btn_go_register = self.findChild(type(self.btn_go_register if hasattr(self, 'btn_go_register') else None),
                                              "btn_go_register")  # Кнопка перехода к регистрации
        self.label_login_info = self.findChild(
            type(self.label_login_info if hasattr(self, 'label_login_info') else None),
            "label_login_info")  # Метка для ошибок

        self.le_name = self.findChild(type(self.le_name if hasattr(self, 'le_name') else None), "le_name")  # Поле "Имя"
        self.le_surname = self.findChild(type(self.le_surname if hasattr(self, 'le_surname') else None),
                                         "le_surname")  # Поле "Фамилия"
        self.le_patronymic = self.findChild(type(self.le_patronymic if hasattr(self, 'le_patronymic') else None),
                                            "le_patronymic")  # Поле "Отчество"
        self.le_email = self.findChild(type(self.le_email if hasattr(self, 'le_email') else None),
                                       "le_email")  # Поле "Email"
        self.le_phone = self.findChild(type(self.le_phone if hasattr(self, 'le_phone') else None),
                                       "le_phone")  # Поле "Телефон"
        self.le_password = self.findChild(type(self.le_password if hasattr(self, 'le_password') else None),
                                          "le_password")  # Поле "Пароль"
        self.le_confirm = self.findChild(type(self.le_confirm if hasattr(self, 'le_confirm') else None),
                                         "le_confirm")  # Поле "Подтверждение пароля"
        self.le_position = self.findChild(type(self.le_position if hasattr(self, 'le_position') else None),
                                          "le_position")  # Поле "Должность"
        self.btn_register = self.findChild(type(self.btn_register if hasattr(self, 'btn_register') else None),
                                           "btn_register")  # Кнопка "Зарегистрироваться"
        self.btn_back_to_login = self.findChild(
            type(self.btn_back_to_login if hasattr(self, 'btn_back_to_login') else None),
            "btn_back_to_login")  # Кнопка "Назад"
        self.label_register_info = self.findChild(
            type(self.label_register_info if hasattr(self, 'label_register_info') else None),
            "label_register_info")  # Метка для ошибок

        # === ВИДЖЕТЫ ГЛАВНОЙ СТРАНИЦЫ (для обратной совместимости) ===
        self.lbl_fullname = self.findChild(QLabel, "lbl_fullname")  # Метка ФИО (скрыта, используются табы)
        self.lbl_email = self.findChild(QLabel, "lbl_email")  # Метка Email (скрыта)
        self.lbl_position = self.findChild(QLabel, "lbl_position")  # Метка должности (скрыта)
        self.table_heatmap = self.findChild(type(self.table_heatmap if hasattr(self, 'table_heatmap') else None),
                                            "table_heatmap")  # Старая таблица (скрыта)
        self.btn_logout = self.findChild(type(self.btn_logout if hasattr(self, 'btn_logout') else None),
                                         "btn_logout")  # Кнопка "Выход"

        self._setup_tabs_on_main_page()

        self.btn_go_register.clicked.connect(self.show_register)  # Переход к регистрации
        self.btn_back_to_login.clicked.connect(self.show_login)  # Возврат к входу
        self.btn_register.clicked.connect(self.do_register)  # Выполнить регистрацию
        self.btn_login.clicked.connect(self.do_login)  # Выполнить вход
        self.btn_logout.clicked.connect(self.do_logout)  # Выполнить выход

        if self.table_heatmap:
            days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            self.table_heatmap.setColumnCount(7)  # 7 столбцов (дни недели)
            self.table_heatmap.setRowCount(1)  # 1 строка
            self.table_heatmap.setHorizontalHeaderLabels(days)  # Заголовки столбцов
            self.table_heatmap.verticalHeader().setVisible(False)  # Скрыть вертикальный заголовок
            self.table_heatmap.setEditTriggers(self.table_heatmap.EditTrigger.NoEditTriggers)  # Только чтение
            self.table_heatmap.setSelectionMode(self.table_heatmap.SelectionMode.NoSelection)

        self.current_user_id = None
        self.session_start_time = None
        self.session_seconds = 0

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)

        self._apply_modern_effects()
        self._setup_logo()

        self.show_login()

    def _apply_modern_effects(self):
        self.setMinimumSize(400, 500)

    def _setup_tabs_on_main_page(self):
        self.tabs_widget = UserTabsWidget(self.page_main)

        # Получаем layout главной страницы
        main_layout = self.page_main.layout()

        if main_layout is None:
            main_layout = QVBoxLayout(self.page_main)
            main_layout.setContentsMargins(10, 10, 10, 10)
            self.page_main.setLayout(main_layout)

        header_layout = QHBoxLayout()

        if self.lbl_fullname:
            self.lbl_fullname.hide()
        if self.lbl_email:
            self.lbl_email.hide()
        if self.lbl_position:
            self.lbl_position.hide()

        welcome_label = QLabel("Добро пожаловать!")
        welcome_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #000000;")
        header_layout.addWidget(welcome_label)

        header_layout.addStretch()

        if self.btn_logout:
            header_layout.addWidget(self.btn_logout)

        main_layout.insertLayout(0, header_layout)

        if self.table_heatmap:
            self.table_heatmap.hide()

        main_layout.addWidget(self.tabs_widget)

    def _setup_logo(self):
        logo_path = "rosneft.png"
        pixmap = QPixmap(logo_path)

        if pixmap.isNull():
            print(f"Внимание: Логотип {logo_path} не найден")
            return

        scaled_pixmap = pixmap.scaled(150, 80, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)

        self._add_logo_to_page(self.page_login, scaled_pixmap)

        self._add_logo_to_page(self.page_register, scaled_pixmap)

        self._add_logo_to_page(self.page_main, scaled_pixmap)

    def _add_logo_to_page(self, page, pixmap):
        logo_label = page.findChild(QLabel, "logo_label")

        if logo_label is None:
            logo_label = QLabel(page)
            logo_label.setObjectName("logo_label")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            logo_label.setMinimumHeight(pixmap.height())
            logo_label.setMaximumHeight(pixmap.height() + 20)

            page_layout = page.layout()

            if page_layout is not None:
                page_layout.insertWidget(0, logo_label)
                spacer = QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
                page_layout.insertItem(1, spacer)
            else:
                new_layout = QVBoxLayout(page)
                new_layout.setContentsMargins(10, 10, 10, 10)

                new_layout.addWidget(logo_label)

                spacer = QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
                new_layout.addItem(spacer)

                for child in page.findChildren(QWidget):
                    if child != logo_label and child.parent() == page:
                        new_layout.addWidget(child)

                page.setLayout(new_layout)

        logo_label.setPixmap(pixmap)
        logo_label.setScaledContents(False)

    def show_login(self):
        self._switch_page(self.page_login)
        self.label_login_info.setText("")

    def show_register(self):
        self._switch_page(self.page_register)
        self.label_register_info.setText("")

    def show_main(self):
        self._switch_page(self.page_main)

    def _switch_page(self, target_page):
        self.stacked.setCurrentWidget(target_page)

    def do_register(self):
        name = self.le_name.text().strip()
        surname = self.le_surname.text().strip()
        patronymic = self.le_patronymic.text().strip()
        email = self.le_email.text().strip().lower()  # Email в нижнем регистре
        phone = self.le_phone.text().strip()
        password = self.le_password.text()
        confirm = self.le_confirm.text()
        position = self.le_position.text().strip()

        if not (name and surname and email and password and confirm and position):
            self.label_register_info.setText("Заполните обязательные поля.")
            return

        if password != confirm:
            self.label_register_info.setText("Пароли не совпадают.")
            return

        if "@" not in email:
            self.label_register_info.setText("Неправильный формат почты.")
            return

        hp = hash_password(password)

        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""INSERT INTO users (name, surname, patronymic, email, phone, password, position)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (name, surname, patronymic, email, phone, hp, position))
            conn.commit()
            user_id = cur.lastrowid
            conn.close()

            create_empty_usage_for_user(user_id)

            QMessageBox.information(self, "Успех", "Пользователь зарегистрирован.")

            self._start_user_session(user_id)

        except sqlite3.IntegrityError:
            self.label_register_info.setText("Пользователь с такой почтой уже существует.")
        except Exception as e:
            self.label_register_info.setText(f"Ошибка: {e}")

    def do_login(self):
        email = self.le_login_email.text().strip().lower()
        password = self.le_login_password.text()

        if not (email and password):
            self.label_login_info.setText("Введите email и пароль.")
            return

        hp = hash_password(password)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email=? AND password=?", (email, hp))
        row = cur.fetchone()
        conn.close()

        if row:
            user_id = row[0]
            self._start_user_session(user_id)
        else:
            self.label_login_info.setText("Неверная почта или пароль.")

    def _start_user_session(self, user_id):
        if self.current_user_id is not None:
            self._save_session_seconds_to_db()

        self.current_user_id = user_id
        self.session_start_time = time.time()
        self.session_seconds = 0

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name, surname, patronymic, email, position FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()

        if row:
            name, surname, patronymic, email, position = row
            fullname = f"{surname} {name} {patronymic}".strip()

            if self.lbl_fullname:
                self.lbl_fullname.setText(fullname)
            if self.lbl_email:
                self.lbl_email.setText(email)
            if self.lbl_position:
                self.lbl_position.setText(position)

        create_empty_usage_for_user(user_id)
        conn.close()

        self.tabs_widget.set_user(user_id)

        self.update_heatmap_from_db()
        self.timer.start()

        self.show_main()

    def _on_tick(self):
        self.session_seconds += 1

        if self.session_seconds % 10 == 0:
            self._save_session_seconds_to_db(update_only=True)
            self.update_heatmap_from_db()  # Обновить таблицу
            self.tabs_widget.update_time_tracking(self.session_seconds)

    def _save_session_seconds_to_db(self, update_only=False):
        if self.current_user_id is None:
            return

        if self.session_seconds <= 0 and update_only:
            return

        seconds = self.session_seconds
        today_weekday = datetime.today().weekday()
        add_hours = seconds / 3600.0

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("SELECT hours FROM usage_hours WHERE user_id=? AND day=?",
                    (self.current_user_id, today_weekday))
        r = cur.fetchone()

        if r:
            new_hours = r[0] + add_hours
            cur.execute("UPDATE usage_hours SET hours=? WHERE user_id=? AND day=?",
                        (new_hours, self.current_user_id, today_weekday))
        else:
            cur.execute("INSERT INTO usage_hours (user_id, day, hours) VALUES (?, ?, ?)",
                        (self.current_user_id, today_weekday, add_hours))

        conn.commit()
        conn.close()

        self.session_seconds = 0

    def update_heatmap_from_db(self):
        if self.current_user_id is None:
            return

        self.tabs_widget.update_time_tracking(self.session_seconds)

        if not self.table_heatmap:
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT day, hours FROM usage_hours WHERE user_id=? ORDER BY day", (self.current_user_id,))
        rows = cur.fetchall()
        conn.close()
        hours_by_day = [0.0] * 7
        for d, h in rows:
            if 0 <= d < 7:
                hours_by_day[d] = h
        if self.session_seconds > 0:
            today = datetime.today().weekday()
            hours_by_day[today] += self.session_seconds / 3600.0

        for col in range(7):
            hours = hours_by_day[col]
            item = QTableWidgetItem(f"{hours:.2f} ч")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = color_for_hours(hours)
            item.setBackground(color)
            if (color.red() * 0.299 + color.green() * 0.587 + color.blue() * 0.114) > 186:
                item.setForeground(QColor(0, 0, 0))
            else:
                item.setForeground(QColor(255, 255, 255))
            self.table_heatmap.setItem(0, col, item)
        self.table_heatmap.resizeColumnsToContents()
        self.table_heatmap.resizeRowsToContents()

    def do_logout(self):
        self.timer.stop()
        self._save_session_seconds_to_db()

        self.current_user_id = None
        self.session_seconds = 0
        self.session_start_time = None

        self.show_login()

    def closeEvent(self, event):
        self.timer.stop()
        self._save_session_seconds_to_db()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyle('Fusion')

    w = MainApp()
    w.resize(420, 640)
    w.setWindowTitle("Роснефть - Система учета рабочего времени")
    w.show()

    sys.exit(app.exec())