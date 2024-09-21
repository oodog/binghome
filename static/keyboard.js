// static/keyboard.js

document.addEventListener('DOMContentLoaded', () => {
    const keyboard = document.getElementById('on-screen-keyboard');
    const inputs = document.querySelectorAll('input[type="text"], textarea');

    inputs.forEach(input => {
        input.addEventListener('focus', () => {
            showKeyboard();
        });

        input.addEventListener('blur', () => {
            // Optionally hide the keyboard when the input loses focus
            // Uncomment the next line if you want this behavior
            // hideKeyboard();
        });
    });

    function showKeyboard() {
        keyboard.style.display = 'flex';
    }

    function hideKeyboard() {
        keyboard.style.display = 'none';
    }

    window.typeKey = function(char) {
        const activeElement = document.activeElement;
        if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
            const start = activeElement.selectionStart;
            const end = activeElement.selectionEnd;
            const value = activeElement.value;
            activeElement.value = value.substring(0, start) + char + value.substring(end);
            activeElement.selectionStart = activeElement.selectionEnd = start + 1;
            activeElement.focus();
        }
    }

    window.closeKeyboard = function() {
        hideKeyboard();
    }
});
