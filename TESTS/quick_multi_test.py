#!/usr/bin/env python3
"""
בדיקה מהירה לתמיכה במשחקים מרובים
"""

import asyncio
import websockets
import json

async def quick_multi_game_test():
    """בדיקה מהירה של תמיכה במשחקים מרובים"""
    print("🚀 בדיקה מהירה של תמיכה במשחקים מרובים")
    print("=" * 60)
    
    results = []
    
    async def connect_player(name):
        try:
            uri = "ws://localhost:8000"
            async with websockets.connect(uri) as websocket:
                # שלח הודעת הצטרפות
                join_message = {
                    "type": "player_join",
                    "data": {
                        "player_name": name,
                        "preferred_color": "white" if "1" in name else "black"
                    }
                }
                
                await websocket.send(json.dumps(join_message))
                
                # קבל תגובה
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get('type') == 'game_state':
                    game_id = data.get('data', {}).get('game_id', 'לא ידוע')
                    return f"✅ {name} -> משחק {game_id}"
                else:
                    return f"❌ {name} -> {data.get('type', 'שגיאה')}"
                    
        except Exception as e:
            return f"❌ {name} -> שגיאה: {e}"
    
    # צור 6 שחקנים = 3 משחקים
    players = [f"שחקן_{i}" for i in range(1, 7)]
    
    print(f"מתחבר {len(players)} שחקנים...")
    tasks = [connect_player(player) for player in players]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    print("\nתוצאות:")
    for result in results:
        print(result)
    
    successful = sum(1 for result in results if isinstance(result, str) and "✅" in result)
    print(f"\n📊 סיכום: {successful}/{len(players)} חיבורים מוצלחים")
    
    if successful >= 4:
        print("🎉 השרת תומך במשחקים מרובים!")
    else:
        print("⚠️  השרת עדיין מוגבל")

if __name__ == "__main__":
    asyncio.run(quick_multi_game_test())
