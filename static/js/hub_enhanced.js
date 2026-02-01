/**
 * BingHome Hub Enhanced - Optimized for 7" Touchscreen
 */

// Global variables
const socket = io();
let settings = {};
let recognition = null;
let weatherView = 'current';
let navigationHistory = [];

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initializeHub();
    setupVoiceRecognition();
    startDataUpdates();
    setupNavigation();
    updateClock();
});

function initializeHub() {
    // Load settings
    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            settings = data;
            updatePhotosWidget();
        });

    // Update weather
    updateWeather();

    // Update network status
    updateNetworkStatus();

    // Check for weather alerts
    checkWeatherAlerts();
}

// Socket handlers
socket.on('connect', function() {
    console.log('Connected to BingHome Hub');
});

socket.on('sensor_update', function(data) {
    document.getElementById('tempValue').textContent =
        data.temperature ? data.temperature.toFixed(1) : '--';
    document.getElementById('humidityValue').textContent =
        data.humidity ? data.humidity.toFixed(1) : '--';
    document.getElementById('airQuality').textContent =
        data.air_quality ? capitalizeFirst(data.air_quality) : 'Unknown';
});

socket.on('wake_word_detected', function() {
    showVoiceOverlay();
});

socket.on('voice_response', function(data) {
    if (data.command) {
        document.getElementById('voiceCommand').textContent = `"${data.command}"`;
    }
    if (data.response) {
        document.getElementById('voiceStatus').textContent = data.response;
    }
    setTimeout(hideVoiceOverlay, 3000);
});

socket.on('weather_alert', function(data) {
    showAlert(data.message, data.severity || 'warning');
});

// Voice Recognition
function setupVoiceRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = function(event) {
            const last = event.results.length - 1;
            const command = event.results[last][0].transcript.toLowerCase();

            // Check for wake word
            const wakeWords = settings.wake_words || ['hey bing', 'okay bing'];
            for (let wake of wakeWords) {
                if (command.includes(wake)) {
                    showVoiceOverlay();
                    const actualCommand = command.replace(wake, '').trim();
                    if (actualCommand) {
                        processVoiceCommand(actualCommand);
                    }
                    break;
                }
            }
        };

        recognition.onerror = function(event) {
            console.error('Voice recognition error:', event.error);
        };

        // Start recognition
        try {
            recognition.start();
            showVoiceIndicator();
        } catch (e) {
            console.log('Voice recognition already started');
        }

        // Restart if stopped
        recognition.onend = function() {
            try {
                recognition.start();
            } catch (e) {
                console.log('Could not restart recognition');
            }
        };
    }
}

function showVoiceOverlay() {
    document.getElementById('voiceOverlay').classList.add('active');
    document.getElementById('voiceStatus').textContent = 'Listening...';
    document.getElementById('voiceCommand').textContent = '';
}

function hideVoiceOverlay() {
    document.getElementById('voiceOverlay').classList.remove('active');
}

function showVoiceIndicator() {
    document.getElementById('voiceIndicator').classList.add('active');
}

function hideVoiceIndicator() {
    document.getElementById('voiceIndicator').classList.remove('active');
}

function processVoiceCommand(command) {
    document.getElementById('voiceCommand').textContent = `"${command}"`;

    socket.emit('voice_command', {
        command: command
    });

    // Local command handling
    if (command.includes('weather')) {
        updateWeather();
        document.getElementById('voiceStatus').textContent = 'Showing weather...';
    } else if (command.includes('netflix') || command.includes('watch')) {
        launchApp('netflix');
        hideVoiceOverlay();
    } else if (command.includes('youtube')) {
        launchApp('youtube');
        hideVoiceOverlay();
    } else if (command.includes('spotify') || command.includes('music')) {
        launchApp('spotify');
        hideVoiceOverlay();
    } else if (command.includes('home') || command.includes('go back')) {
        closeApp();
        hideVoiceOverlay();
    } else if (command.includes('settings')) {
        openSettings();
        hideVoiceOverlay();
    } else if (command.includes('devices')) {
        openDevices();
        hideVoiceOverlay();
    }
}

