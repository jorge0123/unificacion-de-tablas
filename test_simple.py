#!/usr/bin/env python3
"""
Script de prueba simple del API Gateway
Ejecutar: python test_simple.py
"""

import sys
import json
import importlib.util

# Cargar el módulo main-SERVER.py
spec = importlib.util.spec_from_file_location(
    "main_server", 
    "/Users/jorgealdairmarroquinsanchez/Documents/GitHub/unificacion-de-tablas/main-SERVER.py"
)
main_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_server)
app = main_server.app

try:
    print("\n" + "="*70)
    print("PRUEBAS DEL API GATEWAY - MODO TEST")
    print("="*70 + "\n")
    
    with app.test_client() as client:
        
        # Test 1: Endpoint raíz
        print("Test 1: GET /")
        print("-" * 70)
        response = client.get('/')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Message: {data.get('message')}")
        print(f"Version: {data.get('version')}")
        print(f"Endpoints disponibles: {len(data.get('endpoints', {}))}")
        print("✓ PASS\n")
        
        # Test 2: Process ALL (sin parámetros - NUEVO)
        print("Test 2: GET /api/gateway/process-all (PROCESAR TODOS SIN PARÁMETROS)")
        print("-" * 70)
        response = client.get('/api/gateway/process-all')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Success: {data.get('success')}")
        print(f"Total nodos: {data.get('total_nodos')}")
        print(f"Procesados: {data.get('procesados')}")
        print(f"Errores: {data.get('errores')}")
        print(f"Timestamp: {data.get('timestamp')}")
        print("Nodos procesados:")
        for nodo in data.get('nodos', []):
            print(f"  - {nodo['nodo']}: {nodo['status']} ({nodo.get('registros', 0)} registros)")
        print("✓ PASS\n")
        
        # Test 3: Health check
        print("Test 3: GET /api/gateway/health")
        print("-" * 70)
        response = client.get('/api/gateway/health')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        print("✓ PASS\n")
        
        # Test 4: List nodes
        print("Test 4: GET /api/gateway/nodes")
        print("-" * 70)
        response = client.get('/api/gateway/nodes')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        print("✓ PASS\n")
        
        # Test 5: Missing parameter
        print("Test 5: GET /api/gateway/status (sin parámetro)")
        print("-" * 70)
        response = client.get('/api/gateway/status')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        print("✓ PASS\n")
        
        # Test 6: Invalid endpoint
        print("Test 6: GET /invalid (endpoint no existe)")
        print("-" * 70)
        response = client.get('/invalid')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        print("✓ PASS\n")
        
    print("="*70)
    print("✅ TODAS LAS PRUEBAS PASARON")
    print("="*70 + "\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
