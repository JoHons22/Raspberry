def show_touch_popup(
    title,
    message,
    popup_type="yesno",
    yes_text="Yes",
    no_text="No",
    ok_text="OK"
):
    """
    Touchscreen-friendly popup for the 800x480 display.

    The buttons are placed near the top of the popup so they do not get pushed
    off-screen by long instruction text.
    """
    result = {"value": None}

    popup = tk.Tk()
    popup.title(title)

    screen_width = popup.winfo_screenwidth()
    screen_height = popup.winfo_screenheight()

    popup_width = min(740, max(400, screen_width - 60))
    popup_height = min(340, max(280, screen_height - 120))

    popup_x = max(0, int((screen_width - popup_width) / 2))
    popup_y = max(0, int((screen_height - popup_height) / 2))

    popup.geometry(f"{popup_width}x{popup_height}+{popup_x}+{popup_y}")
    popup.resizable(False, False)
    popup.attributes("-topmost", True)

    style = ttk.Style()

    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("TButton", font=("Arial", 11), padding=(6, 8))
    style.configure("TLabel", font=("Arial", 10))

    main_frame = ttk.Frame(popup, padding=6)
    main_frame.pack(fill="both", expand=True)

    title_label = ttk.Label(
        main_frame,
        text=title,
        font=("Arial", 12, "bold"),
        anchor="center"
    )
    title_label.pack(fill="x", pady=(0, 4))

    # Buttons are intentionally placed near the top so they are always visible.
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill="x", pady=(0, 6))

    def close_with_value(value):
        result["value"] = value
        popup.quit()

    if popup_type == "yesno":
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        yes_button = ttk.Button(
            button_frame,
            text=yes_text,
            command=lambda: close_with_value(True)
        )
        yes_button.grid(row=0, column=0, sticky="ew", padx=(0, 4), ipady=8)

        no_button = ttk.Button(
            button_frame,
            text=no_text,
            command=lambda: close_with_value(False)
        )
        no_button.grid(row=0, column=1, sticky="ew", padx=(4, 0), ipady=8)

        popup.bind("<Return>", lambda event: close_with_value(True))
        popup.bind("<Escape>", lambda event: close_with_value(False))
        yes_button.focus_set()

    else:
        button_frame.columnconfigure(0, weight=1)

        ok_button = ttk.Button(
            button_frame,
            text=ok_text,
            command=lambda: close_with_value(True)
        )
        ok_button.grid(row=0, column=0, sticky="ew", padx=80, ipady=8)

        popup.bind("<Return>", lambda event: close_with_value(True))
        popup.bind("<Escape>", lambda event: close_with_value(True))
        ok_button.focus_set()

    text_frame = ttk.Frame(main_frame)
    text_frame.pack(fill="both", expand=True)

    message_text = tk.Text(
        text_frame,
        wrap="word",
        font=("Arial", 10),
        height=8,
        padx=6,
        pady=6
    )

    text_scrollbar = ttk.Scrollbar(
        text_frame,
        orient="vertical",
        command=message_text.yview
    )

    message_text.configure(yscrollcommand=text_scrollbar.set)
    message_text.insert("1.0", message)
    message_text.config(state="disabled")

    message_text.pack(side="left", fill="both", expand=True)
    text_scrollbar.pack(side="right", fill="y")

    def on_close():
        if popup_type == "yesno":
            close_with_value(False)
        else:
            close_with_value(True)

    popup.protocol("WM_DELETE_WINDOW", on_close)

    popup.update_idletasks()
    popup.lift()
    popup.focus_force()

    popup.mainloop()

    try:
        popup.destroy()
    except Exception:
        pass

    return result["value"]
