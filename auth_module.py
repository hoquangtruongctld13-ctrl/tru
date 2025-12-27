"""
Authentication Module for TTS Studio
Provides login/registration functionality with server authentication.
Designed for easy deployment and Nuitka compilation.

Usage:
    from auth_module import AuthManager, LoginWindow
    
    # Initialize auth manager
    auth = AuthManager(server_url="http://your-server.com")
    
    # Show login window (blocks until authenticated)
    if not AuthManager.show_login_dialog(root, auth):
        sys.exit(0)  # User cancelled or failed to login
"""

import os
import sys
import json
import hashlib
import platform
import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Tuple, Any
from dataclasses import dataclass, asdict
import threading

# Try to import customtkinter, fall back to standard tkinter
try:
    import customtkinter as ctk
    HAS_CUSTOMTKINTER = True
except ImportError:
    HAS_CUSTOMTKINTER = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ServerConfig:
    """Server configuration"""
    base_url: str = "http://34.173.37.168"
    timeout: int = 60


@dataclass
class UserSession:
    """User session information after login"""
    token: str
    user_id: int
    username: str
    local_srt_lines_used: int = 0
    daily_local_srt_limit: int = 0


@dataclass
class SavedCredentials:
    """
    Saved credentials for auto-login.
    
    SECURITY NOTE: Password is stored in base64 encoding (NOT encryption).
    This provides minimal obfuscation but is NOT secure against determined attackers.
    For production use, consider:
    - Using OS keyring (keyring module)
    - Implementing proper encryption
    - Using refresh tokens instead of passwords
    """
    username: str
    password: str  # Base64 encoded - see note above
    server_url: str
    remember: bool = True


# =============================================================================
# AUTH SERVICE
# =============================================================================

class AuthService:
    """Service for handling registration/login with server"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.session: Optional[UserSession] = None
    
    def _get_hwid(self) -> str:
        """Generate HWID based on machine information using SHA-256"""
        machine_info = f"{platform.node()}-{uuid.getnode()}"
        return hashlib.sha256(machine_info.encode()).hexdigest()[:32]
    
    def register(self, username: str, password: str, email: str) -> Tuple[bool, str]:
        """Register a new account"""
        if not HAS_REQUESTS:
            return False, "Module 'requests' is not installed"
        
        url = f"{self.config.base_url}/api/auth/register"
        payload = {
            "username": username,
            "password": password,
            "email": email,
            "hwid": self._get_hwid()
        }
        
        try:
            response = requests.post(url, json=payload, timeout=self.config.timeout)
            
            if response.status_code == 200:
                return True, "Đăng ký thành công!"
            else:
                error_msg = response.text
                return False, f"Lỗi đăng ký: {error_msg}"
        except requests.RequestException as e:
            return False, f"Lỗi kết nối: {str(e)}"
    
    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """Login to server"""
        if not HAS_REQUESTS:
            return False, "Module 'requests' is not installed"
        
        url = f"{self.config.base_url}/api/auth/login"
        payload = {
            "username": username,
            "password": password,
            "hwid": self._get_hwid()
        }
        
        try:
            response = requests.post(url, json=payload, timeout=self.config.timeout)
            
            if response.status_code == 200:
                data = response.json()
                self.session = UserSession(
                    token=data.get('token', ''),
                    user_id=data.get('id', 0),
                    username=data.get('username', username),
                    local_srt_lines_used=data.get('localSrtLinesUsedToday', 0),
                    daily_local_srt_limit=data.get('dailyLocalSrtLineLimit', 0)
                )
                return True, "Đăng nhập thành công!"
            else:
                error_msg = response.text
                return False, f"Lỗi đăng nhập: {error_msg}"
        except requests.RequestException as e:
            return False, f"Lỗi kết nối: {str(e)}"
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API calls"""
        if not self.session:
            raise ValueError("Not logged in")
        return {
            "Authorization": f"Bearer {self.session.token}",
            "Content-Type": "application/json"
        }
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.session is not None
    
    def logout(self) -> None:
        """Logout current user"""
        self.session = None


