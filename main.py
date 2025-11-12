#!/usr/bin/env python3
"""
Инструмент визуализации графа зависимостей для менеджера пакетов NuGet
Этап 2: Сбор данных - Исправленная версия с правильными URL
"""

import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, List, Optional


class ConfigError(Exception):
    """Исключение для ошибок конфигурации"""
    pass


class NuGetError(Exception):
    """Исключение для ошибок работы с NuGet API"""
    pass


class DependencyVisualizer:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.dependencies = []

    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации из JSON файла"""
        try:
            if not os.path.exists(self.config_path):
                # Создаем конфиг по умолчанию с пакетом, который точно имеет зависимости
                default_config = {
                    "package_name": "Newtonsoft.Json",
                    "repository_url": "https://api.nuget.org/v3/index.json",
                    "package_version": "13.0.3",
                    "output_image": "dependencies.png",
                    "filter_substring": "",
                    "test_mode": False
                }
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
                print(f"Создан конфиг по умолчанию: {default_config}")
                return default_config

            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Выводим параметры конфигурации (требование этапа 1)
            print("\n=== КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ ===")
            for key, value in config.items():
                print(f"{key}: {value}")
            print("================================\n")

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
            "package_version"
        ]

        # Проверка наличия обязательных полей
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ConfigError(f"Обязательные поля отсутствуют: {', '.join(missing_fields)}")

        # Валидация package_name
        if not isinstance(config["package_name"], str) or not config["package_name"].strip():
            raise ConfigError("package_name должен быть непустой строкой")

        # Валидация repository_url
        if not isinstance(config["repository_url"], str) or not config["repository_url"].strip():
            raise ConfigError("repository_url должен быть непустой строкой")

        # Валидация package_version
        if not isinstance(config["package_version"], str) or not config["package_version"].strip():
            raise ConfigError("package_version должен быть непустой строкой")

        # Устанавливаем значения по умолчанию для опциональных полей
        config.setdefault("output_image", "dependencies.png")
        config.setdefault("filter_substring", "")
        config.setdefault("test_mode", False)

        return config

    def _make_http_request(self, url: str) -> str:
        """Выполнение HTTP запроса"""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'DependencyVisualizer/1.0',
                    'Accept': 'application/json'
                }
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode('utf-8')

        except urllib.error.HTTPError as e:
            raise NuGetError(f"HTTP ошибка {e.code}: {e.reason} для URL {url}")
        except urllib.error.URLError as e:
            raise NuGetError(f"Ошибка подключения: {e.reason} для URL {url}")
        except Exception as e:
            raise NuGetError(f"Ошибка при выполнении запроса к {url}: {e}")

    def _get_json_from_url(self, url: str) -> Dict[str, Any]:
        """Получение и парсинг JSON из URL"""
        try:
            response_data = self._make_http_request(url)
            return json.loads(response_data)
        except json.JSONDecodeError as e:
            raise NuGetError(f"Ошибка парсинга JSON из {url}: {e}")

    def _get_service_index(self) -> Dict[str, Any]:
        """Получение индекса сервисов NuGet"""
        try:
            print(f"Получение индекса сервисов из {self.config['repository_url']}...")
            return self._get_json_from_url(self.config['repository_url'])
        except Exception as e:
            raise NuGetError(f"Ошибка получения индекса сервисов: {e}")

    def _find_service_url(self, service_index: Dict[str, Any], service_type: str) -> str:
        """Поиск URL конкретного сервиса в индексе"""
        resources = service_index.get('resources', [])

        for resource in resources:
            if resource.get('@type') == service_type:
                url = resource.get('@id')
                if url:
                    print(f"Найден {service_type}: {url}")
                    return url

        raise NuGetError(f"Сервис {service_type} не найден в индексе")

    def _get_package_registration_url(self, registration_base_url: str, package_name: str, version: str) -> str:
        """Формирование правильного URL для получения данных о пакете"""
        # Правильный формат URL для NuGet API v3:
        # https://api.nuget.org/v3/registration5-gz-semver2/newtonsoft.json/13.0.3.json
        package_name_lower = package_name.lower()

        # Формируем URL для конкретной версии пакета
        registration_url = f"{registration_base_url}{package_name_lower}/{version}.json"
        print(f"Сформирован URL регистрации пакета: {registration_url}")

        return registration_url

    def _get_package_data(self, registration_base_url: str, package_name: str, version: str) -> Dict[str, Any]:
        """Получение данных о пакете через Registration API"""
        try:
            # Получаем URL для регистрации пакета
            registration_url = self._get_package_registration_url(registration_base_url, package_name, version)

            print(f"Запрос данных пакета: {registration_url}")
            registration_data = self._get_json_from_url(registration_url)

            # Извлекаем catalogEntry из полученных данных
            items = registration_data.get('items', [])
            if not items:
                raise NuGetError(f"Не найдены данные о пакете {package_name} версии {version}")

            # Ищем catalogEntry в данных
            for item in items:
                if 'catalogEntry' in item:
                    catalog_entry = item['catalogEntry']
                    print(f"Найден catalogEntry для {package_name} {version}")
                    return catalog_entry

            # Если catalogEntry не найден напрямую, ищем в items[0].items
            if 'items' in items[0]:
                for sub_item in items[0]['items']:
                    if 'catalogEntry' in sub_item:
                        catalog_entry = sub_item['catalogEntry']
                        print(f"Найден catalogEntry для {package_name} {version}")
                        return catalog_entry

            raise NuGetError(f"Не удалось извлечь catalogEntry для пакета {package_name}")

        except NuGetError:
            raise
        except Exception as e:
            raise NuGetError(f"Ошибка получения данных пакета: {e}")

    def _try_alternative_registration_url(self, registration_base_url: str, package_name: str, version: str) -> Dict[
        str, Any]:
        """Попытка использовать альтернативный формат URL"""
        package_name_lower = package_name.lower()

        # Альтернативный формат: индекс пакета
        alt_url = f"{registration_base_url}{package_name_lower}/index.json"
        print(f"Попытка альтернативного URL: {alt_url}")

        try:
            index_data = self._get_json_from_url(alt_url)
            items = index_data.get('items', [])

            # Ищем нужную версию в индексе
            for item in items:
                items_list = item.get('items', [])
                for sub_item in items_list:
                    catalog_entry = sub_item.get('catalogEntry', {})
                    if catalog_entry.get('version') == version:
                        print(f"Найдена версия {version} через альтернативный URL")
                        return catalog_entry

            # Если точная версия не найдена, берем первую доступную
            for item in items:
                items_list = item.get('items', [])
                if items_list:
                    catalog_entry = items_list[0].get('catalogEntry', {})
                    actual_version = catalog_entry.get('version', 'unknown')
                    print(f"Версия {version} не найдена, используем {actual_version}")
                    return catalog_entry

            raise NuGetError(f"Пакет {package_name} не найден через альтернативный URL")

        except Exception as e:
            raise NuGetError(f"Альтернативный метод также не сработал: {e}")

    def _extract_dependencies(self, package_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Извлечение зависимостей из данных пакета"""
        dependencies = []

        print("Анализ структуры данных пакета...")

        # Выводим доступные ключи для отладки
        print(f"Доступные ключи в package_data: {list(package_data.keys())}")

        # Основной способ получения зависимостей - через dependencyGroups
        dependency_groups = package_data.get('dependencyGroups', [])

        if dependency_groups:
            print(f"Найдено групп зависимостей: {len(dependency_groups)}")

            for i, group in enumerate(dependency_groups):
                if not isinstance(group, dict):
                    continue

                # Получаем зависимости из группы
                group_dependencies = group.get('dependencies', [])
                target_framework = group.get('targetFramework', 'Unknown')

                print(f"Группа {i + 1} (TargetFramework: {target_framework}): {len(group_dependencies)} зависимостей")

                for dep in group_dependencies:
                    if not isinstance(dep, dict):
                        continue

                    # Получаем ID и версию зависимости
                    dep_id = dep.get('id', '')
                    dep_range = dep.get('range', '')

                    if not dep_range:
                        dep_range = dep.get('version', '')

                    if dep_id:
                        dependency_info = {
                            'id': dep_id,
                            'version_range': dep_range,
                            'target_framework': target_framework
                        }
                        dependencies.append(dependency_info)
                        print(f"  → {dep_id} {dep_range}")

        # Если не нашли зависимостей, выводим отладочную информацию
        if not dependencies:
            print("Зависимости не найдены в данных пакета")
            print("Проверяем альтернативные места...")

            # Проверяем другие возможные места для зависимостей
            for key in ['dependencies', 'packageDependencies', 'dependencyGroups']:
                if key in package_data and key != 'dependencyGroups':
                    print(f"Найдено поле '{key}': {package_data[key]}")

        return dependencies

    def get_dependencies(self) -> List[Dict[str, str]]:
        """Основной метод получения зависимостей пакета"""
        package_name = self.config['package_name']
        package_version = self.config['package_version']

        print(f"\nПоиск зависимостей для пакета {package_name} версии {package_version}...")

        try:
            # Получаем индекс сервисов
            service_index = self._get_service_index()

            # Находим URL сервиса регистрации
            registration_base_url = self._find_service_url(service_index, 'RegistrationsBaseUrl/3.6.0')

            # Получаем данные пакета
            try:
                package_data = self._get_package_data(registration_base_url, package_name, package_version)
            except NuGetError as e:
                print(f"Первый метод не сработал: {e}")
                print("Пробуем альтернативный метод...")
                package_data = self._try_alternative_registration_url(registration_base_url, package_name,
                                                                      package_version)

            # Извлекаем зависимости
            dependencies = self._extract_dependencies(package_data)

            # Применяем фильтр если указан
            if self.config.get('filter_substring'):
                filter_str = self.config['filter_substring'].lower()
                original_count = len(dependencies)
                dependencies = [dep for dep in dependencies if filter_str in dep['id'].lower()]
                print(
                    f"Применен фильтр: '{filter_str}', осталось зависимостей: {len(dependencies)} из {original_count}")

            self.dependencies = dependencies
            return dependencies

        except Exception as e:
            print(f"Ошибка при получении зависимостей: {type(e).__name__}: {e}")
            raise

    def display_dependencies(self):
        """Вывод всех прямых зависимостей на экран (требование этапа 2)"""
        if not self.dependencies:
            print("\nЗависимости не найдены")
            return

        print(f"\nПРЯМЫЕ ЗАВИСИМОСТИ ПАКЕТА {self.config['package_name']} {self.config['package_version']}:")
        print("=" * 80)

        for i, dep in enumerate(self.dependencies, 1):
            version_display = dep['version_range'] if dep['version_range'] else '(любая версия)'
            tfw_display = f" [{dep['target_framework']}]" if dep.get('target_framework') and dep[
                'target_framework'] != 'Unknown' else ""
            print(f"{i:2d}. {dep['id']:40} {version_display:20}{tfw_display}")

        print("=" * 80)
        print(f"Всего найдено зависимостей: {len(self.dependencies)}")

    def run(self):
        """Основной метод запуска приложения"""
        try:
            # Получаем зависимости
            dependencies = self.get_dependencies()

            # Выводим зависимости на экран (требование этапа 2)
            self.display_dependencies()

            print(f"\nЭтап 2 завершен успешно!")
            print(f"Результаты сохранены для следующего этапа визуализации")

        except ConfigError as e:
            print(f"Ошибка конфигурации: {e}")
            sys.exit(1)
        except NuGetError as e:
            print(f"Ошибка получения данных: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Неожиданная ошибка: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Точка входа в приложение"""
    print("=== Dependency Visualizer - Этап 2: Сбор данных ===")
    print("Исправленная версия с правильными URL API")

    # Можно указать путь к конфигурационному файлу как аргумент командной строки
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"

    print(f"Используется конфигурационный файл: {config_path}")

    visualizer = DependencyVisualizer(config_path)
    visualizer.run()


if __name__ == "__main__":
    main()