import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar, BooleanVar
import threading
import os
import time
import hashlib


class ExtractTab(ctk.CTkFrame):
    """Tab ekstraksi pesan dari stego-video."""

    def __init__(self, parent, colors, status_var):
        super().__init__(parent, corner_radius=0, fg_color=colors["bg"])
        self.C = colors
        self.status_var = status_var
        self._stego_path      = StringVar()
        self._dec_key         = StringVar()
        self._stego_key       = StringVar()
        self._extracted_bytes = None
        self._extracted_meta  = {}

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self._build_left()
        self._build_mid()
        self._build_right()

    def _c(self, k): return self.C[k]

    def _panel(self, parent, col, padx=(12, 6)):
        f = ctk.CTkScrollableFrame(parent, corner_radius=8,
                                    fg_color=self._c("surface"),
                                    border_width=1, border_color=self._c("border"))
        f.grid(row=0, column=col, sticky="nsew", padx=padx, pady=12)
        f.grid_columnconfigure(0, weight=1)
        return f

    def _section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text.upper(), text_color=self._c("muted"),
                     font=ctk.CTkFont(size=9), fg_color="transparent",
                     anchor="w").pack(fill="x", padx=4, pady=(14, 0))
        ctk.CTkFrame(parent, height=1, fg_color=self._c("border"),
                     corner_radius=0).pack(fill="x", pady=(2, 8))

    def _field_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, text_color=self._c("muted"),
                     font=ctk.CTkFont(size=11), fg_color="transparent",
                     anchor="w").pack(fill="x", padx=4, pady=(6, 1))

    def _entry(self, parent, var=None, show=None, state="normal"):
        e = ctk.CTkEntry(parent, textvariable=var, show=show if show else "",
                          fg_color=self._c("surface2"), border_color=self._c("border"),
                          text_color=self._c("text"), font=ctk.CTkFont(size=12),
                          state=state, corner_radius=6, height=34)
        e.pack(fill="x", padx=4, pady=(0, 4))
        return e

    def _build_left(self):
        wrap = self._panel(self, col=0, padx=(12, 6))

        self._section_label(wrap, "Stego-Video Input")
        row = ctk.CTkFrame(wrap, fg_color="transparent")
        row.pack(fill="x", padx=4)
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(row, textvariable=self._stego_path, state="readonly",
                      fg_color=self._c("surface2"), border_color=self._c("border"),
                      text_color=self._c("text"), font=ctk.CTkFont(size=11),
                      corner_radius=6, height=34).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(row, text="Browse", width=80, height=34,
                       fg_color=self._c("surface3"), text_color=self._c("text"),
                       hover_color=self._c("accent"), font=ctk.CTkFont(size=11),
                       corner_radius=6, command=self._browse_stego).grid(row=0, column=1)
        self._stego_info = ctk.CTkLabel(wrap, text="", text_color=self._c("muted"),
                                         font=ctk.CTkFont(size=10), fg_color="transparent",
                                         anchor="w")
        self._stego_info.pack(fill="x", padx=4, pady=(4, 0))

        self._section_label(wrap, "Decryption")
        self._enc_switch = ctk.CTkSwitch(wrap, text="Message was encrypted (A5/1)",
                                          command=self._on_enc_toggle,
                                          progress_color=self._c("accent"),
                                          button_color=self._c("accent"),
                                          button_hover_color=self._c("accent2"),
                                          text_color=self._c("text"),
                                          font=ctk.CTkFont(size=12))
        self._enc_switch.pack(anchor="w", padx=4, pady=(0, 4))
        self._field_label(wrap, "A5/1 Key (64-bit hex)")
        self._dec_key_entry = self._entry(wrap, var=self._dec_key, show="•", state="disabled")

        self._section_label(wrap, "Insertion Mode")
        self._rand_switch = ctk.CTkSwitch(wrap, text="Random insertion was used",
                                           command=self._on_rand_toggle,
                                           progress_color=self._c("accent"),
                                           button_color=self._c("accent"),
                                           button_hover_color=self._c("accent2"),
                                           text_color=self._c("text"),
                                           font=ctk.CTkFont(size=12))
        self._rand_switch.pack(anchor="w", padx=4, pady=(0, 4))
        self._field_label(wrap, "Stego-Key")
        self._stego_key_entry = self._entry(wrap, var=self._stego_key, state="disabled")

        ctk.CTkFrame(wrap, fg_color="transparent", height=12).pack()

        self._progress = ctk.CTkProgressBar(wrap, progress_color=self._c("accent"),
                                             fg_color=self._c("surface2"), height=6,
                                             corner_radius=3)
        self._progress.set(0)
        self._progress.pack(fill="x", padx=4, pady=(0, 8))

        self._extract_btn = ctk.CTkButton(
            wrap, text="Extract Message", height=42,
            fg_color=self._c("accent"), hover_color=self._c("accent_hover"),
            text_color="white", font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8, command=self._run_extract,
        )
        self._extract_btn.pack(fill="x", padx=4)

    def _build_mid(self):
        wrap = self._panel(self, col=1, padx=(6, 6))

        self._section_label(wrap, "Extracted Message")
        self._result_type_lbl = ctk.CTkLabel(wrap, text="Type: —",
                                              text_color=self._c("muted"),
                                              font=ctk.CTkFont(size=10),
                                              fg_color="transparent", anchor="w")
        self._result_type_lbl.pack(fill="x", padx=4, pady=(0, 4))

        self._msg_result = ctk.CTkTextbox(wrap, height=160,
                                           fg_color=self._c("surface2"),
                                           border_color=self._c("border"),
                                           text_color=self._c("text"),
                                           font=ctk.CTkFont(size=12),
                                           corner_radius=6, border_width=1,
                                           state="disabled")
        self._msg_result.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        self._save_btn = ctk.CTkButton(wrap, text="💾  Save As…", height=36,
                                        fg_color=self._c("surface3"),
                                        text_color=self._c("muted"),
                                        hover_color=self._c("accent"),
                                        font=ctk.CTkFont(size=12),
                                        corner_radius=6, state="disabled",
                                        command=self._save_file)
        self._save_btn.pack(fill="x", padx=4, pady=(0, 4))

        self._section_label(wrap, "Metadata")
        self._meta_vars = {}
        for key, label in [("filename", "Filename"), ("size", "Size"),
                            ("enc", "Encrypted"),    ("mode", "Insertion mode")]:
            self._field_label(wrap, label)
            var = StringVar(value="—")
            self._meta_vars[key] = var
            ctk.CTkEntry(wrap, textvariable=var, state="readonly",
                          fg_color=self._c("surface2"), border_color=self._c("border"),
                          text_color=self._c("muted"), font=ctk.CTkFont(size=11),
                          corner_radius=6, height=32).pack(fill="x", padx=4, pady=(0, 4))

    def _build_right(self):
        wrap = self._panel(self, col=2, padx=(6, 12))

        # File Integrity
        self._section_label(wrap, "File Integrity")

        self._int_vars = {}
        for key, label in [("orig_md5", "Original MD5"),
                            ("ext_md5",  "Extracted MD5")]:
            row = ctk.CTkFrame(wrap, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=2)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=label, text_color=self._c("muted"),
                          font=ctk.CTkFont(size=9), fg_color="transparent",
                          width=100, anchor="w").grid(row=0, column=0, sticky="w")
            var = StringVar(value="—")
            self._int_vars[key] = var
            ctk.CTkEntry(row, textvariable=var, state="readonly",
                          fg_color=self._c("surface2"), border_color=self._c("border"),
                          text_color=self._c("muted"),
                          font=ctk.CTkFont(family="Courier New", size=9),
                          corner_radius=4, height=28).grid(row=0, column=1, sticky="ew")

        # Label perbandingan MD5
        self._integrity_lbl = ctk.CTkLabel(wrap, text="",
                                            text_color=self._c("muted"),
                                            font=ctk.CTkFont(size=11, weight="bold"),
                                            fg_color="transparent", anchor="w")
        self._integrity_lbl.pack(fill="x", padx=4, pady=(8, 0))

        # Quality Metrics
        # self._section_label(wrap, "Quality Metrics")

        # mg = ctk.CTkFrame(wrap, fg_color="transparent")
        # mg.pack(fill="x", padx=4)
        # mg.grid_columnconfigure((0, 1), weight=1)

        self._psnr_var   = StringVar(value="—")
        self._mse_var    = StringVar(value="—")
        self._frm_var    = StringVar(value="—")
        self._md5_status = StringVar(value="—")

        cards_def = [
            ("PSNR (dB)", self._psnr_var,   self._c("green"),  0, 0),
            ("MSE",       self._mse_var,    self._c("accent"), 0, 1),
            ("Frames",    self._frm_var,    self._c("text"),   1, 0),
            ("MD5",       self._md5_status, self._c("muted"),  1, 1),
        ]

        self._md5_value_label = ctk.CTkLabel(wrap, textvariable=self._md5_status,
                                      fg_color="transparent",
                                      text_color=self._c("muted"),
                                      font=ctk.CTkFont(size=1))

        # for lbl, var, color, r, c in cards_def:
        #     card = ctk.CTkFrame(mg, fg_color=self._c("surface2"), corner_radius=8,
        #                          border_width=1, border_color=self._c("border"))
        #     card.grid(row=r, column=c, padx=3, pady=3, sticky="ew", ipadx=8, ipady=6)
        #     ctk.CTkLabel(card, text=lbl, text_color=self._c("muted"),
        #                   font=ctk.CTkFont(size=10), fg_color="transparent",
        #                   anchor="w").pack(anchor="w")
        #     val_lbl = ctk.CTkLabel(card, textvariable=var, text_color=color,
        #                             font=ctk.CTkFont(size=18, weight="bold"),
        #                             fg_color="transparent", anchor="w")
        #     val_lbl.pack(anchor="w")
        #     if lbl == "MD5":
        #         self._md5_value_label = val_lbl

        self._section_label(wrap, "Extract Log")
        self._log_box = ctk.CTkTextbox(wrap, height=180,
                                        fg_color=self._c("surface2"),
                                        border_color=self._c("border"),
                                        text_color=self._c("text"),
                                        font=ctk.CTkFont(family="Courier New", size=10),
                                        corner_radius=6, border_width=1,
                                        state="disabled")
        self._log_box.pack(fill="both", expand=True, padx=4)
        self._log("Waiting for stego-video…")

    def _on_enc_toggle(self):
        state = "normal" if self._enc_switch.get() else "disabled"
        self._dec_key_entry.configure(state=state)

    def _on_rand_toggle(self):
        state = "normal" if self._rand_switch.get() else "disabled"
        self._stego_key_entry.configure(state=state)

    def _browse_stego(self):
        path = filedialog.askopenfilename(
            title="Select stego-video",
            filetypes=[
                ("Video files", "*.avi *.mp4"),
                ("AVI files", "*.avi"),
                ("MP4 files", "*.mp4"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._stego_path.set(path)
            size_mb = os.path.getsize(path) / 1_048_576
            self._stego_info.configure(
                text=f"{os.path.basename(path)}  ({size_mb:.1f} MB)")
            self._log(f"Loaded: {os.path.basename(path)}")

    def _log(self, msg):
        self._log_box.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self._log_box.insert("end", f"[{ts}] {msg}\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _run_extract(self):
        if not self._stego_path.get():
            messagebox.showwarning("Missing input", "Please select a stego-video.")
            return
        if self._enc_switch.get() and not self._dec_key.get():
            messagebox.showwarning("Missing key", "Please enter the A5/1 decryption key.")
            return
        if self._rand_switch.get() and not self._stego_key.get():
            messagebox.showwarning("Missing key", "Please enter the stego-key.")
            return

        self._extract_btn.configure(state="disabled", text="Extracting…")
        self.status_var.set("Extracting…")
        self._progress.set(0)

        params = {
            "stego":     self._stego_path.get(),
            "use_dec":   bool(self._enc_switch.get()),
            "dec_key":   self._dec_key.get(),
            "use_rand":  bool(self._rand_switch.get()),
            "stego_key": self._stego_key.get(),
        }
        threading.Thread(target=self._extract_worker, args=(params,), daemon=True).start()

    def _extract_worker(self, params):
        try:
            from core.video_handler import extract_message
            result = extract_message(
                stego_path=params["stego"],
                use_dec=params["use_dec"],
                dec_key=params["dec_key"],
                use_rand=params["use_rand"],
                stego_key=params["stego_key"],
                progress_cb=self._on_progress,
                log_cb=self._log,
            )
            self.after(0, self._on_extract_done, result)
        except Exception as e:
            self.after(0, self._on_extract_error, str(e))

    def _on_progress(self, pct):
        self.after(0, lambda: self._progress.set(pct / 100))

    def _on_extract_done(self, result):
        self._extract_btn.configure(state="normal", text="Extract Message")
        self.status_var.set("Done")
        self._progress.set(1.0)
        if not result:
            return

        meta = result.get("meta", {})
        self._extracted_meta  = meta
        self._extracted_bytes = result.get("data", b"")

        msg_type = meta.get("msg_type", "text")
        self._result_type_lbl.configure(
            text=f"Type: {msg_type}  |  Size: {len(self._extracted_bytes)} bytes")

        self._meta_vars["filename"].set(meta.get("filename", "—"))
        self._meta_vars["size"].set(f"{meta.get('size', '—')} bytes")
        self._meta_vars["enc"].set("Yes (A5/1)" if meta.get("encrypted") else "No")
        self._meta_vars["mode"].set(meta.get("insert_mode", "—").capitalize())

        self._msg_result.configure(state="normal")
        self._msg_result.delete("1.0", "end")
        if msg_type == "text":
            self._msg_result.insert(
                "1.0", self._extracted_bytes.decode("utf-8", errors="replace"))
            self._save_btn.configure(state="disabled")
        else:
            self._msg_result.insert(
                "1.0",
                f"[File: {meta.get('filename','unknown')}]\n"
                f"Size: {len(self._extracted_bytes):,} bytes\n\n"
                f"Click 'Save As' to save.")
            self._save_btn.configure(state="normal",
                                      fg_color=self._c("accent"),
                                      text_color="white")
        self._msg_result.configure(state="disabled")

        self._psnr_var.set(f"{result.get('psnr', 0):.2f}")
        self._mse_var.set(f"{result.get('mse', 0):.4f}")
        self._frm_var.set(str(result.get("frames", "—")))

        if self._extracted_bytes:
            ext_md5 = hashlib.md5(self._extracted_bytes).hexdigest()
            self._int_vars["ext_md5"].set(ext_md5[:24] + "…")

            orig_md5 = meta.get("orig_md5", "")

            if orig_md5:
                self._int_vars["orig_md5"].set(orig_md5[:24] + "…")
                md5_match = (orig_md5 == ext_md5)

                if md5_match:
                    self._integrity_lbl.configure(
                        text="✔  MD5 match - file intact",
                        text_color=self._c("green"))
                    self._md5_status.set("✓")
                    self._md5_value_label.configure(text_color=self._c("green"))
                else:
                    self._integrity_lbl.configure(
                        text="✘  MD5 mismatch - file corrupted",
                        text_color=self._c("red"))
                    self._md5_status.set("✗")
                    self._md5_value_label.configure(text_color=self._c("red"))

                self._log(
                    f"MD5 orig     : {orig_md5[:16]}…")
                self._log(
                    f"MD5 extracted: {ext_md5[:16]}…")
                self._log(
                    f"Integrity    : {'MATCH ✓' if md5_match else 'MISMATCH ✗'}")
            else:
                self._integrity_lbl.configure(
                    text="No original MD5 in metadata",
                    text_color=self._c("muted"))
                self._md5_status.set("—")
                self._md5_value_label.configure(text_color=self._c("muted"))
                self._log("Integrity: original MD5 tidak tersedia di metadata.")

        self._log("Extraction complete!")

    def _on_extract_error(self, msg):
        self._extract_btn.configure(state="normal", text="Extract Message")
        self.status_var.set("Error")
        self._progress.set(0)
        self._log(f"Error: {msg}")
        messagebox.showerror("Extract failed", msg)

    def _save_file(self):
        if not self._extracted_bytes:
            return
        default_name = self._extracted_meta.get("filename", "extracted_file")
        ext  = os.path.splitext(default_name)[1] or ".*"
        path = filedialog.asksaveasfilename(
            title="Save extracted file",
            initialfile=default_name,
            defaultextension=ext,
            filetypes=[(f"{ext} files", f"*{ext}"), ("All files", "*.*")])
        if path:
            with open(path, "wb") as f:
                f.write(self._extracted_bytes)
            self._log(f"File saved: {os.path.basename(path)}")
            messagebox.showinfo("Saved", f"File saved to:\n{path}")