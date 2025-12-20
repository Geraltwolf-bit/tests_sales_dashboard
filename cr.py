import json
from datetime import datetime, timezone

import pandas as pd
import requests
from shapely.geometry import shape

# --- Настройки ---
GDF_PATH = "gdf.csv"

# geoBoundaries: 
ADM1_GEOJSON_URL = (
    "https://www.geoboundaries.org/data/geoBoundaries-2_0_1/UKR/ADM1/"
    "geoBoundaries-2_0_1-UKR-ADM1.geojson"
)

# Как назовём регионы у тебя в gdf (под это же имя потом должны совпадать данные в df.csv)
TARGETS = [
    ("Республика Крым", ["crimea", "krym", "крым"]),
    ("Севастополь", ["sevastopol", "севастоп"]),
]


def _feat_text(ft: dict) -> str:
    """Собираем весь текст из properties, чтобы искать по ключевым словам."""
    props = ft.get("properties") or {}
    return " ".join(str(v) for v in props.values()).lower()


def find_feature(features: list[dict], keywords: list[str]) -> dict:
    """Ищем фичу по набору ключевых слов (все должны встретиться)."""
    kws = [k.lower() for k in keywords]
    for ft in features:
        t = _feat_text(ft)
        if all(k in t for k in kws):
            return ft
    return {}


def main() -> None:
    gdf = pd.read_csv(GDF_PATH)

    # Уже добавляли? — выходим аккуратно
    existing = set(str(x) for x in gdf.get("name", pd.Series([], dtype=str)).tolist())
    if "Республика Крым" in existing and "Севастополь" in existing:
        print("В gdf.csv уже есть Республика Крым и Севастополь — ничего не делаю.")
        return

    resp = requests.get(ADM1_GEOJSON_URL, timeout=60)
    resp.raise_for_status()
    nf = resp.json()
    features = nf.get("features", [])
    if not features:
        raise RuntimeError("Не нашёл features в GeoJSON, проверь URL/ответ сервера.")

    now = datetime.now(timezone.utc).isoformat()

    # Подготовим поля, которые есть в твоём gdf.csv
    cols = list(gdf.columns)

    # Генераторы новых id/индексов под твой формат
    next_cartodb_id = int(gdf["cartodb_id"].max()) + 1 if "cartodb_id" in gdf.columns else 1
    next_unnamed = int(gdf["Unnamed: 0"].max()) + 1 if "Unnamed: 0" in gdf.columns else None

    new_rows = []

    for i, (new_name, keys) in enumerate(TARGETS):
        if new_name in existing:
            continue

        ft = {}
        # Пытаемся найти по любому из ключей (crimea/krym/крым и т.п.)
        for k in keys:
            ft = find_feature(features, [k])
            if ft:
                break

        if not ft:
            # Дадим максимально понятную ошибку
            sample_names = []
            for f in features[:30]:
                sample_names.append(str((f.get("properties") or {}).get("shapeName", "")))
            raise RuntimeError(
                f"Не смог найти фичу для '{new_name}'. "
                f"Проверь, есть ли она в geoBoundaries, и как называется. "
                f"Пример shapeName из первых 30: {sample_names}"
            )

        geom_wkt = shape(ft["geometry"]).wkt  # POLYGON/MULTIPOLYGON

        row = {c: None for c in cols}
        if "geometry" in row:
            row["geometry"] = geom_wkt
        if "name" in row:
            row["name"] = new_name
        if "name_latin" in row:
            row["name_latin"] = new_name

        if "created_at" in row:
            row["created_at"] = now
        if "updated_at" in row:
            row["updated_at"] = now
        if "cartodb_id" in row:
            row["cartodb_id"] = next_cartodb_id + i
        if "Unnamed: 0" in row and next_unnamed is not None:
            row["Unnamed: 0"] = next_unnamed + i

        new_rows.append(row)

    if not new_rows:
        print("Нечего добавлять (всё уже есть).")
        return

    gdf2 = pd.concat([gdf, pd.DataFrame(new_rows)], ignore_index=True)
    gdf2.to_csv(GDF_PATH, index=False)
    print("Готово. Добавлены регионы:", [r.get("name") for r in new_rows])
    print("Теперь строк в gdf.csv:", len(gdf2))


if __name__ == "__main__":
    main()