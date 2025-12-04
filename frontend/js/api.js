/**
 * API Client for Enrollment System
 * Handles all HTTP requests to the backend
 */

const API_BASE_URL = 'http://localhost:8888/api';

class ApiClient {
    constructor() {
        this.baseURL = API_BASE_URL;
    }

    /**
     * Get authentication token from localStorage
     */
    getToken() {
        return localStorage.getItem('auth_token');
    }

    /**
     * Set authentication token in localStorage
     * Stores token, role, and username for session management
     */
    setToken(token) {
        localStorage.setItem('auth_token', token);
        // Token is stored in localStorage for persistence across browser sessions
        // Use sessionStorage if you want session-only storage (cleared on browser close)
    }

    /**
     * Remove authentication token from localStorage
     * Clears all stored authentication data
     */
    removeToken() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_role');
        localStorage.removeItem('username');
        // Also clear from sessionStorage if used
        sessionStorage.removeItem('auth_token');
        sessionStorage.removeItem('user_role');
        sessionStorage.removeItem('username');
    }

    /**
     * Get headers with authentication if token exists
     */
    getHeaders(includeAuth = true) {
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (includeAuth) {
            const token = this.getToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }
        
        return headers;
    }

    /**
     * Make HTTP request
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: {
                ...this.getHeaders(options.includeAuth !== false),
                ...options.headers,
            },
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                const errorMsg = data.detail || `HTTP error! status: ${response.status}`;
                console.error(`API request failed: ${url}`, {
                    status: response.status,
                    statusText: response.statusText,
                    error: errorMsg,
                    headers: config.headers
                });
                throw new Error(errorMsg);
            }

            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    /**
     * Login
     */
    async login(username, password) {
        const data = await this.request('/login', {
            method: 'POST',
            includeAuth: false,
            body: JSON.stringify({ username, password }),
        });
        
        if (data.access_token) {
            this.setToken(data.access_token);
            localStorage.setItem('user_role', data.role);
            localStorage.setItem('username', username);
            console.log('Login successful, token stored:', data.access_token.substring(0, 20) + '...');
        } else {
            console.error('Login failed: No access token in response', data);
        }
        
        return data;
    }

    /**
     * Logout
     */
    async logout() {
        try {
            await this.request('/logout', {
                method: 'POST',
            });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.removeToken();
        }
    }

    /**
     * Verify authentication
     */
    async verifyAuth() {
        const token = this.getToken();
        if (!token) {
            throw new Error('No token found in localStorage');
        }
        console.log('Verifying token:', token.substring(0, 20) + '...');
        return await this.request('/verify_auth', {
            method: 'GET',
        });
    }

    /**
     * Get available courses
     */
    async getCourses() {
        return await this.request('/courses', {
            method: 'GET',
        });
    }

    /**
     * Enroll in a course
     */
    async enroll(courseId) {
        return await this.request('/enroll', {
            method: 'POST',
            body: JSON.stringify({ course_id: courseId }),
        });
    }

    /**
     * Get student grades
     */
    async getGrades() {
        return await this.request('/grades', {
            method: 'GET',
        });
    }
    /**
    * Unenroll from a course
    */
    async unenroll(courseId) {
    return await this.request('/unenroll', {
        method: 'POST',
        body: JSON.stringify({ course_id: courseId }),
       });
    }
    
    /**
     * Upload grade (faculty only)
     */
    async uploadGrade(enrollmentId, grade) {
        return await this.request('/upload_grade', {
            method: 'POST',
            body: JSON.stringify({ 
                enrollment_id: enrollmentId,
                grade: grade 
            }),
        });
    }
}

// Export singleton instance
const api = new ApiClient();

