import os
import sys
from datetime import datetime

# Добавляем путь к корню проекта, чтобы импорты из src работали
sys.path.append(os.getcwd())

from src.services.crop_classifier import classify_from_raster

def test_prediction(tif_path: str, date: datetime = None):
    if date:
        print(f"--- Анализ файла: {tif_path} (Дата: {date.strftime('%Y-%m-%d')}) ---")
    else:
        print(f"--- Анализ файла: {tif_path} (Дата: НЕ УКАЗАНА) ---")
        
    results = classify_from_raster(tif_path, acquisition_date=date)
    
    if results.get("error"):
        print(f"Ошибка: {results['error']}")
        return

    print(f"Предсказанная культура: {results['crop_type']}")
    print(f"Уверенность (Confidence): {results['confidence']:.2%}")
    
    details = results.get("details", {})
    if "top_candidates" in details:
        print("Топ кандидатов:")
        for cand in details["top_candidates"]:
            print(f"- {cand['crop']}: {cand['score']:.2%}")
            
    if "ndvi_stats" in details:
        s = details["ndvi_stats"]
        print(f"Статистика NDVI: Min={s['min']:.3f}, Max={s['max']:.3f}, Mean={s['mean']:.3f}, Peak={s['peak']:.3f}")

if __name__ == "__main__":
    tif_path = "test_files/NDVI.tif"
    
    # 1. Без даты
    test_prediction(tif_path)
    
    # 2. Май (разгар вегетации озимых)
    test_prediction(tif_path, datetime(2023, 5, 15))
    
    # 3. Август (разгар вегетации кукурузы/подсолнечника)
    test_prediction(tif_path, datetime(2023, 8, 15))

    # 4. Начало марта (посадка рапса, ранняя вегетация)
    test_prediction(tif_path, datetime(2023, 3, 10))