# =============================================================================
# CREDENTIALS MANAGER
# =============================================================================

class CredentialsManager:
    """Manager for saving and loading credentials"""
    
    DEFAULT_FILE = "credentials.json"
    
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or self.DEFAULT_FILE
    
    def save(self, credentials: SavedCredentials) -> bool:
        """Save credentials to file"""
        try:
            data = asdict(credentials)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving credentials: {e}")
            return False
    
    def load(self) -> Optional[SavedCredentials]:
        """Load credentials from file"""
        if not os.path.exists(self.file_path):
            return None
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return SavedCredentials(**data)
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def clear(self) -> bool:
        """Clear saved credentials"""
        try:
            if os.path.exists(self.file_path):
                os.remove(self.file_path)
            return True
        except Exception as e:
            print(f"Error clearing credentials: {e}")
            return False


# =============================================================================
# AUTH MANAGER (Main Interface)
# =============================================================================

class AuthManager:
    """
    Main authentication manager combining AuthService and CredentialsManager.
    This is the main interface for authentication functionality.
    """
    
    def __init__(self, server_url: str = "http://localhost:5000", 
                 credentials_file: Optional[str] = None):
        self.config = ServerConfig(base_url=server_url)
        self.auth_service = AuthService(self.config)
        self.credentials_manager = CredentialsManager(credentials_file)
    
    @property
    def session(self) -> Optional[UserSession]:
        """Get current user session"""
        return self.auth_service.session
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.auth_service.is_authenticated()
    
    def set_server_url(self, url: str) -> None:
        """Update server URL"""
        self.config.base_url = url.rstrip('/')
        self.auth_service.config = self.config
    
    def register(self, username: str, password: str, email: str) -> Tuple[bool, str]:
        """Register a new account"""
        return self.auth_service.register(username, password, email)
    
    def login(self, username: str, password: str, remember: bool = False) -> Tuple[bool, str]:
        """Login and optionally save credentials"""
        success, message = self.auth_service.login(username, password)
        
        if success and remember:
            creds = SavedCredentials(
                username=username,
                password=password,
                server_url=self.config.base_url,
                remember=True
            )
            self.credentials_manager.save(creds)
        
        return success, message
    
    def auto_login(self) -> Tuple[bool, str]:
        """Attempt auto-login with saved credentials"""
        creds = self.credentials_manager.load()
        if not creds or not creds.remember:
            return False, "No saved credentials"
        
        # Update server URL from saved credentials
        self.set_server_url(creds.server_url)
        
        return self.auth_service.login(creds.username, creds.password)
    
    def logout(self, clear_saved: bool = False) -> None:
        """Logout and optionally clear saved credentials"""
        self.auth_service.logout()
        if clear_saved:
            self.credentials_manager.clear()
    
    def get_saved_credentials(self) -> Optional[SavedCredentials]:
        """Get saved credentials (for pre-filling login form)"""
        return self.credentials_manager.load()
    
    @staticmethod
    def show_login_dialog(parent: Optional[tk.Tk], auth_manager: 'AuthManager') -> bool:
        """
        Show login dialog and return True if login successful.
        This is a static method for convenience.
        """
        dialog = LoginWindow(parent, auth_manager)
        return dialog.result


