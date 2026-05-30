import serial
import sqlite3
import os
from datetime import datetime
import time


def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS log (
                        ID TEXT,
                        DT DATETIME
                    )''')
    conn.commit()
    return conn


def main():
    com_port = 'COM3'
    baud_rate = 9600

    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    db_path = os.path.join(desktop_path, "arduino_log.db")

    # Инициализация последовательного порта
    try:
        arduino = serial.Serial(com_port, baud_rate, timeout=1)
        print(f"Подключено к {com_port} с baud rate {baud_rate}")
    except serial.SerialException:
        print("Не удается подключиться к Arduino. Проверьте COM-порт и подключение.")
        return

    # Создание базы данных
    conn = create_database(db_path)
    print("База данных создана или уже существует.")

    # Счетчик для пропуска первых трех строк
    line_count = 0

    try:
        while True:
            if arduino.in_waiting > 0:
                data = arduino.readline().decode('utf-8').strip()

                # Пропускаем первые три строки
                if line_count < 3:
                    line_count += 1
                    continue

                data = data.split(',')
                f = str(data[1:])
                data = f.replace("'", '').replace("[", '').replace("]", '')
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_entry = (data, timestamp)

                # Добавление данных в базу данных
                cursor = conn.cursor()
                cursor.execute('INSERT INTO log (ID, DT) VALUES (?, ?)', log_entry)
                conn.commit()

                # Вывод данных на экран
                print(log_entry)

                time.sleep(1)  # Задержка для предотвращения перегрузки вывода
    except KeyboardInterrupt:
        print("Программа завершена пользователем.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        arduino.close()
        conn.close()
        print("Соединение с Arduino и база данных закрыты.")


if __name__ == "__main__":
    main()