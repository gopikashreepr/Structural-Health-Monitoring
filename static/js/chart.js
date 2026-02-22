// Chart.js configuration for real-time sensor data visualization

// Global variables for charts and data
let vibrationChart, strainChart, temperatureChart;
let isConnected = false;
let updateInterval;

// Chart configuration options
const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
        x: {
            display: true,
            title: {
                display: true,
                text: 'Time'
            },
            grid: {
                color: 'rgba(255, 255, 255, 0.1)'
            }
        },
        y: {
            display: true,
            grid: {
                color: 'rgba(255, 255, 255, 0.1)'
            }
        }
    },
    plugins: {
        legend: {
            display: false
        }
    },
    animation: {
        duration: 300
    }
};

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    startDataUpdates();
});

// Initialize all three charts
function initializeCharts() {
    // Vibration Chart
    const vibrationCtx = document.getElementById('vibrationChart').getContext('2d');
    vibrationChart = new Chart(vibrationCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Vibration',
                data: [],
                borderColor: 'rgb(13, 110, 253)',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            ...chartOptions,
            scales: {
                ...chartOptions.scales,
                y: {
                    ...chartOptions.scales.y,
                    title: {
                        display: true,
                        text: 'Vibration (Units)'
                    },
                    min: 0,
                    max: 3.5
                }
            }
        }
    });

    // Strain Chart
    const strainCtx = document.getElementById('strainChart').getContext('2d');
    strainChart = new Chart(strainCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Strain',
                data: [],
                borderColor: 'rgb(255, 193, 7)',
                backgroundColor: 'rgba(255, 193, 7, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            ...chartOptions,
            scales: {
                ...chartOptions.scales,
                y: {
                    ...chartOptions.scales.y,
                    title: {
                        display: true,
                        text: 'Strain (Units)'
                    },
                    min: 0,
                    max: 1.0
                }
            }
        }
    });

    // Temperature Chart
    const temperatureCtx = document.getElementById('temperatureChart').getContext('2d');
    temperatureChart = new Chart(temperatureCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Temperature',
                data: [],
                borderColor: 'rgb(13, 202, 240)',
                backgroundColor: 'rgba(13, 202, 240, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            ...chartOptions,
            scales: {
                ...chartOptions.scales,
                y: {
                    ...chartOptions.scales.y,
                    title: {
                        display: true,
                        text: 'Temperature (°C)'
                    },
                    min: 15,
                    max: 45
                }
            }
        }
    });
}

// Start periodic data updates
function startDataUpdates() {
    updateInterval = setInterval(fetchSensorData, 2000);
    fetchSensorData(); // Initial fetch
}

// Fetch sensor data from the API
async function fetchSensorData() {
    try {
        const response = await fetch('/sensor-data');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        updateCharts(data);
        updateStatusIndicators(data);
        setConnectionStatus(true);
        
    } catch (error) {
        console.error('Error fetching sensor data:', error);
        setConnectionStatus(false);
    }
}

// Update all charts with new data
function updateCharts(data) {
    // Generate local timestamp for chart labels
    const now = new Date();
    const timestamp = now.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    const maxDataPoints = 20; // Keep only last 20 data points

    // Update vibration chart
    vibrationChart.data.labels.push(timestamp);
    vibrationChart.data.datasets[0].data.push(data.vibration);
    
    if (vibrationChart.data.labels.length > maxDataPoints) {
        vibrationChart.data.labels.shift();
        vibrationChart.data.datasets[0].data.shift();
    }
    
    vibrationChart.update('none');

    // Update strain chart
    strainChart.data.labels.push(timestamp);
    strainChart.data.datasets[0].data.push(data.strain);
    
    if (strainChart.data.labels.length > maxDataPoints) {
        strainChart.data.labels.shift();
        strainChart.data.datasets[0].data.shift();
    }
    
    strainChart.update('none');

    // Update temperature chart
    temperatureChart.data.labels.push(timestamp);
    temperatureChart.data.datasets[0].data.push(data.temperature);
    
    if (temperatureChart.data.labels.length > maxDataPoints) {
        temperatureChart.data.labels.shift();
        temperatureChart.data.datasets[0].data.shift();
    }
    
    temperatureChart.update('none');
}

// Update status indicators with current values
function updateStatusIndicators(data) {
    const vibrationValue = document.getElementById('vibration-value');
    const strainValue = document.getElementById('strain-value');
    const temperatureValue = document.getElementById('temperature-value');
    
    // Update values with animation
    animateValueChange(vibrationValue, data.vibration);
    animateValueChange(strainValue, data.strain);
    animateValueChange(temperatureValue, data.temperature + '°C');
    
    // Update last update timestamp with local time
    const lastUpdateElement = document.getElementById('last-update');
    if (lastUpdateElement) {
        // Convert timestamp to local time
        const now = new Date();
        const localTime = now.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        lastUpdateElement.textContent = localTime;
    }
    
    // Handle alerts
    if (data.alert_level && data.alert_level !== 'normal') {
        showAlert(data.alert_level, data.alert_messages);
    }
    
    // Update card styling based on alert level
    updateCardStyling(data.alert_level);
}

// Animate value changes
function animateValueChange(element, newValue) {
    element.classList.add('value-updated');
    element.textContent = newValue;
    
    setTimeout(() => {
        element.classList.remove('value-updated');
    }, 200);
}

// Set connection status
function setConnectionStatus(connected) {
    const connectedElement = document.getElementById('status-connected');
    const disconnectedElement = document.getElementById('status-disconnected');
    
    if (connected && !isConnected) {
        connectedElement.style.display = 'block';
        disconnectedElement.style.display = 'none';
        isConnected = true;
    } else if (!connected && isConnected) {
        connectedElement.style.display = 'none';
        disconnectedElement.style.display = 'block';
        isConnected = false;
    }
}

// Handle page visibility changes to pause/resume updates
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        clearInterval(updateInterval);
    } else {
        startDataUpdates();
    }
});

// Handle errors and reconnection
window.addEventListener('online', function() {
    setConnectionStatus(true);
    startDataUpdates();
});

window.addEventListener('offline', function() {
    setConnectionStatus(false);
    clearInterval(updateInterval);
});

// Alert handling functions
function showAlert(level, messages) {
    const alertBanner = document.getElementById('alert-banner');
    const alertMessage = document.getElementById('alert-message');
    
    if (alertBanner && alertMessage) {
        alertMessage.textContent = messages.join(', ');
        alertBanner.className = `alert alert-${level === 'critical' ? 'danger' : 'warning'}`;
        alertBanner.style.display = 'block';
        
        // Auto-hide after 10 seconds
        setTimeout(() => {
            alertBanner.style.display = 'none';
        }, 10000);
    }
}

function hideAlert() {
    const alertBanner = document.getElementById('alert-banner');
    if (alertBanner) {
        alertBanner.style.display = 'none';
    }
}

function updateCardStyling(alertLevel) {
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        // Remove existing alert classes
        card.classList.remove('border-warning', 'border-danger', 'border-success');
        
        // Add appropriate border based on alert level
        if (alertLevel === 'critical') {
            card.classList.add('border-danger');
        } else if (alertLevel === 'warning') {
            card.classList.add('border-warning');
        } else {
            card.classList.add('border-success');
        }
    });
}
