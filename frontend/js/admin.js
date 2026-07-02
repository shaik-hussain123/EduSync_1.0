/**
 * frontend/js/admin.js
 * EduSync — Smart Campus ERP | Administrator Controller Logic
 */

let allStudentsCache = [];
let allDepartmentsCache = [];

function getAdminHeaders() {
    const token = localStorage.getItem("access_token");
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
    };
}

// ── 1. Admin Dashboard View ──────────────────────────────────────────────────
async function renderAdminDashboard() {
    if (typeof setDashboardRoleVisibility === 'function') setDashboardRoleVisibility('admin');
    // 1. Welcome name
    let admin = {};
    try {
        const item = localStorage.getItem("admin");
        if (item) admin = JSON.parse(item);
    } catch (e) {
        console.error("Error parsing admin item", e);
    }
    const firstName = admin && admin.full_name ? admin.full_name.split(' ')[0] : 'Admin';
    const welcomeEl = document.getElementById("admin-welcome-name");
    if (welcomeEl) welcomeEl.textContent = firstName;

    try {
        // 2. Fetch stats
        const response = await fetch(`${API_BASE_URL}/admin/stats`, {
            headers: getAdminHeaders()
        });
        if (response.status === 401 || response.status === 403) {
            alert("Your admin session has expired. Please sign in again.");
            localStorage.clear();
            window.location.href = "signin.html";
            return;
        }
        if (response.ok) {
            const data = await response.json();
            document.getElementById("admin-stat-students").textContent = data.students.total;
            document.getElementById("admin-stat-teachers").textContent = data.teachers.total;
            document.getElementById("admin-stat-depts").textContent = data.departments.total;
            
            const pendingEl = document.getElementById("admin-stat-pending");
            pendingEl.textContent = data.students.pending;
            if (data.students.pending > 0) {
                pendingEl.className = "badge bg-danger";
            } else {
                pendingEl.className = "badge bg-success";
            }
        }
        
        // 3. Load verification widget (max 3 pending)
        const vBody = document.getElementById("admin-widget-verification-body");
        const vResponse = await fetch(`${API_BASE_URL}/admin/students`, {
            headers: getAdminHeaders()
        });
        if (vResponse.ok) {
            const vData = await vResponse.json();
            const pendingList = (vData.students || []).filter(s => s.verification_status === 'pending').slice(0, 3);
            if (vBody) {
                if (pendingList.length === 0) {
                    vBody.innerHTML = `<div class="empty-state"><div class="empty-icon">✅</div><div class="empty-msg">All students verified!</div></div>`;
                } else {
                    vBody.innerHTML = pendingList.map(s => `
                        <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                            <div>
                                <div class="fw-bold small">${s.full_name}</div>
                                <div class="text-muted" style="font-size:11px;">USN: ${s.usn} | Dept: ${s.department}</div>
                            </div>
                            <div>
                                <button class="btn btn-sm btn-success py-0 px-2" onclick="verifyStudentQuick('${s.id}', 'approved')">Approve</button>
                                <button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="verifyStudentQuick('${s.id}', 'rejected')">Reject</button>
                            </div>
                        </div>
                    `).join('');
                }
            }
        } else if (vBody) {
            vBody.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Failed to load verifications.</div></div>`;
        }

        // 4. Load audit widget (max 5 events)
        const aBody = document.getElementById("admin-widget-audit-body");
        const auditResponse = await fetch(`${API_BASE_URL}/admin/audit-logs`, {
            headers: getAdminHeaders()
        });
        if (auditResponse.ok) {
            const auditData = await auditResponse.json();
            const logs = (auditData.logs || []).slice(0, 5);
            if (aBody) {
                if (logs.length === 0) {
                    aBody.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-msg">No logs recorded yet.</div></div>`;
                } else {
                    aBody.innerHTML = logs.map(l => `
                        <div class="py-2 border-bottom" style="font-size:12px;">
                            <div class="d-flex justify-content-between">
                                <span class="fw-bold text-primary">${(l.action || '').toUpperCase()}</span>
                                <span class="text-muted" style="font-size:10px;">${l.timestamp}</span>
                            </div>
                            <div class="text-secondary">${l.details}</div>
                        </div>
                    `).join('');
                }
            }
        } else if (aBody) {
            aBody.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Failed to load audit logs.</div></div>`;
        }
    } catch (err) {
        console.error("Dashboard render failed", err);
    }
}

async function verifyStudentQuick(id, status) {
    if (confirm(`Are you sure you want to set status to ${status}?`)) {
        await verifyStudentAction(id, status);
        renderAdminDashboard();
    }
}

function checkAdminAuthResponse(response) {
    if (response.status === 401 || response.status === 403) {
        alert("Your admin session has expired or is invalid. Please sign in again.");
        localStorage.clear();
        window.location.href = "signin.html";
        return false;
    }
    return true;
}

// ── 2. Student Management View ───────────────────────────────────────────────
async function renderAdminStudents() {
    const tbody = document.getElementById("admin-students-table-body");
    if (!tbody) return;
    try {
        const response = await fetch(`${API_BASE_URL}/admin/students`, {
            headers: getAdminHeaders()
        });
        if (!checkAdminAuthResponse(response)) return;
        if (response.ok) {
            const data = await response.json();
            allStudentsCache = data.students || [];
            
            // Populate departments dropdown
            const deptDropdown = document.getElementById("admin-student-filter-dept");
            if (deptDropdown) {
                const depts = [...new Set(allStudentsCache.map(s => s.department).filter(Boolean))];
                deptDropdown.innerHTML = '<option value="">All Departments</option>' + 
                    depts.map(d => `<option value="${d}">${d}</option>`).join('');
            }
            
            renderStudentsTable(allStudentsCache);
        } else {
            tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">Failed to load student list.</td></tr>`;
        }
    } catch (err) {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">Network error loading student list.</td></tr>`;
    }
}

