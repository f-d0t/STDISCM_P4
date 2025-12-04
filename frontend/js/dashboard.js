/**
 * Dashboard functionality
 */

let currentTab = 'courses';

document.addEventListener('DOMContentLoaded', async () => {
    const authenticated = await requireAuth();
    if (!authenticated) return;

    const role = getUserRole();
    const username = getUsername();
    document.getElementById('userInfo').textContent = `${username} (${role})`;

    if (role === 'student') {
        setupStudentDashboard();
    } else if (role === 'faculty') {
        setupFacultyDashboard();
    }

    document.getElementById('logoutBtn').addEventListener('click', async () => {
        await api.logout();
        window.location.href = 'index.html';
    });

    setupTabs();
});


function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const target = button.dataset.tab;

            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            button.classList.add('active');
            document.getElementById(target + 'Tab').classList.add('active');

            if (target === 'courses' || target === 'enroll') {
                loadCourses();
            } else if (target === 'grades') {
                loadGrades();
            }
        });
    });
}

function setupStudentDashboard() {
    document.getElementById('studentView').style.display = 'block';
    document.getElementById('facultyView').style.display = 'none';

    // Load data for student dashboard
    loadCourses();
    loadGrades();
}

async function setupFacultyDashboard() {
    const studentView = document.getElementById('studentView');
    const facultyView = document.getElementById('facultyView');
    if (studentView) studentView.style.display = 'none';
    if (facultyView) facultyView.style.display = 'block';

    const form = document.getElementById('uploadGradeForm');
    const errorMsg = document.getElementById('uploadErrorMessage');
    const successMsg = document.getElementById('uploadSuccessMessage');

    if (!form) {
        console.error('uploadGradeForm not found');
        return;
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorMsg.classList.remove('show');
        successMsg.classList.remove('show');

        const enrollmentIdValue = document.getElementById('enrollmentId').value;
        const gradeValue = document.getElementById('grade').value;

        const enrollmentId = parseInt(enrollmentIdValue, 10);
        const grade = parseFloat(gradeValue);

        if (Number.isNaN(enrollmentId) || enrollmentId <= 0) {
            errorMsg.textContent = 'Please enter a valid Enrollment ID.';
            errorMsg.classList.add('show');
            return;
        }

        if (Number.isNaN(grade) || grade < 0 || grade > 4) {
            errorMsg.textContent = 'Grade must be a number between 0.0 and 4.0.';
            errorMsg.classList.add('show');
            return;
        }

        try {
            const response = await api.uploadGrade(enrollmentId, grade);
            successMsg.textContent = response.message || 'Grade uploaded successfully!';
            successMsg.classList.add('show');
            form.reset();
            // Reload enrollments list so updated grades/status are visible
            await loadFacultyEnrollments();
        } catch (error) {
            errorMsg.textContent = error.message || 'Failed to upload grade.';
            errorMsg.classList.add('show');
        }
    });

    // Initial load of enrollments list
    await loadFacultyEnrollments();
}

