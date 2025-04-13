import os
import time
import random
import requests
import platform
import threading
import ctypes
import sys
import json
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import tkinter as tk
from tkinter import ttk, messagebox
import pystray
from PIL import Image as PilImage

class WallpaperChangerConfig:
    def __init__(self, config_file="wallpaper_config.json"):
        self.config_file = config_file
        self.default_config = {
            "frequency_minutes": 60,  # Default: change every 60 minutes
            "wallpaper_type": "video_games",  # Default: video games
            "run_on_startup": False,
            "download_dir": "wallpapers"
        }
        self.config = self.load_config()
    
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return self.default_config.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config.copy()
    
    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key):
        return self.config.get(key, self.default_config.get(key))
    
    def set(self, key, value):
        self.config[key] = value
        self.save_config()

class WallpaperChanger:
    def __init__(self):
        """Initialize the wallpaper changer."""
        self.config = WallpaperChangerConfig()
        self.download_dir = self.config.get("download_dir")
        self.system = platform.system()
        self.create_download_directory()
        self.running = False
        self.timer = None
        
        # Wallpaper sources for different types
        self.wallpaper_sources = {
            "video_games": [
                "https://wall.alphacoders.com/by_category.php?id=3&name=Video+Game+Wallpapers",
                "https://wallhaven.cc/search?q=video+games&categories=111&purity=100&resolutions=1920x1080,2560x1440,3840x2160&sorting=random"
            ],
            "nature": [
                "https://wall.alphacoders.com/by_category.php?id=15&name=Nature+Wallpapers",
                "https://wallhaven.cc/search?q=nature&categories=111&purity=100&resolutions=1920x1080,2560x1440,3840x2160&sorting=random"
            ],
            "abstract": [
                "https://wall.alphacoders.com/by_category.php?id=7&name=Abstract+Wallpapers",
                "https://wallhaven.cc/search?q=abstract&categories=111&purity=100&resolutions=1920x1080,2560x1440,3840x2160&sorting=random"
            ],
            "anime": [
                "https://wall.alphacoders.com/by_category.php?id=1&name=Anime+Wallpapers",
                "https://wallhaven.cc/search?q=anime&categories=111&purity=100&resolutions=1920x1080,2560x1440,3840x2160&sorting=random"
            ],
            "sci_fi": [
                "https://wall.alphacoders.com/by_category.php?id=30&name=Sci+Fi+Wallpapers",
                "https://wallhaven.cc/search?q=sci-fi&categories=111&purity=100&resolutions=1920x1080,2560x1440,3840x2160&sorting=random"
            ]
        }

    def create_download_directory(self):
        """Create directory to store downloaded wallpapers if it doesn't exist."""
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            print(f"Created directory: {self.download_dir}")

    def get_sources_for_current_type(self):
        """Get the sources for the currently selected wallpaper type."""
        wallpaper_type = self.config.get("wallpaper_type")
        return self.wallpaper_sources.get(wallpaper_type, self.wallpaper_sources["video_games"])

    def download_new_wallpaper(self):
        """Download a single new wallpaper and return its path."""
        print("Downloading a new wallpaper...")
        
        # Get sources for current wallpaper type
        sources = self.get_sources_for_current_type()
        
        # Randomly select a source
        source = random.choice(sources)
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(source, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find image links based on the source
            img_urls = []
            
            if "alphacoders" in source:
                img_elements = soup.select('.img-responsive')
                for img in img_elements:
                    if img.get('src'):
                        img_url = img['src']
                        if not img_url.startswith('http'):
                            img_url = "https:" + img_url
                        img_urls.append(img_url)
            
            elif "wallhaven" in source:
                img_elements = soup.select('.preview')
                for img in img_elements:
                    img_url = img.get('href')
                    if img_url:
                        try:
                            # For wallhaven, we need to get the actual image URL from the detail page
                            detail_response = requests.get(img_url, headers=headers)
                            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                            wallpaper = detail_soup.select_one('#wallpaper')
                            if wallpaper and wallpaper.get('src'):
                                full_img_url = wallpaper['src']
                                if not full_img_url.startswith('http'):
                                    full_img_url = "https:" + full_img_url
                                img_urls.append(full_img_url)
                        except Exception as e:
                            print(f"Error processing wallhaven image: {e}")
                            continue
            
            # Pick a random image URL from the collected ones
            if img_urls:
                # Shuffle the list to try different images if one fails
                random.shuffle(img_urls)
                
                for url in img_urls:
                    file_path = self.save_image(url)
                    if file_path:
                        return file_path
            
            print("Failed to find suitable wallpaper from this source.")
            return None
            
        except Exception as e:
            print(f"Error fetching from source {source}: {e}")
            return None

    def save_image(self, url):
        """Save an image from URL to the download directory and return the file path."""
        try:
            print(f"Downloading: {url}")
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                # Extract filename from URL or create one
                filename = os.path.basename(url)
                if not filename or '.' not in filename:
                    filename = f"wallpaper_{random.randint(1000, 9999)}.jpg"
                
                # Ensure the image is a valid image and has high resolution
                img = Image.open(BytesIO(response.content))
                width, height = img.size
                
                # Only save if the resolution is high enough (at least HD)
                if width >= 1920 and height >= 1080:
                    file_path = os.path.join(self.download_dir, filename)
                    
                    # Save the image
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    print(f"Saved: {file_path}")
                    return file_path
                else:
                    print(f"Skipping low-resolution image: {width}x{height}")
            else:
                print(f"Failed to download image. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error saving image: {e}")
        return None

    def change_wallpaper(self):
        """Download a new wallpaper and set it as desktop background."""
        # Download a new wallpaper
        wallpaper_path = self.download_new_wallpaper()
        
        # If downloading fails, try again with a different source
        attempts = 0
        while not wallpaper_path and attempts < 3:
            print(f"Attempt {attempts+1} failed. Trying again...")
            wallpaper_path = self.download_new_wallpaper()
            attempts += 1
        
        if not wallpaper_path:
            print("Failed to download a new wallpaper after multiple attempts.")
            return
        
        try:
            print(f"Setting new wallpaper: {wallpaper_path}")
            
            if self.system == "Windows":
                # For Windows
                ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.abspath(wallpaper_path), 3)
            
            elif self.system == "Darwin":  # macOS
                # For macOS (requires osascript)
                script = f'''
                tell application "System Events"
                    set desktop picture to POSIX file "{os.path.abspath(wallpaper_path)}"
                end tell
                '''
                os.system(f"osascript -e '{script}'")
            
            elif self.system == "Linux":
                # For Linux (assuming GNOME)
                os.system(f"gsettings set org.gnome.desktop.background picture-uri file://{os.path.abspath(wallpaper_path)}")
                # For KDE Plasma
                os.system(f"qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript '\
                    var allDesktops = desktops();\
                    for (i=0;i<allDesktops.length;i++) {{\
                        d = allDesktops[i];\
                        d.wallpaperPlugin = \"org.kde.image\";\
                        d.currentConfigGroup = Array(\"Wallpaper\", \"org.kde.image\", \"General\");\
                        d.writeConfig(\"Image\", \"file://{os.path.abspath(wallpaper_path)}\");\
                    }}'\
                ")
            
            print("Wallpaper set successfully.")
            
            # Clean up old wallpapers to avoid filling up disk space
            # Keep only the most recent wallpaper
            self.cleanup_old_wallpapers(except_path=wallpaper_path)
            
        except Exception as e:
            print(f"Error setting wallpaper: {e}")

    def cleanup_old_wallpapers(self, except_path=None):
        """Delete old wallpapers except the current one to save disk space."""
        try:
            wallpapers = [os.path.join(self.download_dir, file) for file in os.listdir(self.download_dir) 
                         if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
            
            for wallpaper in wallpapers:
                if except_path and os.path.abspath(wallpaper) == os.path.abspath(except_path):
                    continue  # Skip the current wallpaper
                try:
                    os.remove(wallpaper)
                    print(f"Removed old wallpaper: {wallpaper}")
                except Exception as e:
                    print(f"Failed to remove {wallpaper}: {e}")
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def start_timer(self):
        """Start the timer to change wallpaper periodically."""
        if self.running:
            return
        
        self.running = True
        self.schedule_next_change()
        
    def stop_timer(self):
        """Stop the timer."""
        self.running = False
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def schedule_next_change(self):
        """Schedule the next wallpaper change."""
        if not self.running:
            return
            
        # Cancel any existing timer
        if self.timer:
            self.timer.cancel()
        
        # Get frequency in minutes from config
        frequency_minutes = self.config.get("frequency_minutes")
        
        # Schedule next change
        self.timer = threading.Timer(frequency_minutes * 60, self.handle_timer_event)
        self.timer.daemon = True
        self.timer.start()
        
        print(f"Next wallpaper change scheduled in {frequency_minutes} minutes")
    
    def handle_timer_event(self):
        """Handle the timer event - change wallpaper and reschedule."""
        if self.running:
            print("Timer triggered, changing wallpaper...")
            self.change_wallpaper()
            self.schedule_next_change()

    def add_to_startup_windows(self, enable=True):
        """Add or remove the application from Windows startup."""
        if self.system != "Windows":
            return
            
        import winreg
        startup_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        
        app_path = sys.executable
        if getattr(sys, 'frozen', False):
            # If the application is running as a bundle (compiled with PyInstaller)
            app_path = sys.executable
        else:
            # If running as a script
            app_path = sys.argv[0]
            
        try:
            if enable:
                winreg.SetValueEx(startup_key, "WallpaperChanger", 0, winreg.REG_SZ, f'"{app_path}"')
                print("Added to startup")
            else:
                try:
                    winreg.DeleteValue(startup_key, "WallpaperChanger")
                    print("Removed from startup")
                except FileNotFoundError:
                    pass  # Key doesn't exist, so nothing to delete
        except Exception as e:
            print(f"Error updating startup registry: {e}")
        finally:
            winreg.CloseKey(startup_key)

class WallpaperChangerGUI:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()  # Hide the main window initially
        self.changer = WallpaperChanger()
        
        # Create system tray icon
        self.create_tray_icon()
        
        # Configuration window
        self.config_window = None
        
        # Change wallpaper immediately on startup
        self.initial_setup()
    
    def initial_setup(self):
        """Perform initial setup tasks."""
        # Start downloading the first wallpaper immediately
        # Use a separate thread to avoid blocking the GUI
        threading.Thread(target=self.first_wallpaper_change, daemon=True).start()
        
        # Auto-run on startup if configured
        if self.changer.config.get("run_on_startup"):
            self.changer.add_to_startup_windows(True)
    
    def first_wallpaper_change(self):
        """Download and set the first wallpaper, then start the timer."""
        # Show a notification (if possible)
        try:
            self.tray_icon.notify("Downloading your first wallpaper...")
        except:
            pass
            
        # Change wallpaper immediately
        self.changer.change_wallpaper()
        
        # Start the timer for subsequent changes
        self.changer.start_timer()
        
        # Show notification that wallpaper was changed
        try:
            self.tray_icon.notify("Wallpaper set! Next change in {} minutes.".format(
                self.changer.config.get("frequency_minutes")
            ))
        except:
            pass
    
    def create_tray_icon(self):
        """Create system tray icon and menu."""
        # Create an icon (you should replace this with your own icon file)
        icon_image = self.create_icon_image()
        
        menu = (
            pystray.MenuItem('Change Wallpaper Now', self.change_wallpaper_now),
            pystray.MenuItem('Settings', self.open_settings),
            pystray.MenuItem('Exit', self.quit_application)
        )
        
        self.tray_icon = pystray.Icon("WallpaperChanger", icon_image, "Wallpaper Changer", menu)
        
        # Run the icon in a separate thread
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def create_icon_image(self):
        """Create a simple icon for the tray."""
        # Create a simple colored square as icon
        width = 64
        height = 64
        color = (41, 128, 185)  # Blue color
        
        image = PilImage.new('RGB', (width, height), color)
        return image
    
    def change_wallpaper_now(self):
        """Manually trigger wallpaper change."""
        threading.Thread(target=self.changer.change_wallpaper).start()
    
    def open_settings(self):
        """Open the settings window."""
        if self.config_window is not None and self.config_window.winfo_exists():
            self.config_window.focus_force()
            return
            
        self.config_window = tk.Toplevel(self.root)
        self.config_window.title("Wallpaper Changer Settings")
        self.config_window.geometry("400x300")
        self.config_window.resizable(False, False)
        
        # Add settings controls
        self.create_settings_controls()
    
    def create_settings_controls(self):
        """Create the settings controls."""
        frame = ttk.Frame(self.config_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Wallpaper Type
        ttk.Label(frame, text="Wallpaper Type:").grid(column=0, row=0, sticky=tk.W, pady=5)
        
        type_var = tk.StringVar(value=self.changer.config.get("wallpaper_type"))
        type_combo = ttk.Combobox(frame, textvariable=type_var)
        type_combo['values'] = ('video_games', 'nature', 'abstract', 'anime', 'sci_fi')
        type_combo['state'] = 'readonly'
        type_combo.grid(column=1, row=0, sticky=tk.W, pady=5)
        
        # Change Frequency
        ttk.Label(frame, text="Change Frequency:").grid(column=0, row=1, sticky=tk.W, pady=5)
        
        freq_frame = ttk.Frame(frame)
        freq_frame.grid(column=1, row=1, sticky=tk.W, pady=5)
        
        freq_var = tk.IntVar(value=self.changer.config.get("frequency_minutes"))
        freq_entry = ttk.Entry(freq_frame, textvariable=freq_var, width=5)
        freq_entry.pack(side=tk.LEFT)
        
        ttk.Label(freq_frame, text="minutes").pack(side=tk.LEFT, padx=5)
        
        # Run on startup
        startup_var = tk.BooleanVar(value=self.changer.config.get("run_on_startup"))
        startup_check = ttk.Checkbutton(frame, text="Run on system startup", variable=startup_var)
        startup_check.grid(column=0, row=2, columnspan=2, sticky=tk.W, pady=5)
        
        # Current status
        status_text = "Status: Running" if self.changer.running else "Status: Stopped"
        status_label = ttk.Label(frame, text=status_text)
        status_label.grid(column=0, row=3, columnspan=2, sticky=tk.W, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(column=0, row=4, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Apply", command=lambda: self.apply_settings(
            type_var.get(),
            freq_var.get(),
            startup_var.get()
        )).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Close", command=self.config_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def apply_settings(self, wallpaper_type, frequency_minutes, run_on_startup):
        """Apply the settings."""
        try:
            # Validate frequency
            if frequency_minutes < 1:
                messagebox.showerror("Invalid Input", "Frequency must be at least 1 minute")
                return
                
            # Save settings
            self.changer.config.set("wallpaper_type", wallpaper_type)
            self.changer.config.set("frequency_minutes", frequency_minutes)
            self.changer.config.set("run_on_startup", run_on_startup)
            
            # Handle startup setting
            self.changer.add_to_startup_windows(run_on_startup)
            
            # Restart the timer with new settings
            self.changer.stop_timer()
            self.changer.start_timer()
            
            messagebox.showinfo("Settings", "Settings applied successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error applying settings: {e}")
    
    def quit_application(self):
        """Quit the application."""
        self.changer.stop_timer()
        self.tray_icon.stop()
        self.root.quit()

def main():
    """Main function to run the wallpaper changer with GUI."""
    root = tk.Tk()
    app = WallpaperChangerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()