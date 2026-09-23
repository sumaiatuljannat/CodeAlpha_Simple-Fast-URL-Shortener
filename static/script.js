/**
 * LinkSnap URL Shortener - Client-side Utilities
 */

/**
 * Copies the shortened URL to the system clipboard and provides visual feedback.
 * @param {string} text - The URL to copy.
 */
function copyToClipboard(text) {
    if (!navigator.clipboard) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            updateCopyButtonSuccess();
        } catch (err) {
            console.error('Fallback copy failed:', err);
        }
        document.body.removeChild(textarea);
        return;
    }

    navigator.clipboard.writeText(text).then(function() {
        updateCopyButtonSuccess();
    }).catch(function(err) {
        console.error('Failed to copy text: ', err);
    });
}

/**
 * Updates copy button UI to indicate success and resets after 2 seconds.
 */
function updateCopyButtonSuccess() {
    const copyBtnText = document.getElementById('copyBtnText');
    const copyBtnIcon = document.getElementById('copyBtnIcon');
    const copyBtn = document.getElementById('copyBtn');

    if (copyBtnText && copyBtnIcon) {
        const originalText = copyBtnText.innerText;
        const originalIcon = copyBtnIcon.innerText;

        copyBtnText.innerText = 'Copied!';
        copyBtnIcon.innerText = '✅';
        if (copyBtn) copyBtn.style.backgroundColor = '#dcfce7';

        setTimeout(() => {
            copyBtnText.innerText = originalText;
            copyBtnIcon.innerText = originalIcon;
            if (copyBtn) copyBtn.style.backgroundColor = '';
        }, 2000);
    }
}

/**
 * Handles the quick stats lookup form submission.
 * Extracts the entered code and redirects the browser to /stats/<code_entered>
 * @param {Event} event - The form submit event.
 */
function handleStatsLookup(event) {
    event.preventDefault();
    const input = document.getElementById('statsCodeInput');
    if (!input) return;

    let code = input.value.trim();
    // Handle cases where user pastes the entire shortened link (e.g. http://localhost:5000/abc123)
    if (code.includes('/')) {
        const parts = code.split('/');
        code = parts[parts.length - 1];
    }

    if (code) {
        window.location.href = '/stats/' + encodeURIComponent(code);
    }
}
