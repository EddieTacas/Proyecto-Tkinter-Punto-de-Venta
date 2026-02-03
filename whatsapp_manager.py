import subprocess
import requests
import time
import os
import threading
import json
from config_manager import load_setting

class BaileysManager:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(BaileysManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        
        self.service_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'whatsapp_service')
        self.port = 3000
        self.api_url = f"http://localhost:{self.port}"
        self.process = None
        self.stopping = False
        self.initialized = True
        
        # Start automatically if permitted/configured?
        # User requirement says: Start at 8AM, stop at 6PM.
        # But for now, we just provider methods. Main app schedules them.
        self.start_service()

    def start_service(self):
        if self.is_running():
            print("WhatsApp Service already running.")
            return

        print("Starting WhatsApp Service...")
        npm_cmd = "npm"  # Or full path if needed
        script = "start" # defined in package.json
        
        # Check if node_modules exists
        if not os.path.exists(os.path.join(self.service_dir, 'node_modules')):
            print("Dependencies not installed. Attempting npm install...")
            try:
                subprocess.check_call([npm_cmd, "install"], cwd=self.service_dir, shell=True)
            except Exception as e:
                print(f"Failed to install dependencies: {e}")
                return

        try:
            # shell=True required on Windows for npm
            # Redirect to a file for debugging
            log_file = open(os.path.join(self.service_dir, "service_output.log"), "w")
            self.process = subprocess.Popen(
                [npm_cmd, "start"],
                cwd=self.service_dir,
                shell=True,
                stdout=log_file,
                stderr=subprocess.STDOUT
            )
            print(f"Service started with PID {self.process.pid}")
            time.sleep(5) # Wait for startup
        except Exception as e:
            print(f"Error starting service: {e}")

    def stop_service(self):
        # On Windows, killing Popen shell=True is tricky.
        # Usually need to kill the tree.
        if self.process:
            print("Stopping WhatsApp Service...")
            try:
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.process.pid)])
            except:
                pass
            self.process = None
        else:
            # Always try to clean up port if process logic fails or if it's orphan
            pass 
            
        # FORCE KILL by port to be 100% sure
        self._kill_service_on_port(self.port)

    def _kill_service_on_port(self, port):
        """Finds process listening on port and kills it."""
        try:
            # 1. Find PID using netstat
            cmd = f'netstat -ano | findstr :{port}'
            result = subprocess.check_output(cmd, shell=True).decode()
            
            pids = set()
            for line in result.splitlines():
                parts = line.split()
                if len(parts) >= 5:
                    # Proto Local Address Foreign Address State PID
                    if "LISTENING" in parts:
                        pids.add(parts[-1])
            
            if not pids:
                print(f"No process found listening on port {port}")
                return

            # 2. Kill PIDs
            for pid in pids:
                if pid == "0": continue
                print(f"Killing orphan process PID {pid}")
                subprocess.call(['taskkill', '/F', '/T', '/PID', pid])
                
        except Exception as e:
            print(f"Error killing process on port {port}: {e}")

    def is_running(self):
        try:
            # Check API status
            response = requests.get(f"{self.api_url}/status", timeout=2)
            return response.status_code == 200
        except:
            return False

    def get_status(self):
        try:
            response = requests.get(f"{self.api_url}/status", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            pass
        return {"status": "SERVICE_DOWN"}

    def get_qr(self):
        try:
            response = requests.get(f"{self.api_url}/qr", timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def send_message(self, number, message):
        try:
            payload = {"number": number, "message": message}
            response = requests.post(f"{self.api_url}/send", json=payload, timeout=10)
            return response.json()
        except Exception as e:
            return {"success": False, "message": str(e)}

    def connect_service(self):
        try:
            response = requests.post(f"{self.api_url}/connect", timeout=5)
            return response.json()
        except Exception as e:
            return {"success": False, "message": str(e)}

    def run_list_groups_script(self):
        """Runs the list_groups.js script and returns the path to the output file."""
        script_path = "list_groups.js" # in service_dir
        output_file = "mis_grupos_whatsapp.txt"
        full_output_path = os.path.join(self.service_dir, output_file)
        
        # Ensure service dependencies are there
        if not os.path.exists(os.path.join(self.service_dir, 'node_modules')):
             return {"success": False, "message": "Node modules not found. Service might not be installed."}
        
        print("Running list_groups.js...")
        try:
            npm_cmd = "node" # Run with node directly
            
            # subprocess.run waits for completion
            result = subprocess.run(
                [npm_cmd, script_path],
                cwd=self.service_dir,
                capture_output=True,
                text=True,
                shell=True 
            )
            
            if result.returncode == 0:
                if os.path.exists(full_output_path):
                    return {"success": True, "path": full_output_path, "output": result.stdout}
                else:
                    return {"success": False, "message": "Script finished but output file not found."}
            else:
                 return {"success": False, "message": f"Script failed: {result.stderr}"}
                 
        except Exception as e:
            return {"success": False, "message": str(e)}

# Global instance
baileys_manager = BaileysManager()
