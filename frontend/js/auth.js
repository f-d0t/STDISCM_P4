/**
 * Authentication utilities
 */

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return !!localStorage.getItem('auth_token');
}

/**
 * Get current user role
 */
function getUserRole() {
    return localStorage.getItem('user_role');
}

/**
 * Get current username
 */
function getUsername() {
    return localStorage.getItem('username');
}

/**
 * Redirect to login if not authenticated
 */
async function requireAuth() {
    if (!isAuthenticated()) {
        console.log('Not authenticated - no token found');
        window.location.href = 'index.html';
        return false;
    }

    // Verify token is still valid
    try {
        console.log('Verifying authentication...');
        const result = await api.verifyAuth();
        console.log('Authentication verified:', result);
        return true;
    } catch (error) {
        // Token invalid, redirect to login
        console.error('Authentication verification failed:', error);
        console.error('Error details:', error.message);
        api.removeToken();
        alert('Session expired. Please login again.\nError: ' + error.message);
        window.location.href = 'index.html';
        return false;
    }
}

/**
 * Redirect based on user role
 */
function redirectByRole() {
    const role = getUserRole();
    if (role === 'student' || role === 'faculty') {
        window.location.href = 'dashboard.html';
    } else {
        window.location.href = 'index.html';
    }
}

