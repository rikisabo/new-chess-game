#!/usr/bin/env python3
"""
בדיקת לקוח גרפי - שחקן יחיד (אחרי התיקון)
"""

import sys
import os
import logging

# הגדר לוגים כדי לראות מה קורה
logging.basicConfig(level=logging.INFO)

# הוסף את תיקיות הפרויקט ל-path
current_dir = os.path.dirname(__file__)
client_dir = os.path.dirname(current_dir)  # עכשיו זה client/
shared_dir = os.path.join(os.path.dirname(client_dir), 'shared')  # חזרה לתיקיית הבסיס ואז shared
sys.path.insert(0, client_dir)
sys.path.insert(0, shared_dir)

import asyncio
import time

async def test_graphical_client():
    """בדיקת לקוח גרפי יחיד"""
    print("🎮 יוצר לקוח גרפי...")
    
    try:
        from networked_chess_client import NetworkedChessClient
        
        client = NetworkedChessClient("שחקן_גרפי_בודק", "white")
        
        print("🔌 מתחבר לשרת...")
        await client.connect_to_server()
        print("✅ התחבר לשרת בהצלחה")
        
        # חכה קצת לראות מה קורה
        print("⏳ ממתין 10 שניות לראות אם נפתח חלון...")
        
        for i in range(10):
            await asyncio.sleep(1)
            
            if hasattr(client, 'game') and client.game is not None:
                print(f"❌ שגיאה! המשחק הגרפי נוצר אחרי {i+1} שניות!")
                print(f"   game_started: {client.game_started}")
                print(f"   last_players_data: {getattr(client, 'last_players_data', 'לא קיים')}")
                return False
                
            if i % 2 == 0:
                print(f"   {i+1}/10 שניות - עדיין לא נוצר משחק גרפי ✅")
        
        print("🎉 מעולה! לא נוצר משחק גרפי עם שחקן יחיד!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            if 'client' in locals() and client.connected:
                await client.websocket.close()
                print("🔌 התנתק מהשרת")
        except:
            pass

async def main():
    print("🧪 בדיקת לקוח גרפי יחיד (אחרי התיקון)")
    print("=" * 55)
    
    result = await test_graphical_client()
    
    if result:
        print("\n🎉 הבדיקה עברה בהצלחה!")
        print("הלקוח הגרפי לא פותח חלון עם שחקן יחיד")
    else:
        print("\n💥 הבדיקה נכשלה")
        print("הלקוח הגרפי עדיין פותח חלון עם שחקן יחיד")

if __name__ == "__main__":
    asyncio.run(main())
