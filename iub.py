"""
Главный файл приложения "Роснефть - Система учета рабочего времени"

Описание:
    Приложение для автоматического учета и управления рабочим временем сотрудников.
    Включает в себя систему авторизации, регистрации и визуализации данных.

Автор: [Укажите имя]
Дата создания: 2025
Версия: 1.0
"""

# ============================================================================
# ИМПОРТ БИБЛИОТЕК
# ============================================================================

# Системные библиотеки
import sys                          # Для работы с системными параметрами
import sqlite3                      # Для работы с базой данных SQLite
import hashlib                      # Для хэширования паролей
import time                         # Для работы со временем
from datetime import datetime       # Для работы с датой и временем

# Библиотеки PyQt6
from PyQt6 import uic              # Для загрузки UI файлов
from PyQt6.QtWidgets import (       # Виджеты интерфейса
    QApplication, QWidget, QMessageBox, QTableWidgetItem, 
    QLabel, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import QTimer, Qt # Таймер и константы Qt
from PyQt6.QtGui import QColor, QPixmap  # Работа с цветом и изображениями

# Импорт модулей проекта
from styles import ROSNEFT_STYLES   # Корпоративные стили Роснефти
from user_tabs import UserTabsWidget # Виджет с вкладками


# ============================================================================
# ГЛОБАЛЬНЫЕ КОНСТАНТЫ
# ============================================================================

DB_PATH = "users.db"  # Путь к файлу базы данных
MAX_HOURS_SCALE = 12.0              # Максимальное значение часов для шкалы цветов


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

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
    """
    Создает структуру базы данных, если она еще не существует
    
    Создает две таблицы:
        1. users - информация о пользователях
        2. usage_hours - учет рабочего времени по дням
        
    Примечание:
        Использует CREATE TABLE IF NOT EXISTS для безопасного создания
    """
    # Подключаемся к базе данных (создается автоматически, если не существует)
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
    
    # Создаем таблицу учета рабочего времени
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
    
    conn.commit()  # Сохраняем изменения
    conn.close()   # Закрываем соединение


def create_empty_usage_for_user(user_id):
    """
    Создает пустые записи учета времени для пользователя (все дни недели)
    
    Args:
        user_id (int): ID пользователя в базе данных
        
    Описание:
        Создает 7 записей (по одной на каждый день недели) с нулевым временем.
        Использует INSERT OR IGNORE для избежания дублирования записей.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Создаем запись для каждого дня недели (0=Пн, 6=Вс)
    for d in range(7):
        # INSERT OR IGNORE - вставляет только если записи еще нет
        cur.execute(
            "INSERT OR IGNORE INTO usage_hours (user_id, day, hours) VALUES (?, ?, ?)", 
            (user_id, d, 0.0)
        )
    
    conn.commit()  # Сохраняем изменения
    conn.close()   # Закрываем соединение


def color_for_hours(hours):
    """
    Возвращает цвет для ячейки тепловой карты на основе количества часов
    
    УСТАРЕВШАЯ ФУНКЦИЯ - используется только для обратной совместимости.
    Основная цветовая логика теперь в user_tabs.py
    
    Args:
        hours (float): Количество рабочих часов
        
    Returns:
        QColor: Цвет для отображения ячейки
        
    Цветовая схема (старая):
        0 часов -> Белый (#FFFFFF)
        ~6 часов -> Желтый (#FDD200)
        12+ часов -> Черный (#000000)
    """
    maxh = MAX_HOURS_SCALE
    ratio = min(hours / maxh, 1.0)  # Нормализуем значение в диапазон 0-1
    
    if ratio < 0.5:
        # Первая половина градиента: Белый -> Желтый
        local_ratio = ratio * 2  # Масштабируем 0-0.5 в 0-1
        r1, g1, b1 = 255, 255, 255  # RGB белого цвета
        r2, g2, b2 = 253, 210, 0     # RGB желтого (корпоративный цвет)
        
        # Линейная интерполяция между цветами
        r = int(r1 + (r2 - r1) * local_ratio)
        g = int(g1 + (g2 - g1) * local_ratio)
        b = int(b1 + (b2 - b1) * local_ratio)
    else:
        # Вторая половина градиента: Желтый -> Черный
        local_ratio = (ratio - 0.5) * 2  # Масштабируем 0.5-1 в 0-1
        r1, g1, b1 = 253, 210, 0     # RGB желтого
        r2, g2, b2 = 0, 0, 0         # RGB черного
        
        # Линейная интерполяция между цветами
        r = int(r1 + (r2 - r1) * local_ratio)
        g = int(g1 + (g2 - g1) * local_ratio)
        b = int(b1 + (b2 - b1) * local_ratio)
    
    return QColor(r, g, b)


# ============================================================================
# ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ
# ============================================================================

class MainApp(QWidget):
    """
    Главное окно приложения учета рабочего времени Роснефти
    
    Описание:
        Управляет всей логикой приложения: авторизацией, регистрацией,
        учетом времени, интерфейсом и взаимодействием с базой данных.
        
    Атрибуты:
        current_user_id (int): ID текущего авторизованного пользователя
        session_start_time (float): Время начала сессии (timestamp)
        session_seconds (int): Накопленные секунды текущей сессии
        timer (QTimer): Таймер для обновления счетчика времени
        tabs_widget (UserTabsWidget): Виджет с вкладками главной страницы
    """
    
    def __init__(self):
        """
        Инициализация главного окна приложения
        
        Выполняет следующие действия:
            1. Загружает интерфейс из UI файла
            2. Применяет корпоративные стили
            3. Создает структуру БД
            4. Находит и связывает все виджеты
            5. Настраивает обработчики событий
            6. Инициализирует таймер
            7. Устанавливает логотип
        """
        super().__init__()
        
        # Загружаем интерфейс из файла Qt Designer
        uic.loadUi("interface_1.ui", self)
        
        # Применяем корпоративную цветовую схему Роснефти (черный, желтый, белый)
        self.setStyleSheet(ROSNEFT_STYLES)

        # Создаем структуру базы данных (если еще не создана)
        ensure_db()

        # === ПОИСК ОСНОВНЫХ ВИДЖЕТОВ ИЗ UI ФАЙЛА ===
        
        # Stacked Widget для переключения между страницами
        self.stacked = self.findChild(QWidget, "stackedWidget")
        self.page_login = self.findChild(QWidget, "page_login")          # Страница входа
        self.page_register = self.findChild(QWidget, "page_register")    # Страница регистрации
        self.page_main = self.findChild(QWidget, "page_main")            # Главная страница

        # === ВИДЖЕТЫ СТРАНИЦЫ ВХОДА ===
        self.le_login_email = self.findChild(type(self.le_login_email if hasattr(self, 'le_login_email') else None), "le_login_email")     # Поле Email
        self.le_login_password = self.findChild(type(self.le_login_password if hasattr(self, 'le_login_password') else None), "le_login_password")  # Поле пароля
        self.btn_login = self.findChild(type(self.btn_login if hasattr(self, 'btn_login') else None), "btn_login")  # Кнопка "Войти"
        self.btn_go_register = self.findChild(type(self.btn_go_register if hasattr(self, 'btn_go_register') else None), "btn_go_register")  # Кнопка перехода к регистрации
        self.label_login_info = self.findChild(type(self.label_login_info if hasattr(self, 'label_login_info') else None), "label_login_info")  # Метка для ошибок

        # === ВИДЖЕТЫ СТРАНИЦЫ РЕГИСТРАЦИИ ===
        self.le_name = self.findChild(type(self.le_name if hasattr(self, 'le_name') else None), "le_name")  # Поле "Имя"
        self.le_surname = self.findChild(type(self.le_surname if hasattr(self, 'le_surname') else None), "le_surname")  # Поле "Фамилия"
        self.le_patronymic = self.findChild(type(self.le_patronymic if hasattr(self, 'le_patronymic') else None), "le_patronymic")  # Поле "Отчество"
        self.le_email = self.findChild(type(self.le_email if hasattr(self, 'le_email') else None), "le_email")  # Поле "Email"
        self.le_phone = self.findChild(type(self.le_phone if hasattr(self, 'le_phone') else None), "le_phone")  # Поле "Телефон"
        self.le_password = self.findChild(type(self.le_password if hasattr(self, 'le_password') else None), "le_password")  # Поле "Пароль"
        self.le_confirm = self.findChild(type(self.le_confirm if hasattr(self, 'le_confirm') else None), "le_confirm")  # Поле "Подтверждение пароля"
        self.le_position = self.findChild(type(self.le_position if hasattr(self, 'le_position') else None), "le_position")  # Поле "Должность"
        self.btn_register = self.findChild(type(self.btn_register if hasattr(self, 'btn_register') else None), "btn_register")  # Кнопка "Зарегистрироваться"
        self.btn_back_to_login = self.findChild(type(self.btn_back_to_login if hasattr(self, 'btn_back_to_login') else None), "btn_back_to_login")  # Кнопка "Назад"
        self.label_register_info = self.findChild(type(self.label_register_info if hasattr(self, 'label_register_info') else None), "label_register_info")  # Метка для ошибок

        # === ВИДЖЕТЫ ГЛАВНОЙ СТРАНИЦЫ (для обратной совместимости) ===
        self.lbl_fullname = self.findChild(QLabel, "lbl_fullname")  # Метка ФИО (скрыта, используются табы)
        self.lbl_email = self.findChild(QLabel, "lbl_email")        # Метка Email (скрыта)
        self.lbl_position = self.findChild(QLabel, "lbl_position")  # Метка должности (скрыта)
        self.table_heatmap = self.findChild(type(self.table_heatmap if hasattr(self, 'table_heatmap') else None), "table_heatmap")  # Старая таблица (скрыта)
        self.btn_logout = self.findChild(type(self.btn_logout if hasattr(self, 'btn_logout') else None), "btn_logout")  # Кнопка "Выход"
        
        # === СОЗДАНИЕ ИНТЕРФЕЙСА С ВКЛАДКАМИ ===
        self._setup_tabs_on_main_page()

        # === ПОДКЛЮЧЕНИЕ ОБРАБОТЧИКОВ СОБЫТИЙ (СИГНАЛЫ-СЛОТЫ) ===
        self.btn_go_register.clicked.connect(self.show_register)     # Переход к регистрации
        self.btn_back_to_login.clicked.connect(self.show_login)      # Возврат к входу
        self.btn_register.clicked.connect(self.do_register)          # Выполнить регистрацию
        self.btn_login.clicked.connect(self.do_login)                # Выполнить вход
        self.btn_logout.clicked.connect(self.do_logout)              # Выполнить выход

        # === ИНИЦИАЛИЗАЦИЯ СТАРОЙ ТАБЛИЦЫ (для обратной совместимости) ===
        if self.table_heatmap:
            days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            self.table_heatmap.setColumnCount(7)                      # 7 столбцов (дни недели)
            self.table_heatmap.setRowCount(1)                         # 1 строка
            self.table_heatmap.setHorizontalHeaderLabels(days)        # Заголовки столбцов
            self.table_heatmap.verticalHeader().setVisible(False)     # Скрыть вертикальный заголовок
            self.table_heatmap.setEditTriggers(self.table_heatmap.EditTrigger.NoEditTriggers)  # Только чтение
            self.table_heatmap.setSelectionMode(self.table_heatmap.SelectionMode.NoSelection)  # Без выделения

        # === ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННЫХ СЕССИИ ===
        self.current_user_id = None           # ID текущего пользователя (None = не авторизован)
        self.session_start_time = None        # Время начала сессии
        self.session_seconds = 0              # Накопленные секунды текущей сессии
        
        # === НАСТРОЙКА ТАЙМЕРА ===
        self.timer = QTimer()                 # Создаем таймер
        self.timer.setInterval(1000)          # Интервал 1000 мс = 1 секунда
        self.timer.timeout.connect(self._on_tick)  # Обработчик срабатывания таймера
        
        # === ПРИМЕНЕНИЕ UX НАСТРОЕК И ЛОГОТИПА ===
        self._apply_modern_effects()          # Минимальный размер окна и т.д.
        self._setup_logo()                    # Установка логотипа компании

        # === ПОКАЗЫВАЕМ СТРАНИЦУ ВХОДА ПРИ ЗАПУСКЕ ===
        self.show_login()
    
    # ========================================================================
    # МЕТОДЫ НАСТРОЙКИ ИНТЕРФЕЙСА
    # ========================================================================
    
    def _apply_modern_effects(self):
        """
        Применяет современные UX настройки для главного окна
        
        Описание:
            Устанавливает минимальный размер окна для корректного отображения
            всех элементов интерфейса на различных разрешениях экрана.
        """
        # Устанавливаем минимальный размер окна (ширина x высота)
        self.setMinimumSize(400, 500)
    
    def _setup_tabs_on_main_page(self):
        """
        Создает и добавляет виджет с табами на главную страницу
        """
        # Создаем виджет с табами
        self.tabs_widget = UserTabsWidget(self.page_main)
        
        # Получаем layout главной страницы
        main_layout = self.page_main.layout()
        
        if main_layout is None:
            # Если layout нет, создаем новый
            main_layout = QVBoxLayout(self.page_main)
            main_layout.setContentsMargins(10, 10, 10, 10)
            self.page_main.setLayout(main_layout)
        
        # Создаем горизонтальный layout для заголовка и кнопки выхода
        header_layout = QHBoxLayout()
        
        # Информация о пользователе (скрываем старые labels если они есть)
        if self.lbl_fullname:
            self.lbl_fullname.hide()
        if self.lbl_email:
            self.lbl_email.hide()
        if self.lbl_position:
            self.lbl_position.hide()
        
        # Заголовок
        welcome_label = QLabel("Добро пожаловать!")
        welcome_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #000000;")
        header_layout.addWidget(welcome_label)
        
        header_layout.addStretch()
        
        # Кнопка выхода
        if self.btn_logout:
            header_layout.addWidget(self.btn_logout)
        
        # Вставляем заголовок в начало
        main_layout.insertLayout(0, header_layout)
        
        # Скрываем старую таблицу если она есть
        if self.table_heatmap:
            self.table_heatmap.hide()
        
        # Добавляем табы
        main_layout.addWidget(self.tabs_widget)
    
    def _setup_logo(self):
        """
        Устанавливает логотип Роснефти в верхней части каждой страницы
        """
        logo_path = "rosneft.png"
        pixmap = QPixmap(logo_path)
        
        if pixmap.isNull():
            print(f"Внимание: Логотип {logo_path} не найден")
            return
        
        # Масштабируем логотип (ширина 150px, сохраняя пропорции)
        scaled_pixmap = pixmap.scaled(150, 80, Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
        
        # Добавляем логотип на страницу входа
        self._add_logo_to_page(self.page_login, scaled_pixmap)
        
        # Добавляем логотип на страницу регистрации
        self._add_logo_to_page(self.page_register, scaled_pixmap)
        
        # Добавляем логотип на главную страницу
        self._add_logo_to_page(self.page_main, scaled_pixmap)
    
    def _add_logo_to_page(self, page, pixmap):
        """
        Добавляет логотип на страницу, интегрируя его в layout
        """
        # Ищем существующий logo_label
        logo_label = page.findChild(QLabel, "logo_label")
        
        if logo_label is None:
            # Создаем новый QLabel для логотипа
            logo_label = QLabel(page)
            logo_label.setObjectName("logo_label")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Устанавливаем минимальную высоту для логотипа (без обрезания)
            logo_label.setMinimumHeight(pixmap.height())
            logo_label.setMaximumHeight(pixmap.height() + 20)
            
            # Получаем существующий layout страницы
            page_layout = page.layout()
            
            if page_layout is not None:
                # Вставляем логотип в начало существующего layout
                page_layout.insertWidget(0, logo_label)
                # Добавляем небольшой отступ после логотипа
                spacer = QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
                page_layout.insertItem(1, spacer)
            else:
                # Если нет layout, создаем новый и добавляем все виджеты
                new_layout = QVBoxLayout(page)
                new_layout.setContentsMargins(10, 10, 10, 10)
                
                # Добавляем логотип в начало
                new_layout.addWidget(logo_label)
                
                # Добавляем отступ
                spacer = QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
                new_layout.addItem(spacer)
                
                # Добавляем все существующие дочерние виджеты
                for child in page.findChildren(QWidget):
                    if child != logo_label and child.parent() == page:
                        new_layout.addWidget(child)
                
                page.setLayout(new_layout)
        
        logo_label.setPixmap(pixmap)
        logo_label.setScaledContents(False)

    # ========================================================================
    # МЕТОДЫ НАВИГАЦИИ МЕЖДУ СТРАНИЦАМИ
    # ========================================================================
    
    def show_login(self):
        """Показывает страницу входа и очищает сообщения об ошибках"""
        self._switch_page(self.page_login)
        self.label_login_info.setText("")  # Очищаем сообщения

    def show_register(self):
        """Показывает страницу регистрации и очищает сообщения об ошибках"""
        self._switch_page(self.page_register)
        self.label_register_info.setText("")  # Очищаем сообщения

    def show_main(self):
        """Показывает главную страницу с вкладками"""
        self._switch_page(self.page_main)
    
    def _switch_page(self, target_page):
        """
        Переключает текущую страницу в StackedWidget
        
        Args:
            target_page (QWidget): Страница для отображения
        """
        self.stacked.setCurrentWidget(target_page)


    # ========================================================================
    # МЕТОДЫ РЕГИСТРАЦИИ И АВТОРИЗАЦИИ
    # ========================================================================

    def do_register(self):
        """
        Обрабатывает регистрацию нового пользователя
        
        Процесс:
            1. Получает данные из полей формы
            2. Валидирует введенные данные
            3. Хэширует пароль (SHA-256)
            4. Сохраняет пользователя в БД
            5. Создает пустые записи учета времени
            6. Автоматически выполняет вход
            
        Валидация:
            - Все обязательные поля заполнены
            - Пароли совпадают
            - Email содержит символ "@"
            - Email уникален (проверка БД)
        """
        # Получаем данные из полей формы и очищаем от пробелов
        name = self.le_name.text().strip()
        surname = self.le_surname.text().strip()
        patronymic = self.le_patronymic.text().strip()
        email = self.le_email.text().strip().lower()  # Email в нижнем регистре
        phone = self.le_phone.text().strip()
        password = self.le_password.text()
        confirm = self.le_confirm.text()
        position = self.le_position.text().strip()

        # ВАЛИДАЦИЯ ДАННЫХ
        # Проверка обязательных полей
        if not (name and surname and email and password and confirm and position):
            self.label_register_info.setText("Заполните обязательные поля.")
            return
        
        # Проверка совпадения паролей
        if password != confirm:
            self.label_register_info.setText("Пароли не совпадают.")
            return
        
        # Проверка формата email
        if "@" not in email:
            self.label_register_info.setText("Неправильный формат почты.")
            return

        # Хэшируем пароль для безопасного хранения
        hp = hash_password(password)
        
        try:
            # Подключаемся к БД и добавляем пользователя
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""INSERT INTO users (name, surname, patronymic, email, phone, password, position)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (name, surname, patronymic, email, phone, hp, position))
            conn.commit()
            user_id = cur.lastrowid  # Получаем ID нового пользователя
            conn.close()
            
            # Создаем пустые записи учета времени для всех дней недели
            create_empty_usage_for_user(user_id)
            
            # Показываем успешное уведомление
            QMessageBox.information(self, "Успех", "Пользователь зарегистрирован.")
            
            # Автоматически входим в систему
            self._start_user_session(user_id)
            
        except sqlite3.IntegrityError:
            # Email уже существует в БД (нарушение UNIQUE constraint)
            self.label_register_info.setText("Пользователь с такой почтой уже существует.")
        except Exception as e:
            # Другие ошибки БД
            self.label_register_info.setText(f"Ошибка: {e}")

    def do_login(self):
        """
        Обрабатывает вход пользователя в систему
        
        Процесс:
            1. Получает email и пароль из полей
            2. Хэширует введенный пароль
            3. Проверяет учетные данные в БД
            4. При успехе запускает сессию пользователя
            
        Безопасность:
            - Email приводится к нижнему регистру
            - Пароль хэшируется перед проверкой
            - Используются параметризованные запросы (защита от SQL injection)
        """
        # Получаем данные из полей (email в нижнем регистре)
        email = self.le_login_email.text().strip().lower()
        password = self.le_login_password.text()
        
        # Проверка заполнения полей
        if not (email and password):
            self.label_login_info.setText("Введите email и пароль.")
            return
        
        # Хэшируем введенный пароль
        hp = hash_password(password)
        
        # Ищем пользователя в БД
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email=? AND password=?", (email, hp))
        row = cur.fetchone()
        conn.close()
        
        if row:
            # Пользователь найден - запускаем сессию
            user_id = row[0]
            self._start_user_session(user_id)
        else:
            # Неверные учетные данные
            self.label_login_info.setText("Неверная почта или пароль.")

    # ========================================================================
    # МЕТОДЫ УПРАВЛЕНИЯ СЕССИЕЙ И УЧЕТА ВРЕМЕНИ
    # ========================================================================

    def _start_user_session(self, user_id):
        """
        Запускает новую сессию пользователя после успешного входа
        
        Args:
            user_id (int): ID пользователя в базе данных
            
        Выполняет:
            1. Сохраняет время предыдущей сессии (если была)
            2. Инициализирует параметры новой сессии
            3. Загружает данные пользователя из БД
            4. Настраивает интерфейс (табы, таблицу)
            5. Запускает таймер учета времени
            6. Переключает на главную страницу
        """
        # Если был другой пользователь - сохраняем его время
        if self.current_user_id is not None:
            self._save_session_seconds_to_db()

        # Инициализация параметров новой сессии
        self.current_user_id = user_id
        self.session_start_time = time.time()  # Текущее время (timestamp)
        self.session_seconds = 0               # Обнуляем счетчик
        
        # Загружаем информацию о пользователе из БД
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name, surname, patronymic, email, position FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        
        if row:
            name, surname, patronymic, email, position = row
            fullname = f"{surname} {name} {patronymic}".strip()
            
            # Обновляем старые метки (если они есть)
            if self.lbl_fullname:
                self.lbl_fullname.setText(fullname)
            if self.lbl_email:
                self.lbl_email.setText(email)
            if self.lbl_position:
                self.lbl_position.setText(position)
        
        # Создаем пустые записи учета времени (если их нет)
        create_empty_usage_for_user(user_id)
        conn.close()
        
        # Устанавливаем пользователя для виджета с вкладками
        self.tabs_widget.set_user(user_id)
        
        # Обновляем данные и запускаем таймер
        self.update_heatmap_from_db()
        self.timer.start()  # Запуск таймера (1 тик = 1 секунда)
        
        # Переходим на главную страницу
        self.show_main()

    def _on_tick(self):
        """
        Обработчик таймера - вызывается каждую секунду
        
        Функционал:
            - Увеличивает счетчик секунд текущей сессии
            - Каждые 10 секунд:
                * Сохраняет накопленное время в БД
                * Обновляет визуализацию (тепловую карту)
                * Обновляет вкладки с информацией
        """
        # Увеличиваем счетчик секунд
        self.session_seconds += 1
        
        # Каждые 10 секунд - сохраняем и обновляем
        if self.session_seconds % 10 == 0:
            self._save_session_seconds_to_db(update_only=True)  # Сохранить в БД
            self.update_heatmap_from_db()                       # Обновить таблицу
            self.tabs_widget.update_time_tracking(self.session_seconds)  # Обновить табы

    def _save_session_seconds_to_db(self, update_only=False):
        """
        Сохраняет накопленное время сессии в базу данных
        
        Args:
            update_only (bool): Если True, не сохраняет при нулевом времени
            
        Логика:
            1. Конвертирует секунды в часы
            2. Определяет текущий день недели
            3. Добавляет часы к существующей записи или создает новую
            4. Обнуляет счетчик секунд после сохранения
            
        Примечание:
            Используется UPDATE/INSERT для надежного сохранения данных
        """
        # Проверки перед сохранением
        if self.current_user_id is None:
            return  # Нет авторизованного пользователя
        
        if self.session_seconds <= 0 and update_only:
            return  # Нет времени для сохранения
        
        # Подготовка данных
        seconds = self.session_seconds
        today_weekday = datetime.today().weekday()  # 0=Понедельник, 6=Воскресенье
        add_hours = seconds / 3600.0                 # Конвертация секунд в часы
        
        # Сохранение в БД
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Проверяем существование записи для текущего дня
        cur.execute("SELECT hours FROM usage_hours WHERE user_id=? AND day=?", 
                   (self.current_user_id, today_weekday))
        r = cur.fetchone()
        
        if r:
            # Запись существует - обновляем (добавляем часы)
            new_hours = r[0] + add_hours
            cur.execute("UPDATE usage_hours SET hours=? WHERE user_id=? AND day=?", 
                       (new_hours, self.current_user_id, today_weekday))
        else:
            # Записи нет - создаем новую
            cur.execute("INSERT INTO usage_hours (user_id, day, hours) VALUES (?, ?, ?)", 
                       (self.current_user_id, today_weekday, add_hours))
        
        conn.commit()
        conn.close()
        
        # Обнуляем счетчик после успешного сохранения
        self.session_seconds = 0

    def update_heatmap_from_db(self):
        if self.current_user_id is None:
            return
        
        # Обновляем табы (новый интерфейс)
        self.tabs_widget.update_time_tracking(self.session_seconds)
        
        # Обновляем старую таблицу если она существует (для обратной совместимости)
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
            if (color.red()*0.299 + color.green()*0.587 + color.blue()*0.114) > 186:
                item.setForeground(QColor(0, 0, 0))
            else:
                item.setForeground(QColor(255, 255, 255))
            self.table_heatmap.setItem(0, col, item)
        self.table_heatmap.resizeColumnsToContents()
        self.table_heatmap.resizeRowsToContents()

    # ========================================================================
    # МЕТОДЫ ЗАВЕРШЕНИЯ РАБОТЫ
    # ========================================================================

    def do_logout(self):
        """
        Выполняет выход пользователя из системы
        
        Процесс:
            1. Останавливает таймер учета времени
            2. Сохраняет накопленное время в БД
            3. Очищает данные сессии
            4. Возвращает на страницу входа
            
        Гарантирует:
            Все данные о рабочем времени будут сохранены
        """
        self.timer.stop()                       # Останавливаем таймер
        self._save_session_seconds_to_db()      # Сохраняем последние данные
        
        # Очищаем данные сессии
        self.current_user_id = None
        self.session_seconds = 0
        self.session_start_time = None
        
        # Возвращаемся на страницу входа
        self.show_login()

    def closeEvent(self, event):
        """
        Обработчик закрытия окна приложения (клик на крестик)
        
        Args:
            event: Событие закрытия окна
            
        Важно:
            Перед закрытием приложения сохраняет все данные в БД,
            чтобы не потерять информацию о текущей сессии.
        """
        self.timer.stop()                       # Останавливаем таймер
        self._save_session_seconds_to_db()      # Сохраняем данные перед выходом
        event.accept()                          # Разрешаем закрытие окна


# ============================================================================
# ТОЧКА ВХОДА В ПРИЛОЖЕНИЕ
# ============================================================================

if __name__ == "__main__":
    # Создаем объект приложения Qt
    app = QApplication(sys.argv)
    
    # Устанавливаем стиль Fusion для улучшенного кросс-платформенного вида
    # Fusion - современный стиль, одинаково выглядит на Windows, Linux, Mac
    app.setStyle('Fusion')
    
    # Создаем главное окно приложения
    w = MainApp()
    w.resize(420, 640)  # Устанавливаем размер окна
    w.setWindowTitle("Роснефть - Система учета рабочего времени")  # Заголовок окна
    w.show()  # Показываем окно
    
    # Запускаем цикл обработки событий Qt
    # Приложение работает до тех пор, пока пользователь не закроет окно
    sys.exit(app.exec())