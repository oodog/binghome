/**
 * BingHome Navigation and Gesture Handler
 * Handles touch gestures, keyboard shortcuts, and navigation
 */

class BingHomeNavigation {
    constructor() {
        this.startX = 0;
        this.startY = 0;
        this.startTime = 0;
        this.lastTap = 0;
        this.swipeThreshold = 50;
        this.timeThreshold = 300;
        this.doubleTapThreshold = 500;
        
        this.init();
    }
    
    init() {
        this.setupGestureHandlers();
        this.setupKeyboardShortcuts();
        this.setupVolumeControls();
    }
    
    setupGestureHandlers() {
        // Touch start handler
        document.addEventListener('touchstart', (e) => {
            this.startX = e.touches[0].clientX;
            this.startY = e.touches[0].clientY;
            this.startTime = Date.now();
        }, { passive: true });
        
        // Touch end handler for swipe gestures
        document.addEventListener('touchend', (e) => {
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const endTime = Date.now();
            
            const deltaX = endX - this.startX;
            const deltaY = endY - this.startY;
            const deltaTime = endTime - this.startTime;
            
            // Handle swipe gestures
            this.handleSwipeGesture(deltaX, deltaY, deltaTime);
            
            // Handle double tap for home
            this.handleDoubleTap(e, endTime);
        }, { passive: true });
        
        // Pinch gesture for home (using touch events)
        let initialDistance = 0;
        let currentDistance = 0;
        
        document.addEventListener('touchstart', (e) => {
            if (e.touches.length === 2) {
                initialDistance = this.getDistance(e.touches[0], e.touches[1]);
            }
        }, { passive: true });
        
        document.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2) {
                currentDistance = this.getDistance(e.touches[0], e.touches[1]);
            }
        }, { passive: true });
        
        document.addEventListener('touchend', (e) => {
            if (e.touches.length === 0 && initialDistance > 0 && currentDistance > 0) {
                const pinchRatio = currentDistance / initialDistance;
                
                // Pinch in gesture (zoom out) - go home
                if (pinchRatio < 0.7) {
                    this.goHome();
                }
                
                initialDistance = 0;
                currentDistance = 0;
            }
        }, { passive: true });
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Prevent default browser shortcuts where appropriate
            switch(e.key) {
                case 'Escape':
                case 'Backspace':
                    e.preventDefault();
                    this.goBack();
                    break;
                    
                case 'Home':
                    e.preventDefault();
                    this.goHome();
                    break;
                    
                case 'F5':
                    e.preventDefault();
                    location.reload();
                    break;
                    
                case 'ArrowUp':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.volumeUp();
                    }
                    break;
                    
                case 'ArrowDown':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.volumeDown();
                    }
                    break;
                    
                case 'm':
                case 'M':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.toggleMute();
                    }
                    break;
                    
                case 's':
                case 'S':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.goToSettings();
                    }
                    break;
            }
        });
    }
    
    setupVolumeControls() {
        // Volume control via hardware buttons (if available)
        if ('mediaSession' in navigator) {
            navigator.mediaSession.setActionHandler('seekforward', () => {
                this.volumeUp();
            });
            
            navigator.mediaSession.setActionHandler('seekbackward', () => {
                this.volumeDown();
            });
        }
    }
    
    handleSwipeGesture(deltaX, deltaY, deltaTime) {
        const absX = Math.abs(deltaX);
        const absY = Math.abs(deltaY);
        
        // Only process if within time threshold and movement is significant
        if (deltaTime > this.timeThreshold || (absX < this.swipeThreshold && absY < this.swipeThreshold)) {
            return;
        }
        
        // Determine swipe direction
        if (absX > absY) {
            // Horizontal swipe
            if (deltaX > 0) {
                // Swipe right - go back (if starting from left edge)
                if (this.startX < 50) {
                    this.goBack();
                }
            } else {
                // Swipe left - could be used for forward navigation
                this.handleSwipeLeft();
            }
        } else {
            // Vertical swipe
            if (deltaY > 0) {
                // Swipe down - could be used for refresh or menu
                this.handleSwipeDown();
            } else {
                // Swipe up - could be used for quick actions
                this.handleSwipeUp();
            }
        }
    }
    
    handleDoubleTap(e, currentTime) {
        const tapLength = currentTime - this.lastTap;
        
        if (tapLength < this.doubleTapThreshold && tapLength > 0) {
            // Ignore double taps on interactive elements
            const target = e.target;
            if (target.tagName !== 'BUTTON' && 
                target.tagName !== 'A' && 
                target.tagName !== 'INPUT' && 
                target.tagName !== 'SELECT' &&
                !target.closest('button') &&
                !target.closest('a')) {
                
                this.goHome();
            }
        }
        
        this.lastTap = currentTime;
    }
    
    handleSwipeLeft() {
        // Could be used for forward navigation or next page
        console.log('Swipe left detected');
    }
    
    handleSwipeDown() {
        // Could be used for refresh or pull-down menu
        if (typeof refreshData === 'function') {
            refreshData();
        }
    }
    
    handleSwipeUp() {
        // Could be used for quick settings or notifications
        this.goToSettings();
    }
    
    getDistance(touch1, touch2) {
        const dx = touch1.clientX - touch2.clientX;
        const dy = touch1.clientY - touch2.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    // Navigation methods
    goBack() {
        window.location.href = '/back';
    }
    
    goHome() {
        window.location.href = '/';
    }
    
    goToSettings() {
        window.location.href = '/settings';
    }
    
    // Volume control methods
    async volumeUp(step = 5) {
        try {
            const response = await fetch('/api/volume/up', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ step })
            });
            
            const data = await response.json();
            if (data.success) {
                this.showVolumeIndicator(data.volume);
            }
        } catch (error) {
            console.error('Volume up error:', error);
        }
    }
    
    async volumeDown(step = 5) {
        try {
            const response = await fetch('/api/volume/down', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ step })
            });
            
            const data = await response.json();
            if (data.success) {
                this.showVolumeIndicator(data.volume);
            }
        } catch (error) {
            console.error('Volume down error:', error);
        }
    }
    
    async toggleMute() {
        try {
            const response = await fetch('/api/volume/mute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            if (data.success) {
                this.showVolumeIndicator(data.volume, data.muted);
            }
        } catch (error) {
            console.error('Mute toggle error:', error);
        }
    }
    
    showVolumeIndicator(volume, muted = false) {
        // Create or update volume indicator
        let indicator = document.getElementById('volumeIndicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'volumeIndicator';
            indicator.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 20px 30px;
                border-radius: 15px;
                font-size: 24px;
                font-weight: bold;
                z-index: 10000;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                display: flex;
                align-items: center;
                gap: 15px;
                opacity: 0;
                transition: opacity 0.3s ease;
            `;
            document.body.appendChild(indicator);
        }
        
        // Update indicator content
        const icon = muted ? '🔇' : (volume > 50 ? '🔊' : volume > 0 ? '🔉' : '🔇');
        const text = muted ? 'Muted' : `${volume}%`;
        
        indicator.innerHTML = `
            <span style="font-size: 32px;">${icon}</span>
            <span>${text}</span>
        `;
        
        // Show indicator
        indicator.style.opacity = '1';
        
        // Hide after 2 seconds
        setTimeout(() => {
            if (indicator) {
                indicator.style.opacity = '0';
                setTimeout(() => {
                    if (indicator && indicator.parentNode) {
                        indicator.parentNode.removeChild(indicator);
                    }
                }, 300);
            }
        }, 2000);
    }
    
    // Utility methods
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// Initialize navigation when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.bingHomeNav = new BingHomeNavigation();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BingHomeNavigation;
}