// Network Status
function updateNetworkStatus() {
    fetch('/api/network_status')
        .then(response => response.json())
        .then(data => {
            const networkType = document.getElementById('networkType');
            if (data.ethernet && data.ethernet.connected) {
                networkType.textContent = 'Ethernet';
            } else if (data.wifi && data.wifi.connected) {
                networkType.textContent = data.wifi.ssid || 'WiFi';
            } else {
                networkType.textContent = 'Offline';
            }
        })
        .catch(error => console.error('Network status error:', error));
}

// Weather
function updateWeather() {
    fetch('/api/weather/comprehensive')
        .then(response => response.json())
        .then(data => {
            if (data.current) {
                const current = data.current;
                document.getElementById('weatherTemp').textContent = `${current.temp}°`;
                document.getElementById('weatherDesc').textContent = current.description || '--';
                document.getElementById('weatherLocation').textContent = current.location || 'Your Location';
                document.getElementById('weatherHumidity').textContent = `${current.humidity}%`;
                document.getElementById('weatherWind').textContent = `${current.wind_speed} km/h`;
                document.getElementById('weatherFeels').textContent = `${current.feels_like || current.temp}°`;

                // Update icon based on condition
                const iconMap = {
                    'Clear': '☀️',
                    'Clouds': '☁️',
                    'Rain': '🌧️',
                    'Snow': '❄️',
                    'Thunderstorm': '⛈️',
                    'Drizzle': '🌦️',
                    'Mist': '🌫️',
                    'Partly Cloudy': '⛅'
                };
                document.getElementById('weatherIcon').textContent =
                    iconMap[current.condition] || '🌤️';
            }

            if (data.forecast && data.forecast.length > 0) {
                const forecastEl = document.getElementById('weatherForecast');
                forecastEl.innerHTML = data.forecast.slice(0, 4).map(day => {
                    const date = new Date(day.date);
                    return `
                        <div class="forecast-day">
                            <div style="color: var(--text-secondary); margin-bottom: 3px;">
                                ${date.toLocaleDateString('en', {weekday: 'short'})}
                            </div>
                            <div style="font-size: 16px;">${getWeatherEmoji(day.condition)}</div>
                            <div class="forecast-temp">${day.temp_min}°/${day.temp_max}°</div>
                        </div>
                    `;
                }).join('');
            }

            // Update radar URL if available
            if (data.radar && data.radar.available) {
                document.getElementById('radarFrame').src = data.radar.url;
            }

            // Check for alerts
            if (data.alerts && data.alerts.length > 0) {
                showAlert(data.alerts[0].description, data.alerts[0].severity);
            }
        })
        .catch(error => console.error('Weather error:', error));
}

function toggleWeatherView() {
    const mainView = document.getElementById('weatherMain');
    const radarView = document.getElementById('weatherRadar');

    if (weatherView === 'current') {
        mainView.style.display = 'none';
        radarView.classList.add('active');
        weatherView = 'radar';
    } else {
        mainView.style.display = 'block';
        radarView.classList.remove('active');
        weatherView = 'current';
    }
}

function getWeatherEmoji(condition) {
    const iconMap = {
        'Clear': '☀️',
        'Sunny': '☀️',
        'Clouds': '☁️',
        'Cloudy': '☁️',
        'Rain': '🌧️',
        'Snow': '❄️',
        'Thunderstorm': '⛈️',
        'Drizzle': '🌦️',
        'Mist': '🌫️',
        'Partly Cloudy': '⛅',
        'Light Rain': '🌦️'
    };
    return iconMap[condition] || '🌤️';
}

function checkWeatherAlerts() {
    // Periodically check for weather alerts
    setInterval(() => {
        fetch('/api/weather/comprehensive')
            .then(response => response.json())
            .then(data => {
                if (data.alerts && data.alerts.length > 0) {
                    const alert = data.alerts[0];
                    if (alert.severity === 'high') {
                        showAlert(alert.title + ': ' + alert.description, 'danger');
                    }
                }
            })
            .catch(error => console.error('Weather alert check error:', error));
    }, 300000); // Check every 5 minutes
}

