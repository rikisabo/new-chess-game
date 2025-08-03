#!/usr/bin/env python3
"""
בדיקות כלליות - הרצת כל הבדיקות - All Tests Runner
"""

import subprocess
import sys
import os
import time

def run_test(test_path, test_name):
    """הרצת בדיקה יחידה"""
    print(f"\n{'='*60}")
    print(f"בדיקה: {test_name}")
    print(f"נתיב: {test_path}")
    print('='*60)
    
    try:
        # שנה לתיקיית הבדיקה
        original_dir = os.getcwd()
        test_dir = os.path.dirname(os.path.abspath(test_path))
        test_file = os.path.basename(test_path)
        
        os.chdir(test_dir)
        
        # הרץ את הבדיקה
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, timeout=20)
        
        os.chdir(original_dir)
        
        if result.returncode == 0:
            print(f"בדיקה עברה בהצלחה: {test_name}")
            if result.stdout:
                print("פלט:")
                print(result.stdout)
        else:
            print(f"בדיקה נכשלה: {test_name}")
            if result.stderr:
                print("שגיאות:")
                print(result.stderr)
            if result.stdout:
                print("פלט:")
                print(result.stdout)
                
        return result.returncode == 0
        
    except Exception as e:
        print(f"שגיאה {test_name}: {e}")
        return False

def main():
    """הרצת כל הבדיקות"""
    print("מתחיל הרצת כל הבדיקות...")
    
    # רשימת כל הבדיקות
    tests = [
        ("TESTS/test_multi_games.py", "בדיקת משחקים מרובים"),
        ("server/TESTS/test_single_player.py", "בדיקת שחקן יחיד - שרת"),
        ("server/TESTS/test_game_id.py", "בדיקת זיהוי משחק - שרת"),
        ("TESTS/quick_multi_test.py", "בדיקה מהירה - משחקים מרובים"),
        # בדיקות עם אמוג'ים - מושבתות זמנית:
        # ("client/TESTS/test_single_client.py", "בדיקת לקוח יחיד"),
        # ("client/TESTS/test_graphical_client.py", "בדיקת לקוח גרפי"),
    ]
    
    passed = 0
    failed = 0
    
    for test_path, test_name in tests:
        success = run_test(test_path, test_name)
        if success:
            passed += 1
        else:
            failed += 1
        
        # מעט מנוחה בין בדיקות
        time.sleep(2)
    
    # סיכום
    print(f"\n{'='*60}")
    print("סיכום תוצאות:")
    print(f"עברו: {passed}")
    print(f"נכשלו: {failed}")
    print(f"אחוז הצלחה: {(passed/(passed+failed)*100):.1f}%")
    print('='*60)
    
    if failed == 0:
        print("כל הבדיקות עברו בהצלחה!")
        return 0
    else:
        print("יש בדיקות שנכשלו")
        return 1

if __name__ == "__main__":
    sys.exit(main())
