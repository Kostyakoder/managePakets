#!/usr/bin/env python3
"""
Инструмент визуализации графа зависимостей для менеджера пакетов NuGet
Этап 2: Сбор данных - Гарантированно рабочий вариант
"""

import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, List


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
                    "package_name": "Microsoft.AspNetCore.Mvc.Core",
                    "repository_url": "https://api.nuget.org/v3/index.json",
                    "package_version": "2.2.5"
                }
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                print(f"Создан конфиг по умолчанию с пакетом, который имеет зависимости")
                return default_config

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
        response_data = self._make_http_request(url)
        return json.loads(response_data)

    def _get_service_index(self) -> Dict[str, Any]:
        """Получение индекса сервисов NuGet"""
        try:
            print(f"Получение индекса сервисов из {self.config['repository_url']}...")
            return self._get_json_from_url(self.config['repository_url'])
        except Exception as e:
            raise NuGetError(f"Ошибка получения индекса сервисов: {e}")

    def _find_search_service(self, service_index: Dict[str, Any]) -> str:
        """Поиск URL сервиса поиска пакетов"""
        resources = service_index.get('resources', [])

        for resource in resources:
            if resource.get('@type') == 'SearchQueryService':
                url = resource.get('@id')
                if url:
                    print(f"Найден SearchQueryService: {url}")
                    return url

        raise NuGetError("Сервис поиска пакетов (SearchQueryService) не найден в индексе")

    def _get_package_data(self, search_url: str, package_name: str, version: str) -> Dict[str, Any]:
        """Получение данных о конкретном пакете и версии"""
        # Ищем пакет по имени и версии
        search_url = f"{search_url}?q=packageid:{urllib.parse.quote(package_name)}&prerelease=false"
        print(f"Поиск пакета: {search_url}")

        search_data = self._get_json_from_url(search_url)
        data = search_data.get('data', [])

        if not data:
            raise NuGetError(f"Пакет {package_name} не найден")

        # Ищем нужную версию
        for package in data:
            pkg_id = package.get('id', '')
            pkg_version = package.get('version', '')

            if pkg_id.lower() == package_name.lower() and pkg_version == version:
                print(f"Найден пакет: {pkg_id} {pkg_version}")
                return package

        # Если точная версия не найдена, используем первую доступную
        available_packages = [p for p in data if p.get('id', '').lower() == package_name.lower()]
        if available_packages:
            package = available_packages[0]
            actual_version = package.get('version', '')
            print(f"Запрошенная версия {version} не найдена, используем {actual_version}")
            return package

        raise NuGetError(f"Пакет {package_name} не найден")

    def _extract_dependencies(self, package_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Извлечение зависимостей из данных пакета"""
        dependencies = []

        print("🔬 Анализ структуры данных пакета...")

        # Выводим все ключи для отладки
        print(f"Ключи в данных пакета: {list(package_data.keys())}")

        # Ищем зависимости в разных возможных местах
        dependency_groups = package_data.get('dependencyGroups', [])

        if dependency_groups:
            print(f"Найдено групп зависимостей: {len(dependency_groups)}")

            for i, group in enumerate(dependency_groups):
                if not isinstance(group, dict):
                    continue

                # Ищем зависимости в группе
                group_deps = group.get('dependencies', [])
                target_framework = group.get('targetFramework', 'Unknown')

                print(f"Группа {i + 1} (TargetFramework: {target_framework}): {len(group_deps)} зависимостей")

                for dep in group_deps:
                    if not isinstance(dep, dict):
                        continue

                    dep_id = dep.get('id', '') or dep.get('packageId', '')
                    dep_range = dep.get('range', '') or dep.get('version', '')

                    if dep_id:
                        dependencies.append({
                            'id': dep_id,
                            'version_range': dep_range,
                            'target_framework': target_framework
                        })
                        print(f"Зависимость: {dep_id} {dep_range}")

        # Если не нашли в dependencyGroups, пробуем другие места
        if not dependencies:
            print("Поиск зависимостей в других полях...")
            # Пробуем прямые dependencies
            direct_deps = package_data.get('dependencies', [])
            if direct_deps and isinstance(direct_deps, list):
                for dep in direct_deps:
                    if isinstance(dep, dict):
                        dep_id = dep.get('id', '') or dep.get('packageId', '')
                        dep_range = dep.get('range', '') or dep.get('version', '')
                        if dep_id:
                            dependencies.append({
                                'id': dep_id,
                                'version_range': dep_range,
                                'target_framework': 'Unknown'
                            })
                            print(f"Найдена зависимость: {dep_id} {dep_range}")

        return dependencies

    def get_dependencies(self) -> List[Dict[str, str]]:
        """Основной метод получения зависимостей пакета"""
        package_name = self.config['package_name']
        package_version = self.config['package_version']

        print(f"\nПоиск зависимостей для пакета {package_name} версии {package_version}...")

        try:
            # Получаем индекс сервисов
            service_index = self._get_service_index()

            # Находим URL сервиса поиска
            search_url = self._find_search_service(service_index)

            # Получаем данные пакета
            package_data = self._get_package_data(search_url, package_name, package_version)

            # Обновляем конфиг с фактической версией
            actual_version = package_data.get('version', package_version)
            self.config['package_version'] = actual_version

            # Извлекаем зависимости
            dependencies = self._extract_dependencies(package_data)

            self.dependencies = dependencies
            return dependencies

        except Exception as e:
            print(f"Ошибка при получении зависимостей: {type(e).__name__}: {e}")
            raise

    def display_dependencies(self):
        """Вывод всех прямых зависимостей на экран"""
        if not self.dependencies:
            print("\nЗависимости не найдены")
            return

        print(f"\nПРЯМЫЕ ЗАВИСИМОСТИ ПАКЕТА {self.config['package_name']} {self.config['package_version']}:")
        print("=" * 80)

        for i, dep in enumerate(self.dependencies, 1):
            version_display = dep['version_range'] if dep['version_range'] else '(без версии)'
            tfw_display = f" [{dep['target_framework']}]" if dep.get('target_framework') and dep[
                'target_framework'] != 'Unknown' else ""
            print(f"{i:2d}. {dep['id']:45} {version_display}{tfw_display}")

        print("=" * 80)
        print(f"Всего найдено зависимостей: {len(self.dependencies)}")

    def run(self):
        """Основной метод запуска приложения"""
        try:
            # Получаем зависимости
            self.get_dependencies()

            # Выводим зависимости на экран (требование этапа 2)
            self.display_dependencies()

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
    print("Используются пакеты, которые гарантированно имеют зависимости")

    # Можно указать путь к конфигурационному файлу как аргумент командной строки
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"

    print(f"Используется конфигурационный файл: {config_path}")

    visualizer = DependencyVisualizer(config_path)
    visualizer.run()


if __name__ == "__main__":
    main()