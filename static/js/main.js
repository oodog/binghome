// static/js/main.js

// Clock Functionality
function updateClock() {
    const clockElement = document.getElementById('clock');
    const dateElement = document.getElementById('date');
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    const day = now.toLocaleDateString('en-US', { weekday: 'long' });
    const date = now.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    dateElement.textContent = `${day}, ${date}`;
    clockElement.textContent = `${hours}:${minutes}:${seconds}`;
}
setInterval(updateClock, 1000);
updateClock(); // Initial call

// Fetch and Display Wi-Fi Strength
function fetchWifiStrength() {
    fetch('/wifi_strength')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const strength = data.signal_strength;
            document.getElementById('wifi').textContent = `Wi-Fi: ${strength}%`;
        })
        .catch(error => {
            console.error('Error fetching Wi-Fi strength:', error);
            document.getElementById('wifi').textContent = 'Wi-Fi: --%';
        });
}

// Fetch Wi-Fi Strength on Load and Every Minute
fetchWifiStrength();
setInterval(fetchWifiStrength, 60000); // 60,000 ms = 1 minute

// Fetch News Dynamically
function fetchNews() {
    fetch('/get_news')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const newsList = document.getElementById('news-list');
            newsList.innerHTML = '';
            if (data.news_items.length === 0) {
                newsList.innerHTML = '<li>No news available.</li>';
                return;
            }
            data.news_items.forEach(item => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = item.link;
                a.target = '_blank';
                a.textContent = item.title;
                a.onclick = openNews;
                li.appendChild(a);
                newsList.appendChild(li);
            });
        })
        .catch(error => {
            console.error('Error fetching news:', error);
            const newsList = document.getElementById('news-list');
            newsList.innerHTML = '<li>No news available.</li>';
        });
}

// Fetch news every 10 minutes
setInterval(fetchNews, 600000); // 600,000 ms = 10 minutes

// Initial fetch on load
window.onload = fetchNews;

// Dark Mode Toggle
const toggleSwitch = document.getElementById('dark-mode-toggle');
toggleSwitch.addEventListener('change', () => {
    if (toggleSwitch.checked) {
        document.body.classList.add('dark-mode');
        localStorage.setItem('darkMode', 'enabled');
    } else {
        document.body.classList.remove('dark-mode');
        localStorage.setItem('darkMode', 'disabled');
    }
});

// Apply Dark Mode based on saved preference
const darkMode = localStorage.getItem('darkMode');
if (darkMode === 'enabled') {
    toggleSwitch.checked = true;
    document.body.classList.add('dark-mode');
}

// Loading Overlay Controls
function showLoading() {
    document.getElementById('loading').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// Show Loading Indicator when connecting to Wi-Fi
function connectWifi() {
    showLoading();
    // Assume there's a form submission or AJAX call here
}

// Listen for form submissions to show loading
document.addEventListener('DOMContentLoaded', () => {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', () => {
            showLoading();
        });
    });
});

// Logout Function
function logout() {
    // Redirect to logout route
    window.location.href = '/logout';
}

// Handle News Link Click to Prevent Losing State (Optional)
function openNews(event) {
    // Implement if needed
}

// Inactivity Dimming and Clock Display
let inactivityTimer;
const inactivityLimit = 1800000; // 30 minutes in milliseconds

function resetInactivityTimer() {
    clearTimeout(inactivityTimer);
    hideDim();
    inactivityTimer = setTimeout(dimScreen, inactivityLimit);
}

function dimScreen() {
    document.getElementById('dim-overlay').style.display = 'flex';
    updateDimClock();
}

function hideDim() {
    document.getElementById('dim-overlay').style.display = 'none';
}

function updateDimClock() {
    const dimClock = document.getElementById('dim-clock-time');
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    dimClock.textContent = `${hours}:${minutes}`;
    // Update every minute
    setInterval(() => {
        const now = new Date();
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        dimClock.textContent = `${hours}:${minutes}`;
    }, 60000);
}

// Initialize inactivity timer
function initializeInactivityTimer() {
    window.onload = resetInactivityTimer;
    document.onmousemove = resetInactivityTimer;
    document.onkeypress = resetInactivityTimer;
    document.onclick = resetInactivityTimer;
    document.ontouchstart = resetInactivityTimer;
}

initializeInactivityTimer();

// Background Image Fading
let currentImageIndex = 0;
const images = document.querySelectorAll('.image-display');
const totalImages = images.length;

function fadeImages() {
    images.forEach((img, index) => {
        img.classList.remove('fade-in');
        if (index === currentImageIndex) {
            img.classList.add('fade-in');
        }
    });
    currentImageIndex = (currentImageIndex + 1) % totalImages;
}

// Initial fade
fadeImages();

// Set interval for fading every 30 seconds
setInterval(fadeImages, 30000);
