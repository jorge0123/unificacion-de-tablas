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
    Lista todos los nodos disponibles
    """
    try:
        # Aquí puedes conectar a tu BD para obtener los nodos reales
        # Por ahora, retorna una lista de ejemplo
        logger.info("Listando nodos disponibles")
        return jsonify({
            'success': True,
            'nodes': ['NODO1', 'NODO2', 'NODO3', 'NODO4', 'NODO5']
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
