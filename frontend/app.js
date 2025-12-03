const API_BASE = 'http://localhost:8888/api';
let token = localStorage.getItem('token');
let userRole = localStorage.getItem('role');
let username = localStorage.getItem('username');

async function login() {
    const usernameInput = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!usernameInput || !password) {
        showMessage('Please enter username and password', 'error');
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: usernameInput, password: password })
        });
        const data = await res.json();
        
        if (res.ok) {
            token = data.access_token;
            userRole = data.role;
            username = usernameInput;
            localStorage.setItem('token', token);
            localStorage.setItem('role', userRole);
            localStorage.setItem('username', username);
            showMain();
        } else {
            showMessage('Login failed: ' + (data.detail || 'Invalid credentials'), 'error');
        }
    } catch (e) {
        showMessage('Error: ' + e.message, 'error');
    }
}

function showMain() {
    document.getElementById('auth-section').style.display = 'none';
    document.getElementById('main-section').style.display = 'block';
    document.getElementById('user-display').textContent = username;
    document.getElementById('role-display').textContent = userRole;
    
    if (userRole === 'student') {
        loadCourses();
        loadGrades();
    } else if (userRole === 'faculty') {
        loadUploadGradeSection();
    }
}

async function loadCourses() {
    try {
        const res = await fetch(`${API_BASE}/courses`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const courses = await res.json();
        
        let html = '<h2>Available Courses</h2>';
        if (courses.length === 0) {
            html += '<p>No courses available</p>';
        } else {
            courses.forEach(c => {
                html += `<div class="course-card">
                    <strong>${c.code}: ${c.title}</strong><br>
                    Instructor: ${c.instructor} | Available Slots: ${c.slots}<br>
                    <button onclick="enroll(${c.id})">Enroll</button>
                </div>`;
            });
        }
        document.getElementById('courses-section').innerHTML = html;
    } catch (e) {
        showMessage('Failed to load courses: ' + e.message, 'error');
    }
}

async function enroll(courseId) {
    try {
        const res = await fetch(`${API_BASE}/enroll`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}` 
            },
            body: JSON.stringify({ course_id: courseId })
        });
        const data = await res.json();
        showMessage(data.message || 'Enrollment response received', res.ok ? 'success' : 'error');
        if (res.ok) {
            loadCourses();
            loadGrades();
        }
    } catch (e) {
        showMessage('Enrollment failed: ' + e.message, 'error');
    }
}

async function loadGrades() {
    try {
        const res = await fetch(`${API_BASE}/grades`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const records = await res.json();
        
        let html = '<h2>Your Grades</h2>';
        if (records.length === 0) {
            html += '<p>No grade records found</p>';
        } else {
            records.forEach(r => {
                html += `<div class="grade-card">
                    <strong>${r.course_code}: ${r.course_title}</strong><br>
                    Grade: <strong>${r.grade || 'Not assigned'}</strong> | Status: ${r.status}
                </div>`;
            });
        }
        document.getElementById('grades-section').innerHTML = html;
    } catch (e) {
        console.error('Failed to load grades:', e.message);
    }
}

function loadUploadGradeSection() {
    let html = `<h2>Upload Grade</h2>
        <input type="number" id="enrollment-id" placeholder="Enrollment ID">
        <input type="text" id="grade-input" placeholder="Grade (e.g., A, B, C)">
        <button onclick="uploadGrade()">Upload Grade</button>`;
    document.getElementById('upload-grade-section').innerHTML = html;
}

async function uploadGrade() {
    const enrollmentId = document.getElementById('enrollment-id').value;
    const grade = document.getElementById('grade-input').value;
    
    if (!enrollmentId || !grade) {
        showMessage('Please enter enrollment ID and grade', 'error');
        return;
    }
    
    try {
        const res = await fetch(`${API_BASE}/upload_grade`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}` 
            },
            body: JSON.stringify({ enrollment_id: parseInt(enrollmentId), grade: grade })
        });
        const data = await res.json();
        showMessage(data.message || 'Grade uploaded', res.ok ? 'success' : 'error');
        if (res.ok) {
            document.getElementById('enrollment-id').value = '';
            document.getElementById('grade-input').value = '';
        }
    } catch (e) {
        showMessage('Upload failed: ' + e.message, 'error');
    }
}

function logout() {
    localStorage.clear();
    token = null;
    userRole = null;
    username = null;
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('main-section').style.display = 'none';
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
    showMessage('Logged out successfully', 'success');
}

function showMessage(msg, type) {
    const el = document.getElementById('message');
    el.textContent = msg;
    el.className = type;
    setTimeout(() => el.textContent = '', 5000);
}

// Check if already logged in
if (token && userRole && username) {
    showMain();
}