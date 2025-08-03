#!/usr/bin/env python3
"""
בדיקת תמיכה במשחקים מרובים
"""

import asyncio
import websockets
import json
import sys
import time

async def test_player_connection(player_name, preferred_color):
    """חיבור של שחקן אחד"""
    try:
        uri = "ws://localhost:8000"
        async with websockets.connect(uri) as websocket:
            print(f"שחקן {player_name} מתחבר...")
            
            # שלח הודעת הצטרפות
            join_message = {
                "type": "player_join",
                "data": {
                    "player_name": player_name,
                    "preferred_color": preferred_color
                }
            }
            
            await websocket.send(json.dumps(join_message))
            print(f"שחקן {player_name} שלח הודעת הצטרפות")
            
            # קבל תגובה
            response = await websocket.recv()
            data = json.loads(response)
            print(f"שחקן {player_name} קיבל: {data.get('type', 'לא ידוע')}")
            
            if 'game_id' in data.get('data', {}):
                game_id = data['data']['game_id']
                print(f"שחקן {player_name} הוכנס למשחק {game_id}")
            
            # חכה קצת לקבלת הודעות נוספות
            try:
                for i in range(3):
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(response)
                    print(f"שחקן {player_name} קיבל הודעה נוספת: {data.get('type', 'לא ידוע')}")
            except asyncio.TimeoutError:
                print(f"שחקן {player_name} לא קיבל הודעות נוספות")
            
            return True
            
    except Exception as e:
        print(f"שגיאה בחיבור שחקן {player_name}: {e}")
        return False

async def test_multiple_games():
    """בדיקת משחקים מרובים - 4 שחקנים = 2 משחקים"""
    print("בדיקת משחקים מרובים")
    print("=" * 50)
    
    # צור 4 שחקנים במקביל
    tasks = [
        test_player_connection("שחקן_1", "white"),
        test_player_connection("שחקן_2", "black"),
        test_player_connection("שחקן_3", "white"),
        test_player_connection("שחקן_4", "black")
    ]
    
    print("מתחיל חיבור של 4 שחקנים...")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful_connections = sum(1 for result in results if result is True)
    print(f"חיבורים מוצלחים: {successful_connections}/4")
    
    if successful_connections >= 4:
        print("✅ בדיקת משחקים מרובים עברה בהצלחה!")
        print("השרת יכול להתמודד עם 4 שחקנים (2 משחקים)")
    else:
        print("❌ בדיקת משחקים מרובים נכשלה")

async def test_sequential_games():
    """בדיקה רציפה של משחקים"""
    print("\nבדיקה רציפה של משחקים")
    print("=" * 50)
    
    # משחק ראשון
    print("משחק ראשון:")
    result1 = await test_player_connection("משחק1_שחקן1", "white")
    await asyncio.sleep(1)
    result2 = await test_player_connection("משחק1_שחקן2", "black")
    
    await asyncio.sleep(2)
    
    # משחק שני
    print("\nמשחק שני:")
    result3 = await test_player_connection("משחק2_שחקן1", "white")
    await asyncio.sleep(1)
    result4 = await test_player_connection("משחק2_שחקן2", "black")
    
    if all([result1, result2, result3, result4]):
        print("✅ בדיקה רציפה עברה בהצלחה!")
    else:
        print("❌ בדיקה רציפה נכשלה")

async def main():
    print("בדיקות למשחקים מרובים")
    print("=" * 50)
    
    try:
        # בדיקה 1: משחקים מרובים במקביל
        await test_multiple_games()
        
        await asyncio.sleep(3)
        
        # בדיקה 2: משחקים רציפים
        await test_sequential_games()
        
        print("\nסיום בדיקות!")
        
    except KeyboardInterrupt:
        print("\nבדיקה הופסקה על ידי המשתמש")
    except Exception as e:
        print(f"שגיאה כללית: {e}")

if __name__ == "__main__":
    asyncio.run(main())
