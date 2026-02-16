"""
Test de Nodos Dinámicos
Valida que el sistema busca correctamente los nodos de las tablas reales
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, patch, MagicMock
from src.api_gateway import APIGateway

class TestNodosDinamicos(unittest.TestCase):
    """Tests para funcionalidad de nodos dinámicos"""
    
    def setUp(self):
        """Configurar antes de cada test"""
        self.gateway = APIGateway()
    
    @patch('src.api_gateway.DatabaseManager')
    def test_get_all_nodes_from_database_tabla_a(self, mock_db):
        """Test: Obtener nodos de Tabla A"""
        # Mock: Tabla A retorna 3 nodos
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        
        # Simulación de respuestas
        mock_db_instance.execute_query.side_effect = [
            [('NODO1',), ('NODO3',), ('NODO5',)],  # Tabla A
            [('NODO1',), ('NODO2',), ('NODO4',)],  # Tabla B
            [('NODO1',), ('NODO2',), ('NODO3',)]   # Tabla C
        ]
        
        gateway = APIGateway()
        nodos = gateway.get_all_nodes_from_database()
        
        # Verificar que retorna los 5 nodos únicos
        self.assertEqual(len(nodos), 5)
        self.assertIn('NODO1', nodos)
        self.assertIn('NODO2', nodos)
        self.assertIn('NODO3', nodos)
        self.assertIn('NODO4', nodos)
        self.assertIn('NODO5', nodos)
        
    @patch('src.api_gateway.DatabaseManager')
    def test_get_nodes_comparison(self, mock_db):
        """Test: Comparación de distribución de nodos"""
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        
        # Simulación de respuestas
        mock_db_instance.execute_query.side_effect = [
            [('NODO1',), ('NODO3',), ('NODO5',)],  # Tabla A
            [('NODO1',), ('NODO2',), ('NODO4',)],  # Tabla B
            [('NODO1',), ('NODO2',), ('NODO3',)]   # Tabla C
        ]
        
        gateway = APIGateway()
        comparison = gateway.get_nodes_comparison()
        
        # Verificar estructura
        self.assertTrue(comparison['success'])
        self.assertEqual(len(comparison['tabla_a_tck']), 3)
        self.assertEqual(len(comparison['tabla_b_tiv']), 3)
        self.assertEqual(len(comparison['tabla_c_consolidado']), 3)
        self.assertEqual(comparison['total_unicos'], 5)
        
        # Verificar nodos solo en cada tabla
        self.assertIn('NODO5', comparison['solo_en_a'])
        self.assertIn('NODO4', comparison['solo_en_b'])
        self.assertIn('NODO1', comparison['en_todas'])
        
    @patch('src.api_gateway.DatabaseManager')
    def test_empty_tables(self, mock_db):
        """Test: Manejo de tablas vacías"""
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        
        # Simulación: Todas las tablas vacías
        mock_db_instance.execute_query.side_effect = [
            [],  # Tabla A vacía
            [],  # Tabla B vacía
            []   # Tabla C vacía
        ]
        
        gateway = APIGateway()
        nodos = gateway.get_all_nodes_from_database()
        
        # Debe retornar lista vacía
        self.assertEqual(len(nodos), 0)
        
    @patch('src.api_gateway.DatabaseManager')
    def test_duplicate_nodos(self, mock_db):
        """Test: Elimina duplicados correctamente"""
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        
        # Simulación: Mismo nodo en múltiples tablas
        mock_db_instance.execute_query.side_effect = [
            [('NODO1',), ('NODO1',)],  # Tabla A con duplicados
            [('NODO1',)],               # Tabla B
            [('NODO1',)]                # Tabla C
        ]
        
        gateway = APIGateway()
        nodos = gateway.get_all_nodes_from_database()
        
        # Debe retornar solo 1 NODO1
        self.assertEqual(len(nodos), 1)
        self.assertEqual(nodos[0], 'NODO1')
        
    @patch('src.api_gateway.DatabaseManager')
    def test_nodos_con_espacios(self, mock_db):
        """Test: Limpia espacios en blanco de nodos"""
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        
        # Simulación: Nodos con espacios
        mock_db_instance.execute_query.side_effect = [
            [('  NODO1  ',), (' NODO2 ',)],  # Tabla A con espacios
            [],                               # Tabla B
            []                                # Tabla C
        ]
        
        gateway = APIGateway()
        nodos = gateway.get_all_nodes_from_database()
        
        # Debe limpiar espacios
        self.assertIn('NODO1', nodos)
        self.assertIn('NODO2', nodos)
        self.assertNotIn('  NODO1  ', nodos)


class TestNodosDinamicosIntegracion(unittest.TestCase):
    """Tests de integración con el servidor Flask"""
    
    def setUp(self):
        """Configurar Flask test client"""
        from main_SERVER import app
        self.app = app.test_client()
        self.app.testing = True
        
    @patch('src.api_gateway.APIGateway.get_all_nodes_from_database')
    def test_endpoint_nodes_dinamico(self, mock_get_nodes):
        """Test: Endpoint /nodes retorna nodos dinámicos"""
        mock_get_nodes.return_value = ['NODO1', 'NODO2', 'NODO3']
        
        response = self.app.get('/api/gateway/nodes')
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['total'], 3)
        self.assertEqual(len(data['nodes']), 3)
        
    @patch('src.api_gateway.APIGateway.get_nodes_comparison')
    def test_endpoint_nodes_comparacion(self, mock_comparison):
        """Test: Endpoint /nodes?comparison=true retorna comparación"""
        mock_comparison.return_value = {
            'success': True,
            'tabla_a_tck': ['NODO1', 'NODO3'],
            'tabla_b_tiv': ['NODO1', 'NODO2'],
            'tabla_c_consolidado': ['NODO1', 'NODO2', 'NODO3'],
            'todos_unicos': ['NODO1', 'NODO2', 'NODO3'],
            'solo_en_a': ['NODO3'],
            'solo_en_b': ['NODO2'],
            'solo_en_c': [],
            'en_a_y_b': [],
            'en_todas': ['NODO1'],
            'total_unicos': 3
        }
        
        response = self.app.get('/api/gateway/nodes?comparison=true')
        data = response.get_json()
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['total_unicos'], 3)


if __name__ == '__main__':
    # Ejecutar tests con verbose
    unittest.main(verbosity=2)
