import customtkinter as ctk

class TicTacToeWindow(ctk.CTkToplevel):
    def __init__(self, parent, my_symbol, opponent, send_move_callback, on_close_callback):
        super().__init__(parent)
        self.my_symbol = my_symbol
        self.opponent = opponent
        self.send_move = send_move_callback
        self.on_close_cb = on_close_callback
        self.board = [['']*3 for _ in range(3)]
        self.turn = 'X'
        self.game_over = False
        self.buttons = [[None]*3 for _ in range(3)]
        self.title("Крестики-нолики")
        self.geometry("300x350")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        self._update_status()

    def _build_ui(self):
        self.status_label = ctk.CTkLabel(self, text="", font=("Inter", 14))
        self.status_label.pack(pady=10)
        frame = ctk.CTkFrame(self)
        frame.pack(pady=10)
        for r in range(3):
            for c in range(3):
                btn = ctk.CTkButton(frame, text="", width=60, height=60,
                                    font=("Segoe UI Emoji", 24),
                                    command=lambda row=r, col=c: self._on_cell_click(row, col))
                btn.grid(row=r, column=c, padx=2, pady=2)
                self.buttons[r][c] = btn
        self.reset_btn = ctk.CTkButton(self, text="Сдаться", command=self._surrender)
        self.reset_btn.pack(pady=10)

    def _update_status(self):
        if self.game_over: return
        if self.turn == self.my_symbol:
            self.status_label.configure(text="Ваш ход")
        else:
            self.status_label.configure(text=f"Ход {self.opponent}")

    def _on_cell_click(self, row, col):
        if self.game_over or self.turn != self.my_symbol or self.board[row][col] != '':
            return
        self.board[row][col] = self.my_symbol
        self.buttons[row][col].configure(text=self.my_symbol, state="disabled")
        self.send_move(row, col, surrender=False)
        if self._check_win(self.my_symbol):
            self._end_game(f"Вы выиграли!")
            return
        elif self._check_draw():
            self._end_game("Ничья!")
            return
        self.turn = 'O' if self.turn == 'X' else 'X'
        self._update_status()

    def opponent_move(self, row, col, symbol):
        if self.game_over or self.board[row][col] != '':
            return
        self.board[row][col] = symbol
        self.buttons[row][col].configure(text=symbol, state="disabled")
        if self._check_win(symbol):
            self._end_game(f"{self.opponent} выиграл!")
            return
        elif self._check_draw():
            self._end_game("Ничья!")
            return
        self.turn = 'O' if self.turn == 'X' else 'X'
        self._update_status()

    def _check_win(self, symbol):
        for i in range(3):
            if all(self.board[i][j] == symbol for j in range(3)): return True
            if all(self.board[j][i] == symbol for j in range(3)): return True
        if all(self.board[i][i] == symbol for i in range(3)): return True
        if all(self.board[i][2-i] == symbol for i in range(3)): return True
        return False

    def _check_draw(self):
        return all(self.board[i][j] != '' for i in range(3) for j in range(3))

    def _end_game(self, message):
        self.game_over = True
        self.status_label.configure(text=message)
        for r in range(3):
            for c in range(3):
                self.buttons[r][c].configure(state="disabled")
        self.after(3000, self._on_close)

    def _surrender(self):
        if not self.game_over:
            self.send_move(None, None, surrender=True)
            self._end_game("Вы сдались. Победа соперника.")

    def _on_close(self):
        self.on_close_cb()
        self.destroy()