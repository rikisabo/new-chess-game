#!/usr/bin/env python3
"""
בדיקת לקוח גרפי - שחקן יחיד
"""

import sys
import os

# הוסף את תיקיות הפרויקט ל-path
current_dir = os.path.dirname(__file__)
client_dir = os.path.dirname(current_dir)  # עכשיו זה client/
shared_dir = os.path.join(os.path.dirname(client_dir), 'shared')  # חזרה לתיקיית הבסיס ואז shared
sys.path.insert(0, client_dir)
sys.path.insert(0, shared_dir)

import asyncio
from networked_chess_client import NetworkedChessClient

async def test_single_client():
    """בדיקת לקוח יחיד"""
    print("🎮 מתחיל לקוח יחיד...")
    
    client = NetworkedChessClient("שחקן_בודק", "white")
    
    try:
        await client.connect_to_server()
        print("✅ התחבר לשרת")
        
        # חכה קצת לראות מה קורה
        await asyncio.sleep(5)
        
        if client.game_started:
            print("❌ המשחק התחיל עם שחקן יחיד!")
            return False
        else:
            print("✅ המשחק לא התחיל - מחכה לשחקן נוסף")
            return True
            
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        return False
    finally:
        if client.connected:
            await client.websocket.close()

async def main():
    print("🧪 בדיקת לקוח גרפי יחיד")
    print("=" * 40)
    
    result = await test_single_client()
    
    if result:
        print("\n🎉 הבדיקה עברה בהצלחה!")
    else:
        print("\n💥 הבדיקה נכשלה")

if __name__ == "__main__":
    asyncio.run(main())