// Google Photos
function updatePhotosWidget() {
    const photosFrame = document.getElementById('photosFrame');

    if (settings.apps && settings.apps.google_photos && settings.apps.google_photos.enabled) {
        photosFrame.src = settings.apps.google_photos.url;
    }
}

// App Launcher
function launchApp(appName) {
    const externalApps = {
        'netflix': 'https://www.netflix.com',
        'youtube': 'https://www.youtube.com',
        'spotify': 'https://open.spotify.com',
        'prime': 'https://www.primevideo.com',
        'prime_video': 'https://www.primevideo.com',
        'xbox': 'https://www.xbox.com/play',
        'xbox_cloud': 'https://www.xbox.com/play',
        'disney_plus': 'https://www.disneyplus.com'
    };
    
    if (externalApps[appName]) {
        window.location.href = externalApps[appName];
    } else {
        const pages = {
            'devices': '/devices',
            'timers': '/timers',
            'routines': '/routines',
            'shopping': '/shopping',
            'calendar': '/calendar',
            'intercom': '/intercom',
            'settings': '/settings',
            'news': '/news'
        };
        if (pages[appName]) {
            window.location.href = pages[appName];
        }
    }
}

function closeApp() {
    const appFrame = document.getElementById('appFrame');
    const iframe = document.getElementById('appIframe');

    appFrame.classList.remove('active');

    setTimeout(() => {
        iframe.src = '';
        navigationHistory = [];
    }, 300);
}

function openSettings() {
    navigationHistory.push('home');
    window.location.href = '/settings';
}

function openDevices() {
    navigationHistory.push('home');
    window.location.href = '/devices';
}

function openTimers() {
    navigationHistory.push('home');
    window.location.href = '/timers';
}

function openNews() {
    navigationHistory.push('home');
    window.location.href = '/news';
}

function openCamera() {
    navigationHistory.push('home');
    window.location.href = '/cameras';
}

function openMusic() {
    launchApp('spotify');
}

// Navigation
function setupNavigation() {
    // Add swipe gestures for back navigation
    let touchStartX = 0;
    let touchStartY = 0;

    document.addEventListener('touchstart', function(e) {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;

        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;

        // Swipe right from left edge to go back
        if (touchStartX < 50 && deltaX > 100 && Math.abs(deltaY) < 50) {
            closeApp();
        }
    }, { passive: true });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' || e.key === 'Backspace') {
            closeApp();
            hideVoiceOverlay();
        } else if (e.key === 'Home') {
            window.location.href = '/';
        }
    });
}

// Alerts
function showAlert(message, severity = 'warning') {
    const banner = document.getElementById('alertBanner');
    const messageEl = document.getElementById('alertMessage');

    messageEl.textContent = message;
    banner.className = 'alert-banner active';

    if (severity === 'danger') {
        banner.style.background = 'var(--danger)';
    } else if (severity === 'warning') {
        banner.style.background = 'var(--warning)';
    } else {
        banner.style.background = 'var(--success)';
    }

    // Auto-hide after 10 seconds
    setTimeout(hideAlert, 10000);
}

function hideAlert() {
    document.getElementById('alertBanner').classList.remove('active');
}

// Clock
function updateClock() {
    const timeEl = document.getElementById('currentTime');

    function update() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        timeEl.textContent = `${hours}:${minutes}`;
    }

    update();
    setInterval(update, 1000);
}

// Auto-refresh
function startDataUpdates() {
    // Update sensors every 5 seconds
    setInterval(() => {
        socket.emit('request_sensor_data');
    }, 5000);

    // Update weather every 10 minutes
    setInterval(updateWeather, 600000);

    // Update network status every 30 seconds
    setInterval(updateNetworkStatus, 30000);
}

// Utility functions
function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// Prevent accidental navigation
window.addEventListener('beforeunload', function(e) {
    // Only show warning if in kiosk mode
    if (settings.kiosk_mode) {
        e.preventDefault();
        e.returnValue = '';
    }
});
