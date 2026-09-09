"""Peer identity verification dialog."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox


def ask_trust_peer(parent: tk.Misc, fingerprint: str, peer_name: str = "Собеседник") -> bool:
    """Ask the user whether to trust a peer identity fingerprint."""
    dialog = tk.Toplevel(parent)
    dialog.title("Проверка безопасности")
    dialog.geometry("520x300")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    result = {"trusted": False}

    tk.Label(dialog, text="🔐 Проверка безопасности", font=("TkDefaultFont", 18, "bold")).pack(pady=(20, 10))
    tk.Label(
        dialog,
        text=f"{peer_name} использует новый ключ устройства.\n\nСверьте этот отпечаток с собеседником другим каналом связи:",
        justify="center",
    ).pack(pady=5)
    tk.Label(
        dialog,
        text=fingerprint,
        font=("TkFixedFont", 12, "bold"),
        wraplength=470,
        justify="center",
    ).pack(pady=12)
    tk.Label(
        dialog,
        text="Не подтверждайте ключ, если отпечатки не совпадают.",
        fg="red",
    ).pack(pady=3)

    buttons = tk.Frame(dialog)
    buttons.pack(pady=15)

    def trust() -> None:
        result["trusted"] = True
        dialog.destroy()

    def reject() -> None:
        dialog.destroy()

    tk.Button(buttons, text="Доверять", width=16, command=trust).pack(side="left", padx=8)
    tk.Button(buttons, text="Отклонить", width=16, command=reject).pack(side="left", padx=8)
    dialog.protocol("WM_DELETE_WINDOW", reject)
    dialog.wait_window()
    return result["trusted"]
