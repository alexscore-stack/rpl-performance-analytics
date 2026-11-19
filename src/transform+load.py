"""
ETL-пайплайн: Трансформация и объединение данных РПЛ
Источники:
  1. football-data.co.uk (RUS.csv) — реальные голы, результаты
  2. Kaggle/Understat (game_stats.csv) — метрики xG, xGA

Цель: создать аналитическую витрину для сравнения реальных голов с ожидаемыми (xG)
"""

import pandas as pd
import os
import sqlite3

# ============================================================================
# ШАГ 1: ЗАГРУЗКА СЫРЫХ ДАННЫХ
# ============================================================================

print("Загрузка сырых данных")

df1 = pd.read_csv('data/rpl_raw.csv')

path_understat = "/Users/aleksandr/.cache/kagglehub/datasets/codytipton/understat-data/versions/3"
df2 = pd.read_csv(os.path.join(path_understat, 'game_stats.csv'))

# Оставляем только РПЛ в Understat
df2_rpl = df2[df2['league'] == 'RFPL'].copy()

# ============================================================================
# ШАГ 2: УНИФИКАЦИЯ НАЗВАНИЙ КОМАНД (Entity Resolution)
# ============================================================================
# Разные источники используют разные названия для одних и тех же клубов.
# Например: 'Dinamo Moscow' (Understat) vs 'Dynamo Moscow' (football-data).
# Применяем маппинг к ОБОИМ источникам, чтобы устранить внутренние дубли
# (например, 'T. Moscow' и 'Torpedo Moscow' в football-data).

team_mapping = {
    'Torpedo Moscow': 'T. Moscow',
    'Dinamo Moscow': 'Dynamo Moscow',
    'FC Rostov': 'FK Rostov',
    'FC Krasnodar': 'Krasnodar',
    'FC Orenburg': 'Orenburg',
    'FC Ufa': 'Ufa',
    'FC Tambov': 'Tambov',
    'FC Rotor Volgograd': 'R. Volgograd',
    'FC Yenisey Krasnoyarsk': 'Yenisey',
    'FK Akhmat': 'Akhmat Grozny',
    'Fakel': 'Fakel Voronezh',
    'Krylya Sovetov Samara': 'Krylya Sovetov',
    'Kuban Krasnodar': 'Kuban',
    'Mordovya': 'M. Saransk',
    'Nizhny Novgorod': 'Pari NN',
    'PFC Sochi': 'Sochi',
    'SKA-Khabarovsk': 'SKA Khabarovsk',
    'Tom Tomsk': 'Tomsk',
    'Zenit St. Petersburg': 'Zenit',
    'Anzhi Makhachkala': 'FK Anzi Makhackala',
    'Akron': 'Akron Togliatti'
}

df1['Home'] = df1['Home'].map(team_mapping).fillna(df1['Home'])
df1['Away'] = df1['Away'].map(team_mapping).fillna(df1['Away'])
df2_rpl['club_name'] = df2_rpl['club_name'].map(team_mapping).fillna(df2_rpl['club_name'])

# ============================================================================
# ШАГ 3: ПРЕОБРАЗОВАНИЕ В ДЛИННЫЙ ФОРМАТ (Unpivot)
# ============================================================================
# football-data хранит данные в широком формате (1 строка = 1 матч,
# есть столбцы Home и Away). Understat — в длинном (1 строка = 1 команда в матче).
# Приводим оба источника к длинному формату для корректного слияния.

df1_home = pd.DataFrame({
    'date': df1['Date'],
    'season': df1['Season'],
    'club_name': df1['Home'],
    'home_away': 'h',
    'scored': df1['HG'],
    'result': df1['Res'].map({'H': 'w', 'D': 'd', 'A': 'l'})
})

df1_away = pd.DataFrame({
    'date': df1['Date'],
    'season': df1['Season'],
    'club_name': df1['Away'],
    'home_away': 'a',
    'scored': df1['AG'],
    'result': df1['Res'].map({'A': 'w', 'D': 'd', 'H': 'l'})
})

df1_long = pd.concat([df1_home, df1_away], ignore_index=True)

# Приводим даты к единому формату pandas datetime
df1_long['date'] = pd.to_datetime(df1_long['date'], format='%d/%m/%Y').dt.date
df2_rpl['date'] = pd.to_datetime(df2_rpl['date']).dt.date

# ============================================================================
# ШАГ 4: УНИФИКАЦИЯ ФОРМАТА СЕЗОНА
# ============================================================================
# football-data: '2014/2015', Understat: 2014 (int). Приводим к общему виду.

df2_rpl['season'] = df2_rpl['season'].astype(int).astype(str) + '/' + (df2_rpl['season'].astype(int) + 1).astype(str)

# ============================================================================
# ШАГ 5: СПРАВОЧНИК СЕЗОНОВ РПЛ (Dimension Table)
# ============================================================================
# Вместо грубой фильтрации по месяцам используем справочник официальных дат
# начала и окончания регулярных чемпионатов. Это позволяет автоматически
# исключить стыковые матчи (июнь) и предсезонные игры без риска обрезать
# данные регулярного турнира.

