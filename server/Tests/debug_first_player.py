#!/usr/bin/env python3
"""
בדיקת הבעיה: שחקן ראשון פותח חלון גרפי
"""

import asyncio
import websockets
import json

async def test_first_player_detailed():
    """בדיקה מפורטת של שחקן ראשון"""
    try:
        uri = "ws://localhost:8000"
        async with websockets.connect(uri) as websocket:
            print("🔌 שחקן ראשון מתחבר...")
            
            # שלח הודעת הצטרפות
            join_message = {
                "type": "player_join",
                "data": {
                    "player_name": "שחקן_ראשון",
                    "preferred_color": "white"
                }
            }
            
            await websocket.send(json.dumps(join_message))
            print("📤 שלח הודעת הצטרפות")
            
            # קבל את כל ההודעות ובדוק אותן
            message_count = 0
            while message_count < 5:  # חכה לכמה הודעות
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    data = json.loads(response)
                    message_count += 1
                    
                    print(f"\n📨 הודעה #{message_count}:")
                    print(f"   סוג: {data.get('type', 'לא ידוע')}")
                    
                    if data.get('type') == 'game_state':
                        game_data = data.get('data', {})
                        game_id = game_data.get('game_id', 'לא נמצא')
                        status = game_data.get('status', 'לא ידוע')
                        players = game_data.get('players', {})
                        players_count = len(players)
                        
                        print(f"   🎯 Game ID: {game_id}")
                        print(f"   📊 Status: {status}")
                        print(f"   👥 שחקנים: {players_count}")
                        print(f"   📋 רשימת שחקנים: {list(players.keys())}")
                        
                        # זה החלק החשוב - איזה סטטוס נשלח?
                        if status == 'active' and players_count < 2:
                            print("   ❌ *** בעיה! *** הסטטוס 'active' עם פחות מ-2 שחקנים!")
                            return False
                        elif status == 'waiting' and players_count == 1:
                            print("   ✅ נכון - 'waiting' עם שחקן יחיד")
                        elif status == 'ready' and players_count == 2:
                            print("   ✅ נכון - 'ready' עם 2 שחקנים")
                        else:
                            print(f"   ⚠️ סטטוס לא צפוי: {status} עם {players_count} שחקנים")
                        
                except asyncio.TimeoutError:
                    print("⏰ לא הגיעו עוד הודעות")
                    break
                    
            return True
                
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        return False

async def main():
    print("🧪 בדיקת הבעיה: שחקן ראשון")
    print("=" * 50)
    
    result = await test_first_player_detailed()
    
    if result:
        print("\n✅ לא נמצאה בעיה בהודעות השרת")
    else:
        print("\n❌ נמצאה בעיה - השרת שולח סטטוס שגוי!")

if __name__ == "__main__":
    asyncio.run(main())