function renderStudentsTable(students) {
    const tbody = document.getElementById("admin-students-table-body");
    if (!tbody) return;
    if (students.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4">No student records found matching the filters.</td></tr>`;
        return;
    }

    tbody.innerHTML = students.map(s => {
        const verifyClass = s.verification_status === 'approved' ? 'bg-success' : (s.verification_status === 'rejected' ? 'bg-danger' : 'bg-warning text-dark');
        const statusClass = s.account_status === 'active' ? 'bg-info' : 'bg-secondary';
        const photoHtml = s.profile_photo ? 
            `<img src="${API_BASE_URL.replace('/api/v1', '')}/${s.profile_photo}" style="width:40px; height:40px; object-fit:cover; border-radius:50%;" />` : 
            `<div style="width:40px; height:40px; border-radius:50%; background:#e2e3e5; display:flex; align-items:center; justify-content:center; font-weight:bold; color:#495057;">${s.full_name.charAt(0)}</div>`;

        return `
            <tr>
                <td>${photoHtml}</td>
                <td>
                    <div class="fw-bold">${s.full_name}</div>
                    <div class="text-muted small">${s.email}</div>
                </td>
                <td><code>${s.usn}</code></td>
                <td>${s.department} / Sem ${s.semester || '—'} / Sec ${s.section || '—'}</td>
                <td><span class="badge ${verifyClass}">${s.verification_status}</span></td>
                <td><span class="badge ${statusClass}">${s.account_status}</span></td>
                <td>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">Actions</button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item text-success" href="#" onclick="verifyStudentAction('${s.id}', 'approved')">✓ Approve</a></li>
                            <li><a class="dropdown-item text-warning" href="#" onclick="verifyStudentAction('${s.id}', 'rejected')">✗ Reject</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="#" onclick="toggleStudentStatus('${s.id}', '${s.account_status}')">
                                ${s.account_status === 'active' ? '🔒 Block Account' : '🔓 Unblock Account'}
                            </a></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="deleteStudentAction('${s.id}')">🗑 Delete Account</a></li>
                        </ul>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function filterStudents() {
    const searchVal = document.getElementById("admin-student-search").value.toLowerCase();
    const deptVal = document.getElementById("admin-student-filter-dept").value;
    const verifyVal = document.getElementById("admin-student-filter-verify").value;

    const filtered = allStudentsCache.filter(s => {
        const matchesSearch = s.full_name.toLowerCase().includes(searchVal) || 
                              s.email.toLowerCase().includes(searchVal) || 
                              s.usn.toLowerCase().includes(searchVal);
        const matchesDept = deptVal === "" || s.department === deptVal;
        const matchesVerify = verifyVal === "" || s.verification_status === verifyVal;
        return matchesSearch && matchesDept && matchesVerify;
    });

    renderStudentsTable(filtered);
}

function clearStudentFilters() {
    document.getElementById("admin-student-search").value = "";
    document.getElementById("admin-student-filter-dept").value = "";
    document.getElementById("admin-student-filter-verify").value = "";
    renderStudentsTable(allStudentsCache);
}

async function verifyStudentAction(id, status) {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/students/${id}/verify`, {
            method: 'PUT',
            headers: getAdminHeaders(),
            body: JSON.stringify({ status })
        });
        const data = await response.json();
        if (response.ok) {
            alert(data.message);
            const view = document.getElementById("main-content").dataset.activeView || 'students';
            loadView(view);
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (err) {
        console.error(err);
    }
}

async function toggleStudentStatus(id, currentStatus) {
    const newStatus = currentStatus === 'active' ? 'blocked' : 'active';
    try {
        const response = await fetch(`${API_BASE_URL}/admin/students/${id}/status`, {
            method: 'PUT',
            headers: getAdminHeaders(),
            body: JSON.stringify({ status: newStatus })
        });
        const data = await response.json();
        if (response.ok) {
            alert(data.message);
            renderAdminStudents();
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (err) {
        console.error(err);
    }
}

async function deleteStudentAction(id) {
    if (confirm("Are you absolutely sure you want to delete this student account? This cannot be undone.")) {
        try {
            const response = await fetch(`${API_BASE_URL}/admin/students/${id}`, {
                method: 'DELETE',
                headers: getAdminHeaders()
            });
            const data = await response.json();
            if (response.ok) {
                alert(data.message);
                renderAdminStudents();
            } else {
                alert(`Error: ${data.detail}`);
            }
        } catch (err) {
            console.error(err);
        }
    }
}

// ── 3. Teacher Management View ───────────────────────────────────────────────
async function renderAdminTeachers() {
    const tbody = document.getElementById("admin-teachers-table-body");
    if (!tbody) return;
    try {
        // Load teachers
        const response = await fetch(`${API_BASE_URL}/admin/teachers`, {
            headers: getAdminHeaders()
        });
        if (!checkAdminAuthResponse(response)) return;
        if (response.ok) {
            const data = await response.json();
            renderTeachersTable(data.teachers);
        } else {
            tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">Failed to load faculty list.</td></tr>`;
        }

        // Load departments dropdown for creation modal
        const dResponse = await fetch(`${API_BASE_URL}/admin/departments`, {
            headers: getAdminHeaders()
        });
        if (dResponse.ok) {
            const dData = await dResponse.json();
            const deptSelect = document.getElementById("add-t-dept");
            if (deptSelect) {
                deptSelect.innerHTML = '<option value="" disabled selected>Select Department</option>' + 
                    dData.departments.map(d => `<option value="${d.code}">${d.name} (${d.code})</option>`).join('');
            }
        }
    } catch (err) {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">Network error loading faculty list.</td></tr>`;
    }
}

function renderTeachersTable(teachers) {
    const tbody = document.getElementById("admin-teachers-table-body");
    if (!tbody) return;
    if (teachers.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4">No faculty records registered.</td></tr>`;
        return;
    }

    tbody.innerHTML = teachers.map(t => {
        const activeClass = t.is_active ? 'bg-success' : 'bg-secondary';
        const activeText = t.is_active ? 'Active' : 'Inactive';
        const subjectsText = t.subjects && t.subjects.length > 0 ? t.subjects.join(', ') : 'None assigned';

        return `
            <tr>
                <td><code>${t.employee_id}</code></td>
                <td>
                    <div class="fw-bold">${t.full_name}</div>
                </td>
                <td>${t.email}</td>
                <td>${t.department} / ${t.designation || 'Faculty'}</td>
                <td><span class="small text-muted">${subjectsText}</span></td>
                <td><span class="badge ${activeClass}">${activeText}</span></td>
                <td>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">Actions</button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#" onclick="toggleTeacherStatus('${t.id}', ${t.is_active})">
                                ${t.is_active ? '🔒 Disable Faculty' : '🔓 Enable Faculty'}
                            </a></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="deleteTeacherAction('${t.id}')">🗑 Delete Profile</a></li>
                        </ul>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

async function addTeacherSubmit(e) {
    e.preventDefault();
    const payload = {
        full_name: document.getElementById("add-t-name").value.trim(),
        email: document.getElementById("add-t-email").value.trim(),
        password: document.getElementById("add-t-password").value,
        department: document.getElementById("add-t-dept").value,
        employee_id: document.getElementById("add-t-empid").value.trim(),
        designation: document.getElementById("add-t-designation").value.trim(),
        subjects: []
    };

    try {
        const response = await fetch(`${API_BASE_URL}/admin/teachers`, {
            method: 'POST',
            headers: getAdminHeaders(),
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (response.ok) {
            alert(data.message);
            // Hide Bootstrap Modal
            const modalEl = document.getElementById('addTeacherModal');
            const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            if (modal) modal.hide();
            
            // Clear inputs
            e.target.reset();
            renderAdminTeachers();
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (err) {
        console.error(err);
    }
}

async function toggleTeacherStatus(id, currentStatus) {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/teachers/${id}/status`, {
            method: 'PUT',
            headers: getAdminHeaders(),
            body: JSON.stringify({ is_active: !currentStatus })
        });
        const data = await response.json();
        if (response.ok) {
            alert(data.message);
            renderAdminTeachers();
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (err) {
        console.error(err);
    }
}

async function deleteTeacherAction(id) {
    if (confirm("Are you sure you want to delete this faculty profile?")) {
        try {
            const response = await fetch(`${API_BASE_URL}/admin/teachers/${id}`, {
                method: 'DELETE',
                headers: getAdminHeaders()
            });
            const data = await response.json();
            if (response.ok) {
                alert(data.message);
                renderAdminTeachers();
            } else {
                alert(`Error: ${data.detail}`);
            }
        } catch (err) {
            console.error(err);
        }
    }
}

// ── 4. Department Management View ───────────────────────────────────────────
async function renderAdminDepartments() {
    const tbody = document.getElementById("admin-depts-table-body");
    if (!tbody) return;
    try {
        const response = await fetch(`${API_BASE_URL}/admin/departments`, {
            headers: getAdminHeaders()
        });
        if (!checkAdminAuthResponse(response)) return;
        if (response.ok) {
            const data = await response.json();
            allDepartmentsCache = data.departments;
            tbody.innerHTML = data.departments.map(d => {
                const statusClass = d.active ? 'bg-success' : 'bg-secondary';
                return `
                    <tr>
                        <td class="fw-bold">${d.name}</td>
                        <td><code>${d.code}</code></td>
                        <td>${d.total_semesters} Semesters</td>
                        <td><span class="badge ${statusClass}">${d.active ? 'Active' : 'Inactive'}</span></td>
                        <td>
                            <button class="btn btn-sm btn-outline-secondary" onclick="toggleDeptStatus('${d.code}', ${d.active})">
                                ${d.active ? 'Disable' : 'Enable'}
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">Failed to load departments.</td></tr>`;
        }
    } catch (err) {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">Network error loading departments.</td></tr>`;
    }
}

async function addDeptSubmit(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById("add-d-name").value.trim(),
        code: document.getElementById("add-d-code").value.trim().toUpperCase(),
        total_semesters: parseInt(document.getElementById("add-d-sems").value)
    };

    try {
        const response = await fetch(`${API_BASE_URL}/admin/departments`, {
            method: 'POST',
            headers: getAdminHeaders(),
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (response.ok) {
            alert(data.message);
            const modalEl = document.getElementById('addDeptModal');
            const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            if (modal) modal.hide();
            e.target.reset();
            renderAdminDepartments();
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (err) {
        console.error(err);
    }
}

async function toggleDeptStatus(code, currentStatus) {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/departments/${code}/status`, {
            method: 'PUT',
            headers: getAdminHeaders(),
            body: JSON.stringify({ active: !currentStatus })
        });
        const data = await response.json();
        if (response.ok) {
            alert(data.message);
            renderAdminDepartments();
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (err) {
        console.error(err);
    }
}

// ── 5. Subject Management View ──────────────────────────────────────────────
async function renderAdminSubjects() {
    const tbody = document.getElementById("admin-subjects-table-body");
    if (!tbody) return;
    try {
        // Load subjects
        const response = await fetch(`${API_BASE_URL}/admin/subjects`, {
            headers: getAdminHeaders()
        });
        if (!checkAdminAuthResponse(response)) return;
        if (response.ok) {
            const data = await response.json();
            tbody.innerHTML = data.subjects.map(s => `
                <tr>
                    <td><code>${s.subject_code}</code></td>
                    <td class="fw-bold">${s.subject_name}</td>
                    <td>${s.department} / Sem ${s.semester}</td>
                    <td>${s.credits} Credits</td>
                    <td>${s.faculty_name}</td>
                    <td>
                        <span class="badge ${s.is_active ? 'bg-success' : 'bg-secondary'}">${s.is_active ? 'Active' : 'Inactive'}</span>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `<tr><td colspan="6" class="text-danger text-center">Failed to load subjects syllabus.</td></tr>`;
        }

        // Load departments selection options
        const dRes = await fetch(`${API_BASE_URL}/admin/departments`, {
            headers: getAdminHeaders()
        });
        if (dRes.ok) {
            const dData = await dRes.json();
            document.getElementById("add-s-dept").innerHTML = '<option value="" disabled selected>Select Department</option>' + 
                dData.departments.map(d => `<option value="${d.code}">${d.name} (${d.code})</option>`).join('');
        }

        // Load faculty selection options
        const tRes = await fetch(`${API_BASE_URL}/admin/teachers`, {
            headers: getAdminHeaders()
        });
        if (tRes.ok) {
            const tData = await tRes.json();
            document.getElementById("add-s-faculty").innerHTML = '<option value="" disabled selected>Select Faculty Member</option>' + 
                tData.teachers.map(t => `<option value="${t.id}">${t.full_name}</option>`).join('');
        }
    } catch (err) {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="6" class="text-danger text-center">Network error loading subjects.</td></tr>`;
    }
}

async function addSubjectSubmit(e) {
    e.preventDefault();
    const payload = {
        subject_id: document.getElementById("add-s-id").value.trim(),
        subject_code: document.getElementById("add-s-code").value.trim().toUpperCase(),
        subject_name: document.getElementById("add-s-name").value.trim(),
        department: document.getElementById("add-s-dept").value,
        semester: parseInt(document.getElementById("add-s-sem").value),
        credits: parseInt(document.getElementById("add-s-credits").value),
        faculty_id: document.getElementById("add-s-faculty").value
    };

    try {
        const response = await fetch(`${API_BASE_URL}/admin/subjects`, {
            method: 'POST',
            headers: getAdminHeaders(),
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (response.ok) {
            alert(data.message);
            const modalEl = document.getElementById('addSubjectModal');
            const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            if (modal) modal.hide();
            e.target.reset();
            renderAdminSubjects();
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (err) {
        console.error(err);
    }
}

// ── 6. Student Verification View ─────────────────────────────────────────────
async function renderAdminVerification() {
    const tbody = document.getElementById("admin-verification-table-body");
    if (!tbody) return;
    try {
        const response = await fetch(`${API_BASE_URL}/admin/students`, {
            headers: getAdminHeaders()
        });
        if (!checkAdminAuthResponse(response)) return;
        if (response.ok) {
            const data = await response.json();
            const pending = data.students.filter(s => s.verification_status === 'pending');
            
            if (pending.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4">All student registrations have been processed. No pending accounts!</td></tr>`;
                return;
            }

            tbody.innerHTML = pending.map(s => {
                const photoHtml = s.profile_photo ? 
                    `<img src="${API_BASE_URL.replace('/api/v1', '')}/${s.profile_photo}" style="width:40px; height:40px; object-fit:cover; border-radius:50%;" />` : 
                    `<div style="width:40px; height:40px; border-radius:50%; background:#e2e3e5; display:flex; align-items:center; justify-content:center; font-weight:bold; color:#495057;">${(s.full_name || 'S').charAt(0)}</div>`;

                return `
                    <tr>
                        <td>${photoHtml}</td>
                        <td class="fw-bold">${s.full_name}</td>
                        <td>${s.email}</td>
                        <td><code>${s.usn}</code></td>
                        <td>${s.department}</td>
                        <td class="small text-muted">${s.created_at ? new Date(s.created_at).toLocaleDateString() : '—'}</td>
                        <td>
                            <button class="btn btn-sm btn-success px-3 me-1" onclick="verifyStudentWorkflow('${s.id}', 'approved')">Approve</button>
                            <button class="btn btn-sm btn-outline-danger px-3" onclick="verifyStudentWorkflow('${s.id}', 'rejected')">Reject</button>
                        </td>
                    </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">Failed to load verification queue.</td></tr>`;
        }
    } catch (err) {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">Network error loading verification queue.</td></tr>`;
    }
}

async function verifyStudentWorkflow(id, status) {
    if (confirm(`Approve student registration?`)) {
        await verifyStudentAction(id, status);
        renderAdminVerification();
    }
}

// ── 7. System Audit View ─────────────────────────────────────────────────────
async function renderAdminAudit() {
    const tbody = document.getElementById("admin-audit-table-body");
    if (!tbody) return;
    try {
        const response = await fetch(`${API_BASE_URL}/admin/audit-logs`, {
            headers: getAdminHeaders()
        });
        if (!checkAdminAuthResponse(response)) return;
        if (response.ok) {
            const data = await response.json();
            if (data.logs.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4">No audit logs recorded yet.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.logs.map(l => `
                <tr>
                    <td class="small text-muted" style="white-space:nowrap;">${l.timestamp}</td>
                    <td><span class="badge bg-secondary font-monospace" style="font-size:11px;">${l.action.toUpperCase()}</span></td>
                    <td><code>${l.actor}</code></td>
                    <td><code>${l.target}</code></td>
                    <td class="small">${l.details}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">Failed to load system audit logs.</td></tr>`;
        }
    } catch (err) {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">Network error loading system audit logs.</td></tr>`;
    }
}
