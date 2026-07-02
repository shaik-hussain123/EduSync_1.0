/**
 * frontend/js/dashboard.js
 * EduSync — Smart Campus ERP | Dashboard View Logic
 *
 * Populates the dashboard widgets.
 */

function getStoredUser() {
    const teacherData = localStorage.getItem('teacher');
    if (teacherData) {
        try { return JSON.parse(teacherData); } catch (e) { console.error(e); }
    }
    const studentData = localStorage.getItem('student');
    if (studentData) {
        try { return JSON.parse(studentData); } catch (e) { console.error(e); }
    }
    return null;
}

function renderTeacherDashboard() {
    const teacher = getStoredUser();
    const studentView = document.getElementById('student-dashboard-view');
    const teacherView = document.getElementById('teacher-dashboard-view');

    if (studentView) studentView.classList.add('hidden');
    if (teacherView) teacherView.classList.remove('hidden');

    if (!teacher) return;

    const firstName = teacher.full_name ? teacher.full_name.split(' ')[0] : 'Teacher';
    setText('teacher-welcome-name', firstName);
    setText('teacher-employee-id', teacher.employee_id || '—');
    setText('teacher-dept', teacher.department || '—');
    setText('teacher-subjects', Array.isArray(teacher.subjects) && teacher.subjects.length ? teacher.subjects.join(', ') : 'No subjects assigned');
    setText('teacher-today-classes', '3 scheduled classes');
    setText('teacher-stat-sessions', '2 recent sessions');
    setText('teacher-stat-notifications', '3 unread notifications');
    setText('teacher-profile-summary', 'Review your active profile and teaching details');

    const classes = [
        { label: 'Data Structures', time: '09:00 - 10:00', room: 'B-204' },
        { label: 'Operating Systems', time: '11:00 - 12:00', room: 'C-101' },
        { label: 'Database Systems', time: '02:00 - 03:00', room: 'A-312' }
    ];
    const sessions = [
        { label: 'Biometric Attendance', time: '08:30 AM', status: 'Live' },
        { label: 'Lab Session', time: '01:00 PM', status: 'Completed' },
        { label: 'Tutorial Review', time: '03:30 PM', status: 'Scheduled' }
    ];
    const notifications = [
        { title: 'Attendance reminder', message: '2 classes still need session confirmation.' },
        { title: 'Profile update', message: 'Keep your department and subjects current.' }
    ];

    const classesBody = document.getElementById('teacher-classes-body');
    if (classesBody) {
        classesBody.innerHTML = classes.map(item => `
            <div style="padding: 10px 0; border-bottom: 1px solid #eef2f7;">
                <div style="font-weight: 600; margin-bottom: 3px;">${item.label}</div>
                <div style="font-size: 12px; color: #666;">${item.time} · ${item.room}</div>
            </div>
        `).join('');
    }

    const sessionsBody = document.getElementById('teacher-sessions-body');
    if (sessionsBody) {
        sessionsBody.innerHTML = sessions.map(item => `
            <div style="padding: 10px 0; border-bottom: 1px solid #eef2f7; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-weight: 600; margin-bottom: 3px;">${item.label}</div>
                    <div style="font-size: 12px; color: #666;">${item.time}</div>
                </div>
                <span class="badge" style="background:#e7f1ff; color:#0d6efd; padding: 4px 8px; border-radius: 999px; font-size: 11px;">${item.status}</span>
            </div>
        `).join('');
    }

    const notifBody = document.getElementById('teacher-notifications-body');
    if (notifBody) {
        notifBody.innerHTML = notifications.map(item => `
            <div style="padding: 10px 0; border-bottom: 1px solid #eef2f7;">
                <div style="font-weight: 600; margin-bottom: 3px;">${item.title}</div>
                <div style="font-size: 12px; color: #666;">${item.message}</div>
            </div>
        `).join('');
    }
}

/* ── Profile completion calculation ────────────────────────────────────────── */
function calcProfileCompletion(student) {
    const fields = [
        'full_name', 'email', 'usn', 'department',
        'semester', 'section', 'phone', 'gender', 'date_of_birth', 'profile_photo'
    ];
    const filled = fields.filter(f => student[f] !== null && student[f] !== undefined && student[f] !== '');
    return Math.round((filled.length / fields.length) * 100);
}

