import os
import subprocess
import sys

def check_mail_access():
    print("📧 Checking Mail.app Access...")
    
    # AppleScript to get unread count form Inbox
    scpt = '''
    tell application "Mail"
        return unread count of inbox
    end tell
    '''
    
    try:
        # Run osascript
        result = subprocess.run(['osascript', '-e', scpt], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ SUCCESS! Mail.app is accessible.")
            print(f"📬 Unread Count in Inbox: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ FAILED. Error from macOS:")
            print(f"   {result.stderr.strip()}")
            if "Not authorized" in result.stderr or "User canceled" in result.stderr:
                print("\n🔐 PERMISSION ISSUE DETECTED!")
                print("   Please go to System Settings -> Privacy & Security -> Automation")
                print("   And check if your Terminal/Editor has permission to control 'Mail'.")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    check_mail_access()
