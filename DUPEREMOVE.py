# RhythmShelf Duplicate Finder
# Version: 1.0.0
# Author: Lewis
#
# This work is licensed under the MIT License.
# See: https://opensource.org/licenses/MIT

import os
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import queue
from collections import defaultdict


class DuplicateFinderGUI:
    """A GUI to find and safely remove duplicate music files."""
    APP_VERSION = "1.0.0"

    def __init__(self, root):
        self.root = root
        self.root.title(f"🔎 RhythmShelf Duplicate Finder v{self.APP_VERSION}")
        self.root.geometry("800x650")
        self.root.minsize(700, 500)
        self.root.configure(bg="#2e2e2e")

        self.source_dir = tk.StringVar()
        self.status_text = tk.StringVar(value="Ready.")
        self.progress_var = tk.DoubleVar(value=0)
        self.is_running = False
        self.duplicate_sets = []

        self.create_widgets()

    def create_widgets(self):
        main_frame = tk.Frame(self.root, padx=20, pady=20, bg="#2e2e2e")
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # --- Top Controls ---
        top_frame = tk.Frame(main_frame, bg="#2e2e2e")
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_frame.columnconfigure(1, weight=1)

        tk.Label(top_frame, text="Music Library Folder:", fg="white", bg="#2e2e2e").grid(row=0, column=0, sticky="w",
                                                                                         padx=(0, 10))
        tk.Entry(top_frame, textvariable=self.source_dir, state="readonly", readonlybackground="#555", fg="white").grid(
            row=0, column=1, sticky="ew")
        tk.Button(top_frame, text="Browse...", command=self.select_source_dir).grid(row=0, column=2, padx=(10, 0))

        self.find_button = tk.Button(top_frame, text="🔍 Find Duplicates", command=self.start_finding_thread,
                                     bg="#4a4a4a", fg="white", font=("Helvetica", 10, "bold"), relief=tk.FLAT, padx=10,
                                     pady=5)
        self.find_button.grid(row=0, column=3, padx=(20, 0))

        # --- Progress Bar ---
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # --- Results Treeview ---
        tree_frame = tk.Frame(main_frame)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame, columns=("path", "size"), show="headings")
        self.tree.heading("path", text="File Path")
        self.tree.heading("size", text="Size")
        self.tree.column("path", width=500)
        self.tree.column("size", width=100, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # --- Bottom Controls ---
        bottom_frame = tk.Frame(main_frame, bg="#2e2e2e")
        bottom_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        self.delete_button = tk.Button(bottom_frame, text="🗑️ Delete Selected Duplicates", command=self.delete_selected,
                                       state="disabled", bg="#c0392b", fg="white", font=("Helvetica", 10, "bold"),
                                       relief=tk.FLAT, padx=10, pady=5)
        self.delete_button.pack(side=tk.RIGHT)

        tk.Label(self.root, textvariable=self.status_text, bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#3a3a3a",
                 fg="white").pack(side=tk.BOTTOM, fill=tk.X)

    def select_source_dir(self):
        path = filedialog.askdirectory(title="Select your music library folder to scan")
        if path: self.source_dir.set(path)

    def start_finding_thread(self):
        if self.is_running: return

        source = self.source_dir.get()
        if not source:
            messagebox.showerror("Error", "Please select a source folder to scan.")
            return

        self.is_running = True
        self.tree.delete(*self.tree.get_children())
        self.find_button.config(state="disabled")
        self.delete_button.config(state="disabled")
        self.status_text.set("Scanning files by size...")
        self.progress_var.set(0)

        thread = threading.Thread(target=self.find_duplicates_worker, args=(source,), daemon=True)
        thread.start()

    def find_duplicates_worker(self, folder):
        files_by_size = defaultdict(list)
        # Phase 1: Scan by file size (fast pre-filter)
        all_files = [os.path.join(r, f) for r, d, fs in os.walk(folder) for f in fs]
        total_files = len(all_files)

        for i, path in enumerate(all_files):
            try:
                size = os.path.getsize(path)
                files_by_size[size].append(path)
            except OSError:
                continue  # Skip inaccessible files
            self.progress_var.set((i + 1) / total_files * 50)

        # Phase 2: Hash potential duplicates
        self.status_text.set("Finding duplicates by content (hashing)...")
        hashes = defaultdict(list)
        potential_dupes = {size: files for size, files in files_by_size.items() if len(files) > 1}

        files_to_hash_count = sum(len(files) for files in potential_dupes.values())
        hashed_count = 0

        for size, files in potential_dupes.items():
            for path in files:
                try:
                    hash_md5 = self.hash_file(path)
                    hashes[hash_md5].append(path)
                except (IOError, OSError):
                    continue
                hashed_count += 1
                self.progress_var.set(50 + (hashed_count / files_to_hash_count * 50))

        self.duplicate_sets = [files for files in hashes.values() if len(files) > 1]

        # Signal completion to the main thread
        self.root.after(0, self.on_find_complete)

    def on_find_complete(self):
        self.is_running = False
        self.find_button.config(state="normal")
        self.progress_var.set(100)

        if not self.duplicate_sets:
            self.status_text.set("Scan complete. No duplicate files found!")
            messagebox.showinfo("Finished", "No duplicate files were found in the selected folder.")
            return

        # Populate the treeview
        self.tree.tag_configure('keep', background='#2c3e50', foreground='white')
        self.tree.tag_configure('delete', background='#3e2c2c', foreground='#ffdddd')

        for i, file_list in enumerate(self.duplicate_sets):
            # Keep the first file, mark others for deletion
            file_list.sort()  # Sort to have a predictable "keep" file
            parent_id = self.tree.insert("", "end", text=f"Set {i + 1}",
                                         values=(f"Duplicate Set {i + 1} ({len(file_list)} files)", ""), open=True)

            for j, file_path in enumerate(file_list):
                file_size = f"{os.path.getsize(file_path) / 1024 / 1024:.2f} MB"
                tags = ('keep',) if j == 0 else ('delete',)
                self.tree.insert(parent_id, "end", values=(file_path, file_size), tags=tags)

        total_dupes = sum(len(s) - 1 for s in self.duplicate_sets)
        self.status_text.set(f"Scan complete. Found {total_dupes} duplicate files in {len(self.duplicate_sets)} sets.")
        self.delete_button.config(state="normal")

    def delete_selected(self):
        to_delete = []
        for parent in self.tree.get_children():
            children = self.tree.get_children(parent)
            # The first child is kept, the rest are potential deletions
            to_delete.extend(children[1:])

        if not to_delete:
            messagebox.showinfo("No files", "No files are marked for deletion.")
            return

        total_size = 0
        paths_to_delete = []
        for item_id in to_delete:
            path = self.tree.set(item_id, "path")
            paths_to_delete.append(path)
            try:
                total_size += os.path.getsize(path)
            except OSError:
                continue

        msg = f"Are you sure you want to permanently delete {len(paths_to_delete)} files?\n\n"
        msg += f"This will free up approximately {total_size / 1024 / 1024:.2f} MB of space.\n\n"
        msg += "This action cannot be undone."

        if messagebox.askyesno("Confirm Deletion", msg):
            deleted_count = 0
            for path in paths_to_delete:
                try:
                    os.remove(path)
                    deleted_count += 1
                except OSError as e:
                    self.status_text.set(f"Error deleting {os.path.basename(path)}: {e}")

            messagebox.showinfo("Deletion Complete", f"Successfully deleted {deleted_count} files.")
            # Rescan to show updated state
            self.start_finding_thread()

    @staticmethod
    def hash_file(path):
        """Calculates the MD5 hash of a file."""
        hasher = hashlib.md5()
        with open(path, 'rb') as f:
            buf = f.read(65536)  # Read in 64kb chunks
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()


if __name__ == "__main__":
    root = tk.Tk()
    # Adding some style for ttk widgets
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#1e1e1e", foreground="#dcdcdc", fieldbackground="#1e1e1e", rowheight=25)
    style.configure("Treeview.Heading", background="#4a4a4a", foreground="white", relief="flat")
    style.map("Treeview.Heading", relief=[('active', 'groove'), ('pressed', 'sunken')])
    root.tk_setPalette(background='#2e2e2e', foreground='white')
    app = DuplicateFinderGUI(root)
    root.mainloop()
