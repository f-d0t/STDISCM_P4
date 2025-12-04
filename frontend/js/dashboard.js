/**
 * Dashboard functionality
 */

let currentTab = 'courses';

document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication
    const authenticated = await requireAuth();
    if (!authenticated) return;

    // Setup UI based on role
    const role = getUserRole();
    const username = getUsername();
    
    document.getElementById('userInfo').textContent = `${username} (${role})`;

    if (role === 'student') {
        document.getElementById('studentView').style.display = 'block';
        setupStudentDashboard();
    } else if (role === 'faculty') {
        document.getElementById('facultyView').style.display = 'block';
        setupFacultyDashboard();
    }

    // Setup logout
    document.getElementById('logoutBtn').addEventListener('click', async () => {
        await api.logout();
        window.location.href = 'index.html';
    });

    // Setup tabs
    setupTabs();
});

function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            
            // Remove active class from all
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked
            btn.classList.add('active');
            document.getElementById(`${tabName}Tab`).classList.add('active');
            
            currentTab = tabName;
            
            // Load data for the tab
            if (tabName === 'courses' || tabName === 'enroll') {
                loadCourses();
            } else if (tabName === 'grades') {
                loadGrades();
            }
        });
    });
}

async function setupStudentDashboard() {
    await loadCourses();
}

async function setupFacultyDashboard() {
    // Setup upload grade form
    const form = document.getElementById('uploadGradeForm');
    const errorMsg = document.getElementById('uploadErrorMessage');
    const successMsg = document.getElementById('uploadSuccessMessage');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorMsg.classList.remove('show');
        successMsg.classList.remove('show');

        const enrollmentId = parseInt(document.getElementById('enrollmentId').value);
        const grade = parseFloat(document.getElementById('grade').value);

        try {
            const response = await api.uploadGrade(enrollmentId, grade);
            successMsg.textContent = `Grade uploaded successfully! Student: ${response.student_username}, Grade: ${response.grade}`;
            successMsg.classList.add('show');
            form.reset();
        } catch (error) {
            errorMsg.textContent = error.message || 'Failed to upload grade.';
            errorMsg.classList.add('show');
        }
    });
}

async function loadCourses() {
    const coursesList = document.getElementById('coursesList');
    const enrollCoursesList = document.getElementById('enrollCoursesList');
    
    if (!coursesList && !enrollCoursesList) return;

    try {
        const courses = await api.getCourses();
        
        const renderCourse = (course, showEnrollButton = false) => {
            const card = document.createElement('div');
            card.className = 'course-card';
            card.innerHTML = `
                <div class="course-code">${course.code}</div>
                <h4>${course.title}</h4>
                <div class="course-info">
                    <div class="slots ${course.slots === 0 ? 'full' : ''}">
                        ${course.slots} slot${course.slots !== 1 ? 's' : ''} available
                    </div>
                    <div>Status: ${course.is_open ? 'Open' : 'Closed'}</div>
                </div>
                ${showEnrollButton && course.is_open && course.slots > 0 ? 
                    `<button class="btn btn-enroll" onclick="enrollInCourse(${course.id})">Enroll</button>` : 
                    ''}
            `;
            return card;
        };

        if (coursesList) {
            coursesList.innerHTML = '';
            courses.forEach(course => {
                coursesList.appendChild(renderCourse(course, false));
            });
        }

        if (enrollCoursesList) {
            enrollCoursesList.innerHTML = '';
            courses.forEach(course => {
                enrollCoursesList.appendChild(renderCourse(course, true));
            });
        }
    } catch (error) {
        console.error('Failed to load courses:', error);
        const container = coursesList || enrollCoursesList;
        if (container) {
            container.innerHTML = `<div class="error-message show">Failed to load courses: ${error.message}</div>`;
        }
    }
}

async function enrollInCourse(courseId) {
    try {
        const response = await api.enroll(courseId);
        alert(`Successfully enrolled! ${response.message}`);
        // Reload courses to update slot counts
        await loadCourses();
    } catch (error) {
        alert(`Enrollment failed: ${error.message}`);
    }
}

async function loadGrades() {
    const gradesList = document.getElementById('gradesList');
    if (!gradesList) return;

    try {
        const grades = await api.getGrades();
        
        if (grades.length === 0) {
            gradesList.innerHTML = '<div class="loading">No grades found.</div>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'grades-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Course Code</th>
                    <th>Course Title</th>
                    <th>Grade</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${grades.map(grade => `
                    <tr>
                        <td>${grade.course_code}</td>
                        <td>${grade.course_title}</td>
                        <td>${grade.grade > 0 ? grade.grade.toFixed(2) : 'N/A'}</td>
                        <td><span class="grade-badge ${grade.status.toLowerCase()}">${grade.status}</span></td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        
        gradesList.innerHTML = '';
        gradesList.appendChild(table);
    } catch (error) {
        console.error('Failed to load grades:', error);
        gradesList.innerHTML = `<div class="error-message show">Failed to load grades: ${error.message}</div>`;
    }
}

// Make enrollInCourse available globally
window.enrollInCourse = enrollInCourse;

