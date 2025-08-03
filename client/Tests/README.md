# 🧪 בדיקות לקוח (Client Tests)

תיקייה זו מכילה בדיקות עבור הלקוח הגרפי של משחק השחמט.

## קבצי בדיקות:

### `test_single_client.py`
- **מטרה**: בדיקת לקוח יחיד - וידוא שהמשחק לא מתחיל עם שחקן אחד
- **שימוש**: `python test_single_client.py`
- **מה זה בודק**: שהלקוח הגרפי לא פותח חלון כשיש רק שחקן אחד

### `test_graphical_client.py`
- **מטרה**: בדיקה מפורטת של הלקוח הגרפי
- **שימוש**: `python test_graphical_client.py`
- **מה זה בודק**: שהמשחק הגרפי לא נוצר עם שחקן יחיד (10 שניות מעקב)

## איך להריץ:

```bash
cd client/TESTS
python test_single_client.py
python test_graphical_client.py
```

## דרישות:
- השרת צריך להיות פועל על פורט 8000
- חבילות Python: `websockets`, `asyncio`
- הלקוח הגרפי צריך להיות זמין
