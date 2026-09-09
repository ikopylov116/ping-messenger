"""
Скрипт запуска модульных тестов для проекта PING! Messenger.

Использование:
    python run_tests.py             # запустить все тесты
    python run_tests.py -v          # подробный вывод
    python run_tests.py games       # только тесты игр
    python run_tests.py ping        # только тесты мессенджера
"""
import sys
import os
import unittest


def run_tests(test_filter=None):
    """Запускает тесты и возвращает результат."""
    # Добавляем корень проекта в PYTHONPATH
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    loader = unittest.TestLoader()

    if test_filter:
        if test_filter == 'games':
            suite = loader.loadTestsFromName('tests.test_games')
        elif test_filter == 'ping':
            suite = loader.loadTestsFromName('tests.test_ping')
        else:
            suite = loader.discover('tests', pattern='test_*.py')
    else:
        suite = loader.discover('tests', pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    test_filter = sys.argv[1] if len(sys.argv) > 1 else None
    result = run_tests(test_filter)
    sys.exit(0 if result.wasSuccessful() else 1)
