"""
Нагрузочные тесты для системы управления заявками
Запуск: python manage.py test tests.load_tests
"""
import time
import threading
import random
from django.test import TestCase, Client
from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from tickets.models import Ticket, ServiceType, TicketStatus, Role

User = get_user_model()

class LoadTestMixin:
    """Миксин для нагрузочных тестов"""
    
    def setUp(self):
        """Создаем тестовые данные"""
        # Создаем роли
        self.client_role = Role.objects.create(name=Role.CLIENT)
        self.worker_role = Role.objects.create(name=Role.WORKER)
        
        # Создаем типы услуг
        self.service_type = ServiceType.objects.create(
            name="Ремонт компьютера",
            description="Диагностика и ремонт ПК"
        )
        
        # Создаем статусы
        self.status_new = TicketStatus.objects.create(name=TicketStatus.NEW)
        self.status_work = TicketStatus.objects.create(name=TicketStatus.IN_PROGRESS)
        
        # Создаем тестовых пользователей
        self.test_users = []
        for i in range(50):
            user = User.objects.create_user(
                username=f'testuser{i}',
                email=f'test{i}@example.com',
                password='testpass123',
                role=self.client_role
            )
            self.test_users.append(user)
        
        # Создаем тестовые заявки
        self.test_tickets = []
        for i in range(100):
            ticket = Ticket.objects.create(
                title=f'Тестовая заявка {i}',
                description=f'Описание тестовой заявки номер {i}',
                user=random.choice(self.test_users),
                service_type=self.service_type,
                status=self.status_new
            )
            self.test_tickets.append(ticket)

class LoginLoadTest(LoadTestMixin, TestCase):
    """Тест нагрузки входа в систему"""
    
    def simulate_login(self, username, password, results, index):
        """Симуляция входа одного пользователя"""
        client = Client()
        start_time = time.time()
        
        try:
            response = client.post('/login/', {
                'username': username,
                'password': password
            })
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            results[index] = {
                'username': username,
                'response_time': response_time,
                'status_code': response.status_code,
                'success': response.status_code == 302  # Redirect после успешного входа
            }
        except Exception as e:
            end_time = time.time()
            results[index] = {
                'username': username,
                'response_time': (end_time - start_time) * 1000,
                'status_code': 500,
                'success': False,
                'error': str(e)
            }
    
    def test_concurrent_login_10_users(self):
        """Тест: 10 одновременных входов"""
        self.run_login_test(10)
    
    def test_concurrent_login_25_users(self):
        """Тест: 25 одновременных входов"""
        self.run_login_test(25)
    
    def test_concurrent_login_50_users(self):
        """Тест: 50 одновременных входов"""
        self.run_login_test(50)
    
    def run_login_test(self, num_users):
        """Запуск теста с указанным количеством пользователей"""
        results = [None] * num_users
        threads = []
        
        start_time = time.time()
        
        # Создаем и запускаем потоки
        for i in range(num_users):
            user = self.test_users[i % len(self.test_users)]
            thread = threading.Thread(
                target=self.simulate_login,
                args=(user.username, 'testpass123', results, i)
            )
            threads.append(thread)
        
        # Запускаем все потоки одновременно
        for thread in threads:
            thread.start()
        
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Анализ результатов
        successful_logins = sum(1 for r in results if r and r['success'])
        avg_response_time = sum(r['response_time'] for r in results if r) / len(results)
        
        print(f"\n=== Тест входа: {num_users} пользователей ===")
        print(f"Общее время: {total_time:.2f} секунд")
        print(f"Успешных входов: {successful_logins}/{num_users} ({successful_logins/num_users*100:.1f}%)")
        print(f"Среднее время ответа: {avg_response_time:.2f} мс")
        
        # Проверяем требования
        self.assertLess(avg_response_time, 1000, "Среднее время ответа должно быть < 1000 мс")
        self.assertGreater(successful_logins/num_users, 0.9, "Успешных входов должно быть > 90%")

class DatabaseLoadTest(LoadTestMixin, TestCase):
    """Тест нагрузки базы данных"""
    
    def test_read_performance_small(self):
        """Тест чтения: 100 записей"""
        self.run_read_test(100)
    
    def test_read_performance_medium(self):
        """Тест чтения: 1000 записей"""
        self.run_read_test(1000)
    
    def test_read_performance_large(self):
        """Тест чтения: 10000 записей"""
        self.run_read_test(10000)
    
    def run_read_test(self, record_count):
        """Тест производительности чтения"""
        start_time = time.time()
        
        # Выполняем сложный запрос с фильтрацией
        tickets = Ticket.objects.filter(
            status=self.status_new
        ).select_related('user', 'service_type')[:record_count]
        
        # Принудительно выполняем запрос
        list(tickets)
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        print(f"Чтение {record_count} записей: {response_time:.2f} мс")
        
        # Проверяем требования
        if record_count <= 1000:
            self.assertLess(response_time, 50, f"Чтение {record_count} записей должно быть < 50 мс")
        elif record_count <= 10000:
            self.assertLess(response_time, 200, f"Чтение {record_count} записей должно быть < 200 мс")
    
    def test_write_performance(self):
        """Тест производительности записи"""
        times = []
        iterations = 100
        
        for i in range(iterations):
            start_time = time.time()
            
            ticket = Ticket.objects.create(
                title=f'Тестовая заявка {i}',
                description=f'Описание тестовой заявки {i}',
                user=random.choice(self.test_users),
                service_type=self.service_type,
                status=self.status_new
            )
            
            end_time = time.time()
            times.append((end_time - start_time) * 1000)
        
        avg_time = sum(times) / len(times)
        print(f"Среднее время создания заявки: {avg_time:.2f} мс")
        
        # Проверяем требования
        self.assertLess(avg_time, 20, "Создание заявки должно быть < 20 мс")

