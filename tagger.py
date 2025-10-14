# RhythmShelf Tagger
# Version: 1.2.0
# Author: Lewis
#
# This work is licensed under the MIT License.
# See: https://opensource.org/licenses/MIT

import os
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import queue


class MusicTaggerGUI:
    """A GUI to tag music files based on their filename structure."""
    APP_VERSION = "1.2.0"
    DEFAULT_FORMATS = ".mp3 .flac .m4a .aac .ogg .wav .wma .opus .aiff .aif"

    def __init__(self, root):
        self.root = root
        self.root.title(f"🎵 RhythmShelf Tagger v{self.APP_VERSION}")
        self.root.geometry("700x640")
        self.root.minsize(600, 550)
        self.root.configure(bg="#2e2e2e")

        # --- Data ---
        self.source_dir = tk.StringVar()
        self.filename_pattern = tk.StringVar(value="%artist% - %title%")
        self.formats_var = tk.StringVar(value=self.DEFAULT_FORMATS)
        self.rename_files_var = tk.BooleanVar(value=True)
        self.status_text = tk.StringVar(value="Ready.")
        self.progress_var = tk.DoubleVar(value=0)
        self.processed_file_count = 0
        self.is_running = False
        self.log_queue = queue.Queue()

        self.create_widgets()
        self.root.after(100, self.process_log_queue)

    def create_widgets(self):
        main_frame = tk.Frame(self.root, padx=20, pady=20, bg="#2e2e2e")
        main_frame.pack(expand=True, fill=tk.BOTH)

        folders_frame = tk.LabelFrame(main_frame, text="Source Folder", fg="white", bg="#2e2e2e", padx=10, pady=10)
        folders_frame.pack(fill=tk.X)
        folders_frame.columnconfigure(1, weight=1)

        tk.Label(folders_frame, text="Music Folder:", fg="white", bg="#2e2e2e", font=("Helvetica", 10)).grid(row=0,
                                                                                                             column=0,
                                                                                                             sticky="w",
                                                                                                             pady=(0,
                                                                                                                   5))
        source_entry = tk.Entry(folders_frame, textvariable=self.source_dir, state="readonly", width=60,
                                readonlybackground="#555", fg="white")
        source_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=(0, 5))
        tk.Button(folders_frame, text="Browse...", command=self.select_source_dir).grid(row=0, column=2, pady=(0, 5))

        pattern_frame = tk.LabelFrame(main_frame, text="Filename Pattern", fg="white", bg="#2e2e2e", padx=10, pady=10)
        pattern_frame.pack(fill=tk.X, pady=10)

        tk.Label(pattern_frame, text="Use %artist% and %title% as placeholders.", fg="#ccc", bg="#2e2e2e").pack(
            anchor='w')
        pattern_entry = tk.Entry(pattern_frame, textvariable=self.filename_pattern, bg="#555", fg="white",
                                 font=("Consolas", 10))
        pattern_entry.pack(fill=tk.X, pady=5)

        # --- Options Frame ---
        options_frame = tk.LabelFrame(main_frame, text="Options", fg="white", bg="#2e2e2e", padx=10, pady=10)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(options_frame, text="File formats to tag (space-separated):", fg="#ccc", bg="#2e2e2e").pack(anchor='w')
        formats_entry = tk.Entry(options_frame, textvariable=self.formats_var, bg="#555", fg="white",
                                 font=("Consolas", 10))
        formats_entry.pack(fill=tk.X, pady=(5, 10))

        rename_check = tk.Checkbutton(options_frame, text="Rename files to just '%title%' after tagging",
                                      variable=self.rename_files_var, fg="white", bg="#2e2e2e", selectcolor="#1e1e1e",
                                      activebackground="#2e2e2e", activeforeground="white", highlightthickness=0, bd=0)
        rename_check.pack(anchor='w')

        self.tag_button = tk.Button(main_frame, text="✍️ Start Tagging Files", command=self.start_tagging_thread,
                                    bg="#4a4a4a", fg="white", font=("Helvetica", 12, "bold"), relief=tk.FLAT, padx=10,
                                    pady=10)
        self.tag_button.pack(pady=10)

        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        log_frame = tk.LabelFrame(main_frame, text="Progress Log", fg="white", bg="#2e2e2e", padx=10, pady=10)
        log_frame.pack(expand=True, fill=tk.BOTH)

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state="disabled", bg="#1e1e1e", fg="#dcdcdc",
                                                  font=("Consolas", 9))
        self.log_area.pack(expand=True, fill=tk.BOTH)

        tk.Label(self.root, textvariable=self.status_text, bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#3a3a3a",
                 fg="white").pack(side=tk.BOTTOM, fill=tk.X)

    def select_source_dir(self):
        path = filedialog.askdirectory(title="Select the folder with music to tag")
        if path: self.source_dir.set(path)

    def start_tagging_thread(self):
        if self.is_running: return

        source = self.source_dir.get()
        pattern = self.filename_pattern.get()
        rename_files = self.rename_files_var.get()
        formats_str = self.formats_var.get()

        if not source:
            messagebox.showerror("Error", "Please select a source folder.")
            return
        if not formats_str:
            messagebox.showerror("Error", "Please specify at least one file format.")
            return
        if "%artist%" not in pattern or "%title%" not in pattern:
            messagebox.showerror("Error", "The pattern must include both %artist% and %title%.")
            return

        supported_formats = tuple(f.strip() for f in formats_str.split() if f.strip().startswith('.'))

        self.is_running = True
        self.tag_button.config(state="disabled", text="🏃‍♂️ Processing...")
        self.log_message("--- Starting Tagging Process ---", clear=True)
        self.progress_var.set(0)
        self.status_text.set("Scanning for music files...")

        thread = threading.Thread(target=self.tag_files_worker, args=(source, pattern, rename_files, supported_formats),
                                  daemon=True)
        thread.start()

    def process_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                if message == "---DONE---":
                    self.on_tagging_complete()
                else:
                    self.log_area.config(state="normal")
                    if "clear" in message: self.log_area.delete('1.0', tk.END)
                    self.log_area.insert(tk.END, message.replace("clear", "") + "\n")
                    self.log_area.see(tk.END)
                    self.log_area.config(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_log_queue)

    def log_message(self, message, clear=False):
        log_entry = f"clear{message}" if clear else message
        self.log_queue.put(log_entry)

    def on_tagging_complete(self):
        self.is_running = False
        self.tag_button.config(state="normal", text="✍️ Start Tagging Files")
        self.status_text.set(f"Finished. Tagged {self.processed_file_count} files.")

    def tag_files_worker(self, source_folder, pattern, rename_files, supported_formats):
        self.processed_file_count = 0

        self.log_message(f"Searching for files with extensions: {' '.join(supported_formats)}")
        files_to_process = [f for f in os.listdir(source_folder) if
                            os.path.isfile(os.path.join(source_folder, f)) and f.lower().endswith(supported_formats)]
        total_files = len(files_to_process)
        if total_files == 0:
            self.log_message("No matching music files found.")
            self.log_queue.put("---DONE---")
            messagebox.showinfo("Finished", "No music files were found to process.")
            return

        pattern_parts = pattern.replace("%artist%", "ARTIST_PLACEHOLDER").replace("%title%", "TITLE_PLACEHOLDER").split(
            "ARTIST_PLACEHOLDER")
        pattern_split_on_title = pattern_parts[1].split("TITLE_PLACEHOLDER")

        separator = pattern_split_on_title[0]

        for i, filename in enumerate(files_to_process):
            self.status_text.set(f"Tagging {i + 1}/{total_files}: {filename}")
            filepath = os.path.join(source_folder, filename)

            try:
                filename_no_ext = os.path.splitext(filename)[0]

                if separator not in filename_no_ext:
                    self.log_message(f"⚠️ Skipping '{filename}': Pattern separator '{separator}' not found.")
                    continue

                artist, title = [part.strip() for part in filename_no_ext.split(separator, 1)]

                audio = mutagen.File(filepath, easy=True)
                if audio is None:
                    try:
                        audio = EasyID3(filepath)
                    except:
                        pass

                if audio is None:
                    self.log_message(f"⚠️ Skipping '{filename}': Could not load audio data.")
                    continue

                # Write tags
                audio['artist'] = artist
                audio['title'] = title
                audio.save()

                self.log_message(f"✅ Tagged '{filename}' -> Artist: {artist}, Title: {title}")
                self.processed_file_count += 1

                if rename_files:
                    try:
                        _, file_ext = os.path.splitext(filename)
                        new_filename = f"{title}{file_ext}"
                        new_filepath = os.path.join(source_folder, new_filename)

                        counter = 1
                        while os.path.exists(new_filepath):
                            new_filename = f"{title} ({counter}){file_ext}"
                            new_filepath = os.path.join(source_folder, new_filename)
                            counter += 1

                        os.rename(filepath, new_filepath)
                        self.log_message(f"   RENAMED to '{new_filename}'")

                    except Exception as rename_error:
                        self.log_message(f"   ❌ RENAME FAILED for '{filename}': {rename_error}")

            except Exception as e:
                self.log_message(f"❌ ERROR with '{filename}': {e}")

            self.progress_var.set(((i + 1) / total_files) * 100)

        self.log_queue.put("---DONE---")
        messagebox.showinfo("Success!", f"Tagging complete!\n\nUpdated tags for {self.processed_file_count} files.")


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicTaggerGUI(root)
    root.mainloop()

