"""
Script de prueba para los endpoints del API Gateway
Ejecutar: python test_api_gateway.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

def test_health():
    """Prueba endpoint de health check"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/api/gateway/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_list_nodes():
    """Prueba endpoint de listar nodos"""
    print("\n" + "="*60)
    print("TEST 2: Listar Nodos")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/api/gateway/nodes")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_get_status(nodo="NODO1"):
    """Prueba endpoint de estado del nodo"""
    print("\n" + "="*60)
    print(f"TEST 3: Estado del Nodo ({nodo})")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/api/gateway/status?nodo={nodo}")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code in [200, 404]
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_process_node(nodo="NODO1"):
    """Prueba endpoint de procesamiento del nodo"""
    print("\n" + "="*60)
    print(f"TEST 4: Procesar Nodo ({nodo})")
    print("="*60)
    try:
        print(f"Enviando solicitud a {BASE_URL}/api/gateway/process?nodo={nodo}")
        response = requests.get(f"{BASE_URL}/api/gateway/process?nodo={nodo}", timeout=60)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response preview:")
        print(f"  success: {data.get('success')}")
        if 'error' in data:
            print(f"  error: {data['error']}")
        if 'data' in data:
            print(f"  registros: {len(data['data'])}")
            if data['data']:
                print(f"  primer registro: {json.dumps(data['data'][0], indent=4, ensure_ascii=False)}")
        return response.status_code in [200, 500]
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_invalid_endpoint():
    """Prueba endpoint inválido"""
    print("\n" + "="*60)
    print("TEST 5: Endpoint Inválido")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/api/gateway/invalid")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 404
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_missing_params():
    """Prueba parámetro faltante"""
    print("\n" + "="*60)
    print("TEST 6: Parámetro Faltante (nodo)")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/api/gateway/process")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 400
    except Exception as e:
        print(f"Error: {e}")
        return False


def run_all_tests():
    """Ejecuta todas las pruebas"""
    print("\n" + "#"*60)
    print("# INICIANDO SUITE DE PRUEBAS DEL API GATEWAY")
    print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*60)

    tests = [
        ("Health Check", test_health),
        ("Listar Nodos", test_list_nodes),
        ("Estado del Nodo", test_get_status),
        ("Procesar Nodo", test_process_node),
        ("Endpoint Inválido", test_invalid_endpoint),
        ("Parámetro Faltante", test_missing_params),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"Error en test: {e}")
            results[test_name] = False

    # Resumen
    print("\n" + "#"*60)
    print("# RESUMEN DE PRUEBAS")
    print("#"*60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nResultados: {passed}/{total} pruebas pasadas\n")
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print("\n" + "#"*60)


if __name__ == "__main__":
    print("\n⚠️  Asegúrate de que el servidor está corriendo:")
    print("   python main-SERVER.py")
    print("\nPresiona Enter para continuar...")
    input()
    
    run_all_tests()