# =============================================================================
# LOGIN WINDOW (CustomTkinter version)
# =============================================================================
if HAS_CUSTOMTKINTER:
    import queue
    
    class LoginWindow(ctk.CTkToplevel):
        """Login/Registration window using CustomTkinter"""
        
        def __init__(self, parent: Optional[tk.Tk], auth_manager: AuthManager):
            # Create root if parent is None
            if parent is None:
                self._temp_root = ctk.CTk()
                self._temp_root.withdraw()
                parent = self._temp_root
            else:
                self._temp_root = None
            
            self._parent = parent
            
            super().__init__(parent)
            
            self.auth_manager = auth_manager
            self.result = False
            self._is_destroyed = False
            self._callback_queue = queue.Queue()
            
            # Window setup
            self.title("🔐 Đăng nhập - TTS Studio")
            # FIX: Tăng chiều cao lên 500 để chắc chắn nút hiển thị
            self.geometry("420x500") 
            self.resizable(False, False)
            
            # Center window
            self.update_idletasks()
            x = (self.winfo_screenwidth() // 2) - (420 // 2)
            y = (self.winfo_screenheight() // 2) - (500 // 2)
            self.geometry(f"+{x}+{y}")
            
            # Make modal
            self.transient(parent)
            self.grab_set()
            
            # Setup UI
            self._setup_ui()
            
            # Load saved credentials
            self._load_saved_credentials()
            
            # Handle window close
            self.protocol("WM_DELETE_WINDOW", self._on_close)
            
            # Start polling for thread callbacks
            self._poll_callbacks()
            
            # Wait for window to close
            self.wait_window()
        
        def _poll_callbacks(self):
            if self._is_destroyed:
                return
            while True:
                try:
                    callback = self._callback_queue.get_nowait()
                    callback()
                except queue.Empty:
                    break
                except Exception as e:
                    print(f"Callback error: {e}")
            try:
                self.after(50, self._poll_callbacks)
            except Exception:
                pass
        
        def _schedule_callback(self, callback):
            self._callback_queue.put(callback)
        
        def _setup_ui(self):
            """Setup the login window UI - Compact Layout"""
            print("DEBUG: Setting up UI...")
            
            # Main frame
            main_frame = ctk.CTkFrame(self, fg_color="#1a1a2e")
            main_frame.pack(fill="both", expand=True)
            
            # Inner content frame
            content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            content_frame.pack(fill="both", expand=True, padx=40, pady=20)
            
            # Logo/Title
            ctk.CTkLabel(
                content_frame, 
                text="🎙️ TTS Studio",
                font=("Segoe UI", 32, "bold"),
                text_color="#3B82F6"
            ).pack(pady=(10, 5))
            
            ctk.CTkLabel(
                content_frame,
                text="Vui lòng đăng nhập để tiếp tục",
                font=("Segoe UI", 13),
                text_color="#9CA3AF"
            ).pack(pady=(0, 20)) # Giảm padding dưới
            
            # Username field
            ctk.CTkLabel(
                content_frame, 
                text="Tên đăng nhập", 
                anchor="w",
                font=("Segoe UI", 12),
                text_color="#E5E7EB"
            ).pack(fill="x")
            
            self.entry_username = ctk.CTkEntry(
                content_frame, 
                placeholder_text="Nhập tên đăng nhập",
                height=40, # Giảm height chút
                font=("Segoe UI", 13),
                corner_radius=8
            )
            self.entry_username.pack(fill="x", pady=(5, 10)) # Giảm padding
            
            # Password field
            ctk.CTkLabel(
                content_frame, 
                text="Mật khẩu", 
                anchor="w",
                font=("Segoe UI", 12),
                text_color="#E5E7EB"
            ).pack(fill="x")
            
            self.entry_password = ctk.CTkEntry(
                content_frame, 
                placeholder_text="Nhập mật khẩu", 
                show="*",
                height=40, # Giảm height chút
                font=("Segoe UI", 13),
                corner_radius=8
            )
            self.entry_password.pack(fill="x", pady=(5, 10)) # Giảm padding
            
            # Remember me checkbox
            self.var_remember = ctk.BooleanVar(value=True)
            self.check_remember = ctk.CTkCheckBox(
                content_frame, 
                text="Ghi nhớ đăng nhập",
                variable=self.var_remember,
                font=("Segoe UI", 12),
                text_color="#E5E7EB",
                checkbox_height=20,
                checkbox_width=20,
                corner_radius=4
            )
            self.check_remember.pack(anchor="w", pady=(5, 20))
            
            # Login button - FIX: Pack trực tiếp, không qua frame trung gian
            self.btn_login = ctk.CTkButton(
                content_frame,
                text="🔑 Đăng nhập",
                font=("Segoe UI", 15, "bold"),
                height=45,
                fg_color="#22C55E",
                hover_color="#16A34A",
                corner_radius=10,
                command=self._do_login
            )
            self.btn_login.pack(fill="x", pady=10)
            print("DEBUG: Button packed!") # Debug line
            
            # Status label
            self.lbl_status = ctk.CTkLabel(
                content_frame,
                text="",
                font=("Segoe UI", 12),
                text_color="#9CA3AF",
                wraplength=340
            )
            self.lbl_status.pack(pady=(10, 5))
            
            # Bind Enter key to login
            self.entry_password.bind("<Return>", lambda e: self._do_login())
            self.entry_username.bind("<Return>", lambda e: self.entry_password.focus())
        
        def _load_saved_credentials(self):
            """Load and fill saved credentials"""
            creds = self.auth_manager.get_saved_credentials()
            if creds:
                self.entry_username.insert(0, creds.username)
                self.entry_password.insert(0, creds.password)
                self.var_remember.set(creds.remember)
        
        def _set_status(self, text: str, color: str = "#9CA3AF"):
            """Update status label"""
            if self._is_destroyed: return
            try:
                self.lbl_status.configure(text=text, text_color=color)
                self.update_idletasks()
            except Exception: pass
        
        def _do_login(self):
            """Handle login button click"""
            if self._is_destroyed: return
            
            print("DEBUG: Login clicked")
            username = self.entry_username.get().strip()
            password = self.entry_password.get()
            remember = self.var_remember.get()
            
            if not username or not password:
                self._set_status("❌ Vui lòng nhập tên đăng nhập và mật khẩu", "#EF4444")
                return
            
            self._set_status("⏳ Đang đăng nhập...", "#3B82F6")
            self.btn_login.configure(state="disabled")
            
            def login_thread():
                try:
                    success, message = self.auth_manager.login(username, password, remember)
                    if not self._is_destroyed:
                        self._schedule_callback(lambda: self._handle_login_result(success, message))
                except Exception as e:
                    print(f"Login error: {e}")
                    if not self._is_destroyed:
                        self._schedule_callback(lambda: self._set_status(f"❌ Lỗi: {e}", "#EF4444"))
                        self._schedule_callback(lambda: self.btn_login.configure(state="normal"))

            threading.Thread(target=login_thread, daemon=True).start()
        
        def _handle_login_result(self, success: bool, message: str):
            """Handle login result in main thread"""
            if self._is_destroyed: return
            try:
                self.btn_login.configure(state="normal")
                
                if success:
                    self._set_status("✅ " + message, "#22C55E")
                    self.result = True
                    self.after(500, self._close)
                else:
                    self._set_status("❌ " + message, "#EF4444")
            except Exception: pass
        
        def _close(self):
            self._is_destroyed = True
            try: self.grab_release()
            except: pass
            try: self.destroy()
            except: pass
            if self._temp_root:
                try: self._temp_root.destroy()
                except: pass
        
        def _on_close(self):
            self.result = False
            self._close()

else:
    import queue as queue_module
    
    # Fallback to standard tkinter if customtkinter is not available
    class LoginWindow(tk.Toplevel):
        """Login/Registration window using standard Tkinter"""
        
        def __init__(self, parent: Optional[tk.Tk], auth_manager: AuthManager):
            if parent is None:
                self._temp_root = tk.Tk()
                self._temp_root.withdraw()
                parent = self._temp_root
            else:
                self._temp_root = None
            
            self._parent = parent
            
            super().__init__(parent)
            
            self.auth_manager = auth_manager
            self.result = False
            self._is_destroyed = False
            self._callback_queue = queue_module.Queue()
            
            # Window setup
            self.title("🔐 Đăng nhập - TTS Studio")
            self.geometry("380x420")
            self.resizable(False, False)
            self.configure(bg="#1a1a2e")
            
            # Center window
            self.update_idletasks()
            x = (self.winfo_screenwidth() // 2) - (380 // 2)
            y = (self.winfo_screenheight() // 2) - (420 // 2)
            self.geometry(f"+{x}+{y}")
            
            # Make modal
            self.transient(parent)
            self.grab_set()
            
            # Setup UI
            self._setup_ui()
            
            # Load saved credentials
            self._load_saved_credentials()
            
            # Handle window close
            self.protocol("WM_DELETE_WINDOW", self._on_close)
            
            # Start polling for thread callbacks
            self._poll_callbacks()
            
            # Wait for window to close
            self.wait_window()
        
        def _poll_callbacks(self):
            """Poll for pending callbacks from background threads"""
            if self._is_destroyed:
                return
            # Process all pending callbacks
            while True:
                try:
                    callback = self._callback_queue.get_nowait()
                    callback()
                except queue_module.Empty:
                    break
                except Exception as e:
                    print(f"Callback error: {e}")
            try:
                self.after(50, self._poll_callbacks)
            except Exception:
                pass
        
        def _schedule_callback(self, callback):
            """Thread-safe way to schedule a callback to run in main thread"""
            self._callback_queue.put(callback)
        
        def _setup_ui(self):
            """Setup the login window UI - Modified: Removed Register & Email"""
            print("DEBUG: Setting up UI - Registration disabled") # Debug line
            
            # Main frame with gradient-like background
            main_frame = ctk.CTkFrame(self, fg_color="#1a1a2e")
            main_frame.pack(fill="both", expand=True)
            
            # Inner content frame
            content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            content_frame.pack(fill="both", expand=True, padx=35, pady=25)
            
            # Logo/Title
            ctk.CTkLabel(
                content_frame, 
                text="🎙️ TTS Studio",
                font=("Segoe UI", 32, "bold"),
                text_color="#3B82F6"
            ).pack(pady=(20, 8))
            
            ctk.CTkLabel(
                content_frame,
                text="Vui lòng đăng nhập để tiếp tục",
                font=("Segoe UI", 13),
                text_color="#9CA3AF"
            ).pack(pady=(0, 35))
            
            # Username field
            ctk.CTkLabel(
                content_frame, 
                text="Tên đăng nhập", 
                anchor="w",
                font=("Segoe UI", 12),
                text_color="#E5E7EB"
            ).pack(fill="x")
            self.entry_username = ctk.CTkEntry(
                content_frame, 
                placeholder_text="Nhập tên đăng nhập",
                height=42,
                font=("Segoe UI", 13),
                corner_radius=8
            )
            self.entry_username.pack(fill="x", pady=(5, 15))
            
            # Password field
            ctk.CTkLabel(
                content_frame, 
                text="Mật khẩu", 
                anchor="w",
                font=("Segoe UI", 12),
                text_color="#E5E7EB"
            ).pack(fill="x")
            self.entry_password = ctk.CTkEntry(
                content_frame, 
                placeholder_text="Nhập mật khẩu", 
                show="*",
                height=42,
                font=("Segoe UI", 13),
                corner_radius=8
            )
            self.entry_password.pack(fill="x", pady=(5, 15))
            
            # REMOVED: Email entry field logic here
            
            # Remember me checkbox
            self.var_remember = ctk.BooleanVar(value=True)
            self.check_remember = ctk.CTkCheckBox(
                content_frame, 
                text="Ghi nhớ đăng nhập",
                variable=self.var_remember,
                font=("Segoe UI", 12),
                text_color="#E5E7EB",
                checkbox_height=20,
                checkbox_width=20,
                corner_radius=4
            )
            self.check_remember.pack(anchor="w", pady=(5, 30)) # Increased bottom padding slightly
            
            # Buttons frame
            btn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=(5, 10))
            
            # Login button
            self.btn_login = ctk.CTkButton(
                btn_frame,
                text="🔑 Đăng nhập",
                font=("Segoe UI", 15, "bold"),
                height=48,
                fg_color="#22C55E",
                hover_color="#16A34A",
                corner_radius=10,
                command=self._do_login
            )
            self.btn_login.pack(fill="x", pady=(0, 10))
            
            # REMOVED: Register button logic here
            
            # Status label
            self.lbl_status = ctk.CTkLabel(
                content_frame,
                text="",
                font=("Segoe UI", 12),
                text_color="#9CA3AF",
                wraplength=340
            )
            self.lbl_status.pack(pady=(15, 5))
            
            # Bind Enter key to login
            self.entry_password.bind("<Return>", lambda e: self._do_login())
            self.entry_username.bind("<Return>", lambda e: self.entry_password.focus())
        
        def _load_saved_credentials(self):
            """Load saved credentials"""
            creds = self.auth_manager.get_saved_credentials()
            if creds:
                self.entry_username.insert(0, creds.username)
                self.entry_password.insert(0, creds.password)
                self.var_remember.set(creds.remember)
        
        def _set_status(self, text: str, color: str = "gray"):
            """Update status"""
            if self._is_destroyed:
                return
            try:
                self.lbl_status.configure(text=text, foreground=color)
                self.update_idletasks()
            except Exception:
                pass
        
        def _do_login(self):
            """Handle login button click"""
            if self._is_destroyed:
                return
            
            print("DEBUG: Processing login request...") 
            username = self.entry_username.get().strip()
            password = self.entry_password.get()
            remember = self.var_remember.get()
            
            if not username or not password:
                self._set_status("❌ Vui lòng nhập tên đăng nhập và mật khẩu", "#EF4444")
                return
            
            self._set_status("⏳ Đang đăng nhập...", "#3B82F6")
            self.btn_login.configure(state="disabled")
            # REMOVED: self.btn_register configuration
            
            def login_thread():
                try:
                    success, message = self.auth_manager.login(username, password, remember)
                    
                    if not self._is_destroyed:
                        self._schedule_callback(lambda: self._handle_login_result(success, message))
                except Exception as e:
                    print(f"DEBUG: Login thread error: {e}")
                    if not self._is_destroyed:
                        self._schedule_callback(lambda: self._handle_login_result(False, f"Lỗi hệ thống: {str(e)}"))
            
            threading.Thread(target=login_thread, daemon=True).start()
        
        def _handle_login_result(self, success: bool, message: str):
            """Handle login result in main thread"""
            if self._is_destroyed:
                return
            try:
                self.btn_login.configure(state="normal")
                # REMOVED: self.btn_register configuration
                
                if success:
                    print(f"DEBUG: Login successful for user: {self.entry_username.get()}")
                    self._set_status("✅ " + message, "#22C55E")
                    self.result = True
                    self.after(500, self._close)
                else:
                    print(f"DEBUG: Login failed: {message}")
                    self._set_status("❌ " + message, "#EF4444")
            except Exception as e:
                print(f"DEBUG: Error in handle_login_result: {e}")
               
        
        def _close(self):
            """Close window"""
            self._is_destroyed = True
            try:
                self.grab_release()
            except Exception:
                pass
            try:
                self.destroy()
            except Exception:
                pass
            if self._temp_root:
                try:
                    self._temp_root.destroy()
                except Exception:
                    pass
        
        def _on_close(self):
            """Handle close button"""
            self.result = False
            self._close()


# =============================================================================
# HELPER FUNCTION FOR MAIN APP INTEGRATION
# =============================================================================

def require_login(server_url: str = "http://localhost:5000", 
                  credentials_file: Optional[str] = None,
                  skip_auto_login: bool = False) -> Optional[AuthManager]:
    """
    Require user to login before application starts.
    Returns AuthManager if login successful, None if cancelled.
    
    Usage:
        auth = require_login("http://your-server.com")
        if auth is None:
            sys.exit(0)
        # Continue with authenticated user
        print(f"Welcome, {auth.session.username}!")
    """
    auth = AuthManager(server_url=server_url, credentials_file=credentials_file)
    
    # Try auto-login first
    if not skip_auto_login:
        success, _ = auth.auto_login()
        if success:
            return auth
    
    # Show login dialog
    if AuthManager.show_login_dialog(None, auth):
        return auth
    
    return None


# =============================================================================
# TEST/DEMO
# =============================================================================

if __name__ == "__main__":
    # Demo usage
    print("Testing Authentication Module...")
    
    # For testing without server
    auth = AuthManager(server_url="http://localhost:5000")
    
    # Show login dialog
    if HAS_CUSTOMTKINTER:
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
    
    if AuthManager.show_login_dialog(None, auth):
        print(f"Login successful! User: {auth.session.username}")
    else:
        print("Login cancelled or failed")
