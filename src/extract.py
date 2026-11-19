# 0. Импортируем необходимые библиотеки
import pandas as pd
import os
import kagglehub as kh

# Загружаем данные с сайта Kaggle
print("Загружаем данные Uderstat с сайта Kaggle...")
path = kh.dataset_download("codytipton/understat-data")
print(f"Датасет скачан в папку: {path}")

print("\nСмотрим файлы в архиве...")
print(os.listdir(path))

# 1. Указываем прямую ссылку на CSV-файл с матчами РПЛ сезона 22/23
url = "https://www.football-data.co.uk/new/RUS.csv"

# 2. Загружаем данные в DataFrame (таблицу pandas)
df = pd.read_csv(url)

# 3. Смотрим на результат
print("Данные успешно загружены!")
print(f"Размер таблицы: {df.shape[0]} строк и {df.shape[1]} столбцов")
print("\nПервые 5 строк:")
print(df.head())

# 4. Сохраняем данные в локальный CSV-файл для дальнейшего использования
df.to_csv("data/rpl_raw.csv", index=False)
print("\nДанные сохранены в файл 'data/rpl_raw.csv'")

# 5. Формируем корректный путь к файлу 'game_stats.csv' внутри скачанного архива
understat_file_path = os.path.join(path, "game_stats.csv")
understat_df = pd.read_csv(understat_file_path)
print("\nДанные Understat успешно загружены!")

print(f"Размер таблицы Understat: {understat_df.shape[0]} строк и {understat_df.shape[1]} столбцов")
print("\nНазвания столбцов:")
print(understat_df.columns.tolist())

print("\nСлучайные 5 строк таблицы Understat:")
print(understat_df.sample(5))  # Используем sample для случайного выбора строк, чтобы увидеть разнообразие данных