/* ── Render student info ────────────────────────────────────────────────────── */
function renderStudentInfo(student) {
    if (!student) return;

    const studentView = document.getElementById('student-dashboard-view');
    const teacherView = document.getElementById('teacher-dashboard-view');
    if (studentView) studentView.classList.remove('hidden');
    if (teacherView) teacherView.classList.add('hidden');

    const firstName = student.full_name ? student.full_name.split(' ')[0] : 'Student';

    // Welcome
    setText('welcome-name', firstName);

    // Info cards
    setText('info-usn',    student.usn        || '—');
    setText('info-dept',   student.department || '—');

    const semEl = document.getElementById('info-sem');
    if (semEl) {
        if (student.semester != null) {
            semEl.textContent = `Semester ${student.semester}`;
            semEl.classList.remove('not-set');
        } else {
            semEl.textContent = 'Not Set';
            semEl.classList.add('not-set');
        }
    }

    const secEl = document.getElementById('info-sec');
    if (secEl) {
        if (student.section) {
            secEl.textContent = `Section ${student.section}`;
            secEl.classList.remove('not-set');
        } else {
            secEl.textContent = 'Not Set';
            secEl.classList.add('not-set');
        }
    }

    // Verification badge
    const verEl = document.getElementById('info-verification');
    if (verEl) {
        const status = student.verification_status || 'pending';
        verEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        verEl.className = `badge badge-${status}`;
    }

    // Profile completion
    const pct = calcProfileCompletion(student);
    const fillEl = document.getElementById('profile-bar-fill');
    const labelEl = document.getElementById('profile-bar-label');
    if (fillEl)  fillEl.style.width  = `${pct}%`;
    if (labelEl) labelEl.textContent = `${pct}% complete`;

    // Profile completion banner
    const banner = document.getElementById('profile-banner');
    if (banner) {
        if (pct < 100) {
            banner.classList.remove('hidden');
        } else {
            banner.classList.add('hidden');
        }
    }
}

