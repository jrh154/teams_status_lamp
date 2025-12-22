import comtypes
import psutil
from pycaw.pycaw import AudioUtilities
# We no longer need to import AudioSessionState as we use the integer value

# Define the numerical constant for clarity
AUDIO_SESSION_STATE_ACTIVE = 1 

def is_app_using_microphone(target_app_name: str) -> bool:
    """Checks if a specific application (by name) has an active audio session."""
    
    comtypes.CoInitialize()
    target_app_name = target_app_name.lower()
    
    try:
        sessions = AudioUtilities.GetAllSessions()
        
        for session in sessions:
            # FIX: Use the integer value 1 for AudioSessionStateActive
            if session.State == AUDIO_SESSION_STATE_ACTIVE: 
                
                pid = session.ProcessId
                
                try:
                    process = psutil.Process(pid)
                    process_name = process.name().lower()
                    
                    if target_app_name in process_name:
                        return True
                        
                except psutil.NoSuchProcess:
                    continue
                except Exception as e:
                    # Handle other potential errors during process lookup
                    print(f"Error checking process with PID {pid}: {e}")
                    continue
            
    finally:
        comtypes.CoUninitialize()

    return False

# Example usage:
if is_app_using_microphone("ms-teams.exe"):
    print("✅ Teams is currently using the microphone.")
else:
    print("❌ Teams is NOT currently using the microphone.")