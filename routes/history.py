from flask import Blueprint, render_template, request, jsonify
from flasgger import swag_from
from datetime import datetime, timedelta
import logging
from services.sensor_service import SensorService
from models import SensorReading
from config import Config

logger = logging.getLogger(__name__)

history_bp = Blueprint('history', __name__)

@history_bp.route('/')
@swag_from({
    'tags': ['History'],
    'summary': 'History dashboard',
    'description': 'Renders the history dashboard page',
    'responses': {
        200: {
            'description': 'History dashboard rendered successfully'
        }
    }
})
def history_dashboard():
    """Render the history dashboard page"""
    try:
        # Get recent readings for initial display
        sensor_service = SensorService()
        recent_readings = sensor_service.get_readings(limit=100)
        
        # Get statistics
        stats = sensor_service.get_statistics()
        
        return render_template('history.html', 
                             readings=recent_readings, 
                             stats=stats)
    except Exception as e:
        logger.error(f"Error rendering history dashboard: {str(e)}")
        return render_template('history.html', readings=[], stats={})

@history_bp.route('/data')
@swag_from({
    'tags': ['History'],
    'summary': 'Get historical data',
    'description': 'Retrieve historical sensor data with filtering and pagination',
    'parameters': [
        {
            'name': 'page',
            'in': 'query',
            'type': 'integer',
            'default': 1,
            'description': 'Page number'
        },
        {
            'name': 'per_page',
            'in': 'query',
            'type': 'integer',
            'default': 50,
            'description': 'Items per page'
        },
        {
            'name': 'start_date',
            'in': 'query',
            'type': 'string',
            'format': 'date',
            'description': 'Start date (YYYY-MM-DD)'
        },
        {
            'name': 'end_date',
            'in': 'query',
            'type': 'string',
            'format': 'date',
            'description': 'End date (YYYY-MM-DD)'
        },
        {
            'name': 'alert_level',
            'in': 'query',
            'type': 'string',
            'enum': ['normal', 'warning', 'critical'],
            'description': 'Filter by alert level'
        },
        {
            'name': 'anomalies_only',
            'in': 'query',
            'type': 'boolean',
            'default': False,
            'description': 'Show only anomalies'
        }
    ],
    'responses': {
        200: {
            'description': 'Historical data retrieved successfully',
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
                    'per_page': {'type': 'integer'},
                    'pages': {'type': 'integer'}
                }
            }
        }
    }
})
def get_history_data():
    """Get historical sensor data with filtering and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        alert_level = request.args.get('alert_level')
        anomalies_only = request.args.get('anomalies_only', False, type=bool)
        
        # Build query
        query = SensorReading.query
        
        # Date filtering
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(SensorReading.timestamp >= start_dt)
            except ValueError:
                return jsonify({'error': 'Invalid start_date format'}), 400
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(SensorReading.timestamp < end_dt)
            except ValueError:
                return jsonify({'error': 'Invalid end_date format'}), 400
        
        # Alert level filtering
        if alert_level:
            query = query.filter(SensorReading.alert_level == alert_level)
        
        # Anomaly filtering
        if anomalies_only:
            query = query.filter(SensorReading.is_anomaly == True)
        
        # Order by timestamp descending
        query = query.order_by(SensorReading.timestamp.desc())
        
        # Paginate
        paginated = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Convert to dictionaries
        readings_data = [reading.to_dict() for reading in paginated.items]
        
        return jsonify({
            'readings': readings_data,
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'pages': paginated.pages
        })
        
    except Exception as e:
        logger.error(f"Error getting history data: {str(e)}")
        return jsonify({'error': 'Failed to get history data'}), 500

@history_bp.route('/export')
@swag_from({
    'tags': ['History'],
    'summary': 'Export historical data',
    'description': 'Export historical data as CSV',
    'parameters': [
        {
            'name': 'start_date',
            'in': 'query',
            'type': 'string',
            'format': 'date',
            'description': 'Start date (YYYY-MM-DD)'
        },
        {
            'name': 'end_date',
            'in': 'query',
            'type': 'string',
            'format': 'date',
            'description': 'End date (YYYY-MM-DD)'
        }
    ],
    'responses': {
        200: {
            'description': 'CSV data exported successfully',
            'headers': {
                'Content-Type': 'text/csv',
                'Content-Disposition': 'attachment; filename=sensor_data.csv'
            }
        }
    }
})
def export_data():
    """Export historical data as CSV"""
    try:
        import csv
        from io import StringIO
        from flask import Response
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Build query
        query = SensorReading.query
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(SensorReading.timestamp >= start_dt)
            except ValueError:
                return jsonify({'error': 'Invalid start_date format'}), 400
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(SensorReading.timestamp < end_dt)
            except ValueError:
                return jsonify({'error': 'Invalid end_date format'}), 400
        
        # Get data ordered by timestamp
        readings = query.order_by(SensorReading.timestamp.asc()).all()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Timestamp', 'Vibration', 'Strain', 'Temperature',
            'Is Anomaly', 'Anomaly Score', 'Alert Level', 'Alert Sent'
        ])
        
        # Write data
        for reading in readings:
            writer.writerow([
                reading.id,
                reading.timestamp.isoformat(),
                reading.vibration,
                reading.strain,
                reading.temperature,
                reading.is_anomaly,
                reading.anomaly_score,
                reading.alert_level,
                reading.alert_sent
            ])
        
        # Prepare response
        csv_data = output.getvalue()
        filename = f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        return jsonify({'error': 'Failed to export data'}), 500

@history_bp.route('/charts')
@swag_from({
    'tags': ['History'],
    'summary': 'Get chart data',
    'description': 'Get aggregated data for historical charts',
    'parameters': [
        {
            'name': 'period',
            'in': 'query',
            'type': 'string',
            'enum': ['hour', 'day', 'week', 'month'],
            'default': 'day',
            'description': 'Aggregation period'
        },
        {
            'name': 'days',
            'in': 'query',
            'type': 'integer',
            'default': 7,
            'description': 'Number of days to include'
        }
    ],
    'responses': {
        200: {
            'description': 'Chart data retrieved successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'labels': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'datasets': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'label': {'type': 'string'},
                                'data': {
                                    'type': 'array',
                                    'items': {'type': 'number'}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
})
def get_chart_data():
    """Get aggregated data for charts"""
    try:
        period = request.args.get('period', 'day')
        days = request.args.get('days', 7, type=int)
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get readings in date range
        readings = SensorReading.query.filter(
            SensorReading.timestamp >= start_date,
            SensorReading.timestamp <= end_date
        ).order_by(SensorReading.timestamp.asc()).all()
        
        if not readings:
            return jsonify({
                'labels': [],
                'datasets': []
            })
        
        # Group by time period
        from collections import defaultdict
        
        grouped_data = defaultdict(list)
        
        for reading in readings:
            if period == 'hour':
                key = reading.timestamp.strftime('%Y-%m-%d %H:00')
            elif period == 'day':
                key = reading.timestamp.strftime('%Y-%m-%d')
            elif period == 'week':
                # Get start of week
                start_of_week = reading.timestamp - timedelta(days=reading.timestamp.weekday())
                key = start_of_week.strftime('%Y-%m-%d')
            else:  # month
                key = reading.timestamp.strftime('%Y-%m')
            
            grouped_data[key].append(reading)
        
        # Calculate averages for each group
        labels = []
        vibration_data = []
        strain_data = []
        temperature_data = []
        
        for key in sorted(grouped_data.keys()):
            readings_group = grouped_data[key]
            
            avg_vibration = sum(r.vibration for r in readings_group) / len(readings_group)
            avg_strain = sum(r.strain for r in readings_group) / len(readings_group)
            avg_temperature = sum(r.temperature for r in readings_group) / len(readings_group)
            
            labels.append(key)
            vibration_data.append(round(avg_vibration, 2))
            strain_data.append(round(avg_strain, 3))
            temperature_data.append(round(avg_temperature, 1))
        
        return jsonify({
            'labels': labels,
            'datasets': [
                {
                    'label': 'Vibration',
                    'data': vibration_data,
                    'borderColor': 'rgb(13, 110, 253)',
                    'backgroundColor': 'rgba(13, 110, 253, 0.1)'
                },
                {
                    'label': 'Strain',
                    'data': strain_data,
                    'borderColor': 'rgb(255, 193, 7)',
                    'backgroundColor': 'rgba(255, 193, 7, 0.1)'
                },
                {
                    'label': 'Temperature',
                    'data': temperature_data,
                    'borderColor': 'rgb(13, 202, 240)',
                    'backgroundColor': 'rgba(13, 202, 240, 0.1)'
                }
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting chart data: {str(e)}")
        return jsonify({'error': 'Failed to get chart data'}), 500