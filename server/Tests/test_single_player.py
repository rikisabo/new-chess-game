#!/usr/bin/env python3
"""
בדיקת שחקן יחיד - לוודא שהוא לא מתחיל את המשחק
"""

import asyncio
import websockets
import json

async def test_single_player():
    """חיבור של שחקן יחיד"""
    try:
        uri = "ws://localhost:8000"
        async with websockets.connect(uri) as websocket:
            print("🔌 שחקן יחיד מתחבר...")
            
            # שלח הודעת הצטרפות
            join_message = {
                "type": "player_join",
                "data": {
                    "player_name": "שחקן_יחיד",
                    "preferred_color": "white"
                }
            }
            
            await websocket.send(json.dumps(join_message))
            print("📤 שלח הודעת הצטרפות")
            
            # קבל תגובה
            response = await websocket.recv()
            data = json.loads(response)
            
            print(f"📨 קיבל: {data.get('type', 'לא ידוע')}")
            
            if data.get('type') == 'game_state':
                game_data = data.get('data', {})
                game_id = game_data.get('game_id', 'לא נמצא')
                status = game_data.get('status', 'לא ידוע')
                players_count = len(game_data.get('players', {}))
                
                print(f"🎯 Game ID: {game_id}")
                print(f"📊 Status: {status}")
                print(f"👥 שחקנים: {players_count}")
                
                if status == 'waiting':
                    print("✅ נכון! השרת מחכה לשחקן נוסף")
                    return True
                elif status == 'active':
                    print("❌ שגיאה! השרת התחיל משחק עם שחקן יחיד")
                    return False
                else:
                    print(f"⚠️ סטטוס לא צפוי: {status}")
                    return False
            
            # חכה קצת לראות אם מגיעות הודעות נוספות
            print("⏳ ממתין לבדוק אם מגיעות הודעות נוספות...")
            try:
                for i in range(3):
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(response)
                    print(f"📨 הודעה נוספת: {data.get('type', 'לא ידוע')}")
                    
                    if data.get('type') == 'game_state':
                        status = data.get('data', {}).get('status', 'לא ידוע')
                        if status == 'active':
                            print("❌ השרת שלח 'active' לשחקן יחיד!")
                            return False
                            
            except asyncio.TimeoutError:
                print("✅ לא הגיעו הודעות נוספות - זה טוב!")
                
            return True
                
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        return False

async def main():
    print("🧪 בדיקת שחקן יחיד")
    print("=" * 40)
    
    result = await test_single_player()
    
    if result:
        print("\n🎉 הבדיקה עברה בהצלחה!")
        print("השרת לא מתחיל משחק עם שחקן יחיד")
    else:
        print("\n💥 הבדיקה נכשלה")
        print("השרת מתחיל משחק עם שחקן יחיד")

if __name__ == "__main__":
    asyncio.run(main())
