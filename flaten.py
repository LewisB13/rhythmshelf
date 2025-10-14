# RhythmShelf Flattener
# Version: 1.0.0
# Author: Lewis
#
# This work is licensed under the MIT License.
# See: https://opensource.org/licenses/MIT

import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import queue


class MusicFlattenerGUI:
    """A simple GUI for flattening a music library into a single folder."""
    APP_VERSION = "1.0.0"
    SUPPORTED_FORMATS = ('.mp3', '.flac', '.m4a', '.aac', '.ogg', '.wav', '.wma')

    def __init__(self, root):
        self.root = root
        self.root.title(f"🎵 RhythmShelf Flattener v{self.APP_VERSION}")
        self.root.geometry("700x550")
        self.root.minsize(600, 450)
        self.root.configure(bg="#2e2e2e")

        # --- Data ---
        self.source_dir = tk.StringVar()
        self.dest_dir = tk.StringVar()
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

        tk.Label(folders_frame, text="Organized Source Folder:", fg="white", bg="#2e2e2e", font=("Helvetica", 10)).grid(
            row=0, column=0, sticky="w", pady=(0, 5))
        source_entry = tk.Entry(folders_frame, textvariable=self.source_dir, state="readonly", width=60,
                                readonlybackground="#555", fg="white")
        source_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=(0, 5))
        tk.Button(folders_frame, text="Browse...", command=self.select_source_dir).grid(row=0, column=2, pady=(0, 5))

        tk.Label(folders_frame, text="Single Destination Folder:", fg="white", bg="#2e2e2e",
                 font=("Helvetica", 10)).grid(row=1, column=0, sticky="w", pady=(5, 10))
        dest_entry = tk.Entry(folders_frame, textvariable=self.dest_dir, state="readonly", width=60,
                              readonlybackground="#555", fg="white")
        dest_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=(5, 10))
        tk.Button(folders_frame, text="Browse...", command=self.select_dest_dir).grid(row=1, column=2, pady=(5, 10))

        # --- Start Button ---
        self.flatten_button = tk.Button(main_frame, text="🚀 Start Flattening", command=self.start_flattening_thread,
                                        bg="#4a4a4a", fg="white", font=("Helvetica", 12, "bold"), relief=tk.FLAT,
                                        borderwidth=0, padx=10, pady=10)
        self.flatten_button.pack(pady=20)

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
        path = filedialog.askdirectory(title="Select your organized music library")
        if path: self.source_dir.set(path)

    def select_dest_dir(self):
        path = filedialog.askdirectory(title="Select the destination folder for all music files")
        if path: self.dest_dir.set(path)

    def start_flattening_thread(self):
        if self.is_running: return

        source, dest = self.source_dir.get(), self.dest_dir.get()

        if not source or not dest:
            messagebox.showerror("Error", "Please select both a source and a destination folder.")
            return
        if source == dest:
            messagebox.showwarning("Warning", "Source and destination folders cannot be the same.")
            return

        self.is_running = True
        self.flatten_button.config(state="disabled", text="🏃‍♂️ Processing...")
        self.log_message("--- Starting to Flatten Library ---", clear=True)
        self.progress_var.set(0)
        self.status_text.set("Scanning for music files...")

        thread = threading.Thread(target=self.flatten_library_worker, args=(source, dest), daemon=True)
        thread.start()

    def process_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                if message == "---DONE---":
                    self.on_flattening_complete()
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

    def on_flattening_complete(self):
        self.is_running = False
        self.flatten_button.config(state="normal", text="🚀 Start Flattening")
        self.status_text.set(f"Finished. Moved {self.processed_file_count} files.")

    def flatten_library_worker(self, source_folder, dest_folder):
        self.processed_file_count = 0

        # Pre-scan for progress bar
        files_to_move = []
        for root, _, files in os.walk(source_folder):
            for file in files:
                if file.lower().endswith(self.SUPPORTED_FORMATS):
                    files_to_move.append(os.path.join(root, file))

        total_files = len(files_to_move)
        if total_files == 0:
            self.log_message("No music files found in the source directory.")
            self.log_queue.put("---DONE---")
            messagebox.showinfo("Finished", "No music files were found to process.")
            return

        for i, source_path in enumerate(files_to_move):
            filename = os.path.basename(source_path)
            self.status_text.set(f"Moving {i + 1}/{total_files}: {filename}")

            # --- Safely handle filename collisions ---
            destination_path = os.path.join(dest_folder, filename)
            counter = 1
            while os.path.exists(destination_path):
                name, ext = os.path.splitext(filename)
                new_filename = f"{name} ({counter}){ext}"
                destination_path = os.path.join(dest_folder, new_filename)
                counter += 1

            if filename != os.path.basename(destination_path):
                self.log_message(
                    f"⚠️ Renaming '{filename}' to '{os.path.basename(destination_path)}' to avoid overwrite.")

            # --- Move the file ---
            try:
                shutil.move(source_path, destination_path)
                self.log_message(f"Moved '{filename}'")
                self.processed_file_count += 1
            except Exception as e:
                self.log_message(f"❌ ERROR moving '{filename}': {e}")

            self.progress_var.set(((i + 1) / total_files) * 100)

        self.log_queue.put("---DONE---")
        messagebox.showinfo("Success!", f"Flattening complete!\n\nMoved {self.processed_file_count} files.")


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicFlattenerGUI(root)
    root.mainloop()