class TicketOperationsLoadTest(LoadTestMixin, TestCase):
    """Тест нагрузки операций с заявками"""
    
    def simulate_ticket_operations(self, user_id, operations_count, results, index):
        """Симуляция работы с заявками"""
        client = Client()
        
        # Входим в систему
        user = self.test_users[user_id % len(self.test_users)]
        client.force_login(user)
        
        operation_times = []
        
        for i in range(operations_count):
            start_time = time.time()
            
            # Создаем заявку
            response = client.post('/client/create-ticket/', {
                'title': f'Тестовая заявка {user_id}-{i}',
                'description': f'Описание заявки {user_id}-{i}',
                'service_type': self.service_type.id,
                'equipment': 'Тестовое оборудование'
            })
            
            end_time = time.time()
            operation_times.append((end_time - start_time) * 1000)
        
        results[index] = {
            'user_id': user_id,
            'operations_count': operations_count,
            'avg_time': sum(operation_times) / len(operation_times),
            'total_time': sum(operation_times)
        }
    
    def test_concurrent_ticket_operations_5_users(self):
        """Тест: 5 пользователей работают с заявками"""
        self.run_operations_test(5, 10)  # 5 пользователей, 10 операций каждый
    
    def test_concurrent_ticket_operations_15_users(self):
        """Тест: 15 пользователей работают с заявками"""
        self.run_operations_test(15, 10)  # 15 пользователей, 10 операций каждый
    
    def run_operations_test(self, num_users, operations_per_user):
        """Запуск теста операций с заявками"""
        results = [None] * num_users
        threads = []
        
        start_time = time.time()
        
        # Создаем и запускаем потоки
        for i in range(num_users):
            thread = threading.Thread(
                target=self.simulate_ticket_operations,
                args=(i, operations_per_user, results, i)
            )
            threads.append(thread)
        
        # Запускаем все потоки одновременно
        for thread in threads:
            thread.start()
        
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Анализ результатов
        total_operations = sum(r['operations_count'] for r in results if r)
        avg_response_time = sum(r['avg_time'] for r in results if r) / len(results)
        operations_per_minute = (total_operations / total_time) * 60
        
        print(f"\n=== Тест операций: {num_users} пользователей ===")
        print(f"Общее время: {total_time:.2f} секунд")
        print(f"Всего операций: {total_operations}")
        print(f"Операций в минуту: {operations_per_minute:.1f}")
        print(f"Среднее время операции: {avg_response_time:.2f} мс")
        
        # Проверяем требования
        self.assertLess(avg_response_time, 500, "Среднее время операции должно быть < 500 мс")
        self.assertGreater(operations_per_minute, 50, "Операций в минуту должно быть > 50")

class PerformanceReportTest(TestCase):
    """Тест для генерации отчета о производительности"""
    
    def test_generate_performance_report(self):
        """Генерация полного отчета о производительности"""
        print("\n" + "="*60)
        print("ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ СИСТЕМЫ")
        print("="*60)
        
        # Запускаем все тесты
        login_test = LoginLoadTest()
        login_test.setUp()
        
        print("\n1. ТЕСТЫ ВХОДА В СИСТЕМУ")
        print("-" * 40)
        
        # Тестируем разное количество пользователей
        for users in [10, 25, 50]:
            login_test.run_login_test(users)
        
        print("\n2. ТЕСТЫ БАЗЫ ДАННЫХ")
        print("-" * 40)
        
        db_test = DatabaseLoadTest()
        db_test.setUp()
        
        # Тестируем чтение
        for records in [100, 1000, 10000]:
            db_test.run_read_test(records)
        
        # Тестируем запись
        db_test.test_write_performance()
        
        print("\n3. ТЕСТЫ ОПЕРАЦИЙ С ЗАЯВКАМИ")
        print("-" * 40)
        
        ops_test = TicketOperationsLoadTest()
        ops_test.setUp()
        
        # Тестируем операции
        for users in [5, 15]:
            ops_test.run_operations_test(users, 10)
        
        print("\n" + "="*60)
        print("ТЕСТЫ ЗАВЕРШЕНЫ")
        print("="*60)
        
        self.assertTrue(True, "Отчет успешно сгенерирован")

if __name__ == '__main__':
    import django
    from django.conf import settings
    
    # Настройка Django
    if not settings.configured:
        settings.configure()
    
    django.setup()
    
    # Запуск тестов
    import unittest
    unittest.main()
