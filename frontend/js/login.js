/**
 * Login page functionality
 */

document.addEventListener('DOMContentLoaded', () => {
    // Redirect if already logged in
    if (isAuthenticated()) {
        redirectByRole();
        return;
    }

    const loginForm = document.getElementById('loginForm');
    const errorMessage = document.getElementById('errorMessage');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorMessage.classList.remove('show');
        errorMessage.textContent = '';

        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const loginBtn = document.getElementById('loginBtn');
        const loginBtnText = document.getElementById('loginBtnText');
        const loginBtnSpinner = document.getElementById('loginBtnSpinner');

        // Disable button and show loading state
        loginBtn.disabled = true;
        loginBtnText.style.display = 'none';
        loginBtnSpinner.style.display = 'inline';

        try {
            const response = await api.login(username, password);
            
            // Store token and user info in localStorage
            // (Already done in api.login, but we verify here)
            if (response.access_token) {
                // Redirect to dashboard
                redirectByRole();
            } else {
                throw new Error('No access token received');
            }
        } catch (error) {
            errorMessage.textContent = error.message || 'Login failed. Please check your credentials.';
            errorMessage.classList.add('show');
            
            // Re-enable button
            loginBtn.disabled = false;
            loginBtnText.style.display = 'inline';
            loginBtnSpinner.style.display = 'none';
        }
    });
});

