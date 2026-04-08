#!/usr/bin/env python
"""
Скрипт для запуска нагрузочных тестов
Использование: python run_load_tests.py
"""
import os
import sys
import django
import time
import psutil
from datetime import datetime

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chinilkin.settings')
django.setup()

from django.core.management import call_command
from django.test.utils import get_runner
from django.conf import settings

class LoadTestRunner:
    """Запускатель нагрузочных тестов с мониторингом системы"""
    
    def __init__(self):
        self.start_time = None
        self.system_stats = []
    
    def get_system_stats(self):
        """Получение статистики системы"""
        return {
            'timestamp': time.time(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_used_gb': psutil.virtual_memory().used / (1024**3),
            'disk_usage_percent': psutil.disk_usage('/').percent
        }
    
    def start_monitoring(self):
        """Начать мониторинг системы"""
        self.start_time = time.time()
        print("Начинаю мониторинг системы...")
        
        # Записываем начальные показатели
        initial_stats = self.get_system_stats()
        self.system_stats.append(initial_stats)
        
        print(f"Начальные показатели:")
        print(f"  CPU: {initial_stats['cpu_percent']:.1f}%")
        print(f"  RAM: {initial_stats['memory_percent']:.1f}% ({initial_stats['memory_used_gb']:.1f} ГБ)")
        print(f"  Диск: {initial_stats['disk_usage_percent']:.1f}%")
    
    def stop_monitoring(self):
        """Остановить мониторинг и показать результаты"""
        if self.start_time:
            end_time = time.time()
            total_time = end_time - self.start_time
            
            final_stats = self.get_system_stats()
            
            print(f"\nФинальные показатели:")
            print(f"  CPU: {final_stats['cpu_percent']:.1f}%")
            print(f"  RAM: {final_stats['memory_percent']:.1f}% ({final_stats['memory_used_gb']:.1f} ГБ)")
            print(f"  Диск: {final_stats['disk_usage_percent']:.1f}%")
            print(f"  Время выполнения: {total_time:.2f} секунд")
    
    def run_login_tests(self):
        """Запуск тестов входа в систему"""
        print("\n" + "="*60)
        print("ЗАПУСК ТЕСТОВ ВХОДА В СИСТЕМУ")
        print("="*60)
        
        self.start_monitoring()
        
        try:
            # Запускаем тесты входа
            from tests.load_tests import LoginLoadTest
            
            test_cases = [
                ('10 пользователей', LoginLoadTest, 'test_concurrent_login_10_users'),
                ('25 пользователей', LoginLoadTest, 'test_concurrent_login_25_users'),
                ('50 пользователей', LoginLoadTest, 'test_concurrent_login_50_users'),
            ]
            
            for description, test_class, method_name in test_cases:
                print(f"\nТест: {description}")
                print("-" * 40)
                
                test_instance = test_class(method_name)
                test_instance.setUp()
                getattr(test_instance, method_name)()
                
                # Записываем статистику после теста
                stats = self.get_system_stats()
                self.system_stats.append(stats)
                
                print(f"  CPU: {stats['cpu_percent']:.1f}%")
                print(f"  RAM: {stats['memory_percent']:.1f}%")
        
        except Exception as e:
            print(f"Ошибка при выполнении тестов входа: {e}")
        
        self.stop_monitoring()
    
    def run_database_tests(self):
        """Запуск тестов базы данных"""
        print("\n" + "="*60)
        print("ЗАПУСК ТЕСТОВ БАЗЫ ДАННЫХ")
        print("="*60)
        
        self.start_monitoring()
        
        try:
            from tests.load_tests import DatabaseLoadTest
            
            test_instance = DatabaseLoadTest()
            test_instance.setUp()
            
            # Тесты чтения
            print("\nТесты производительности чтения:")
            test_instance.test_read_performance_small()
            test_instance.test_read_performance_medium()
            test_instance.test_read_performance_large()
            
            # Тест записи
            print("\nТест производительности записи:")
            test_instance.test_write_performance()
            
        except Exception as e:
            print(f"Ошибка при выполнении тестов БД: {e}")
        
        self.stop_monitoring()
    
    def run_operations_tests(self):
        """Запуск тестов операций с заявками"""
        print("\n" + "="*60)
        print("ЗАПУСК ТЕСТОВ ОПЕРАЦИЙ С ЗАЯВКАМИ")
        print("="*60)
        
        self.start_monitoring()
        
        try:
            from tests.load_tests import TicketOperationsLoadTest
            
            test_instance = TicketOperationsLoadTest()
            test_instance.setUp()
            
            # Тесты операций
            test_instance.test_concurrent_ticket_operations_5_users()
            test_instance.test_concurrent_ticket_operations_15_users()
            
        except Exception as e:
            print(f"Ошибка при выполнении тестов операций: {e}")
        
        self.stop_monitoring()
    
    def run_all_tests(self):
        """Запуск всех нагрузочных тестов"""
        print(f"Начинаем нагрузочное тестирование в {datetime.now().strftime('%H:%M:%S')}")
        print(f"Система: {os.name}")
        print(f"Python: {sys.version}")
        print(f"Django: {django.get_version()}")
        
        total_start = time.time()
        
        # 1. Тесты входа
        self.run_login_tests()
        
        # 2. Тесты базы данных
        self.run_database_tests()
        
        # 3. Тесты операций
        self.run_operations_tests()
        
        total_end = time.time()
        total_time = total_end - total_start
        
        print("\n" + "="*60)
        print("ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
        print("="*60)
        print(f"Общее время выполнения: {total_time:.2f} секунд ({total_time/60:.1f} минут)")
        
        # Генерируем отчет
        self.generate_report()
    
    def generate_report(self):
        """Генерация отчета о тестировании"""
        report_file = f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("ОТЧЕТ О НАГРУЗОЧНОМ ТЕСТИРОВАНИИ\n")
            f.write("="*50 + "\n\n")
            f.write(f"Дата и время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write(f"Система: {os.name}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Django: {django.get_version()}\n\n")
            
            f.write("СТАТИСТИКА СИСТЕМЫ:\n")
            f.write("-" * 30 + "\n")
            
            for i, stats in enumerate(self.system_stats):
                f.write(f"Замер {i+1}: CPU={stats['cpu_percent']:.1f}%, ")
                f.write(f"RAM={stats['memory_percent']:.1f}%, ")
                f.write(f"Диск={stats['disk_usage_percent']:.1f}%\n")
        
        print(f"\nОтчет сохранен в файл: {report_file}")

def main():
    """Главная функция"""
    runner = LoadTestRunner()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'login':
            runner.run_login_tests()
        elif command == 'database':
            runner.run_database_tests()
        elif command == 'operations':
            runner.run_operations_tests()
        elif command == 'all':
            runner.run_all_tests()
        else:
            print("Неизвестная команда. Доступные команды:")
            print("  login      - тесты входа в систему")
            print("  database   - тесты базы данных")
            print("  operations  - тесты операций с заявками")
            print("  all        - все тесты")
    else:
        print("Использование: python run_load_tests.py [команда]")
        print("\nДоступные команды:")
        print("  login      - тесты входа в систему")
        print("  database   - тесты базы данных")
        print("  operations  - тесты операций с заявками")
        print("  all        - все тесты")

if __name__ == '__main__':
    main()
