import json
import os
import sys
from typing import Dict, Any, List


class ConfigError(Exception):
    pass


class DependencyVisualizer:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации из JSON файла"""
        try:
            if not os.path.exists(self.config_path):
                raise ConfigError(f"Конфигурационный файл не найден: {self.config_path}")

            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            return self._validate_config(config)

        except json.JSONDecodeError as e:
            raise ConfigError(f"Ошибка парсинга JSON: {e}")
        except Exception as e:
            raise ConfigError(f"Ошибка загрузки конфигурации: {e}")

    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация параметров конфигурации"""
        required_fields = [
            "package_name",
            "repository_url",
            "test_repository_mode",
            "package_version",
            "output_filename",
            "package_filter"
        ]

        # Проверка наличия обязательных полей
        for field in required_fields:
            if field not in config:
                raise ConfigError(f"Обязательное поле отсутствует: {field}")

        # Валидация package_name
        if not isinstance(config["package_name"], str) or not config["package_name"].strip():
            raise ConfigError("package_name должен быть непустой строкой")

        # Валидация repository_url
        if not isinstance(config["repository_url"], str) or not config["repository_url"].strip():
            raise ConfigError("repository_url должен быть непустой строкой")

        # Валидация test_repository_mode
        if not isinstance(config["test_repository_mode"], bool):
            raise ConfigError("test_repository_mode должен быть булевым значением")

        # Валидация package_version
        if not isinstance(config["package_version"], str) or not config["package_version"].strip():
            raise ConfigError("package_version должен быть непустой строкой")

        # Валидация output_filename
        if not isinstance(config["output_filename"], str) or not config["output_filename"].strip():
            raise ConfigError("output_filename должен быть непустой строкой")

        # Валидация package_filter
        if not isinstance(config["package_filter"], str):
            raise ConfigError("package_filter должен быть строкой")

        return config

    def display_config(self):
        """Вывод всех параметров конфигурации в формате ключ-значение"""
        print("=== Конфигурационные параметры ===")
        for key, value in self.config.items():
            print(f"{key}: {value}")
        print("==================================")

    def run(self):
        """Основной метод запуска приложения"""
        try:
            self.display_config()
            print("Конфигурация успешно загружена и валидирована!")

            # Здесь будет основная логика на следующих этапах
            if self.config["test_repository_mode"]:
                print("Режим тестового репозитория активирован")
            else:
                print("Работа с реальным репозиторием")

        except ConfigError as e:
            print(f"Ошибка конфигурации: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            sys.exit(1)


def main():
    """Точка входа в приложение"""
    # Можно указать путь к конфигурационному файлу как аргумент командной строки
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"

    visualizer = DependencyVisualizer(config_path)
    visualizer.run()


if __name__ == "__main__":
    main()