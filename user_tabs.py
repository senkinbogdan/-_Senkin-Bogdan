"""
Модуль с функционалом вкладок для главной страницы приложения

Описание:
    Содержит классы для реализации вкладочного интерфейса главной страницы:
    - TimeTrackingTab - вкладка учета рабочего времени с редактированием
    - UserInfoTab - вкладка с информацией о пользователе и статистикой
    - UserTabsWidget - контейнер для управления вкладками
    
Функционал:
    • Визуализация рабочего времени (тепловая карта)
    • Редактирование записей о времени
    • Просмотр профиля пользователя
    • Отображение статистики работы
    • Цветовая индикация (красный/желтый/зеленый)

Автор: [Укажите имя]
Дата создания: 2025
Версия: 1.0
"""

# ============================================================================
# ИМПОРТ БИБЛИОТЕК
# ============================================================================

import sqlite3                          # Работа с базой данных SQLite
from datetime import datetime            # Работа с датой и временем

# Виджеты PyQt6
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,   # Базовые виджеты и layout'ы
    QTableWidget, QTableWidgetItem,      # Таблицы
    QLabel, QTabWidget, QGridLayout,     # Метки и табы
    QFrame, QSizePolicy,                 # Рамки и политики размеров
    QPushButton, QMessageBox             # Кнопки и диалоги
)
from PyQt6.QtCore import Qt              # Константы Qt
from PyQt6.QtGui import QColor           # Работа с цветом


# ============================================================================
# ГЛОБАЛЬНЫЕ КОНСТАНТЫ
# ============================================================================

DB_PATH = "users.db"  # Путь к базе данных
MAX_HOURS_SCALE = 12.0                   # Максимум для старой цветовой схемы


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def color_for_hours(hours):
    """
    Возвращает цвет ячейки на основе количества рабочих часов
    
    Args:
        hours (float): Количество рабочих часов
        
    Returns:
        QColor: Объект цвета для отображения
        
    Цветовая схема (логика оценки времени):
        ⚪ 0-0.5 час -> Белый (нет данных)
        🔴 0.5-3 часа -> Красный (критично мало)
        🟡 3-7 часов -> Желтый (ниже нормы)
        🟢 7-9 часов -> Зеленый (НОРМА, оптимально!)
        🟡 9-12 часов -> Желтый (переработка)
        🟠 12+ часов -> Оранжевый (сверхурочные, критично много)
    """
    if hours <= 0.5:
        # Почти нет времени - белый (нет данных/выходной)
        return QColor(255, 255, 255)
    elif hours <= 3:
        # Мало (до 3 часов) - красный (КРИТИЧНО!)
        return QColor(231, 76, 60)
    elif hours < 7:
        # Недоработка (3-7 часов) - желтый (внимание)
        return QColor(253, 210, 0)  # Корпоративный желтый Роснефти
    elif hours <= 9:
        # НОРМА (7-9 часов) - зеленый (оптимально!)
        return QColor(46, 204, 113)
    elif hours <= 12:
        # Переработка (9-12 часов) - желтый (внимание)
        return QColor(253, 210, 0)  # Корпоративный желтый Роснефти
    else:
        # Сверхурочные (12+ часов) - оранжевый (КРИТИЧНО!)
        return QColor(230, 126, 34)


# ============================================================================
# КЛАСС ВКЛАДКИ УЧЕТА ВРЕМЕНИ
# ============================================================================

