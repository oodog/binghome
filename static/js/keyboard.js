// static/js/keyboard.js

// Function to show the on-screen keyboard
function showKeyboard() {
    document.getElementById('on-screen-keyboard').style.display = 'flex';
}

// Function to close the on-screen keyboard
function closeKeyboard() {
    document.getElementById('on-screen-keyboard').style.display = 'none';
}

// Function to insert a character into the focused input
function insertCharacter(char) {
    const activeElement = document.activeElement;
    if (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA') {
        const start = activeElement.selectionStart;
        const end = activeElement.selectionEnd;
        const value = activeElement.value;
        activeElement.value = value.substring(0, start) + char + value.substring(end);
        activeElement.selectionStart = activeElement.selectionEnd = start + char.length;
        activeElement.focus();
    }
}

// Event listeners for input fields to show the keyboard
document.addEventListener('DOMContentLoaded', () => {
    const inputs = document.querySelectorAll('input[type="text"], input[type="password"], textarea');
    inputs.forEach(input => {
        input.addEventListener('focus', showKeyboard);
    });
});
