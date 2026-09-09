"""
Модульные тесты для games.py - игровая логика Крестики-нолики.
GUI-зависимости замоканы через tests/mock_gui.py.
"""
import unittest
from unittest.mock import MagicMock

from tests.mock_gui import _install_gui_mocks
_install_gui_mocks()

import games  # noqa: E402


class TicTacToeGameLogicTests(unittest.TestCase):
    def _make_game(self, my_symbol='X', opponent='O'):
        send_move_cb = MagicMock()
        on_close_cb = MagicMock()
        game = games.TicTacToeWindow.__new__(games.TicTacToeWindow)
        game.my_symbol = my_symbol
        game.opponent = opponent
        game.send_move = send_move_cb
        game.on_close_cb = on_close_cb
        game.board = [[''] * 3 for _ in range(3)]
        game.turn = 'X'
        game.game_over = False
        game.buttons = [[MagicMock() for _ in range(3)] for _ in range(3)]
        game.status_label = MagicMock()
        game.after = MagicMock()
        return game, send_move_cb

    def test_check_win_first_row(self):
        game, _ = self._make_game()
        game.board = [['X', 'X', 'X'], ['', '', ''], ['', '', '']]
        self.assertTrue(game._check_win('X'))

    def test_check_win_second_row(self):
        game, _ = self._make_game()
        game.board = [['', '', ''], ['O', 'O', 'O'], ['', '', '']]
        self.assertTrue(game._check_win('O'))

    def test_check_win_third_row(self):
        game, _ = self._make_game()
        game.board = [['', '', ''], ['', '', ''], ['X', 'X', 'X']]
        self.assertTrue(game._check_win('X'))

    def test_check_win_first_col(self):
        game, _ = self._make_game()
        game.board = [['X', '', ''], ['X', '', ''], ['X', '', '']]
        self.assertTrue(game._check_win('X'))

    def test_check_win_second_col(self):
        game, _ = self._make_game()
        game.board = [['', 'O', ''], ['', 'O', ''], ['', 'O', '']]
        self.assertTrue(game._check_win('O'))

    def test_check_win_third_col(self):
        game, _ = self._make_game()
        game.board = [['', '', 'X'], ['', '', 'X'], ['', '', 'X']]
        self.assertTrue(game._check_win('X'))

    def test_check_win_main_diagonal(self):
        game, _ = self._make_game()
        game.board = [['X', '', ''], ['', 'X', ''], ['', '', 'X']]
        self.assertTrue(game._check_win('X'))

    def test_check_win_anti_diagonal(self):
        game, _ = self._make_game()
        game.board = [['', '', 'O'], ['', 'O', ''], ['O', '', '']]
        self.assertTrue(game._check_win('O'))

    def test_check_win_no_win(self):
        game, _ = self._make_game()
        self.assertFalse(game._check_win('X'))

    def test_check_win_opponent_does_not_win(self):
        game, _ = self._make_game()
        game.board = [['X', 'X', ''], ['', 'O', ''], ['', '', '']]
        self.assertFalse(game._check_win('O'))
        self.assertFalse(game._check_win('X'))

    def test_check_draw_empty_board(self):
        game, _ = self._make_game()
        self.assertFalse(game._check_draw())

    def test_check_draw_partial_board(self):
        game, _ = self._make_game()
        game.board[0][0] = 'X'
        game.board[0][1] = 'O'
        self.assertFalse(game._check_draw())

    def test_check_draw_full_board_no_winner(self):
        game, _ = self._make_game()
        game.board = [['X', 'O', 'X'], ['X', 'O', 'O'], ['O', 'X', 'X']]
        self.assertTrue(game._check_draw())

    def test_on_cell_click_places_move(self):
        game, _ = self._make_game(my_symbol='X')
        game._on_cell_click(0, 0)
        self.assertEqual(game.board[0][0], 'X')
        game.buttons[0][0].configure.assert_any_call(text='X', state='disabled')

    def test_on_cell_click_switches_turn(self):
        game, _ = self._make_game(my_symbol='X')
        game._on_cell_click(0, 0)
        self.assertEqual(game.turn, 'O')

    def test_on_cell_click_occupied_cell_ignored(self):
        game, send = self._make_game(my_symbol='X')
        game._on_cell_click(0, 0)
        send.reset_mock()
        game._on_cell_click(0, 0)
        send.assert_not_called()

    def test_on_cell_click_wins_game(self):
        game, send = self._make_game(my_symbol='X')
        game.board = [['X', 'X', ''], ['', '', ''], ['', '', '']]
        game._on_cell_click(0, 2)
        self.assertTrue(game.game_over)
        send.assert_called_once_with(0, 2, surrender=False)

    def test_on_cell_click_draw(self):
        game, _ = self._make_game(my_symbol='X')
        game.board = [['X', 'O', 'X'], ['X', 'O', 'O'], ['O', 'X', '']]
        game.turn = 'X'
        game._on_cell_click(2, 2)
        self.assertTrue(game.game_over)

    def test_on_cell_click_not_your_turn(self):
        game, send = self._make_game(my_symbol='X')
        game.turn = 'O'
        game._on_cell_click(0, 0)
        self.assertEqual(game.board[0][0], '')
        send.assert_not_called()

    def test_on_cell_click_game_over_ignored(self):
        game, send = self._make_game(my_symbol='X')
        game.game_over = True
        game._on_cell_click(0, 0)
        self.assertEqual(game.board[0][0], '')
        send.assert_not_called()

    def test_on_cell_click_calls_send_move_with_coordinates(self):
        game, send = self._make_game(my_symbol='X')
        game._on_cell_click(1, 2)
        send.assert_called_once_with(1, 2, surrender=False)

    def test_opponent_move_places_symbol(self):
        game, _ = self._make_game(my_symbol='X')
        game.opponent_move(1, 1, 'O')
        self.assertEqual(game.board[1][1], 'O')

    def test_opponent_move_switches_turn(self):
        game, _ = self._make_game(my_symbol='X')
        game.turn = 'O'
        game.opponent_move(0, 0, 'O')
        self.assertEqual(game.turn, 'X')

    def test_opponent_move_wins(self):
        game, _ = self._make_game(my_symbol='X')
        game.board = [['O', 'O', ''], ['', '', ''], ['', '', '']]
        game.opponent_move(0, 2, 'O')
        self.assertTrue(game.game_over)

    def test_opponent_move_draw(self):
        game, _ = self._make_game(my_symbol='X')
        game.board = [['X', 'O', 'X'], ['X', 'O', 'O'], ['O', 'X', '']]
        game.opponent_move(2, 2, 'O')
        self.assertTrue(game.game_over)

    def test_opponent_move_occupied_cell_ignored(self):
        game, _ = self._make_game(my_symbol='X')
        game.board[0][0] = 'X'
        game.opponent_move(0, 0, 'O')
        self.assertEqual(game.board[0][0], 'X')

    def test_opponent_move_game_over_ignored(self):
        game, _ = self._make_game(my_symbol='X')
        game.game_over = True
        game.opponent_move(0, 0, 'O')
        self.assertEqual(game.board[0][0], '')

    def test_opponent_move_symbol_from_param(self):
        game, _ = self._make_game(my_symbol='O')
        game.opponent_move(0, 0, 'X')
        self.assertEqual(game.board[0][0], 'X')


    def test_surrender_calls_send_move(self):
        game, send = self._make_game(my_symbol='X')
        game._surrender()
        send.assert_called_once_with(None, None, surrender=True)

    def test_surrender_ends_game(self):
        game, _ = self._make_game(my_symbol='X')
        game._surrender()
        self.assertTrue(game.game_over)

    def test_surrender_when_already_over(self):
        game, send = self._make_game(my_symbol='X')
        game.game_over = True
        game._surrender()
        send.assert_not_called()

    def test_end_game_disables_all_buttons(self):
        game, _ = self._make_game()
        game._end_game('Test')
        for r in range(3):
            for c in range(3):
                game.buttons[r][c].configure.assert_any_call(state='disabled')

    def test_end_game_sets_game_over(self):
        game, _ = self._make_game()
        game._end_game('Game over')
        self.assertTrue(game.game_over)

    def test_end_game_updates_status(self):
        game, _ = self._make_game()
        game._end_game('Win')
        game.status_label.configure.assert_called_with(text='Win')

    def test_full_game_scenario(self):
        game, send = self._make_game(my_symbol='X')
        game._on_cell_click(1, 1)
        self.assertFalse(game.game_over)
        game.opponent_move(0, 1, 'O')
        self.assertFalse(game.game_over)
        game._on_cell_click(0, 0)
        self.assertFalse(game.game_over)
        game.opponent_move(1, 2, 'O')
        self.assertFalse(game.game_over)
        game._on_cell_click(2, 2)
        self.assertTrue(game.game_over)


