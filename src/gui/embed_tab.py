import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar, IntVar, BooleanVar
import tkinter as tk
import threading
import os
import time


def _get_downloads_dir() -> str:
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.isdir(downloads):
        downloads = os.path.expanduser("~")
    return downloads


class EmbedTab(ctk.CTkFrame):
    """Tab penyisipan pesan ke dalam video AVI."""

    def __init__(self, parent, colors, status_var):
        super().__init__(parent, corner_radius=0, fg_color=colors["bg"])
        self.C = colors
        self.status_var = status_var

        self._cover_path  = StringVar()
        self._output_path = StringVar()
        self._msg_type    = StringVar(value="text")
        self._file_path   = StringVar()
        self._use_enc     = BooleanVar(value=False)
        self._enc_key     = StringVar()
        self._insert_mode = StringVar(value="sequential")
        self._stego_key   = StringVar()
        self._frame_sel   = StringVar(value="All frames")
        self._frame_n     = StringVar(value="50")
        self._r_bits      = IntVar(value=3)
        self._g_bits      = IntVar(value=3)
        self._b_bits      = IntVar(value=2)

        # Data histogram
        self._hist_cover_frame = None
        self._hist_stego_frame = None

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self._build_left()
        self._build_mid()
        self._build_right()

    # helpers

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
                          fg_color=self._c("surface2"),
                          border_color=self._c("border"),
                          text_color=self._c("text"),
                          font=ctk.CTkFont(size=12),
                          state=state, corner_radius=6, height=34)
        e.pack(fill="x", padx=4, pady=(0, 4))
        return e

    # Left Panel

    def _build_left(self):
        wrap = self._panel(self, col=0, padx=(12, 6))

        # Cover video
        self._section_label(wrap, "Cover Video")
        row = ctk.CTkFrame(wrap, fg_color="transparent")
        row.pack(fill="x", padx=4)
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(row, textvariable=self._cover_path, state="readonly",
                      fg_color=self._c("surface2"), border_color=self._c("border"),
                      text_color=self._c("text"), font=ctk.CTkFont(size=11),
                      corner_radius=6, height=34).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(row, text="Browse", width=80, height=34,
                       fg_color=self._c("surface3"), text_color=self._c("text"),
                       hover_color=self._c("accent"), font=ctk.CTkFont(size=11),
                       corner_radius=6,
                       command=self._browse_cover).grid(row=0, column=1)

        self._cap_label = ctk.CTkLabel(wrap, text="Capacity: —",
                                        text_color=self._c("muted"),
                                        font=ctk.CTkFont(size=10),
                                        fg_color="transparent", anchor="w")
        self._cap_label.pack(fill="x", padx=4, pady=(4, 0))
        self._cap_bar = ctk.CTkProgressBar(wrap, progress_color=self._c("accent"),
                                            fg_color=self._c("surface2"), height=5,
                                            corner_radius=3)
        self._cap_bar.set(0)
        self._cap_bar.pack(fill="x", padx=4, pady=(4, 0))

        # Secret message
        self._section_label(wrap, "Secret Message")
        seg = ctk.CTkSegmentedButton(wrap, values=["Text", "File"],
                                      command=self._on_msg_type,
                                      fg_color=self._c("surface2"),
                                      selected_color=self._c("accent"),
                                      selected_hover_color=self._c("accent2"),
                                      unselected_color=self._c("surface2"),
                                      unselected_hover_color=self._c("surface3"),
                                      text_color=self._c("text"),
                                      font=ctk.CTkFont(size=11))
        seg.set("Text")
        seg.pack(fill="x", padx=4, pady=(0, 8))

        self._msg_container = ctk.CTkFrame(wrap, fg_color="transparent")
        self._msg_container.pack(fill="both", expand=True)

        # text frame
        self._text_frame = ctk.CTkFrame(self._msg_container, fg_color="transparent")
        self._text_frame.pack(fill="both", expand=True)
        self._msg_text = ctk.CTkTextbox(
            self._text_frame, height=100,
            fg_color=self._c("surface2"), border_color=self._c("border"),
            text_color=self._c("text"), font=ctk.CTkFont(size=12),
            corner_radius=6, border_width=1,
        )
        self._msg_text.pack(fill="both", expand=True, padx=4)

        # file frame
        self._file_frame = ctk.CTkFrame(self._msg_container, fg_color="transparent")
        fr = ctk.CTkFrame(self._file_frame, fg_color="transparent")
        fr.pack(fill="x", padx=4)
        fr.grid_columnconfigure(0, weight=1)
        self._file_entry = ctk.CTkEntry(
            fr, textvariable=self._file_path, state="readonly",
            fg_color=self._c("surface2"), border_color=self._c("border"),
            text_color=self._c("text"), font=ctk.CTkFont(size=11),
            corner_radius=6, height=34)
        self._file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(fr, text="Browse", width=80, height=34,
                       fg_color=self._c("surface3"), text_color=self._c("text"),
                       hover_color=self._c("accent"), font=ctk.CTkFont(size=11),
                       corner_radius=6,
                       command=self._browse_file).grid(row=0, column=1)

        # LSB Bit Allocation
        self._section_label(wrap, "LSB Bit Allocation")
        lf = ctk.CTkFrame(wrap, fg_color="transparent")
        lf.pack(fill="x", padx=4)
        lf.grid_columnconfigure((0, 1, 2), weight=1)

        ch_colors = {"R": self._c("red"), "G": self._c("green"), "B": self._c("blue")}
        lsb_vars  = {"R": self._r_bits, "G": self._g_bits, "B": self._b_bits}

        for col, ch in enumerate(("R", "G", "B")):
            cell = ctk.CTkFrame(lf, fg_color=self._c("surface2"),
                                 corner_radius=8, border_width=1,
                                 border_color=self._c("border"))
            cell.grid(row=0, column=col, padx=3, pady=2, sticky="ew", ipady=4)
            ctk.CTkLabel(cell, text=ch, text_color=ch_colors[ch],
                          font=ctk.CTkFont(size=11), fg_color="transparent").pack(pady=(6, 0))
            ctk.CTkLabel(cell, textvariable=lsb_vars[ch],
                          text_color=ch_colors[ch],
                          font=ctk.CTkFont(size=20, weight="bold"),
                          fg_color="transparent").pack()
            ctk.CTkSlider(cell, from_=1, to=4, number_of_steps=3,
                           variable=lsb_vars[ch],
                           progress_color=ch_colors[ch],
                           button_color=ch_colors[ch],
                           button_hover_color=ch_colors[ch],
                           fg_color=self._c("surface3"),
                           command=lambda _: self._update_capacity()).pack(
                               fill="x", padx=8, pady=(2, 8))

        self._bpp_label = ctk.CTkLabel(wrap, text="Bits/pixel: 8",
                                        text_color=self._c("muted"),
                                        font=ctk.CTkFont(size=10),
                                        fg_color="transparent", anchor="w")
        self._bpp_label.pack(fill="x", padx=4, pady=(4, 0))

    # Mid Panel

    def _build_mid(self):
        wrap = self._panel(self, col=1, padx=(6, 6))

        # Encryption
        self._section_label(wrap, "Encryption")
        self._enc_switch = ctk.CTkSwitch(wrap, text="Use A5/1 Encryption",
                                          command=self._on_enc_toggle,
                                          progress_color=self._c("accent"),
                                          button_color=self._c("accent"),
                                          button_hover_color=self._c("accent2"),
                                          text_color=self._c("text"),
                                          font=ctk.CTkFont(size=12))
        self._enc_switch.pack(anchor="w", padx=4, pady=(0, 4))
        self._field_label(wrap, "A5/1 Key (64-bit hex)")
        self._enc_key_entry = self._entry(wrap, var=self._enc_key, show="•", state="disabled")

        # Insertion mode
        self._section_label(wrap, "Insertion Mode")
        self._mode_seg = ctk.CTkSegmentedButton(
            wrap, values=["Sequential", "Random"],
            command=self._on_mode_change,
            fg_color=self._c("surface2"),
            selected_color=self._c("accent"),
            selected_hover_color=self._c("accent2"),
            unselected_color=self._c("surface2"),
            unselected_hover_color=self._c("surface3"),
            text_color=self._c("text"),
            font=ctk.CTkFont(size=11),
        )
        self._mode_seg.set("Sequential")
        self._mode_seg.pack(fill="x", padx=4, pady=(0, 4))
        self._field_label(wrap, "Stego-Key (seed)")
        self._stego_entry = self._entry(wrap, var=self._stego_key, state="disabled")

        # Frame selection
        self._section_label(wrap, "Frame Selection")
        self._field_label(wrap, "Mode")
        self._frame_combo = ctk.CTkOptionMenu(
            wrap, variable=self._frame_sel,
            values=["All frames", "Key frames only", "Even frames", "First N frames"],
            command=self._on_frame_sel,
            fg_color=self._c("surface2"),
            button_color=self._c("surface3"),
            button_hover_color=self._c("accent"),
            text_color=self._c("text"),
            dropdown_fg_color=self._c("surface"),
            dropdown_text_color=self._c("text"),
            dropdown_hover_color=self._c("surface2"),
            font=ctk.CTkFont(size=12),
            corner_radius=6, height=34,
        )
        self._frame_combo.pack(fill="x", padx=4, pady=(0, 4))
        self._field_label(wrap, "N (first-N frames)")
        self._frame_n_entry = self._entry(wrap, var=self._frame_n, state="disabled")

        # Output
        self._section_label(wrap, "Output")
        self._field_label(wrap, "Output filename")
        out_row = ctk.CTkFrame(wrap, fg_color="transparent")
        out_row.pack(fill="x", padx=4)
        out_row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(out_row, textvariable=self._output_path,
                      fg_color=self._c("surface2"), border_color=self._c("border"),
                      text_color=self._c("text"), font=ctk.CTkFont(size=11),
                      corner_radius=6, height=34).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(out_row, text="…", width=40, height=34,
                       fg_color=self._c("surface3"), text_color=self._c("muted"),
                       hover_color=self._c("accent"), font=ctk.CTkFont(size=12),
                       corner_radius=6,
                       command=self._browse_output).grid(row=0, column=1)

        # Label info output path
        self._out_info_label = ctk.CTkLabel(
            wrap, text="",
            text_color=self._c("muted"),
            font=ctk.CTkFont(size=9),
            fg_color="transparent", anchor="w",
            wraplength=220,
        )
        self._out_info_label.pack(fill="x", padx=4, pady=(2, 0))

        ctk.CTkFrame(wrap, fg_color="transparent", height=12).pack()

        self._progress = ctk.CTkProgressBar(wrap, progress_color=self._c("accent"),
                                             fg_color=self._c("surface2"), height=6,
                                             corner_radius=3)
        self._progress.set(0)
        self._progress.pack(fill="x", padx=4, pady=(0, 8))

        self._embed_btn = ctk.CTkButton(
            wrap, text="Embed Message", height=42,
            fg_color=self._c("accent"), hover_color=self._c("accent_hover"),
            text_color="white", font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8, command=self._run_embed,
        )
        self._embed_btn.pack(fill="x", padx=4)

    # Right Panel
    def _build_right(self):
        wrap = self._panel(self, col=2, padx=(6, 12))

        # Metrics
        self._section_label(wrap, "Visual Quality")
        mg = ctk.CTkFrame(wrap, fg_color="transparent")
        mg.pack(fill="x", padx=4)
        mg.grid_columnconfigure((0, 1), weight=1)

        self._psnr_var = StringVar(value="—")
        self._mse_var  = StringVar(value="—")
        self._frm_var  = StringVar(value="—")
        self._bpp_var  = StringVar(value="8")

        for i, (lbl, var, color) in enumerate([
            ("PSNR (dB)", self._psnr_var, self._c("green")),
            ("MSE",       self._mse_var,  self._c("accent")),
            ("Frames",    self._frm_var,  self._c("text")),
            ("Bits/px",   self._bpp_var,  self._c("amber")),
        ]):
            card = ctk.CTkFrame(mg, fg_color=self._c("surface2"), corner_radius=8,
                                 border_width=1, border_color=self._c("border"))
            card.grid(row=i//2, column=i%2, padx=3, pady=3, sticky="ew", ipadx=8, ipady=6)
            ctk.CTkLabel(card, text=lbl, text_color=self._c("muted"),
                          font=ctk.CTkFont(size=10), fg_color="transparent",
                          anchor="w").pack(anchor="w")
            ctk.CTkLabel(card, textvariable=var, text_color=color,
                          font=ctk.CTkFont(size=18, weight="bold"),
                          fg_color="transparent", anchor="w").pack(anchor="w")

        self._section_label(wrap, "Histogram — Frame 1")

        hdr = ctk.CTkFrame(wrap, fg_color="transparent")
        hdr.pack(fill="x", padx=4, pady=(0, 4))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Cover (solid) vs Stego (faded)",
                     text_color=self._c("muted"),
                     font=ctk.CTkFont(size=10),
                     fg_color="transparent", anchor="w").grid(row=0, column=0, sticky="w")
        self._hist_info_label = ctk.CTkLabel(
            hdr, text="",
            text_color=self._c("muted"),
            font=ctk.CTkFont(size=9),
            fg_color="transparent", anchor="e")
        self._hist_info_label.grid(row=0, column=1, sticky="e")

        hist_wrapper = ctk.CTkFrame(wrap, fg_color=self._c("surface2"),
                                     corner_radius=6, border_width=1,
                                     border_color=self._c("border"))
        hist_wrapper.pack(fill="x", padx=4, pady=(0, 4))
        self._hist_canvas = tk.Canvas(
            hist_wrapper, height=90,
            bg=self._c("surface2"),
            highlightthickness=0)
        self._hist_canvas.pack(fill="x", padx=6, pady=6)
        self._hist_canvas.bind("<Configure>", self._on_hist_resize)

        leg = ctk.CTkFrame(wrap, fg_color="transparent")
        leg.pack(fill="x", padx=4, pady=(0, 2))
        for label_text, hex_color in [
            ("● Red",   self._c("red")),
            ("● Green", self._c("green")),
            ("● Blue",  self._c("blue")),
        ]:
            ctk.CTkLabel(leg, text=label_text, text_color=hex_color,
                          font=ctk.CTkFont(size=10),
                          fg_color="transparent").pack(side="left", padx=(0, 10))

        self.after(200, self._draw_placeholder_histogram)

        # Activity Log
        self._section_label(wrap, "Activity Log")
        self._log_box = ctk.CTkTextbox(wrap, height=180,
                                        fg_color=self._c("surface2"),
                                        border_color=self._c("border"),
                                        text_color=self._c("text"),
                                        font=ctk.CTkFont(family="Courier New", size=10),
                                        corner_radius=6, border_width=1,
                                        state="disabled")
        self._log_box.pack(fill="both", expand=True, padx=4)
        self._log("Waiting for input…")

    def _load_cover_frame(self, video_path):
        try:
            import cv2
            import numpy as np

            cap = cv2.VideoCapture(video_path)
            ok, frame_bgr = cap.read()
            cap.release()

            if not ok or frame_bgr is None:
                self.after(0, lambda: self._log("Histogram: gagal baca frame pertama."))
                return

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            self._hist_cover_frame = frame_rgb
            self._hist_stego_frame = None

            h, w = frame_rgb.shape[:2]
            self.after(0, lambda: self._hist_info_label.configure(
                text=f"{w}×{h}px · cover only"))
            self.after(0, self._redraw_histogram)

        except ImportError:
            self.after(0, lambda: self._log("Histogram: OpenCV tidak terinstall."))
        except Exception as e:
            self.after(0, lambda: self._log(f"Histogram error: {e}"))

    # Histogram
    def draw_histogram(self, cover_frame, stego_frame):
        self._hist_cover_frame = cover_frame
        self._hist_stego_frame = stego_frame
        h, w = cover_frame.shape[:2]
        self.after(0, lambda: self._hist_info_label.configure(
            text=f"{w}×{h}px · cover + stego"))
        self.after(0, self._redraw_histogram)

    def reset_histogram(self):
        self._hist_cover_frame = None
        self._hist_stego_frame = None
        self.after(0, lambda: self._hist_info_label.configure(text=""))
        self.after(0, self._draw_placeholder_histogram)

    def _on_hist_resize(self, event):
        self._redraw_histogram()

    def _redraw_histogram(self):
        canvas = self._hist_canvas
        canvas.update_idletasks()
        W = canvas.winfo_width()
        H = canvas.winfo_height()
        if W < 10 or H < 10:
            return
        canvas.delete("all")

        if self._hist_cover_frame is not None:
            self._render_real_histogram(canvas, W, H,
                                        self._hist_cover_frame,
                                        self._hist_stego_frame)
        else:
            self._draw_placeholder_histogram()

    def _render_real_histogram(self, canvas, W, H, cover_frame, stego_frame=None):
        try:
            import numpy as np
        except ImportError:
            return

        bins      = 24
        padding   = 2
        max_h     = H - padding * 2
        section_w = W / 3

        solid_colors = [self._c("red"), self._c("green"), self._c("blue")]

        for ch in range(3):
            x_off = ch * section_w

            cover_hist, _ = np.histogram(
                cover_frame[:, :, ch].ravel(), bins=bins, range=(0, 256))

            if stego_frame is not None:
                stego_hist, _ = np.histogram(
                    stego_frame[:, :, ch].ravel(), bins=bins, range=(0, 256))
                max_val = max(cover_hist.max(), stego_hist.max(), 1)
            else:
                stego_hist = None
                max_val    = max(cover_hist.max(), 1)

            bw = section_w / bins

            for i in range(bins):
                x0 = x_off + i * bw + 1
                x1 = x0 + bw - 2

                if stego_hist is not None:
                    sh  = (stego_hist[i] / max_val) * max_h
                    sy0 = H - padding - sh
                    canvas.create_rectangle(x0, sy0, x1, H - padding,
                                             fill=solid_colors[ch],
                                             outline="", stipple="gray25")

                ch_h = (cover_hist[i] / max_val) * max_h
                cy0  = H - padding - ch_h
                canvas.create_rectangle(x0, cy0, x1, H - padding,
                                         fill=solid_colors[ch], outline="")

    def _draw_placeholder_histogram(self):
        import math
        canvas = self._hist_canvas
        canvas.update_idletasks()
        W = canvas.winfo_width()
        H = canvas.winfo_height()
        if W < 10 or H < 10:
            return

        canvas.delete("all")

        bins    = 20
        padding = 2
        max_h   = H - padding * 2

        channels = [
            (0.35, 0.18, self._c("red")),
            (0.50, 0.18, self._c("green")),
            (0.65, 0.18, self._c("blue")),
        ]

        for ch_idx, (peak, spread, color) in enumerate(channels):
            x_start   = ch_idx * (W / 3)
            section_w = W / 3

            vals  = [math.exp(-0.5 * (((i / bins) - peak + 0.15) / spread) ** 2)
                     for i in range(bins)]
            max_v = max(vals) or 1
            bw    = section_w / bins

            for i, v in enumerate(vals):
                bar_h = (v / max_v) * max_h * 0.80
                x0 = x_start + i * bw + 1
                x1 = x0 + bw - 2
                y0 = H - padding - bar_h
                canvas.create_rectangle(x0, y0, x1, H - padding,
                                         fill=color, outline="",
                                         stipple="gray50")

    # Event Handlers
    def _on_msg_type(self, val):
        self._msg_type.set(val.lower())
        self._text_frame.pack_forget()
        self._file_frame.pack_forget()
        if val == "Text":
            self._text_frame.pack(fill="both", expand=True)
        else:
            self._file_frame.pack(fill="x")

    def _on_enc_toggle(self):
        state = "normal" if self._enc_switch.get() else "disabled"
        self._enc_key_entry.configure(state=state)

    def _on_mode_change(self, val):
        self._insert_mode.set(val.lower())
        state = "normal" if val == "Random" else "disabled"
        self._stego_entry.configure(state=state)

    def _on_frame_sel(self, val):
        state = "normal" if val == "First N frames" else "disabled"
        self._frame_n_entry.configure(state=state)

    # File Browsing
    def _browse_cover(self):
        path = filedialog.askopenfilename(
            title="Select cover video",
            filetypes=[
                ("Video files", "*.avi *.mp4"),
                ("AVI files", "*.avi"),
                ("MP4 files", "*.mp4"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._cover_path.set(path)
            base = os.path.splitext(os.path.basename(path))[0]
            ext  = os.path.splitext(path)[1].lower()
            if ext == ".mp4":
                messagebox.showwarning(
                    "Warning",
                    "MP4 uses lossy compression. Hidden data may be corrupted after encoding.\n\n"
                    "AVI is recommended for reliable extraction."
                )
            self._update_capacity()
            self._log(f"Video loaded: {os.path.basename(path)}")

            if ext not in [".avi", ".mp4"]:
                ext = ".avi"

            out_name = f"{base}_embedded{ext}"
            out_path = os.path.join(_get_downloads_dir(), out_name)
            self._output_path.set(out_path)
            self._out_info_label.configure(
                text=f"📁 {out_path}")
            self._log(f"Output → {out_path}")

            self.reset_histogram()
            threading.Thread(
                target=self._load_cover_frame, args=(path,), daemon=True
            ).start()

    def _browse_file(self):
        path = filedialog.askopenfilename(title="Select secret file",
                                           filetypes=[("All files", "*.*")])
        if path:
            self._file_path.set(path)
            self._update_capacity()

    def _browse_output(self):
        """Buka dialog Save As dengan default directory = Downloads."""
        downloads = _get_downloads_dir()
        current   = self._output_path.get()

        cover_ext = os.path.splitext(self._cover_path.get())[1].lower()
        default_ext = ".mp4" if cover_ext == ".mp4" else ".avi"

        initial_file = os.path.basename(current) if current else f"stego_video{default_ext}"
        initial_dir  = os.path.dirname(current) if current and os.path.isdir(
            os.path.dirname(current)) else downloads

        path = filedialog.asksaveasfilename(
            title="Save stego-video as",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=default_ext,
            filetypes=[
                ("Video files", "*.avi *.mp4"),
                ("AVI files", "*.avi"),
                ("MP4 files", "*.mp4"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._output_path.set(path)
            self._out_info_label.configure(text=f"Output: {path}")
            self._log(f"Output → {path}")

    # Capacity

    def _update_capacity(self):
        bpp = self._r_bits.get() + self._g_bits.get() + self._b_bits.get()
        self._bpp_label.configure(text=f"Bits/pixel: {bpp}")
        self._bpp_var.set(str(bpp))
        cover = self._cover_path.get()
        if not cover or not os.path.exists(cover):
            self._cap_label.configure(text="Capacity: load a video first")
            self._cap_bar.set(0)
            return
        try:
            from utils.capacity import compute_capacity
            cap_bytes, used_bytes = compute_capacity(cover, bpp)
            cap_mb  = cap_bytes  / 1_048_576
            used_mb = used_bytes / 1_048_576
            pct = min(1.0, used_bytes / cap_bytes) if cap_bytes else 0
            self._cap_label.configure(
                text=f"Capacity: {used_mb:.2f} / {cap_mb:.2f} MB  ({int(pct*100)}%)")
            self._cap_bar.set(pct)
        except Exception:
            self._cap_label.configure(
                text=f"Capacity: bits/px = {bpp} (load video for exact)")

    # Logging

    def _log(self, msg):
        self._log_box.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self._log_box.insert("end", f"[{ts}] {msg}\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    # Embed

    def _run_embed(self):
        if not self._cover_path.get():
            messagebox.showwarning("Missing input", "Please select a cover video.")
            return
        msg_type = self._msg_type.get()
        if msg_type == "text":
            msg_data = self._msg_text.get("1.0", "end").strip()
            if not msg_data:
                messagebox.showwarning("Missing input", "Please enter a secret message.")
                return
        else:
            if not self._file_path.get():
                messagebox.showwarning("Missing input", "Please select a secret file.")
                return
            msg_data = self._file_path.get()
        if not self._output_path.get():
            messagebox.showwarning("Missing input", "Please specify an output filename.")
            return
        if self._enc_switch.get() and not self._enc_key.get():
            messagebox.showwarning("Missing key", "Please enter the A5/1 encryption key.")
            return
        if self._insert_mode.get() == "random" and not self._stego_key.get():
            messagebox.showwarning("Missing key", "Please enter the stego-key.")
            return

        self._embed_btn.configure(state="disabled", text="Embedding…")
        self.status_var.set("Embedding…")
        self._progress.set(0)

        params = {
            "cover":       self._cover_path.get(),
            "output":      self._output_path.get(),
            "msg_type":    msg_type,
            "msg_data":    msg_data,
            "use_enc":     bool(self._enc_switch.get()),
            "enc_key":     self._enc_key.get(),
            "insert_mode": self._insert_mode.get().lower(),
            "stego_key":   self._stego_key.get(),
            "frame_sel":   self._frame_sel.get(),
            "frame_n":     self._frame_n.get(),
            "r_bits":      self._r_bits.get(),
            "g_bits":      self._g_bits.get(),
            "b_bits":      self._b_bits.get(),
        }
        threading.Thread(target=self._embed_worker, args=(params,), daemon=True).start()

    def _embed_worker(self, params):
        try:
            from core.video_handler import embed_message
            result = embed_message(
                cover_path=params["cover"],
                output_path=params["output"],
                msg_type=params["msg_type"],
                msg_data=params["msg_data"],
                use_enc=params["use_enc"],
                enc_key=params["enc_key"],
                insert_mode=params["insert_mode"],
                stego_key=params["stego_key"],
                frame_sel=params["frame_sel"],
                frame_n=int(params["frame_n"]) if params["frame_n"].isdigit() else 50,
                r_bits=params["r_bits"],
                g_bits=params["g_bits"],
                b_bits=params["b_bits"],
                progress_cb=self._on_progress,
                log_cb=self._log,
            )
            self.after(0, self._on_embed_done, result)
        except Exception as e:
            self.after(0, self._on_embed_error, str(e))

    def _on_progress(self, pct):
        self.after(0, lambda: self._progress.set(pct / 100))

    def _on_embed_done(self, result):
        self._embed_btn.configure(state="normal", text="Embed Message")
        self.status_var.set("Done")
        self._progress.set(1.0)
        if result:
            self._psnr_var.set(f"{result.get('psnr', 0):.2f}")
            self._mse_var.set(f"{result.get('mse', 0):.4f}")
            self._frm_var.set(str(result.get("frames", "—")))
            self._log("Embedding complete!")
            self._log(f"PSNR: {result.get('psnr',0):.2f} dB  MSE: {result.get('mse',0):.4f}")

            out = result.get("output", "")
            self._log(f"Saved → {out}")

            cover_frame = result.get("cover_frame")
            stego_frame = result.get("stego_frame")
            if cover_frame is not None and stego_frame is not None:
                self.draw_histogram(cover_frame, stego_frame)

            messagebox.showinfo(
                "Success",
                f"Stego-video saved to:\n{out}"
            )

    def _on_embed_error(self, msg):
        self._embed_btn.configure(state="normal", text="Embed Message")
        self.status_var.set("Error")
        self._progress.set(0)
        self._log(f"Error: {msg}")
        messagebox.showerror("Embed failed", msg)

    # Public Getters
    def get_cover_path(self):  return self._cover_path.get()
    def get_output_path(self): return self._output_path.get()