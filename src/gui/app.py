import customtkinter as ctk
from gui.embed_tab import EmbedTab
from gui.extract_tab import ExtractTab
from gui.compare_tab import CompareTab

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

C = {
    "bg":       "#f5f5f7",
    "surface":  "#ffffff",
    "surface2": "#f0f0f2",
    "surface3": "#e4e4e8",
    "border":   "#d0d0d8",
    "accent":   "#5b4fff",
    "accent2":  "#7c6fff",
    "accent_hover": "#4a3fee",
    "text":     "#1a1a2e",
    "muted":    "#6b6b80",
    "green":    "#0d9e6e",
    "red":      "#d94f4f",
    "amber":    "#b87c00",
    "blue":     "#2563eb",
}

NAV_ITEMS = [
    ("embed",   "⬡  Embed"),
    ("extract", "⬢  Extract"),
    ("compare", "▣  Compare"),
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("StegoAVI")
        self.geometry("1160x700")
        self.minsize(960, 600)
        self.configure(fg_color=C["bg"])
        self._active = "embed"
        self._build()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=200, corner_radius=0,
                           fg_color=C["surface"],
                           border_width=1, border_color=C["border"])
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(10, weight=1)

        # Logo
        logo = ctk.CTkFrame(sb, fg_color=C["accent"], corner_radius=8, width=30, height=30)
        logo.grid(row=0, column=0, padx=(16, 8), pady=(20, 0), sticky="w")
        ctk.CTkLabel(logo, text="⬡", text_color="white",
                     font=ctk.CTkFont(size=16, weight="bold")).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(sb, text="StegoAVI",
                     text_color=C["text"],
                     font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="transparent").grid(row=0, column=1, padx=(0, 16), pady=(20, 0), sticky="w")

        ctk.CTkLabel(sb, text="MODE", text_color=C["muted"],
                     font=ctk.CTkFont(size=10),
                     fg_color="transparent").grid(row=1, column=0, columnspan=2,
                                                   padx=16, pady=(18, 4), sticky="w")

        self._nav_btns = {}
        for i, (key, label) in enumerate(NAV_ITEMS):
            btn = ctk.CTkButton(
                sb, text=label, anchor="w",
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                text_color=C["muted"],
                hover_color=C["surface2"],
                corner_radius=6,
                height=38,
                command=lambda k=key: self._switch_tab(k),
            )
            btn.grid(row=i+2, column=0, columnspan=2, padx=8, pady=2, sticky="ew")
            self._nav_btns[key] = btn

        # Bottom badge
        ctk.CTkLabel(sb, text="v1.0.0", text_color=C["muted"],
                     font=ctk.CTkFont(size=10),
                     fg_color="transparent").grid(row=11, column=0, columnspan=2,
                                                   padx=16, pady=(0, 4), sticky="w")
        ctk.CTkLabel(sb, text=" LSB · A5/1 ", text_color=C["accent"],
                     font=ctk.CTkFont(size=10),
                     fg_color=C["surface2"],
                     corner_radius=4).grid(row=12, column=0, columnspan=2,
                                            padx=16, pady=(0, 16), sticky="w")

        # # Activate default
        # self._switch_tab("embed")

    def _switch_tab(self, key):
        for k, btn in self._nav_btns.items():
            if k == key:
                btn.configure(fg_color=C["surface2"], text_color=C["accent"])
            else:
                btn.configure(fg_color="transparent", text_color=C["muted"])
        self._active = key
        titles = {
            "embed":   "Message Embedding",
            "extract": "Message Extraction",
            "compare": "Frame Comparison",
        }
        self._title_lbl.configure(text=titles[key])
        for k, frame in self._tab_frames.items():
            if k == key:
                frame.grid()
            else:
                frame.grid_remove()

    def _build_main(self):
        main = ctk.CTkFrame(self, corner_radius=0, fg_color=C["bg"])
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # Topbar
        topbar = ctk.CTkFrame(main, height=52, corner_radius=0,
                               fg_color=C["surface"],
                               border_width=1, border_color=C["border"])
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)

        self._title_lbl = ctk.CTkLabel(
            topbar, text="Message Embedding",
            text_color=C["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
        )
        self._title_lbl.grid(row=0, column=0, padx=20, pady=14, sticky="w")

        self._status_var = ctk.StringVar(value="Ready")
        ctk.CTkLabel(
            topbar, textvariable=self._status_var,
            text_color=C["green"],
            font=ctk.CTkFont(size=11),
            fg_color=C["surface2"],
            corner_radius=12,
        ).grid(row=0, column=1, padx=16, pady=14, sticky="e")

        # Tab container
        container = ctk.CTkFrame(main, corner_radius=0, fg_color=C["bg"])
        container.grid(row=1, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self._tab_frames = {}
        for key, cls in [("embed", EmbedTab), ("extract", ExtractTab), ("compare", CompareTab)]:
            frame = cls(container, C, self._status_var)
            frame.grid(row=0, column=0, sticky="nsew")
            self._tab_frames[key] = frame

        self._switch_tab("embed")


def run():
    app = App()
    app.mainloop()