class TicTacToeInitTests(unittest.TestCase):
    def _make_game(self, my_symbol='X', opponent='O'):
        send_move_cb = MagicMock()
        on_close_cb = MagicMock()
        game = games.TicTacToeWindow.__new__(games.TicTacToeWindow)
        game.my_symbol = my_symbol
        game.opponent = opponent
        game.send_move = send_move_cb
        game.on_close_cb = on_close_cb
        game.board = [[''] * 3 for _ in range(3)]
        game.turn = 'X'
        game.game_over = False
        game.buttons = [[MagicMock() for _ in range(3)] for _ in range(3)]
        game.status_label = MagicMock()
        game.after = MagicMock()
        return game, send_move_cb

    def test_initial_board_empty(self):
        game, _ = self._make_game()
        for r in range(3):
            for c in range(3):
                self.assertEqual(game.board[r][c], '')

    def test_initial_turn_is_x(self):
        game, _ = self._make_game()
        self.assertEqual(game.turn, 'X')

    def test_initial_game_not_over(self):
        game, _ = self._make_game()
        self.assertFalse(game.game_over)

    def test_update_status_shows_your_turn(self):
        game, _ = self._make_game(my_symbol='X')
        game._update_status()
        game.status_label.configure.assert_called_with(text='Ваш ход')

    def test_update_status_shows_opponent_turn(self):
        game, _ = self._make_game(my_symbol='X')
        game.turn = 'O'
        game._update_status()
        game.status_label.configure.assert_called()

    def test_update_status_when_game_over_does_nothing(self):
        game, _ = self._make_game()
        game.game_over = True
        game._update_status()
        game.status_label.configure.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
