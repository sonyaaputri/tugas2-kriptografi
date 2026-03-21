import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar, IntVar
import threading
import os

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


class CompareTab(ctk.CTkFrame):
    """Tab perbandingan cover video vs stego-video."""

    def __init__(self, parent, colors, status_var):
        super().__init__(parent, corner_radius=0, fg_color=colors["bg"])
        self.C = colors
        self.status_var = status_var
        self._cover_path = StringVar()
        self._stego_path = StringVar()
        self._frame_idx  = IntVar(value=1)
        self._max_frames = 1
        self._cover_frames = None
        self._stego_frames = None
        self._psnr_list    = []
        self._mse_list     = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)
        self._build_controls()
        self._build_charts()

    def _c(self, k): return self.C[k]

    def _section_label(self, parent, text):
        ctk.CTkLabel(parent, text=text.upper(), text_color=self._c("muted"),
                     font=ctk.CTkFont(size=9), fg_color="transparent",
                     anchor="w").pack(fill="x", padx=4, pady=(14, 0))
        ctk.CTkFrame(parent, height=1, fg_color=self._c("border"),
                     corner_radius=0).pack(fill="x", pady=(2, 8))

    def _field_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, text_color=self._c("muted"),
                     font=ctk.CTkFont(size=11), fg_color="transparent",
                     anchor="w").pack(fill="x", padx=4, pady=(4, 1))

    def _build_controls(self):
        left = ctk.CTkScrollableFrame(self, corner_radius=8,
                                       fg_color=self._c("surface"),
                                       border_width=1, border_color=self._c("border"))
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.grid_columnconfigure(0, weight=1)

        self._section_label(left, "Videos")
        for label, var, cb in [
            ("Cover Video (AVI)", self._cover_path, self._browse_cover),
            ("Stego-Video (AVI)", self._stego_path, self._browse_stego),
        ]:
            self._field_label(left, label)
            row = ctk.CTkFrame(left, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=(0, 4))
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkEntry(row, textvariable=var, state="readonly",
                          fg_color=self._c("surface2"), border_color=self._c("border"),
                          text_color=self._c("text"), font=ctk.CTkFont(size=10),
                          corner_radius=6, height=32).grid(row=0, column=0, sticky="ew", padx=(0, 6))
            ctk.CTkButton(row, text="…", width=36, height=32,
                           fg_color=self._c("surface3"), text_color=self._c("text"),
                           hover_color=self._c("accent"), font=ctk.CTkFont(size=12),
                           corner_radius=6, command=cb).grid(row=0, column=1)
            
        # Analyze Button
        self._analyze_btn = ctk.CTkButton(
            left, text="Analyze Videos", height=30,
            fg_color=self._c("accent"), hover_color=self._c("accent_hover"),
            text_color="white", font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8, command=self._run_analysis,
        )
        self._analyze_btn.pack(fill="x", padx=4, pady=(15, 12))
        
        # Frame Navigator
        self._section_label(left, "Frame Navigator")
        self._frame_info = ctk.CTkLabel(left, text="Frame: 1 / —",
                                         text_color=self._c("text"),
                                         font=ctk.CTkFont(size=13, weight="bold"),
                                         fg_color="transparent", anchor="w")
        self._frame_info.pack(fill="x", padx=4, pady=(0, 6))

        self._frame_slider = ctk.CTkSlider(left, from_=1, to=2,
                                            variable=self._frame_idx,
                                            command=self._on_frame_change,
                                            progress_color=self._c("accent"),
                                            button_color=self._c("accent"),
                                            button_hover_color=self._c("accent2"),
                                            fg_color=self._c("surface2"))
        self._frame_slider.pack(fill="x", padx=4, pady=(0, 4))

        # nav = ctk.CTkFrame(left, fg_color="transparent")
        # nav.pack(fill="x", padx=4, pady=(2, 8))
        # nav.grid_columnconfigure((0, 1), weight=1)
        # ctk.CTkButton(nav, text="◀ Prev", height=32,
        #                fg_color=self._c("surface3"), text_color=self._c("text"),
        #                hover_color=self._c("surface2"), font=ctk.CTkFont(size=11),
        #                corner_radius=6,
        #                command=lambda: self._step_frame(-1)).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        # ctk.CTkButton(nav, text="Next ▶", height=32,
        #                fg_color=self._c("surface3"), text_color=self._c("text"),
        #                hover_color=self._c("surface2"), font=ctk.CTkFont(size=11),
        #                corner_radius=6,
        #                command=lambda: self._step_frame(1)).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        # Frame Matrics
        self._section_label(left, "Frame Metrics")
        self._fm_psnr = StringVar(value="PSNR: —")
        self._fm_mse  = StringVar(value="MSE:  —")
        for var, color in ((self._fm_psnr, self._c("green")),
                           (self._fm_mse,  self._c("accent"))):
            ctk.CTkLabel(left, textvariable=var, text_color=color,
                          font=ctk.CTkFont(size=13, weight="bold"),
                          fg_color="transparent", anchor="w").pack(fill="x", padx=4, pady=2)

        # Video Sumary
        self._section_label(left, "Video Summary")
        mg = ctk.CTkFrame(left, fg_color="transparent")
        mg.pack(fill="x", padx=4)
        mg.grid_columnconfigure((0, 1), weight=1)
        self._avg_psnr_var = StringVar(value="—")
        self._avg_mse_var  = StringVar(value="—")
        self._min_psnr_var = StringVar(value="—")
        self._max_mse_var  = StringVar(value="—")
        for i, (lbl, var, color) in enumerate([
            ("Avg PSNR", self._avg_psnr_var, self._c("green")),
            ("Avg MSE",  self._avg_mse_var,  self._c("accent")),
            ("Min PSNR", self._min_psnr_var, self._c("amber")),
            ("Max MSE",  self._max_mse_var,  self._c("red")),
        ]):
            card = ctk.CTkFrame(mg, fg_color=self._c("surface2"), corner_radius=8,
                                 border_width=1, border_color=self._c("border"))
            card.grid(row=i//2, column=i%2, padx=3, pady=3, sticky="ew", ipadx=6, ipady=5)
            ctk.CTkLabel(card, text=lbl, text_color=self._c("muted"),
                          font=ctk.CTkFont(size=9), fg_color="transparent",
                          anchor="w").pack(anchor="w")
            ctk.CTkLabel(card, textvariable=var, text_color=color,
                          font=ctk.CTkFont(size=15, weight="bold"),
                          fg_color="transparent", anchor="w").pack(anchor="w")

        ctk.CTkFrame(left, fg_color="transparent", height=16).pack()

        # ctk.CTkButton(left, text="Export Histogram PNG", height=34,
        #                fg_color=self._c("surface3"), text_color=self._c("muted"),
        #                hover_color=self._c("surface2"), font=ctk.CTkFont(size=11),
        #                corner_radius=6,
        #                command=self._export_hist_png).pack(fill="x", padx=4, pady=(0, 4))
        # ctk.CTkButton(left, text="Export Metrics CSV", height=34,
        #                fg_color=self._c("surface3"), text_color=self._c("muted"),
        #                hover_color=self._c("surface2"), font=ctk.CTkFont(size=11),
        #                corner_radius=6,
        #                command=self._export_csv).pack(fill="x", padx=4)

    def _build_charts(self):
        right = ctk.CTkFrame(self, corner_radius=0, fg_color=self._c("bg"))
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_rowconfigure(0, weight=2)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        if not HAS_MPL:
            ctk.CTkLabel(right, text="matplotlib not installed.\nRun: pip install matplotlib",
                        text_color=self._c("muted"), font=ctk.CTkFont(size=12),
                        fg_color="transparent").grid(row=0, column=0)
            return

        hist_frame = ctk.CTkFrame(right, corner_radius=8,
                                fg_color=self._c("surface"),
                                border_width=1, border_color=self._c("border"))
        hist_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 6))

        top_row = ctk.CTkFrame(hist_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(10, 0))
        ctk.CTkLabel(top_row, text="COLOR HISTOGRAM", text_color=self._c("muted"),
                    font=ctk.CTkFont(size=9), fg_color="transparent").pack(side="left")
        self._hist_frame_lbl = ctk.CTkLabel(top_row, text="", text_color=self._c("accent"),
                                            font=ctk.CTkFont(size=10), fg_color="transparent")
        self._hist_frame_lbl.pack(side="left", padx=(8, 0))

        # Tombol download histogram di kanan atas
        ctk.CTkButton(top_row, text="Export Histogram PNG", width=70, height=24,
                    fg_color=self._c("surface3"), text_color=self._c("muted"),
                    hover_color=self._c("accent"), font=ctk.CTkFont(size=10),
                    corner_radius=6, command=self._export_hist_png).pack(side="right")

        self._hist_fig = Figure(figsize=(6, 3.2), dpi=96, facecolor=self._c("surface"))
        self._hist_fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.12, wspace=0.3)
        self._hist_axes = [self._hist_fig.add_subplot(1, 3, i+1) for i in range(3)]
        self._style_axes(self._hist_axes)
        self._hist_canvas = FigureCanvasTkAgg(self._hist_fig, master=hist_frame)
        self._hist_canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        psnr_frame = ctk.CTkFrame(right, corner_radius=8,
                                fg_color=self._c("surface"),
                                border_width=1, border_color=self._c("border"))
        psnr_frame.grid(row=1, column=0, sticky="nsew")

        psnr_top = ctk.CTkFrame(psnr_frame, fg_color="transparent")
        psnr_top.pack(fill="x", padx=14, pady=(10, 0))
        ctk.CTkLabel(psnr_top, text="PSNR PER FRAME", text_color=self._c("muted"),
                    font=ctk.CTkFont(size=9), fg_color="transparent").pack(side="left")

        # Tombol download PSNR chart di kanan atas
        ctk.CTkButton(psnr_top, text= "Export Metrics CSV", width=70, height=24,
                    fg_color=self._c("surface3"), text_color=self._c("muted"),
                    hover_color=self._c("accent"), font=ctk.CTkFont(size=10),
                    corner_radius=6, command=self._export_csv).pack(side="right")

        self._psnr_fig = Figure(figsize=(6, 1.6), dpi=96, facecolor=self._c("surface"))
        self._psnr_fig.subplots_adjust(left=0.06, right=0.98, top=0.85, bottom=0.18)
        self._psnr_ax = self._psnr_fig.add_subplot(1, 1, 1)
        self._style_axes([self._psnr_ax])
        self._psnr_canvas = FigureCanvasTkAgg(self._psnr_fig, master=psnr_frame)
        self._psnr_canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=(0, 6))

    def _style_axes(self, axes):
        for ax in axes:
            ax.set_facecolor(self._c("surface2"))
            ax.tick_params(colors=self._c("muted"), labelsize=7)
            for spine in ax.spines.values():
                spine.set_edgecolor(self._c("border"))
            ax.title.set_color(self._c("text"))
            ax.title.set_fontsize(9)
            ax.xaxis.label.set_color(self._c("muted"))
            ax.yaxis.label.set_color(self._c("muted"))

    def _browse_cover(self):
        path = filedialog.askopenfilename(title="Select cover video",
                                         filetypes=[("Video files", "*.avi *.mp4"),
                                                    ("AVI files", "*.avi"),
                                                    ("MP4 files", "*.mp4"),
                                                    ("All files", "*.*"),
                                                ])
        if path:
            self._cover_path.set(path)
            self._cover_frames = None

    def _browse_stego(self):
        path = filedialog.askopenfilename(title="Select stego-video",
                                         filetypes=[("Video files", "*.avi *.mp4"),
                                                    ("AVI files", "*.avi"),
                                                    ("MP4 files", "*.mp4"),
                                                    ("All files", "*.*"),
                                                ])
        if path:
            self._stego_path.set(path)
            self._stego_frames = None

    def _on_frame_change(self, _=None):
        idx = int(self._frame_idx.get()) - 1
        self._frame_info.configure(text=f"Frame: {idx+1} / {self._max_frames}")
        if (self._cover_frames is not None and self._stego_frames is not None
                and idx < len(self._cover_frames)):
            self._draw_histograms(idx)
            if self._psnr_list:
                self._fm_psnr.set(f"PSNR: {self._psnr_list[idx]:.2f} dB")
                self._fm_mse.set(f"MSE:  {self._mse_list[idx]:.4f}")

    def _step_frame(self, delta):
        new = max(1, min(self._max_frames, self._frame_idx.get() + delta))
        self._frame_idx.set(new)
        self._on_frame_change()

    def _run_analysis(self):
        if not self._cover_path.get() or not self._stego_path.get():
            messagebox.showwarning("Missing input", "Please select both cover and stego-videos.")
            return
        self._analyze_btn.configure(state="disabled", text="Analyzing…")
        self.status_var.set("Analyzing…")
        threading.Thread(target=self._analysis_worker, daemon=True).start()

    def _analysis_worker(self):
        try:
            from core.video_handler import load_frames
            from utils.quality import compute_psnr_mse_frames
            self.after(0, lambda: self.status_var.set("Loading cover…"))
            cover_frames = load_frames(self._cover_path.get())
            self.after(0, lambda: self.status_var.set("Loading stego…"))
            stego_frames = load_frames(self._stego_path.get())
            n = min(len(cover_frames), len(stego_frames))
            psnr_list, mse_list = compute_psnr_mse_frames(cover_frames[:n], stego_frames[:n])
            self.after(0, self._on_analysis_done, cover_frames[:n], stego_frames[:n], psnr_list, mse_list)
        except Exception as e:
            self.after(0, self._on_analysis_error, str(e))

    def _on_analysis_done(self, cover_frames, stego_frames, psnr_list, mse_list):
        self._cover_frames = cover_frames
        self._stego_frames = stego_frames
        self._psnr_list    = psnr_list
        self._mse_list     = mse_list
        self._max_frames   = len(cover_frames)
        self._frame_slider.configure(to=self._max_frames)
        self._frame_idx.set(1)
        if psnr_list:
            finite_psnr = [p for p in psnr_list if p != float("inf")]
            if finite_psnr:
                self._avg_psnr_var.set(f"{sum(finite_psnr)/len(finite_psnr):.2f}")
                self._min_psnr_var.set(f"{min(finite_psnr):.2f}")
            else:
                self._avg_psnr_var.set("inf")
                self._min_psnr_var.set("inf")
        if mse_list:
            self._avg_mse_var.set(f"{sum(mse_list)/len(mse_list):.4f}")
            self._max_mse_var.set(f"{max(mse_list):.4f}")
        self._draw_histograms(0)
        self._draw_psnr_chart()
        self._analyze_btn.configure(state="normal", text="Analyze Videos")
        self.status_var.set("Done")
        self._on_frame_change()

    def _on_analysis_error(self, msg):
        self._analyze_btn.configure(state="normal", text="Analyze Videos")
        self.status_var.set("Error")
        messagebox.showerror("Analysis failed", msg)

    def _draw_histograms(self, frame_idx):
        if not HAS_MPL:
            return
        try:
            cover = self._cover_frames[frame_idx]
            stego = self._stego_frames[frame_idx]
            channel_data = [
                ("#d94f4f", "Red",   0),
                ("#0d9e6e", "Green", 1),
                ("#2563eb", "Blue",  2),
            ]
            for ax, (color, title, ch) in zip(self._hist_axes, channel_data):
                ax.clear()
                self._style_axes([ax])
                ax.set_title(title, fontsize=9)
                ax.hist(cover[:, :, ch].flatten(), bins=64, range=(0, 256),
                        color=color, alpha=0.7, label="Cover", linewidth=0)
                ax.hist(stego[:, :, ch].flatten(), bins=64, range=(0, 256),
                        color=color, alpha=0.35, label="Stego", linewidth=0)
                ax.legend(fontsize=7, facecolor=self._c("surface2"),
                           edgecolor=self._c("border"), labelcolor=self._c("muted"))
            self._hist_frame_lbl.configure(text=f"Frame #{frame_idx + 1}")
            self._hist_fig.canvas.draw_idle()
        except Exception:
            pass

    def _draw_psnr_chart(self):
        if not HAS_MPL or not self._psnr_list:
            return

        try:
            import math

            ax = self._psnr_ax
            ax.clear()
            self._style_axes([ax])

            frames = list(range(1, len(self._psnr_list) + 1))

            # hanya untuk plotting: inf -> nan
            plot_psnr = [
                float("nan") if (p == float("inf") or math.isinf(p)) else p
                for p in self._psnr_list
            ]

            # nilai finite untuk batas sumbu / garis rata-rata
            finite_psnr = [p for p in self._psnr_list if not math.isinf(p)]

            # plot garis/titik
            ax.plot(
                frames,
                plot_psnr,
                linestyle="-",
                marker="o",
                markersize=4,
            )

            # atur batas dan avg
            if finite_psnr:
                avg = sum(finite_psnr) / len(finite_psnr)
                ymin = min(finite_psnr) - 1
                ymax = max(finite_psnr) + 1

                ax.set_ylim(ymin, ymax)
                ax.axhline(avg, linestyle="--", linewidth=1.0)

            ax.set_xlabel("Frame")
            ax.set_ylabel("dB")
            ax.set_title("PSNR per Frame")

            self._psnr_fig.canvas.draw_idle()

        except Exception:
            pass

    def _export_hist_png(self):
        if not HAS_MPL:
            messagebox.showwarning("Not available", "matplotlib is required.")
            return
        if self._cover_frames is None:
            messagebox.showwarning("No data", "Run analysis first.")
            return
        path = filedialog.asksaveasfilename(title="Save histogram", defaultextension=".png",
                                             filetypes=[("PNG image", "*.png")])
        if path:
            self._hist_fig.savefig(path, facecolor=self._c("surface"), dpi=150, bbox_inches="tight")
            messagebox.showinfo("Saved", f"Histogram saved to:\n{path}")

    def _export_csv(self):
        if not self._psnr_list:
            messagebox.showwarning("No data", "Run analysis first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save metrics CSV",
            defaultextension=".csv",
            filetypes=[("CSV file", "*.csv")]
        )
        if path:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write("frame,psnr_db,mse\n")
                for i, (p, m) in enumerate(zip(self._psnr_list, self._mse_list), 1):
                    psnr_txt = "INF" if p == float("inf") else f"{p:.4f}"
                    f.write(f"{i},{psnr_txt},{m:.6f}\n")
            messagebox.showinfo("Saved", f"Metrics CSV saved to:\n{path}")

    def _export_psnr_png(self):
        if not HAS_MPL:
            messagebox.showwarning("Not available", "matplotlib is required.")
            return
        if not self._psnr_list:
            messagebox.showwarning("No data", "Run analysis first.")
            return
        path = filedialog.asksaveasfilename(title="Save PSNR chart", defaultextension=".png",
                                            filetypes=[("PNG image", "*.png")])
        if path:
            self._psnr_fig.savefig(path, facecolor=self._c("surface"), dpi=150, bbox_inches="tight")
            messagebox.showinfo("Saved", f"PSNR chart saved to:\n{path}")