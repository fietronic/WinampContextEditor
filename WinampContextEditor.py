import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import winreg
import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path
import ctypes
from ctypes import wintypes
import struct
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL not available - icon preview will be limited")

class WinampContextEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Winamp Context Editor")
        self.root.geometry("600x500")
        
        # Default config
        self.winamp_path = tk.StringVar(value=r"C:\Program Files (x86)\Winamp\winamp.exe")
        self.icon_index = tk.IntVar(value=0)
        
        # Icon extraction
        self.extracted_icons = None
        self.icon_count = 0
        self.current_icon_photo = None
        
        # Menu options
        self.enable_play = tk.BooleanVar(value=True)
        self.enable_enqueue = tk.BooleanVar(value=True)
        self.enable_bookmark = tk.BooleanVar(value=False)  # ListBookmark from registry
        self.enable_icon = tk.BooleanVar(value=True)
        
        self.setup_ui()
        self.load_icons()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Winamp path selection
        path_frame = ttk.LabelFrame(main_frame, text="Winamp Configuration", padding="10")
        path_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(path_frame, text="Winamp Path:").grid(row=0, column=0, sticky=tk.W)
        path_entry = ttk.Entry(path_frame, textvariable=self.winamp_path, width=50)
        path_entry.grid(row=0, column=1, padx=(5, 5), sticky=(tk.W, tk.E))
        ttk.Button(path_frame, text="Browse", command=self.browse_winamp).grid(row=0, column=2)
        
        path_frame.columnconfigure(1, weight=1)
        
        # Context menu options (moved above icon selection)
        menu_frame = ttk.LabelFrame(main_frame, text="Context Menu Options", padding="10")
        menu_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Checkbutton(menu_frame, text="Play in Winamp", variable=self.enable_play).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(menu_frame, text="Enqueue in Winamp", variable=self.enable_enqueue).grid(row=1, column=0, sticky=tk.W)
        ttk.Checkbutton(menu_frame, text="Add to Bookmark list", variable=self.enable_bookmark).grid(row=2, column=0, sticky=tk.W)
        ttk.Checkbutton(menu_frame, text="Show Icon in Context Menu", variable=self.enable_icon, command=self.on_icon_checkbox_change).grid(row=3, column=0, sticky=tk.W)
        
        # Icon selection (moved below context menu options)
        icon_frame = ttk.LabelFrame(main_frame, text="Icon Selection", padding="10")
        icon_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Icon preview (left side)
        self.icon_label = tk.Label(icon_frame, width=64, height=64, bg='gray', relief='sunken', bd=2)
        self.icon_label.grid(row=0, column=0, rowspan=2, padx=(0, 15), pady=5)
        
        # Icon controls (right side)
        controls_frame = ttk.Frame(icon_frame)
        controls_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(controls_frame, text=" ").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Icon slider
        self.icon_slider = ttk.Scale(
            controls_frame, 
            from_=0, 
            to=20, 
            orient=tk.HORIZONTAL, 
            variable=self.icon_index,
            command=self.on_icon_slider_change,
            length=300
        )
        self.icon_slider.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Index display - Initialize with proper format
        self.index_label = ttk.Label(controls_frame, text="1 of 1")
        self.index_label.grid(row=2, column=0, sticky="")
        
        controls_frame.columnconfigure(0, weight=1)
        icon_frame.columnconfigure(1, weight=1)
        
        # Store icon frame widgets for enabling/disabling
        self.icon_widgets = [self.icon_label, self.icon_slider, self.index_label]
        
        # File types info
        info_frame = ttk.LabelFrame(main_frame, text="File Types Found", padding="10")
        info_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Treeview for file types
        self.tree = ttk.Treeview(info_frame, columns=('Type', 'Description'), show='tree headings', height=8)
        self.tree.heading('#0', text='Registry Key')
        self.tree.heading('Type', text='File Type')
        self.tree.heading('Description', text='Description')
        self.tree.column('#0', width=200)
        self.tree.column('Type', width=100)
        self.tree.column('Description', width=250)
        
        scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="Scan Registry", command=self.scan_registry).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Apply Changes", command=self.apply_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Backup Registry", command=self.backup_registry).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Restore Backup", command=self.restore_backup).pack(side=tk.LEFT, padx=(5, 0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Initial scan
        self.scan_registry()
        
        # Set initial icon widget state
        self.on_icon_checkbox_change()
    
    def on_icon_checkbox_change(self):
        """Handle icon checkbox state change"""
        enabled = self.enable_icon.get()
        state = tk.NORMAL if enabled else tk.DISABLED
        
        # Enable/disable icon widgets
        for widget in self.icon_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                # Some widgets might not support state configuration
                pass
        
        # Special handling for the slider
        self.icon_slider.configure(state=state)
    
    def browse_winamp(self):
        filename = filedialog.askopenfilename(
            title="Select Winamp executable",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.winamp_path.set(filename)
            self.load_icons()
    
    def load_icons(self):
        """Load and count available icons in the winamp executable"""
        try:
            # Reset to first icon when loading new exe
            self.icon_index.set(0)
            
            path = self.winamp_path.get()
            if os.path.exists(path):
                if PIL_AVAILABLE:
                    # Try to extract actual icons
                    self.extracted_icons = self.extract_icons_from_exe(path)
                    self.icon_count = len(self.extracted_icons) if self.extracted_icons else 20
                else:
                    # Fallback without PIL
                    self.icon_count = self.get_icon_count_fallback(path)
                    self.extracted_icons = None
                
                # Ensure at least 1 icon
                if self.icon_count <= 0:
                    self.icon_count = 1
                
                # Update slider range (0-based)
                self.icon_slider.configure(to=max(0, self.icon_count-1))
                
                # Update the preview and index label
                self.update_icon_preview()
                self.update_index_label()
            else:
                self.icon_count = 1  # Default to 1 when exe not found
                self.extracted_icons = None
                self.icon_slider.configure(to=0)
                self.update_icon_preview()
                self.update_index_label()
        except Exception as e:
            print(f"Error loading icons: {e}")
            self.icon_count = 1
            self.extracted_icons = None
            self.icon_slider.configure(to=0)
            self.update_icon_preview()
            self.update_index_label()
    
    def on_icon_slider_change(self, value):
        """Handle slider value change"""
        # Update both the index display and icon preview
        self.update_index_label()
        self.update_icon_preview()
    
    def update_index_label(self):
        """Update the index label to show current position and total"""
        current_index = self.icon_index.get()  # 0-based
        display_index = current_index + 1  # Convert to 1-based for display
        total_icons = max(1, self.icon_count)  # Ensure at least 1
        
        self.index_label.config(text=f"{display_index} of {total_icons}")
    
    def update_icon_preview(self):
        """Update the icon preview based on current index"""
        current_index = self.icon_index.get()
        
        if not os.path.exists(self.winamp_path.get()):
            # Show placeholder for missing exe
            self.show_placeholder_icon("EXE not found")
            return
        
        if PIL_AVAILABLE and self.extracted_icons:
            # Find the icon with the current index
            icon_image = None
            for icon_index, pil_image in self.extracted_icons:
                if icon_index == current_index:
                    icon_image = pil_image
                    break
            
            if icon_image:
                # Resize to fit the preview area (48x48)
                preview_image = icon_image.resize((48, 48), Image.Resampling.LANCZOS)
                self.current_icon_photo = ImageTk.PhotoImage(preview_image)
                self.icon_label.configure(image=self.current_icon_photo, text="")
            else:
                # Icon index not found in extracted icons
                self.show_placeholder_icon(f"Icon {current_index}\nnot available")
        else:
            # Fallback when PIL not available or icons not extracted
            if not PIL_AVAILABLE:
                self.show_placeholder_icon(f"Icon {current_index}\nInstall PIL\nfor preview")
            else:
                self.show_placeholder_icon(f"Icon {current_index}\nPreview\nnot available")
    
    def show_placeholder_icon(self, text):
        """Show a placeholder text when icon can't be displayed"""
        self.current_icon_photo = None
        self.icon_label.configure(image="", text=text, compound=tk.CENTER)
    
    def get_icon_count_fallback(self, exe_path):
        """Get estimated icon count without PIL"""
        try:
            # Use Windows API to get icon count
            shell32 = ctypes.windll.shell32
            icon_count = shell32.ExtractIconW(0, exe_path, -1)
            return max(icon_count, 1) if icon_count > 0 else 20
        except:
            return 20
    
    def extract_icons_from_exe(self, exe_path):
        """Extract icons from executable using Windows API"""
        if not PIL_AVAILABLE:
            return None
            
        try:
            # Load required Windows APIs
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32
            
            # Get icon count
            icon_count = shell32.ExtractIconW(0, exe_path, -1)
            if icon_count <= 0:
                return None
            
            icons = []
            for i in range(min(icon_count, 50)):  # Limit to first 50 icons
                try:
                    # Extract large and small icons
                    large_icon = ctypes.c_void_p()
                    small_icon = ctypes.c_void_p()
                    
                    result = shell32.ExtractIconExW(
                        exe_path, i, 
                        ctypes.byref(large_icon), 
                        ctypes.byref(small_icon), 1
                    )
                    
                    if result > 0 and large_icon.value:
                        # Convert HICON to PIL Image
                        icon_image = self.hicon_to_pil(large_icon.value)
                        if icon_image:
                            # Resize to consistent size for display
                            icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
                            icons.append((i, icon_image))
                        
                        # Clean up
                        user32.DestroyIcon(large_icon.value)
                        if small_icon.value:
                            user32.DestroyIcon(small_icon.value)
                            
                except Exception as e:
                    print(f"Error extracting icon {i}: {e}")
                    continue
            
            return icons if icons else None
            
        except Exception as e:
            print(f"Icon extraction failed: {e}")
            return None
    
    def hicon_to_pil(self, hicon):
        """Convert Windows HICON to PIL Image"""
        if not PIL_AVAILABLE:
            return None
            
        try:
            # Get icon info
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            
            # Create a memory DC
            screen_dc = user32.GetDC(0)
            mem_dc = gdi32.CreateCompatibleDC(screen_dc)
            
            # Create bitmap
            bmp = gdi32.CreateCompatibleBitmap(screen_dc, 32, 32)
            old_bmp = gdi32.SelectObject(mem_dc, bmp)
            
            # Fill with white background
            gdi32.PatBlt(mem_dc, 0, 0, 32, 32, 0x00FFFFFF)
            
            # Draw icon
            user32.DrawIconEx(mem_dc, 0, 0, hicon, 32, 32, 0, 0, 0x0003)
            
            # Get bitmap data
            bmp_info = struct.pack('<LLLHHLLLLLL', 40, 32, 32, 1, 24, 0, 0, 0, 0, 0, 0)
            
            # Get DIB bits
            buf = ctypes.create_string_buffer(32 * 32 * 3)
            gdi32.GetDIBits(mem_dc, bmp, 0, 32, buf, bmp_info, 0)
            
            # Clean up
            gdi32.SelectObject(mem_dc, old_bmp)
            gdi32.DeleteObject(bmp)
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(0, screen_dc)
            
            # Convert to PIL Image
            img_data = bytes(buf)
            # Convert BGR to RGB and flip vertically (DIB format)
            rgb_data = bytearray()
            for y in range(31, -1, -1):  # Flip vertically
                for x in range(32):
                    offset = (y * 32 + x) * 3
                    # Convert BGR to RGB
                    rgb_data.extend([img_data[offset+2], img_data[offset+1], img_data[offset]])
            
            image = Image.frombytes('RGB', (32, 32), bytes(rgb_data))
            return image
            
        except Exception as e:
            print(f"HICON conversion failed: {e}")
            # Fallback: create a simple colored square with index number
            img = Image.new('RGB', (32, 32), (100, 100, 200))
            return img
    
    def get_subkeys(self, root, path=None):
        """Get registry subkeys"""
        try:
            key = winreg.OpenKey(root, path if path else "")
            result = []
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(key, i)
                    result.append(subkey)
                    i += 1
                except OSError:
                    break
            key.Close()
            return result
        except FileNotFoundError:
            return []
    
    def get_registry_value(self, root, path, name):
        """Get a registry value"""
        try:
            with winreg.OpenKey(root, path) as key:
                value, _ = winreg.QueryValueEx(key, name)
                return value
        except:
            return ""
    
    def manual_export_key(self, root, key_path, output_file):
        """Manually export a registry key when reg.exe fails"""
        try:
            with open(output_file, 'w', encoding='utf-16le') as f:
                f.write('\ufeffWindows Registry Editor Version 5.00\n\n')
                self._export_key_recursive(root, key_path, f, key_path)
        except Exception as e:
            print(f"Manual export failed for {key_path}: {e}")
    
    def _export_key_recursive(self, root, key_path, file_handle, base_path):
        """Recursively export registry key and all subkeys"""
        try:
            # Write key header
            file_handle.write(f'[HKEY_CLASSES_ROOT\\{key_path}]\n')
            
            # Export values for this key
            with winreg.OpenKey(root, key_path) as key:
                i = 0
                while True:
                    try:
                        name, value, reg_type = winreg.EnumValue(key, i)
                        
                        # Format the value based on type
                        if reg_type == winreg.REG_SZ:
                            if name == "":
                                file_handle.write(f'@="{value}"\n')
                            else:
                                file_handle.write(f'"{name}"="{value}"\n')
                        elif reg_type == winreg.REG_DWORD:
                            if name == "":
                                file_handle.write(f'@=dword:{value:08x}\n')
                            else:
                                file_handle.write(f'"{name}"=dword:{value:08x}\n')
                        # Add other registry types as needed
                        
                        i += 1
                    except OSError:
                        break
            
            file_handle.write('\n')
            
            # Export subkeys
            subkeys = self.get_subkeys(root, key_path)
            for subkey in subkeys:
                subkey_path = f"{key_path}\\{subkey}"
                self._export_key_recursive(root, subkey_path, file_handle, base_path)
                
        except Exception as e:
            print(f"Error exporting key {key_path}: {e}")
    
    def scan_registry(self):
        """Scan registry for Winamp file types"""
        self.tree.delete(*self.tree.get_children())
        
        root = winreg.HKEY_CLASSES_ROOT
        all_keys = self.get_subkeys(root)
        winamp_keys = [k for k in all_keys if k.startswith("Winamp.File.")]
        
        for key in winamp_keys:
            try:
                # Get description
                description = self.get_registry_value(root, key, "")
                
                # Get file extension
                ext = key.replace("Winamp.File.", "").upper()
                
                self.tree.insert('', 'end', text=key, values=(ext, description))
            except Exception as e:
                self.tree.insert('', 'end', text=key, values=("Unknown", f"Error: {e}"))
    
    def apply_changes(self):
        """Apply registry changes"""
        if not self.check_admin():
            messagebox.showerror("Error", "Administrator privileges required to modify registry!")
            return
        
        if not os.path.exists(self.winamp_path.get()):
            messagebox.showerror("Error", "Winamp executable not found!")
            return
        
        # Confirm action
        if not messagebox.askyesno("Confirm", "This will modify the Windows registry. Continue?"):
            return
        
        try:
            # Backup first
            self.backup_registry(silent=True)
            
            root = winreg.HKEY_CLASSES_ROOT
            all_keys = self.get_subkeys(root)
            winamp_keys = [k for k in all_keys if k.startswith("Winamp.File.")]
            
            icon_string = f'{self.winamp_path.get()},{self.icon_index.get()}'
            changes_made = 0
            
            for base in winamp_keys:
                shell_path = f"{base}\\shell"
                
                # Handle Play menu
                self.handle_menu_item(root, shell_path, "Play", "Play", 
                                    "&Play in Winamp", self.enable_play.get(), icon_string)
                
                # Handle Enqueue menu  
                self.handle_menu_item(root, shell_path, "Enqueue", "Enqueue",
                                    "&Enqueue in Winamp", self.enable_enqueue.get(), icon_string)
                
                # Handle Bookmark menu (ListBookmark in registry)
                self.handle_menu_item(root, shell_path, "ListBookmark", "ListBookmark",
                                    "Add to Winamp's &Bookmark list", self.enable_bookmark.get(), icon_string)
                
                changes_made += 1
            
            messagebox.showinfo("Success", f"Registry updated for {changes_made} file types!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply changes: {e}")
    
    def handle_menu_item(self, root, shell_path, menu_name, command_type, display_name, enabled, icon_string):
        """Handle individual menu item creation/deletion"""
        menu_path = f"{shell_path}\\{menu_name}"
        
        if enabled:
            # Create/update menu item
            try:
                # Create the menu key
                with winreg.CreateKey(root, menu_path) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, display_name)
                    # Only add icon if icon checkbox is enabled
                    if self.enable_icon.get():
                        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_string)
                
                # Create command subkey
                command_path = f"{menu_path}\\command"
                with winreg.CreateKey(root, command_path) as key:
                    if command_type == "Enqueue":
                        cmd = f'"{self.winamp_path.get()}" /ADD "%1"'
                    elif command_type == "ListBookmark":
                        cmd = f'"{self.winamp_path.get()}" /BOOKMARK "%1"'
                    else:  # Play
                        cmd = f'"{self.winamp_path.get()}" "%1"'
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd)
                
                # Add DropTarget for Play and Enqueue
                if command_type in ["Play", "Enqueue"]:
                    droptarget_path = f"{menu_path}\\DropTarget"
                    with winreg.CreateKey(root, droptarget_path) as key:
                        if command_type == "Play":
                            clsid = "{46986115-84D6-459c-8F95-52DD653E532E}"
                        else:  # Enqueue
                            clsid = "{77A366BA-2BE4-4a1e-9263-7734AA3E99A2}"
                        winreg.SetValueEx(key, "Clsid", 0, winreg.REG_SZ, clsid)
                        
            except Exception as e:
                print(f"Error creating {menu_name}: {e}")
        else:
            # Delete menu item
            self.delete_subkey_tree(root, menu_path)
    
    def delete_subkey_tree(self, root, path):
        """Recursively delete registry key and subkeys"""
        try:
            # Get all subkeys first
            subkeys = self.get_subkeys(root, path)
            
            # Delete all subkeys recursively
            for subkey in subkeys:
                self.delete_subkey_tree(root, f"{path}\\{subkey}")
            
            # Delete the key itself
            winreg.DeleteKey(root, path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Failed to delete {path}: {e}")
            return False
    
    def check_admin(self):
        """Check if running with administrator privileges"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def backup_registry(self, silent=False):
        """Backup Winamp registry keys"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"winamp_backup_{timestamp}.reg"
            
            root = winreg.HKEY_CLASSES_ROOT
            all_keys = self.get_subkeys(root)
            winamp_keys = [k for k in all_keys if k.startswith("Winamp.File.")]
            
            if not winamp_keys:
                if not silent:
                    messagebox.showwarning("Warning", "No Winamp registry keys found to backup!")
                return
            
            # Create temporary files for each key, then combine them
            temp_files = []
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # Export each key to a separate temp file
                for i, key in enumerate(winamp_keys):
                    temp_file = os.path.join(temp_dir, f"temp_{i}.reg")
                    try:
                        cmd = ['reg', 'export', f'HKCR\\{key}', temp_file, '/y']
                        result = subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, 
                                              stderr=subprocess.DEVNULL)
                        if os.path.exists(temp_file):
                            temp_files.append(temp_file)
                    except subprocess.CalledProcessError:
                        # If reg export fails, try manual export
                        self.manual_export_key(root, key, temp_file)
                        if os.path.exists(temp_file):
                            temp_files.append(temp_file)
                
                # Combine all temp files into one
                with open(backup_file, 'w', encoding='utf-16le') as output:
                    output.write('\ufeffWindows Registry Editor Version 5.00\n\n')
                    
                    for temp_file in temp_files:
                        try:
                            with open(temp_file, 'r', encoding='utf-16le') as input_file:
                                content = input_file.read()
                                # Skip the header line and add the rest
                                lines = content.split('\n')
                                for line in lines[1:]:  # Skip first line (header)
                                    if line.strip():  # Only write non-empty lines
                                        output.write(line + '\n')
                                output.write('\n')  # Add separator between keys
                        except UnicodeError:
                            # Try different encodings
                            try:
                                with open(temp_file, 'r', encoding='utf-8') as input_file:
                                    content = input_file.read()
                                    lines = content.split('\n')
                                    for line in lines[1:]:
                                        if line.strip() and not line.startswith('Windows Registry'):
                                            output.write(line + '\n')
                                    output.write('\n')
                            except:
                                continue
                
                # Clean up temp files
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                        
                try:
                    os.rmdir(temp_dir)
                except:
                    pass
                
                if not silent:
                    messagebox.showinfo("Success", f"Registry backup saved as: {backup_file}\n({len(winamp_keys)} file types backed up)")
                    
            finally:
                # Ensure cleanup even if something goes wrong
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                        
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Failed to backup registry: {e}")
    
    def restore_backup(self):
        """Restore registry from backup file"""
        backup_file = filedialog.askopenfilename(
            title="Select registry backup file",
            filetypes=[("Registry files", "*.reg"), ("All files", "*.*")]
        )
        
        if not backup_file:
            return
        
        if not messagebox.askyesno("Confirm", 
                                 "This will restore registry settings from backup. Continue?"):
            return
        
        try:
            # Import registry file
            cmd = ['reg', 'import', backup_file]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                messagebox.showinfo("Success", "Registry restored from backup!")
                self.scan_registry()  # Refresh the display
            else:
                messagebox.showerror("Error", f"Failed to restore registry: {result.stderr}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restore registry: {e}")

def main():
    # Check if running as admin
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False
    
    if not is_admin:
        # Show warning but don't exit
        root = tk.Tk()
        root.withdraw()  # Hide main window temporarily
        messagebox.showwarning("Administrator Rights", 
                             "This application requires administrator privileges to modify the registry.\n\n"
                             "Some features may not work properly. Please run as administrator for full functionality.")
        root.deiconify()  # Show main window
    else:
        root = tk.Tk()
    
    app = WinampContextEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
