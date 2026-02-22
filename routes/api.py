from flask import Blueprint, request, jsonify
from flasgger import swag_from
from datetime import datetime, timedelta
import logging
from services.sensor_service import SensorService
from services.ml_service import MLService
from services.alert_service import AlertService

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

@api_bp.route('/readings')
@swag_from({
    'tags': ['API'],
    'summary': 'Get sensor readings',
    'description': 'Retrieve sensor readings with optional filtering',
    'parameters': [
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'default': 20,
            'description': 'Number of readings to return'
        },
        {
            'name': 'start_date',
            'in': 'query',
            'type': 'string',
            'format': 'date',
            'description': 'Start date for filtering (YYYY-MM-DD)'
        },
        {
            'name': 'end_date',
            'in': 'query',
            'type': 'string',
            'format': 'date',
            'description': 'End date for filtering (YYYY-MM-DD)'
        },
        {
            'name': 'anomalies_only',
            'in': 'query',
            'type': 'boolean',
            'default': False,
            'description': 'Return only anomalous readings'
        }
    ],
    'responses': {
        200: {
            'description': 'Readings retrieved successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'readings': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer'},
                                'timestamp': {'type': 'string'},
                                'vibration': {'type': 'number'},
                                'strain': {'type': 'number'},
                                'temperature': {'type': 'number'},
                                'is_anomaly': {'type': 'boolean'},
                                'alert_level': {'type': 'string'}
                            }
                        }
                    },
                    'total': {'type': 'integer'},
                    'page': {'type': 'integer'},
                    'limit': {'type': 'integer'}
                }
            }
        }
    }
})
def get_readings():
    """Get sensor readings with filtering options"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 20, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        anomalies_only = request.args.get('anomalies_only', False, type=bool)
        
        sensor_service = SensorService()
        
        # Filter by date range if provided
        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                readings = sensor_service.get_readings_by_date_range(start_dt, end_dt)
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            readings = sensor_service.get_readings(limit=limit)
        
        # Filter anomalies if requested
        if anomalies_only:
            readings = [r for r in readings if r.is_anomaly]
        
        # Convert to dictionaries
        readings_data = [reading.to_dict() for reading in readings[:limit]]
        
        return jsonify({
            'readings': readings_data,
            'total': len(readings_data),
            'limit': limit,
            'anomalies_only': anomalies_only
        })
        
    except Exception as e:
        logger.error(f"Error getting readings: {str(e)}")
        return jsonify({'error': 'Failed to get readings'}), 500

@api_bp.route('/ml/train', methods=['POST'])
@swag_from({
    'tags': ['Machine Learning'],
    'summary': 'Train ML model',
    'description': 'Train a new anomaly detection model',
    'parameters': [
        {
            'name': 'model_type',
            'in': 'formData',
            'type': 'string',
            'enum': ['isolation_forest', 'one_class_svm'],
            'default': 'isolation_forest',
            'description': 'Type of ML model to train'
        },
        {
            'name': 'contamination',
            'in': 'formData',
            'type': 'number',
            'default': 0.1,
            'description': 'Contamination parameter for Isolation Forest'
        }
    ],
    'responses': {
        200: {
            'description': 'Model trained successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'model_type': {'type': 'string'},
                    'training_samples': {'type': 'integer'},
                    'anomalies_detected': {'type': 'integer'},
                    'model_id': {'type': 'integer'}
                }
            }
        }
    }
})
def train_model():
    """Train a new ML model"""
    try:
        model_type = request.form.get('model_type', 'isolation_forest')
        contamination = float(request.form.get('contamination', 0.1))
        
        ml_service = MLService()
        
        if model_type == 'isolation_forest':
            result = ml_service.train_isolation_forest(contamination=contamination)
        elif model_type == 'one_class_svm':
            nu = float(request.form.get('nu', 0.1))
            result = ml_service.train_one_class_svm(nu=nu)
        else:
            return jsonify({'error': 'Invalid model type'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error training model: {str(e)}")
        return jsonify({'error': 'Failed to train model'}), 500

@api_bp.route('/ml/info')
@swag_from({
    'tags': ['Machine Learning'],
    'summary': 'Get ML model information',
    'description': 'Get information about the current ML model',
    'responses': {
        200: {
            'description': 'Model information retrieved successfully'
        }
    }
})
def model_info():
    """Get ML model information"""
    try:
        ml_service = MLService()
        return jsonify(ml_service.get_model_info())
    except Exception as e:
        logger.error(f"Error getting model info: {str(e)}")
        return jsonify({'error': 'Failed to get model info'}), 500

@api_bp.route('/alerts/history')
@swag_from({
    'tags': ['Alerts'],
    'summary': 'Get alert history',
    'description': 'Retrieve history of sent alerts',
    'parameters': [
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'default': 50,
            'description': 'Number of alerts to return'
        }
    ],
    'responses': {
        200: {
            'description': 'Alert history retrieved successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'alerts': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer'},
                                'alert_type': {'type': 'string'},
                                'alert_level': {'type': 'string'},
                                'recipient': {'type': 'string'},
                                'sent_at': {'type': 'string'},
                                'success': {'type': 'boolean'}
                            }
                        }
                    }
                }
            }
        }
    }
})
def alert_history():
    """Get alert history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        alert_service = AlertService()
        alerts = alert_service.get_alert_history(limit=limit)
        
        return jsonify({
            'alerts': alerts,
            'total': len(alerts)
        })
        
    except Exception as e:
        logger.error(f"Error getting alert history: {str(e)}")
        return jsonify({'error': 'Failed to get alert history'}), 500

@api_bp.route('/alerts/test', methods=['POST'])
@swag_from({
    'tags': ['Alerts'],
    'summary': 'Test alert system',
    'description': 'Send a test alert to verify alert system functionality',
    'parameters': [
        {
            'name': 'alert_type',
            'in': 'formData',
            'type': 'string',
            'enum': ['email', 'sms'],
            'required': True,
            'description': 'Type of alert to test'
        },
        {
            'name': 'recipient',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Recipient for the test alert'
        }
    ],
    'responses': {
        200: {
            'description': 'Test alert sent successfully'
        }
    }
})
def test_alert():
    """Send a test alert"""
    try:
        alert_type = request.form.get('alert_type')
        recipient = request.form.get('recipient')
        
        if not alert_type or not recipient:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Create a dummy reading for testing
        from models import SensorReading
        from datetime import datetime
        
        test_reading = SensorReading(
            timestamp=datetime.utcnow(),
            vibration=2.5,
            strain=0.7,
            temperature=35.0,
            alert_level='warning'
        )
        
        alert_service = AlertService()
        
        if alert_type == 'email':
            result = alert_service.send_email_alert(
                test_reading, 'warning', ['Test alert'], recipient
            )
        elif alert_type == 'sms':
            result = alert_service.send_sms_alert(
                test_reading, 'warning', ['Test alert'], recipient
            )
        else:
            return jsonify({'error': 'Invalid alert type'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error sending test alert: {str(e)}")
        return jsonify({'error': 'Failed to send test alert'}), 500