class TimeTrackingTab(QWidget):
    """
    Вкладка для учета и редактирования рабочего времени
    
    Функционал:
        • Отображение тепловой карты часов по дням недели
        • Редактирование записей о рабочем времени
        • Валидация введенных данных
        • Сохранение изменений в базу данных
        • Цветовая индикация (зеленый=норма, красный=мало, желтый=отклонение)
        
    Атрибуты:
        user_id (int): ID текущего пользователя
        session_seconds (int): Текущие секунды активной сессии
        edit_mode (bool): Флаг режима редактирования (True/False)
        original_hours (dict): Исходные значения часов для отмены изменений
        table_heatmap (QTableWidget): Таблица с тепловой картой
        btn_edit/save/cancel (QPushButton): Кнопки управления редактированием
    """
    
    def __init__(self, parent=None):
        """
        Инициализация вкладки учета времени
        
        Args:
            parent: Родительский виджет (опционально)
        """
        super().__init__(parent)
        
        # Инициализация переменных состояния
        self.user_id = None              # ID пользователя (устанавливается позже)
        self.session_seconds = 0         # Секунды текущей сессии
        self.edit_mode = False           # Режим редактирования отключен
        self.original_hours = {}         # Словарь для хранения исходных значений
        
        # Создаем интерфейс вкладки
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса вкладки"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок
        title_label = QLabel("📊 Учет рабочего времени")
        title_label.setObjectName("tab_title")
        title_label.setStyleSheet("""
            QLabel#tab_title {
                font-size: 16pt;
                font-weight: bold;
                color: #000000;
                padding: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Описание
        desc_label = QLabel("Тепловая карта показывает количество часов работы по дням недели")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #555555; font-size: 10pt; padding: 5px;")
        layout.addWidget(desc_label)
        
        # Таблица тепловой карты
        self.table_heatmap = QTableWidget()
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        self.table_heatmap.setColumnCount(7)
        self.table_heatmap.setRowCount(1)
        self.table_heatmap.setHorizontalHeaderLabels(days)
        self.table_heatmap.verticalHeader().setVisible(False)
        self.table_heatmap.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_heatmap.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table_heatmap.setMinimumHeight(100)
        
        # Устанавливаем размер строк для лучшей видимости
        self.table_heatmap.setRowHeight(0, 50)
        
        # Стиль для таблицы с увеличенным шрифтом
        self.table_heatmap.setStyleSheet("""
            QTableWidget {
                font-size: 13pt;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 10px;
            }
        """)
        
        layout.addWidget(self.table_heatmap)
        
        # Кнопки управления редактированием
        buttons_layout = QHBoxLayout()
        
        self.btn_edit = QPushButton("✏️ Редактировать")
        self.btn_edit.setObjectName("btn_edit")
        self.btn_edit.clicked.connect(self.enable_edit_mode)
        buttons_layout.addWidget(self.btn_edit)
        
        self.btn_save = QPushButton("💾 Сохранить")
        self.btn_save.setObjectName("btn_save")
        self.btn_save.clicked.connect(self.save_changes)
        self.btn_save.setVisible(False)
        buttons_layout.addWidget(self.btn_save)
        
        self.btn_cancel = QPushButton("❌ Отмена")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.clicked.connect(self.cancel_edit)
        self.btn_cancel.setVisible(False)
        buttons_layout.addWidget(self.btn_cancel)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Подсказка
        self.hint_label = QLabel("💡 Нажмите 'Редактировать' для изменения рабочего времени")
        self.hint_label.setStyleSheet("color: #555555; font-style: italic; padding: 5px;")
        layout.addWidget(self.hint_label)
        
        # Легенда
        legend_frame = QFrame()
        legend_frame.setStyleSheet("QFrame { background-color: #F8F8F8; border-radius: 5px; padding: 10px; }")
        legend_layout = QVBoxLayout(legend_frame)
        
        legend_title = QLabel("📌 Легенда:")
        legend_title.setStyleSheet("font-weight: bold; color: #000000; font-size: 11pt;")
        legend_layout.addWidget(legend_title)
        
        # Создаем три строки легенды
        legend_items = [
            (2, "1-3 часа", "❌ Мало рабочего времени"),
            (5.5, "4-6 и 10-12 часов", "⚠️ Отклонение от нормы"),
            (8, "7-9 часов", "✅ Норма")
        ]
        
        for hours_val, range_text, description in legend_items:
            item_layout = QHBoxLayout()
            
            # Цветной квадратик
            color_box = QLabel("  ")
            color = color_for_hours(hours_val)
            color_box.setStyleSheet(f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); border: 2px solid #000;")
            color_box.setFixedSize(35, 25)
            item_layout.addWidget(color_box)
            
            # Диапазон часов
            range_label = QLabel(range_text)
            range_label.setStyleSheet("color: #000000; font-weight: bold; min-width: 120px;")
            item_layout.addWidget(range_label)
            
            # Описание
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #555555;")
            item_layout.addWidget(desc_label)
            
            item_layout.addStretch()
            legend_layout.addLayout(item_layout)
        
        layout.addWidget(legend_frame)
        
        # Добавляем растягивающийся элемент
        layout.addStretch()
    
    def set_user(self, user_id):
        """Устанавливает текущего пользователя"""
        self.user_id = user_id
        self.update_heatmap()
    
    def update_session_seconds(self, seconds):
        """Обновляет текущие секунды сессии"""
        self.session_seconds = seconds
    
    def update_heatmap(self):
        """Обновляет тепловую карту из базы данных"""
        if self.user_id is None:
            return
        
        # Не обновляем в режиме редактирования
        if self.edit_mode:
            return
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT day, hours FROM usage_hours WHERE user_id=? ORDER BY day", (self.user_id,))
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
            
            # Устанавливаем начальные флаги (нередактируемый)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            
            color = color_for_hours(hours)
            item.setBackground(color)
            
            # Определяем цвет текста для контраста
            luminance = (color.red()*0.299 + color.green()*0.587 + color.blue()*0.114)
            
            # Для зеленого и светлых цветов - черный текст, для темных - белый
            if luminance > 140:  # Светлые цвета (белый, желтый, зеленый)
                item.setForeground(QColor(0, 0, 0))
            else:  # Темные цвета (красный)
                item.setForeground(QColor(255, 255, 255))
            
            self.table_heatmap.setItem(0, col, item)
        
        # Устанавливаем ширину столбцов
        for col in range(7):
            self.table_heatmap.setColumnWidth(col, 80)
        
        self.table_heatmap.setRowHeight(0, 50)
    
    def enable_edit_mode(self):
        """Включает режим редактирования"""
        if self.user_id is None:
            QMessageBox.warning(self, "Ошибка", "Нет активного пользователя")
            return
        
        try:
            self.edit_mode = True
            
            # Сохраняем исходные значения
            self.original_hours = {}
            for col in range(7):
                item = self.table_heatmap.item(0, col)
                if item:
                    try:
                        hours_text = item.text().replace(' ч', '').replace(',', '.')
                        self.original_hours[col] = float(hours_text)
                    except (ValueError, AttributeError):
                        self.original_hours[col] = 0.0
            
            # Делаем таблицу редактируемой
            self.table_heatmap.setEditTriggers(
                QTableWidget.EditTrigger.DoubleClicked | 
                QTableWidget.EditTrigger.AnyKeyPressed
            )
            self.table_heatmap.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            
            # Увеличиваем размер для режима редактирования
            self.table_heatmap.setRowHeight(0, 60)
            for col in range(7):
                self.table_heatmap.setColumnWidth(col, 90)
            
            # Увеличиваем шрифт для режима редактирования
            self.table_heatmap.setStyleSheet("""
                QTableWidget {
                    font-size: 14pt;
                    font-weight: bold;
                }
                QTableWidget::item {
                    padding: 12px;
                }
            """)
            
            # Обновляем таблицу для редактирования
            for col in range(7):
                item = self.table_heatmap.item(0, col)
                if item is not None:
                    # Убираем цвет фона для лучшей видимости при редактировании
                    item.setBackground(QColor(255, 255, 255))
                    item.setForeground(QColor(0, 0, 0))
                    # Делаем элемент редактируемым
                    flags = item.flags()
                    item.setFlags(flags | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            
            # Переключаем видимость кнопок
            self.btn_edit.setVisible(False)
            self.btn_save.setVisible(True)
            self.btn_cancel.setVisible(True)
            
            # Меняем подсказку
            self.hint_label.setText("✏️ Введите количество часов (можно использовать десятичные дроби, например: 8.5)")
            self.hint_label.setStyleSheet("color: #FDD200; font-weight: bold; padding: 5px;")
            
        except Exception as e:
            self.edit_mode = False
            QMessageBox.critical(self, "Ошибка", f"Не удалось включить режим редактирования: {str(e)}")
            print(f"Error in enable_edit_mode: {e}")  # Для отладки
    
    def save_changes(self):
        """Сохраняет изменения в базу данных"""
        if self.user_id is None:
            QMessageBox.warning(self, "Ошибка", "Нет активного пользователя")
            return
        
        try:
            # Собираем новые значения из таблицы
            new_hours = {}
            days_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            
            for col in range(7):
                item = self.table_heatmap.item(0, col)
                if item is None:
                    QMessageBox.warning(self, "Ошибка", 
                                      f"Отсутствуют данные для дня {days_names[col]}")
                    return
                
                hours_text = item.text().replace(' ч', '').replace(',', '.').strip()
                try:
                    hours = float(hours_text)
                    if hours < 0:
                        QMessageBox.warning(self, "Ошибка", 
                                          f"Количество часов не может быть отрицательным\n({days_names[col]})")
                        return
                    if hours > 24:
                        QMessageBox.warning(self, "Ошибка", 
                                          f"Количество часов не может превышать 24 в сутки\n({days_names[col]})")
                        return
                    new_hours[col] = hours
                except ValueError:
                    QMessageBox.warning(self, "Ошибка", 
                                      f"Некорректное значение для дня {days_names[col]}\nВведите число (например: 8 или 8.5)")
                    return
            
            # Сохраняем в базу данных
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            for day, hours in new_hours.items():
                cur.execute("""
                    INSERT INTO usage_hours (user_id, day, hours) 
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, day) 
                    DO UPDATE SET hours=?
                """, (self.user_id, day, hours, hours))
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Успех", "Изменения успешно сохранены!")
            
            # Выходим из режима редактирования
            self.disable_edit_mode()
            self.update_heatmap()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")
    
    def cancel_edit(self):
        """Отменяет редактирование и восстанавливает исходные значения"""
        try:
            reply = QMessageBox.question(self, "Отмена", 
                                         "Вы уверены, что хотите отменить изменения?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                # Восстанавливаем исходные значения
                for col, hours in self.original_hours.items():
                    item = self.table_heatmap.item(0, col)
                    if item is not None:
                        item.setText(f"{hours:.2f} ч")
                
                self.disable_edit_mode()
                self.update_heatmap()
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при отмене: {str(e)}")
            print(f"Error in cancel_edit: {e}")  # Для отладки
    
    def disable_edit_mode(self):
        """Отключает режим редактирования"""
        try:
            self.edit_mode = False
            
            # Делаем таблицу нередактируемой
            self.table_heatmap.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table_heatmap.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
            
            # Восстанавливаем обычный размер и стиль
            self.table_heatmap.setRowHeight(0, 50)
            for col in range(7):
                self.table_heatmap.setColumnWidth(col, 80)
            
            self.table_heatmap.setStyleSheet("""
                QTableWidget {
                    font-size: 13pt;
                    font-weight: bold;
                }
                QTableWidget::item {
                    padding: 10px;
                }
            """)
            
            # Убираем флаги редактирования у ячеек
            for col in range(7):
                item = self.table_heatmap.item(0, col)
                if item is not None:
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            
            # Переключаем видимость кнопок
            self.btn_edit.setVisible(True)
            self.btn_save.setVisible(False)
            self.btn_cancel.setVisible(False)
            
            # Восстанавливаем подсказку
            self.hint_label.setText("💡 Нажмите 'Редактировать' для изменения рабочего времени")
            self.hint_label.setStyleSheet("color: #555555; font-style: italic; padding: 5px;")
            
        except Exception as e:
            print(f"Error in disable_edit_mode: {e}")  # Для отладки


class UserInfoTab(QWidget):
    """
    Вкладка с информацией о пользователе
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_id = None
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса вкладки"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок
        title_label = QLabel("👤 Профиль пользователя")
        title_label.setObjectName("tab_title")
        title_label.setStyleSheet("""
            QLabel#tab_title {
                font-size: 16pt;
                font-weight: bold;
                color: #000000;
                padding: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Контейнер для информации
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #F8F8F8;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        info_layout = QGridLayout(info_frame)
        info_layout.setSpacing(15)
        
        # Создаем поля для отображения информации
        row = 0
        
        # ФИО
        self._add_info_row(info_layout, row, "ФИО:", "lbl_fullname_value")
        row += 1
        
        # Email
        self._add_info_row(info_layout, row, "Email:", "lbl_email_value")
        row += 1
        
        # Телефон
        self._add_info_row(info_layout, row, "Телефон:", "lbl_phone_value")
        row += 1
        
        # Должность
        self._add_info_row(info_layout, row, "Должность:", "lbl_position_value")
        row += 1
        
        layout.addWidget(info_frame)
        
        # Статистика
        stats_label = QLabel("📈 Статистика работы")
        stats_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #000000; padding: 10px;")
        layout.addWidget(stats_label)
        
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #F8F8F8;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        stats_layout = QGridLayout(stats_frame)
        stats_layout.setSpacing(15)
        
        # Статистика
        stat_row = 0
        self._add_info_row(stats_layout, stat_row, "Всего часов за неделю:", "lbl_total_hours")
        stat_row += 1
        self._add_info_row(stats_layout, stat_row, "Среднее часов в день:", "lbl_avg_hours")
        stat_row += 1
        self._add_info_row(stats_layout, stat_row, "Дней с активностью:", "lbl_active_days")
        
        layout.addWidget(stats_frame)
        
        # Добавляем растягивающийся элемент
        layout.addStretch()
    
    def _add_info_row(self, layout, row, label_text, value_name):
        """Добавляет строку с информацией"""
        label = QLabel(label_text)
        label.setStyleSheet("font-weight: bold; color: #000000; font-size: 11pt;")
        layout.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight)
        
        value = QLabel("-")
        value.setObjectName(value_name)
        value.setStyleSheet("color: #333333; font-size: 11pt;")
        layout.addWidget(value, row, 1, Qt.AlignmentFlag.AlignLeft)
        
        setattr(self, value_name, value)
    
    def set_user(self, user_id):
        """Устанавливает текущего пользователя и загружает его данные"""
        self.user_id = user_id
        self.load_user_info()
        self.load_statistics()
    
    def load_user_info(self):
        """Загружает информацию о пользователе из базы данных"""
        if self.user_id is None:
            return
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name, surname, patronymic, email, phone, position FROM users WHERE id=?", 
                   (self.user_id,))
        row = cur.fetchone()
        conn.close()
        
        if row:
            name, surname, patronymic, email, phone, position = row
            fullname = f"{surname} {name} {patronymic}".strip()
            
            self.lbl_fullname_value.setText(fullname)
            self.lbl_email_value.setText(email or "-")
            self.lbl_phone_value.setText(phone or "-")
            self.lbl_position_value.setText(position or "-")
    
    def load_statistics(self):
        """Загружает статистику работы пользователя"""
        if self.user_id is None:
            return
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT day, hours FROM usage_hours WHERE user_id=?", (self.user_id,))
        rows = cur.fetchall()
        conn.close()
        
        if rows:
            total_hours = sum(h for _, h in rows)
            active_days = sum(1 for _, h in rows if h > 0)
            avg_hours = total_hours / 7 if rows else 0
            
            self.lbl_total_hours.setText(f"{total_hours:.2f} ч")
            self.lbl_avg_hours.setText(f"{avg_hours:.2f} ч")
            self.lbl_active_days.setText(f"{active_days} дней")
        else:
            self.lbl_total_hours.setText("0.00 ч")
            self.lbl_avg_hours.setText("0.00 ч")
            self.lbl_active_days.setText("0 дней")
    
    def update_statistics(self):
        """Обновляет статистику"""
        self.load_statistics()


class UserTabsWidget(QTabWidget):
    """
    Главный виджет с вкладками для авторизованного пользователя
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Инициализация вкладок"""
        # Создаем вкладки
        self.time_tracking_tab = TimeTrackingTab()
        self.user_info_tab = UserInfoTab()
        
        # Добавляем вкладки
        self.addTab(self.time_tracking_tab, "⏱ Учет времени")
        self.addTab(self.user_info_tab, "👤 Мой профиль")
        
        # Стили для табов
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #E0E0E0;
                border-radius: 5px;
                background-color: #FFFFFF;
            }
            
            QTabBar::tab {
                background-color: #F0F0F0;
                color: #000000;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-weight: bold;
            }
            
            QTabBar::tab:selected {
                background-color: #FDD200;
                color: #000000;
            }
            
            QTabBar::tab:hover {
                background-color: #E0E0E0;
            }
        """)
    
    def set_user(self, user_id):
        """Устанавливает текущего пользователя для всех вкладок"""
        self.time_tracking_tab.set_user(user_id)
        self.user_info_tab.set_user(user_id)
    
    def update_time_tracking(self, session_seconds):
        """Обновляет данные учета времени"""
        self.time_tracking_tab.update_session_seconds(session_seconds)
        self.time_tracking_tab.update_heatmap()
        self.user_info_tab.update_statistics()