async function loadFacultyEnrollments() {
    const container = document.getElementById('facultyEnrollmentsList');
    if (!container) return;

    container.innerHTML = '<div class="loading">Loading enrollments...</div>';

    try {
        const enrollments = await api.getFacultyEnrollments();

        if (!enrollments.length) {
            container.innerHTML = '<div class="loading">No enrollments found.</div>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'grades-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Enrollment ID</th>
                    <th>Student</th>
                    <th>Course Code</th>
                    <th>Course Title</th>
                    <th>Grade</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${enrollments.map(rec => `
                    <tr data-enrollment-id="${rec.enrollment_id}">
                        <td>${rec.enrollment_id}</td>
                        <td>${rec.student_username}</td>
                        <td>${rec.course_code}</td>
                        <td>${rec.course_title}</td>
                        <td>${rec.grade > 0 ? rec.grade.toFixed(2) : 'N/A'}</td>
                        <td><span class="grade-badge ${rec.status.toLowerCase()}">${rec.status}</span></td>
                    </tr>
                `).join('')}
            </tbody>
        `;

        // Attach click handlers to prefill Enrollment ID
        table.querySelectorAll('tbody tr').forEach(row => {
            row.addEventListener('click', () => {
                const id = row.getAttribute('data-enrollment-id');
                const enrollmentInput = document.getElementById('enrollmentId');
                if (enrollmentInput && id) {
                    enrollmentInput.value = id;
                }
            });
        });

        container.innerHTML = '';
        container.appendChild(table);
    } catch (error) {
        console.error('Failed to load faculty enrollments:', error);
        container.innerHTML = `<div class="error-message show">Failed to load enrollments: ${error.message}</div>`;
    }
}

async function loadCourses() {
    const coursesList = document.getElementById('coursesList');
    const enrollCoursesList = document.getElementById('enrollCoursesList');

    if (!coursesList && !enrollCoursesList) return;

    try {
        // 1. Get courses
        const courses = await api.getCourses();

        // 2. Get current enrollments (ENROLLED status)
        let enrolledIds = new Set();
        try {
            const grades = await api.getGrades();   // hits /api/grades
            enrolledIds = new Set(
                grades
                    .filter(r => r.status === 'ENROLLED')
                    .map(r => r.course_id)
            );
        } catch (e) {
            console.warn('Could not load current enrollments:', e);
        }

        const renderCourse = (course, showActions = false, isEnrolled = false) => {
            const card = document.createElement('div');
            card.className = 'course-card';

            let actionBtn = '';
            if (showActions) {
                if (isEnrolled) {
                    actionBtn = `
                        <button class="btn btn-danger"
                                onclick="unenrollFromCourse(${course.id})">
                            Unenroll
                        </button>`;
                } else if (course.is_open && course.slots > 0) {
                    actionBtn = `
                        <button class="btn btn-enroll"
                                onclick="enrollInCourse(${course.id})">
                            Enroll
                        </button>`;
                }
            }

            card.innerHTML = `
                <div class="course-code">${course.code}</div>
                <h4>${course.title}</h4>
                <div class="course-info">
                    <div class="slots ${course.slots === 0 ? 'full' : ''}">
                        ${course.slots} slot${course.slots !== 1 ? 's' : ''} available
                    </div>
                    <div>Status: ${course.is_open ? 'Open' : 'Closed'}</div>
                </div>
                ${actionBtn}
            `;
            return card;
        };

        // "Available Courses" tab – read-only listing
        if (coursesList) {
            coursesList.innerHTML = '';
            courses.forEach(course => {
                coursesList.appendChild(
                    renderCourse(course, false, enrolledIds.has(course.id))
                );
            });
        }

        // "Enroll in Course" tab – with Enroll / Unenroll buttons
        if (enrollCoursesList) {
            enrollCoursesList.innerHTML = '';
            courses.forEach(course => {
                const isEnrolled = enrolledIds.has(course.id);
                enrollCoursesList.appendChild(
                    renderCourse(course, true, isEnrolled)
                );
            });
        }
    } catch (error) {
        console.error('Failed to load courses:', error);
        const container = coursesList || enrollCoursesList;
        if (container) {
            container.innerHTML = `<div class="error-message show">
                Failed to load courses: ${error.message}
            </div>`;
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

async function unenrollFromCourse(courseId) {
    if (!confirm('Are you sure you want to unenroll from this course?')) {
        return;
    }

    try {
        const res = await api.unenroll(courseId);
        if (!res.success) {
            alert(res.message || 'Unenrollment failed');
            return;
        }

        // Reload courses & grades so UI updates
        await loadCourses();
        await loadGrades?.();    // if you already have loadGrades()
    } catch (err) {
        console.error('Unenroll error:', err);
        alert(err.message || 'Failed to unenroll from course.');
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