seasons_mapping = {
    '2014/2015': {'start': '2014-08-01', 'end': '2015-05-23'},
    '2015/2016': {'start': '2015-07-17', 'end': '2016-05-21'},
    '2016/2017': {'start': '2016-07-30', 'end': '2017-05-21'},
    '2017/2018': {'start': '2017-07-15', 'end': '2018-05-13'},
    '2018/2019': {'start': '2018-07-27', 'end': '2019-05-26'},
    '2019/2020': {'start': '2019-07-12', 'end': '2020-07-22'}, #COVID
    '2020/2021': {'start': '2020-08-08', 'end': '2021-05-16'},
    '2021/2022': {'start': '2021-07-23', 'end': '2022-05-21'},
    '2022/2023': {'start': '2022-07-15', 'end': '2023-06-03'},
    '2023/2024': {'start': '2023-07-21', 'end': '2024-05-25'}
}

seasons_df = pd.DataFrame([
    {'season': s, 'start_date': i['start'], 'end_date': i['end']}
    for s, i in seasons_mapping.items()
])
seasons_df['start_date'] = pd.to_datetime(seasons_df['start_date'])
seasons_df['end_date'] = pd.to_datetime(seasons_df['end_date']).dt.date

# Применяем справочник к обоим источникам
df1_with_seasons = pd.merge(df1_long, seasons_df, on='season', how='left')
df2_with_seasons = pd.merge(df2_rpl, seasons_df, on='season', how='left')

# Фильтруем только матчи в рамках регулярного чемпионата
df1_regular = df1_with_seasons[
    (df1_with_seasons['date'] >= df1_with_seasons['start_date']) &
    (df1_with_seasons['date'] <= df1_with_seasons['end_date'])
].copy()

df2_regular = df2_with_seasons[
    (df2_with_seasons['date'] >= df2_with_seasons['start_date']) &
    (df2_with_seasons['date'] <= df2_with_seasons['end_date'])
].copy()

# ============================================================================
# ОТЛАДКА: Проверка данных перед финальным merge
# ============================================================================
print(f"\n=== ОТЛАДКА ===")
print(f"df1_regular: {df1_regular.shape[0]} записей")
print(f"df2_regular: {df2_regular.shape[0]} записей")

print(f"\nФормат дат в df1_regular:")
print(df1_regular['date'].head())
print(f"Тип: {df1_regular['date'].dtype}")

print(f"\nФормат дат в df2_regular:")
print(df2_regular['date'].head())
print(f"Тип: {df2_regular['date'].dtype}")

print(f"\nЗначения home_away в df1_regular:")
print(df1_regular['home_away'].unique())

print(f"\nЗначения home_away в df2_regular:")
print(df2_regular['home_away'].unique())

print(f"\nПримеры club_name в df1_regular:")
print(df1_regular['club_name'].unique()[:10])

print(f"\nПримеры club_name в df2_regular:")
print(df2_regular['club_name'].unique()[:10])

# ============================================================================
# ШАГ 6: ФИНАЛЬНОЕ СЛИЯНИЕ (Inner Join)
# ============================================================================
# Используем inner join для гарантии 100% наличия как реальных голов,
# так и метрик xG в итоговой витрине.

df_final = pd.merge(
    df1_regular,
    df2_regular,
    on=['date', 'club_name', 'home_away'],
    how='inner',
    suffixes=('_fd', '_us')
)

# ============================================================================
# ШАГ 7: СОЗДАНИЕ БИЗНЕС-МЕТРИК
# ============================================================================
# xG_diff: разница между забитыми голами и ожидаемыми.
# Положительное значение = перевыполнение xG (хорошая реализация).
# Отрицательное = недореализация.

df_final['xG_diff'] = df_final['scored_fd'] - df_final['xG']
df_final = df_final.rename(columns={'scored_fd': 'goals_scored'})

# ============================================================================
# ШАГ 8: СОХРАНЕНИЕ ВИТРИНЫ (LOAD)
# ============================================================================

# Создаём папки, если их нет
os.makedirs('data', exist_ok=True)
os.makedirs('database', exist_ok=True)

# Сохранение в CSV (для быстрого доступа и Excel)
csv_path = 'data/rpl_final_vitrina.csv'
df_final.to_csv(csv_path, index=False, encoding='utf-8-sig')
print(f"Витрина сохранена в CSV: {csv_path}")

# Сохранение в SQLite (демонстрация навыков работы с БД)
db_path = 'database/rpl_analytics.db'
conn = sqlite3.connect(db_path)
df_final.to_sql('matches_xg', conn, if_exists='replace', index=False)
conn.close()
print(f"Витрина загружена в SQLite: {db_path}")

# ============================================================================
# ИТОГОВАЯ СТАТИСТИКА
# ============================================================================
print(f"\nИтоговые метрики витрины:")
print(f"   Записей: {df_final.shape[0]}")
print(f"   Столбцов: {df_final.shape[1]}")
print(f"   Период: с {df_final['date'].min()} по {df_final['date'].max()}")
print(f"   Уникальных команд: {df_final['club_name'].nunique()}")
print(f"   Уникальных сезонов: {df_final['season_fd'].nunique()}")