# RhythmShelf
# Version: 1.0.0
# Author: Lewis
#
# This work is licensed under the MIT License.
# See: https://opensource.org/licenses/MIT

import os
import shutil
import mutagen
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import queue


class MusicOrganizerGUI:
    """A simple GUI for organizing a music library."""
    APP_VERSION = "1.0.0"

    def __init__(self, root):
        self.root = root
        self.root.title(f"🎵 RhythmShelf v{self.APP_VERSION}")
        self.root.geometry("700x600")
        self.root.minsize(600, 450)
        self.root.configure(bg="#2e2e2e")

        # --- Data ---
        self.source_dir = tk.StringVar()
        self.dest_dir = tk.StringVar()
        self.operation_mode = tk.StringVar(value="copy")  # 'copy' or 'move'
        self.status_text = tk.StringVar(value="Ready.")
        self.progress_var = tk.DoubleVar(value=0)
        self.processed_file_count = 0

        self.is_running = False
        self.log_queue = queue.Queue()

        # --- UI Setup ---
        self.create_widgets()
        self.root.after(100, self.process_log_queue)

    def create_widgets(self):
        """Creates and arranges all the UI elements in the window."""
        main_frame = tk.Frame(self.root, padx=20, pady=20, bg="#2e2e2e")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Folder Selection ---
        folders_frame = tk.LabelFrame(main_frame, text="Folders", fg="white", bg="#2e2e2e", padx=10, pady=10)
        folders_frame.pack(fill=tk.X)
        folders_frame.columnconfigure(1, weight=1)

        tk.Label(folders_frame, text="Source Music Folder:", fg="white", bg="#2e2e2e", font=("Helvetica", 10)).grid(
            row=0, column=0, sticky="w", pady=(0, 5))
        source_entry = tk.Entry(folders_frame, textvariable=self.source_dir, state="readonly", width=60,
                                readonlybackground="#555", fg="white")
        source_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=(0, 5))
        tk.Button(folders_frame, text="Browse...", command=self.select_source_dir).grid(row=0, column=2, pady=(0, 5))

        tk.Label(folders_frame, text="Destination Folder:", fg="white", bg="#2e2e2e", font=("Helvetica", 10)).grid(
            row=1, column=0, sticky="w", pady=(5, 10))
        dest_entry = tk.Entry(folders_frame, textvariable=self.dest_dir, state="readonly", width=60,
                              readonlybackground="#555", fg="white")
        dest_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=(5, 10))
        tk.Button(folders_frame, text="Browse...", command=self.select_dest_dir).grid(row=1, column=2, pady=(5, 10))

        # --- Options ---
        options_frame = tk.LabelFrame(main_frame, text="Options", fg="white", bg="#2e2e2e", padx=10, pady=10)
        options_frame.pack(fill=tk.X, pady=10)

        tk.Radiobutton(options_frame, text="Copy files (Safer)", variable=self.operation_mode, value="copy",
                       bg="#2e2e2e", fg="white", selectcolor="#444").pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(options_frame, text="Move files (Faster)", variable=self.operation_mode, value="move",
                       bg="#2e2e2e", fg="white", selectcolor="#444").pack(side=tk.LEFT, padx=10)

        # --- Start Button ---
        self.organize_button = tk.Button(main_frame, text="🚀 Start Organizing", command=self.start_organization_thread,
                                         bg="#4a4a4a", fg="white", font=("Helvetica", 12, "bold"), relief=tk.FLAT,
                                         borderwidth=0, padx=10, pady=10)
        self.organize_button.pack(pady=15)

        # --- Progress Bar ---
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # --- Log/Status Area ---
        log_frame = tk.LabelFrame(main_frame, text="Progress Log", fg="white", bg="#2e2e2e", padx=10, pady=10)
        log_frame.pack(expand=True, fill=tk.BOTH)

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state="disabled", bg="#1e1e1e", fg="#dcdcdc",
                                                  font=("Consolas", 9))
        self.log_area.pack(expand=True, fill=tk.BOTH)

        # --- Status Bar ---
        tk.Label(self.root, textvariable=self.status_text, bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#3a3a3a",
                 fg="white").pack(side=tk.BOTTOM, fill=tk.X)

    def select_source_dir(self):
        path = filedialog.askdirectory(title="Select your music folder")
        if path: self.source_dir.set(path)

    def select_dest_dir(self):
        path = filedialog.askdirectory(title="Select where to save the organized library")
        if path: self.dest_dir.set(path)

    def sanitize_foldername(self, name):
        """Removes characters from a string that are invalid for folder names."""
        if not name: return ""
        name = name.replace('/', '-').replace('\\', '-')
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            name = name.replace(char, '')
        return name.strip('. ')

    def start_organization_thread(self):
        if self.is_running: return

        source, dest = self.source_dir.get(), self.dest_dir.get()

        if not source or not dest:
            messagebox.showerror("Error", "Please select both a source and a destination folder.")
            return
        if source == dest:
            messagebox.showwarning("Warning", "Source and destination folders cannot be the same.")
            return

        self.is_running = True
        self.organize_button.config(state="disabled", text="🏃‍♂️ Processing...")
        self.log_message("--- Starting Organization ---", clear=True)
        self.progress_var.set(0)
        self.status_text.set("Preparing to organize...")

        thread = threading.Thread(target=self.organize_files, args=(source, dest, self.operation_mode.get()),
                                  daemon=True)
        thread.start()

    def process_log_queue(self):
        """Checks the queue for new log messages and updates the GUI."""
        try:
            while True:
                message = self.log_queue.get_nowait()
                if message == "---DONE---":
                    self.on_organization_complete()
                else:
                    self.log_area.config(state="normal")
                    if "clear" in message:
                        self.log_area.delete('1.0', tk.END)
                        message = message.replace("clear", "")
                    self.log_area.insert(tk.END, message + "\n")
                    self.log_area.see(tk.END)
                    self.log_area.config(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_log_queue)

    def log_message(self, message, clear=False):
        log_entry = f"clear{message}" if clear else message
        self.log_queue.put(log_entry)

    def on_organization_complete(self):
        self.is_running = False
        self.organize_button.config(state="normal", text="🚀 Start Organizing")
        self.status_text.set(f"Finished. Processed {self.processed_file_count} files.")

    def organize_files(self, source_folder, dest_folder, operation):
        self.processed_file_count = 0

        # Pre-scan to get total file count for the progress bar
        files_to_process = [f for f in os.listdir(source_folder) if os.path.isfile(os.path.join(source_folder, f))]
        total_files = len(files_to_process)
        if total_files == 0:
            self.log_message("No files found in the source directory.")
            self.log_queue.put("---DONE---")
            messagebox.showinfo("Finished", "No files were found to process.")
            return

        operation_verb = "Copying" if operation == "copy" else "Moving"
        operation_past_tense = "Copied" if operation == "copy" else "Moved"

        for i, filename in enumerate(files_to_process):
            source_path = os.path.join(source_folder, filename)
            self.status_text.set(f"{operation_verb} {i + 1}/{total_files}: {filename}")

            artist_name, album_name = "Unknown Artist", "Unknown Album"
            try:
                audio = mutagen.File(source_path, easy=True)
                if not audio: raise ValueError("Not a supported audio file.")
                artist_name = audio.get('artist', ['Unknown Artist'])[0]
                album_name = audio.get('album', ['Unknown Album'])[0]
            except Exception as e:
                self.log_message(f"⚠️ Skipping '{filename}': Could not read tags.")
                artist_name, album_name = "Untagged", "Untagged Files"

            sane_artist = self.sanitize_foldername(artist_name)
            sane_album = self.sanitize_foldername(album_name)

            artist_dir = os.path.join(dest_folder, sane_artist)
            album_dir = os.path.join(artist_dir, sane_album)
            os.makedirs(album_dir, exist_ok=True)

            destination_path = os.path.join(album_dir, filename)
            try:
                if operation == "copy":
                    shutil.copy2(source_path, destination_path)  # copy2 preserves metadata
                else:
                    shutil.move(source_path, destination_path)

                self.log_message(f"{operation_past_tense} '{filename}' to '{sane_artist}/{sane_album}/'")
                self.processed_file_count += 1
            except Exception as e:
                self.log_message(f"❌ ERROR with '{filename}': {e}")

            self.progress_var.set(((i + 1) / total_files) * 100)

        self.log_queue.put("---DONE---")
        messagebox.showinfo("Success!",
                            f"Organization complete!\n\n{operation_past_tense} {self.processed_file_count} files.")


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicOrganizerGUI(root)
    root.mainloop()

