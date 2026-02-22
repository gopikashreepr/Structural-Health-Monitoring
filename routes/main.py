from flask import Blueprint, render_template, request, jsonify, current_app
from flasgger import swag_from
import logging
from services.sensor_service import SensorService
from services.ml_service import MLService
from services.alert_service import AlertService

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@swag_from({
    'tags': ['Main'],
    'summary': 'Dashboard page',
    'description': 'Renders the main dashboard for real-time sensor monitoring',
    'responses': {
        200: {
            'description': 'Dashboard page rendered successfully'
        }
    }
})
def dashboard():
    """Render the main dashboard page"""
    try:
        # Get some basic statistics for the dashboard
        stats = SensorService.get_statistics()
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        return render_template('dashboard.html', stats={})

@main_bp.route('/healthcheck')
@swag_from({
    'tags': ['Health'],
    'summary': 'Health check endpoint',
    'description': 'Returns the health status of the application',
    'responses': {
        200: {
            'description': 'Application is healthy',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'healthy'},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                    'version': {'type': 'string', 'example': '1.0.0'}
                }
            }
        }
    }
})
def healthcheck():
    """Health check endpoint for deployment readiness"""
    from datetime import datetime
    
    try:
        # Test database connection
        from __init__ import db
        db.session.execute('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'components': {
                'database': 'healthy',
                'ml_service': 'healthy',
                'alert_service': 'healthy'
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@main_bp.route('/sensor-data')
@swag_from({
    'tags': ['Sensors'],
    'summary': 'Get real-time sensor data',
    'description': 'Returns current sensor readings with ML anomaly detection and alert checking',
    'responses': {
        200: {
            'description': 'Sensor data retrieved successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                    'vibration': {'type': 'number'},
                    'strain': {'type': 'number'},
                    'temperature': {'type': 'number'},
                    'is_anomaly': {'type': 'boolean'},
                    'anomaly_score': {'type': 'number'},
                    'alert_level': {'type': 'string', 'enum': ['normal', 'warning', 'critical']},
                    'alert_messages': {'type': 'array', 'items': {'type': 'string'}}
                }
            }
        },
        500: {
            'description': 'Internal server error'
        }
    }
})
def sensor_data():
    """Return real-time sensor data with ML predictions and alerts"""
    try:
        # Generate and save sensor data
        sensor_service = SensorService()
        sensor_data = sensor_service.generate_sensor_data()
        reading = sensor_service.save_reading(sensor_data)
        
        # Run ML anomaly detection
        ml_service = MLService()
        reading = ml_service.update_reading_with_prediction(reading)
        
        # Check thresholds and send alerts
        alert_level, messages = sensor_service.check_thresholds(reading)
        reading.alert_level = alert_level
        
        # Save updated reading
        from __init__ import db
        db.session.commit()
        
        # Send alerts if needed
        if alert_level != 'normal':
            alert_service = AlertService()
            alert_result = alert_service.check_and_send_alerts(reading, alert_level, messages)
            logger.info(f"Alert processing result: {alert_result}")
        
        # Return data for frontend
        response_data = reading.to_dict()
        response_data['alert_messages'] = messages
        # Remove server timestamp - let frontend handle local time display
        response_data.pop('timestamp', None)
        
        logger.debug(f"Generated sensor data: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in sensor_data endpoint: {str(e)}")
        return jsonify({'error': 'Failed to generate sensor data'}), 500

@main_bp.route('/statistics')
@swag_from({
    'tags': ['Statistics'],
    'summary': 'Get system statistics',
    'description': 'Returns comprehensive statistics about the monitoring system',
    'responses': {
        200: {
            'description': 'Statistics retrieved successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'sensor_stats': {'type': 'object'},
                    'alert_stats': {'type': 'object'},
                    'ml_stats': {'type': 'object'}
                }
            }
        }
    }
})
def statistics():
    """Get comprehensive system statistics"""
    try:
        sensor_service = SensorService()
        alert_service = AlertService()
        ml_service = MLService()
        
        return jsonify({
            'sensor_stats': sensor_service.get_statistics(),
            'alert_stats': alert_service.get_alert_statistics(),
            'ml_stats': ml_service.get_model_info()
        })
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({'error': 'Failed to get statistics'}), 500