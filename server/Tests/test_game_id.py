#!/usr/bin/env python3
"""
בדיקת הצגת Game ID
"""

import asyncio
import websockets
import json

async def test_game_id_display():
    """בדיקה שה-game_id מועבר נכון"""
    try:
        uri = "ws://localhost:8000"
        async with websockets.connect(uri) as websocket:
            print("מתחבר לשרת...")
            
            # שלח הודעת הצטרפות
            join_message = {
                "type": "player_join",
                "data": {
                    "player_name": "בודק_Game_ID",
                    "preferred_color": "white"
                }
            }
            
            await websocket.send(json.dumps(join_message))
            print("שלח הודעת הצטרפות")
            
            # קבל תגובה
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get('type') == 'game_state':
                game_id = data.get('data', {}).get('game_id', 'לא נמצא')
                print(f"קיבל Game ID: {game_id}")
                
                if game_id != 'לא נמצא':
                    print("✅ השרת מעביר Game ID בהצלחה!")
                    return True
                else:
                    print("❌ השרת לא מעביר Game ID")
                    return False
            else:
                print(f"❌ קיבל סוג הודעה לא צפוי: {data.get('type')}")
                return False
                
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        return False

async def main():
    print("בדיקת הצגת Game ID")
    print("=" * 40)
    
    result = await test_game_id_display()
    
    if result:
        print("\nהבדיקה עברה בהצלחה!")
        print("השרת מעביר Game ID נכון ללקוחות")
    else:
        print("\nהבדיקה נכשלה")

if __name__ == "__main__":
    asyncio.run(main())
