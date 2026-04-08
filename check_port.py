#!/usr/bin/env python
"""Проверка доступности порта"""

import socket
import sys

def check_port(host, port, timeout=10):
    """Проверяет доступность порта"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✓ Порт {port} на {host} доступен")
            return True
        else:
            print(f"✗ Порт {port} на {host} недоступен (код ошибки: {result})")
            return False
    except Exception as e:
        print(f"✗ Ошибка при проверке порта {port}: {e}")
        return False

if __name__ == "__main__":
    print("=== Проверка доступности портов ===")
    
    # Проверяем порты для Gmail
    ports_to_check = [
        ("smtp.gmail.com", 587),
        ("smtp.gmail.com", 465),
        ("smtp.gmail.com", 25),
    ]
    
    for host, port in ports_to_check:
        check_port(host, port)
    
    print("\n=== Проверка завершена ===")
