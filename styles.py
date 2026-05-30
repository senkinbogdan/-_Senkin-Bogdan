"""
Файл стилей приложения Роснефть

Описание:
    Содержит CSS-подобные стили Qt для всех элементов интерфейса.
    Использует корпоративную цветовую схему Роснефти:
    - Черный (#000000) - основной цвет
    - Желтый (#FDD200) - акцентный цвет
    - Белый (#FFFFFF) - фон

Примечание:
    Стили написаны в формате Qt Style Sheets (QSS),
    который похож на CSS, но имеет свои особенности.
"""

ROSNEFT_STYLES = """
/* ========================================================================
   БАЗОВЫЕ СТИЛИ ВИДЖЕТОВ
   ======================================================================== */

/* Общие настройки для всех виджетов */
QWidget {
    background-color: #FFFFFF;                          /* Белый фон */
    color: #000000;                                     /* Черный текст */
    font-family: 'Segoe UI', Arial, sans-serif;        /* Шрифт */
    font-size: 10pt;                                    /* Размер шрифта */
}

/* Контейнер для переключения страниц */
QStackedWidget {
    background-color: #FFFFFF;
}

/* ========================================================================
   КНОПКИ
   ======================================================================== */

/* Основные кнопки (черные) - для главных действий */
QPushButton {
    background-color: #000000;          /* Черный фон (корпоративный цвет) */
    color: #FFFFFF;                     /* Белый текст */
    border: none;                       /* Без рамки */
    border-radius: 6px;                 /* Закругленные углы */
    padding: 10px 20px;                 /* Отступы внутри кнопки */
    font-weight: bold;                  /* Жирный текст */
    font-size: 10pt;
}

/* Эффект при наведении мыши */
QPushButton:hover {
    background-color: #333333;          /* Светлее при наведении */
}

/* Эффект при нажатии */
QPushButton:pressed {
    background-color: #1A1A1A;          /* Темнее при нажатии */
}

/* Вторичные кнопки (желтые) - для второстепенных действий */
QPushButton#btn_go_register, QPushButton#btn_back_to_login {
    background-color: #FDD200;          /* Желтый фон (корпоративный цвет) */
    color: #000000;                     /* Черный текст */
}

/* Эффект наведения для желтых кнопок */
QPushButton#btn_go_register:hover, QPushButton#btn_back_to_login:hover {
    background-color: #E6BE00;          /* Темнее при наведении */
}

/* ========================================================================
   КНОПКИ РЕДАКТИРОВАНИЯ (во вкладках)
   ======================================================================== */

/* Кнопка "Редактировать" - желтая */
QPushButton#btn_edit {
    background-color: #FDD200;          /* Желтый (корпоративный) */
    color: #000000;
}

/* Кнопка "Сохранить" - зеленая */
QPushButton#btn_save {
    background-color: #28A745;          /* Зеленый (успех) */
    color: #FFFFFF;
}

/* Кнопка "Отмена" - красная */
QPushButton#btn_cancel {
    background-color: #DC3545;          /* Красный (опасность) */
    color: #FFFFFF;
}

/* ========================================================================
   ПОЛЯ ВВОДА (QLineEdit)
   ======================================================================== */

QLineEdit {
    background-color: #FFFFFF;          /* Белый фон */
    border: 2px solid #000000;          /* Черная рамка */
    border-radius: 5px;                 /* Закругленные углы */
    padding: 8px;                       /* Отступы внутри */
    color: #000000;                     /* Черный текст */
    font-size: 10pt;
}

/* Подсветка при фокусе (активное поле) */
QLineEdit:focus {
    border: 2px solid #FDD200;          /* Желтая рамка при фокусе */
}

/* ========================================================================
   ТЕКСТОВЫЕ МЕТКИ (QLabel)
   ======================================================================== */

/* Общие настройки меток */
QLabel {
    color: #000000;
    font-size: 10pt;
    background-color: transparent;       /* Прозрачный фон */
}

/* Метка с ФИО пользователя (крупная, жирная) */
QLabel#lbl_fullname {
    font-size: 14pt;
    font-weight: bold;
    color: #000000;
}

/* Метки с email и должностью */
QLabel#lbl_email, QLabel#lbl_position {
    font-size: 11pt;
    color: #333333;                      /* Серый текст */
}

/* Метки с сообщениями об ошибках (красные) */
QLabel#label_login_info, QLabel#label_register_info {
    color: #CC0000;                      /* Красный цвет для ошибок */
    font-weight: bold;
    background-color: transparent;
}

/* ========================================================================
   ТАБЛИЦЫ (QTableWidget)
   ======================================================================== */

/* Основная таблица */
QTableWidget {
    background-color: #FFFFFF;
    border: 2px solid #000000;           /* Черная рамка */
    border-radius: 5px;
    gridline-color: #DDDDDD;             /* Серые линии сетки */
}

/* Ячейки таблицы */
QTableWidget::item {
    padding: 10px;
}

/* Заголовки столбцов таблицы */
QHeaderView::section {
    background-color: #000000;           /* Черный фон */
    color: #FDD200;                      /* Желтый текст */
    padding: 8px;
    border: 1px solid #333333;
    font-weight: bold;
}

/* ========================================================================
   ПОЛОСЫ ПРОКРУТКИ (QScrollBar)
   ======================================================================== */

/* Вертикальная полоса прокрутки */
QScrollBar:vertical {
    border: none;
    background: #F5F5F5;                 /* Светло-серый фон */
    width: 10px;                         /* Ширина полосы */
    margin: 0px;
}

/* Ползунок вертикальной полосы */
QScrollBar::handle:vertical {
    background: #000000;                 /* Черный ползунок */
    border-radius: 5px;
}

/* Ползунок при наведении */
QScrollBar::handle:vertical:hover {
    background: #FDD200;                 /* Желтый при наведении */
}

/* Горизонтальная полоса прокрутки */
QScrollBar:horizontal {
    border: none;
    background: #F5F5F5;
    height: 10px;                        /* Высота полосы */
    margin: 0px;
}

/* Ползунок горизонтальной полосы */
QScrollBar::handle:horizontal {
    background: #000000;
    border-radius: 5px;
}

/* Ползунок при наведении */
QScrollBar::handle:horizontal:hover {
    background: #FDD200;
}

/* ========================================================================
   СПЕЦИАЛЬНЫЕ ЭЛЕМЕНТЫ
   ======================================================================== */

/* Логотип компании (прозрачный фон) */
QLabel#logo_label {
    background-color: transparent;
    border: none;
}
"""