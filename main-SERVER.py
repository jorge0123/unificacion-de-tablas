"""
Servidor Flask - API Gateway REST
Expone el motor de sincronización como endpoints REST
"""

from flask import Flask, request, jsonify
import logging
from datetime import datetime
from src.api_gateway import APIGateway
from src.logger import setup_logger

# Configurar logger
logger = setup_logger(__name__)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # Para soportar caracteres UTF-8

# Instanciar gateway
gateway = APIGateway()


def format_datetime(obj):
    """Formatea datetime para JSON"""
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@app.before_request
def log_request():
    """Log de cada request"""
    logger.info(f"{request.method} {request.path} - {request.remote_addr}")


@app.route('/', methods=['GET'])
def index():
    """
    Página de inicio con documentación de endpoints
    """
    return jsonify({
        'success': True,
        'message': 'API Gateway - Motor Integrado y Seguro',
        'version': '2.0.0',
        'description': 'Sistema de sincronización automática con nodos dinámicos',
        'endpoints': {
            'process_all': {
                'url': 'GET /api/gateway/process-all',
                'description': 'Procesa AUTOMÁTICAMENTE TODOS los nodos (sin parámetros)',
                'how_it_works': 'Busca dinámicamente los nodos en tablas A, B, C y procesa cada uno'
            },
            'process': {
                'url': 'GET /api/gateway/process?nodo=NODO1',
                'description': 'Ejecuta el flujo completo de sincronización para un nodo específico',
                'parameters': {'nodo': 'Nombre del nodo (requerido)'}
            },
            'health': {
                'url': 'GET /api/gateway/health',
                'description': 'Verifica si el servidor está activo'
            },
            'status': {
                'url': 'GET /api/gateway/status?nodo=NODO1',
                'description': 'Obtiene estadísticas del nodo (total, abiertos, cerrados)',
                'parameters': {'nodo': 'Nombre del nodo (requerido)'}
            },
            'nodes': {
                'url': 'GET /api/gateway/nodes',
                'description': 'Lista todos los nodos únicos encontrados en las tablas',
                'optional': 'Usa ?comparison=true para ver distribución entre tablas (A, B, C)'
            }
        },
        'tables_monitored': ['homeb2c_tck (Tabla A)', 'homeb2c_tiv (Tabla B)', 'homeb2c_consolidado (Tabla C)'],
        'documentation': 'Ver DOCUMENTACION_API_GATEWAY.md para más información'
    }), 200


@app.route('/api/gateway/process-all', methods=['GET'])
def process_all():
    """
    Procesa TODOS los nodos automáticamente sin parámetros
    Ejecuta el flujo completo para cada nodo disponible
    """
    try:
        logger.info("Procesando todos los nodos automáticamente")
        
        # Obtener nodos dinámicamente de las tablas reales
        nodos = gateway.get_all_nodes_from_database()
        
        if not nodos:
            logger.warning("No se encontraron nodos en las tablas")
            return jsonify({
                'success': False,
                'error': 'No hay nodos disponibles en las tablas',
                'total_nodos': 0,
                'procesados': 0
            }), 404
        
        resultados = {
            'success': True,
            'total_nodos': len(nodos),
            'procesados': 0,
            'errores': 0,
            'nodos_encontrados': nodos,
            'nodos': []
        }
        
        for nodo in nodos:
            logger.info(f"Procesando nodo automático: {nodo}")
            try:
                result = gateway.process_node(nodo)
                
                nodo_info = {
                    'nodo': nodo,
                    'success': result['success'],
                    'registros': len(result.get('data', []))
                }
                
                if result['success']:
                    resultados['procesados'] += 1
                    nodo_info['status'] = 'procesado'
                else:
                    resultados['errores'] += 1
                    nodo_info['status'] = 'error'
                    nodo_info['error'] = result.get('error', 'Error desconocido')
                
                resultados['nodos'].append(nodo_info)
                
            except Exception as e:
                logger.error(f"Error procesando nodo {nodo}: {e}")
                resultados['errores'] += 1
                resultados['nodos'].append({
                    'nodo': nodo,
                    'success': False,
                    'status': 'error',
                    'error': str(e)
                })
        
        resultados['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Procesamiento automático completado: {resultados['procesados']}/{resultados['total_nodos']} exitosos")
        
        return jsonify(resultados), 200 if resultados['errores'] == 0 else 206
    
    except Exception as e:
        logger.error(f"Error en procesamiento automático: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/gateway/process', methods=['GET'])
def process_node():
    """
    Endpoint: GET /api/gateway/process?nodo=NODO1
    Procesa un nodo específico ejecutando el flujo completo de sincronización
    """
    try:
        nodo = request.args.get('nodo', '').strip()
        
        if not nodo:
            return jsonify({
                'success': False,
                'error': 'Parámetro "nodo" requerido'
            }), 400
        
        logger.info(f"Procesando nodo: {nodo}")
        result = gateway.process_node(nodo)
        
        return jsonify(result), 200 if result['success'] else 500
    
    except Exception as e:
        logger.error(f"Error en endpoint /process: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/gateway/status', methods=['GET'])
def get_status():
    """
    Endpoint: GET /api/gateway/status?nodo=NODO1
    Obtiene el estado actual de un nodo
    """
    try:
        nodo = request.args.get('nodo', '').strip()
        
        if not nodo:
            return jsonify({
                'success': False,
                'error': 'Parámetro "nodo" requerido'
            }), 400
        
        logger.info(f"Obteniendo estado de nodo: {nodo}")
        result = gateway.get_node_status(nodo)
        
        return jsonify(result), 200 if result['success'] else 404
    
    except Exception as e:
        logger.error(f"Error en endpoint /status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/gateway/health', methods=['GET'])
def health_check():
    """
    Endpoint: GET /api/gateway/health
    Verifica si el servidor está activo
    """
    return jsonify({
        'success': True,
        'status': 'online',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }), 200


@app.route('/api/gateway/nodes', methods=['GET'])
def list_nodes():
    """
    Endpoint: GET /api/gateway/nodes
    Lista todos los nodos disponibles en las tablas reales
    Opcionalmente, con ?comparison=true, muestra detalles de distribución
    """
    try:
        logger.info("Listando nodos disponibles")
        
        # Verificar si se solicita comparación detallada
        comparison = request.args.get('comparison', 'false').lower() == 'true'
        
        if comparison:
            # Retornar comparación detallada
            return jsonify(gateway.get_nodes_comparison()), 200
        else:
            # Retornar solo lista de nodos únicos
            nodos = gateway.get_all_nodes_from_database()
            return jsonify({
                'success': True,
                'total': len(nodos),
                'nodes': nodos
            }), 200
    
    except Exception as e:
        logger.error(f"Error en endpoint /nodes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Manejo de rutas no encontradas"""
    return jsonify({
        'success': False,
        'error': 'Endpoint no encontrado',
        'path': request.path
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Manejo de errores internos del servidor"""
    logger.error(f"Error interno del servidor: {error}")
    return jsonify({
        'success': False,
        'error': 'Error interno del servidor'
    }), 500


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Iniciando API Gateway REST Server")
    logger.info("=" * 60)
    logger.info("Endpoints disponibles:")
    logger.info("  GET /api/gateway/process?nodo=NODO1")
    logger.info("  GET /api/gateway/status?nodo=NODO1")
    logger.info("  GET /api/gateway/health")
    logger.info("  GET /api/gateway/nodes")
    logger.info("=" * 60)
    
    # Ejecutar servidor en puerto 5000
    app.run(host='0.0.0.0', port=5000, debug=False)
