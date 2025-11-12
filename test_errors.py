"""
Скрипт для демонстрации обработки ошибок
"""

import subprocess
import sys


def test_configurations():
    """Тестирование различных конфигураций"""

    print("=== Тест 1: Корректная конфигурация ===")
    result = subprocess.run([sys.executable, "dependency_visualizer.py", "config.json"],
                            capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print("Return code:", result.returncode)

    print("\n=== Тест 2: Неполная конфигурация ===")
    result = subprocess.run([sys.executable, "dependency_visualizer.py", "config_invalid.json"],
                            capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print("Return code:", result.returncode)

    print("\n=== Тест 3: Невалидный JSON ===")
    result = subprocess.run([sys.executable, "dependency_visualizer.py", "config_broken.json"],
                            capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print("Return code:", result.returncode)

    print("\n=== Тест 4: Несуществующий файл ===")
    result = subprocess.run([sys.executable, "dependency_visualizer.py", "nonexistent.json"],
                            capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print("Return code:", result.returncode)


if __name__ == "__main__":
    test_configurations()