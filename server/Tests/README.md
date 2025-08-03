# 🧪 בדיקות שרת (Server Tests)

תיקייה זו מכילה בדיקות עבור השרת של משחק השחמט.

## קבצי בדיקות:

### `test_single_player.py`
- **מטרה**: בדיקת שחקן יחיד - וידוא שהשרת מחכה לשחקן נוסף
- **שימוש**: `python test_single_player.py`
- **מה זה בודק**: שהשרת שולח סטטוס `waiting` עם שחקן יחיד

### `test_game_id.py`
- **מטרה**: בדיקת העברת Game ID מהשרת ללקוח
- **שימוש**: `python test_game_id.py`
- **מה זה בודק**: שהשרת מעביר `game_id` נכון בהודעות

### `debug_first_player.py`
- **מטרה**: ניפוי שגיאות - בדיקה מפורטת של שחקן ראשון
- **שימוש**: `python debug_first_player.py`
- **מה זה בודק**: מעקב מפורט אחר כל ההודעות שהשרת שולח לשחקן ראשון

## איך להריץ:

```bash
cd server/TESTS
python test_single_player.py
python test_game_id.py
python debug_first_player.py
```

## דרישות:
- השרת צריך להיות פועל על פורט 8000
- חבילות Python: `websockets`, `asyncio`, `json`