/* ── Today's Timetable Widget ───────────────────────────────────────── */
async function renderTimetable(student) {
    const el = document.getElementById('widget-timetable-body');
    if (!el) return;

    if (!student.semester || !student.section) {
        el.innerHTML = emptyState('📅', 'Set your semester & section to view your timetable.');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/student/timetable/today`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            const schedule = data.today || { periods: [] };
            
            if (!schedule.periods || schedule.periods.length === 0) {
                el.innerHTML = emptyState('📅', 'No timetable assigned.');
                return;
            }
            
            // Logic to find current, next and remaining classes
            const now = new Date();
            const currentMins = now.getHours() * 60 + now.getMinutes();
            
            const parseTime = (tStr) => {
                const [h, m] = tStr.split(':').map(Number);
                return h * 60 + m;
            };
            
            let currentClass = null;
            let nextClass = null;
            let remainingCount = 0;
            
            for (const p of schedule.periods) {
                if (p.is_cancelled) continue;
                
                const startMins = parseTime(p.start_time);
                const endMins = parseTime(p.end_time);
                
                if (currentMins >= startMins && currentMins <= endMins) {
                    currentClass = p;
                } else if (startMins > currentMins) {
                    if (!nextClass) nextClass = p;
                    remainingCount++;
                }
            }
            
            let html = '<div style="padding: 16px;">';
            
            if (currentClass) {
                html += `
                    <div style="margin-bottom: 16px; border-left: 4px solid #0d6efd; padding-left: 12px;">
                        <div class="text-primary small fw-bold text-uppercase mb-1">Current Class</div>
                        <div class="fw-bold">${currentClass.subject_name}</div>
                        <div class="small text-muted">${currentClass.start_time} - ${currentClass.end_time} | Room: ${currentClass.room}</div>
                    </div>
                `;
            } else {
                html += `
                    <div style="margin-bottom: 16px; border-left: 4px solid #ddd; padding-left: 12px;">
                        <div class="small fw-bold text-uppercase mb-1 text-muted">Current Class</div>
                        <div class="text-muted small">No ongoing class</div>
                    </div>
                `;
            }
            
            if (nextClass) {
                html += `
                    <div style="margin-bottom: 12px; border-left: 4px solid #ffc107; padding-left: 12px;">
                        <div class="text-warning small fw-bold text-uppercase mb-1">Next Class</div>
                        <div class="fw-bold">${nextClass.subject_name}</div>
                        <div class="small text-muted">${nextClass.start_time} - ${nextClass.end_time} | Room: ${nextClass.room}</div>
                    </div>
                `;
            }
            
            html += `<div class="small text-muted mt-3 pt-2 border-top"><strong>${remainingCount}</strong> remaining classes today.</div>`;
            html += '</div>';
            
            el.innerHTML = html;
        } else {
            el.innerHTML = emptyState('📅', 'Failed to load timetable.');
        }
    } catch (err) {
        console.error(err);
        el.innerHTML = emptyState('📅', 'Failed to load timetable.');
    }
}

/* ── Recent Notifications Widget ─────────────────────────────────────────── */
async function renderNotifications() {
    const el = document.getElementById('widget-notif-body');
    if (!el) return;

    try {
        const response = await fetch(`${API_BASE_URL}/student/notifications`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });

        if (!response.ok) throw new Error('Failed to load notifications');

        const data = await response.json();
        const items = (data.notifications || []).slice(0, 5);

        if (!items.length) {
            el.innerHTML = emptyState('🔔', 'No new notifications yet.');
            return;
        }

        el.innerHTML = items.map(item => `
            <div class="notification-item" style="padding: 10px 0; border-bottom: 1px solid #eef2f7;">
                <div class="notification-title" style="font-size: 13px; margin-bottom: 2px;">${item.title}</div>
                <div class="notification-message" style="font-size: 12px;">${item.message}</div>
                <div class="notification-date" style="font-size: 11px; margin-top: 4px;">${item.created_at ? new Date(item.created_at).toLocaleString() : ''}</div>
            </div>
        `).join('');
    } catch (err) {
        console.error(err);
        el.innerHTML = emptyState('⚠️', 'Could not load notifications.');
    }
}

/* ── Attendance Overview (placeholder) ─────────────────────────────────────── */
function renderAttendance() {
    // TODO: fetch from GET /api/v1/student/attendance/summary
    const el = document.getElementById('widget-attendance-body');
    if (!el) return;
    el.innerHTML = emptyState('📊', 'No attendance records available yet.');
}

/* ── Upcoming Holidays (placeholder) ───────────────────────────────────────── */
function renderHolidays() {
    // TODO: fetch from GET /api/v1/admin/holidays?upcoming=true
    const el = document.getElementById('widget-holiday-body');
    if (!el) return;

    // Static placeholder holidays (will come from API later)
    const holidays = [
        { day: '15', mon: 'Aug', name: 'Independence Day',   type: 'National Holiday' },
        { day: '02', mon: 'Oct', name: 'Gandhi Jayanti',     type: 'National Holiday' },
        { day: '01', mon: 'Nov', name: 'Kannada Rajyotsava', type: 'State Holiday' },
    ];

    el.innerHTML = holidays.map(h => `
        <div class="holiday-item">
            <div class="holiday-date">
                <div class="hd-day">${h.day}</div>
                <div class="hd-mon">${h.mon}</div>
            </div>
            <div class="holiday-info">
                <div class="hd-name">${h.name}</div>
                <div class="hd-type">${h.type}</div>
            </div>
        </div>
    `).join('');
}

/* ── Helpers ────────────────────────────────────────────────────────────────── */
function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function emptyState(icon, msg) {
    return `<div class="empty-state">
        <div class="empty-icon">${icon}</div>
        <div class="empty-msg">${msg}</div>
    </div>`;
}

/* ── Face Registration Widget ──────────────────────────────────────────────── */
async function renderFaceWidget() {
    const el = document.getElementById('widget-face-body');
    if (!el) return;

    try {
        const response = await fetch(`${API_BASE_URL}/student/face/status`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        
        if (!response.ok) throw new Error("Failed to fetch face status");
        
        const data = await response.json();
        
        if (data.is_registered) {
            el.innerHTML = `
                <div style="padding: 16px;">
                    <div style="display:flex; align-items:center; gap: 12px; margin-bottom: 12px;">
                        <span class="badge" style="background:#d1e7dd; color:#0f5132; padding: 6px 12px; font-size: 14px;">✅ ${data.status}</span>
                    </div>
                    <div style="font-size: 13px; color: var(--muted); margin-bottom: 6px;">Images: <strong>${data.images_captured} / 8</strong></div>
                    <div style="font-size: 13px; color: var(--muted); margin-bottom: 6px;">Quality: <strong>Excellent</strong></div>
                    <div style="font-size: 13px; color: var(--muted); margin-bottom: 6px;">Version: <strong>${data.version}</strong></div>
                </div>
            `;
        } else {
            el.innerHTML = `
                <div class="empty-state" style="padding-top: 16px;">
                    <div class="empty-icon" style="font-size: 24px; margin-bottom: 8px;">❌</div>
                    <div style="font-weight: 600; margin-bottom: 4px;">Not Registered</div>
                    <div style="font-size: 13px; color: var(--muted); margin-bottom: 16px;">Images: 0 / 8</div>
                    <button class="btn-primary-erp" onclick="loadView('face')" style="padding: 8px 16px; font-size: 13px;">Register Face</button>
                </div>
            `;
        }
    } catch (err) {
        console.error(err);
        el.innerHTML = emptyState('⚠️', 'Could not load face registration status.');
    }
}

/* ── Leave Requests Widget ──────────────────────────────────────────────────── */
async function renderLeaveWidget() {
    const el = document.getElementById('widget-leave-body');
    if (!el) return;

    try {
        const response = await fetch(`${API_BASE_URL}/student/leave/history`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });

        if (!response.ok) throw new Error('Failed to fetch leave history');

        const data = await response.json();
        const history = data.history || [];

        if (history.length === 0) {
            el.innerHTML = emptyState('📝', 'No leave requests yet.');
            return;
        }

        // Count by status
        const counts = { Pending: 0, Approved: 0, Rejected: 0 };
        history.forEach(r => {
            if (counts[r.status] !== undefined) counts[r.status]++;
        });

        // Show only latest 3
        const recent = history.slice(0, 3);

        const statusColors = {
            Pending:   { bg: '#fff3cd', color: '#856404' },
            Approved:  { bg: '#d1e7dd', color: '#0f5132' },
            Rejected:  { bg: '#f8d7da', color: '#842029' },
            Cancelled: { bg: '#e2e3e5', color: '#383d41' },
            Completed: { bg: '#cff4fc', color: '#055160' },
        };

        let html = `
            <div style="display:flex; gap:12px; padding: 12px 16px; border-bottom:1px solid #eee;">
                <div style="text-align:center; flex:1;">
                    <div style="font-size:20px; font-weight:700; color:#856404;">${counts.Pending}</div>
                    <div style="font-size:11px; color:#999; text-transform:uppercase;">Pending</div>
                </div>
                <div style="text-align:center; flex:1;">
                    <div style="font-size:20px; font-weight:700; color:#0f5132;">${counts.Approved}</div>
                    <div style="font-size:11px; color:#999; text-transform:uppercase;">Approved</div>
                </div>
                <div style="text-align:center; flex:1;">
                    <div style="font-size:20px; font-weight:700; color:#842029;">${counts.Rejected}</div>
                    <div style="font-size:11px; color:#999; text-transform:uppercase;">Rejected</div>
                </div>
            </div>
        `;

        recent.forEach(r => {
            const sc = statusColors[r.status] || { bg: '#eee', color: '#333' };
            const dateStr = new Date(r.applied_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            html += `
                <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 16px; border-bottom:1px solid #f5f5f5;">
                    <div>
                        <div style="font-weight:600; font-size:14px;">${r.leave_type_name}</div>
                        <div style="font-size:12px; color:#999;">${dateStr} · ${r.total_days} day${r.total_days > 1 ? 's' : ''}</div>
                    </div>
                    <span style="background:${sc.bg}; color:${sc.color}; font-size:11px; font-weight:600; padding:3px 9px; border-radius:20px;">${r.status}</span>
                </div>
            `;
        });

        el.innerHTML = html;

    } catch (err) {
        console.error(err);
        el.innerHTML = emptyState('⚠️', 'Could not load leave requests.');
    }
}
