/**
 * frontend/js/profile.js
 * EduSync — Smart Campus ERP | Student Profile Module
 *
 * Loads inside the dashboard's #page-content area when "My Profile" is clicked.
 * Calls:
 *   GET /api/v1/student/profile   — fetch full profile
 *   PUT /api/v1/student/profile   — update fields + optional photo
 */

/* ── Helpers ─────────────────────────────────────────────────────────────── */
function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return { Authorization: `Bearer ${token}` };
}

function profileAlert(type, msg) {
    const el = document.getElementById('profile-alert');
    if (!el) return;
    el.className = `alert alert-${type} mb-4`;
    el.textContent = msg;
    el.style.display = 'block';
    if (type === 'success') {
        setTimeout(() => { el.style.display = 'none'; }, 4000);
    }
}

function profileAlertHide() {
    const el = document.getElementById('profile-alert');
    if (el) el.style.display = 'none';
}

/* ── Profile completion helpers ─────────────────────────────────────────── */
const PROFILE_FIELDS = [
    'full_name', 'email', 'usn', 'department',
    'semester', 'section', 'phone', 'gender', 'date_of_birth', 'profile_photo'
];

function calcPct(profile) {
    const filled = PROFILE_FIELDS.filter(f => profile[f] != null && profile[f] !== '');
    return Math.round((filled.length / PROFILE_FIELDS.length) * 100);
}

/* ── Render the profile page HTML ───────────────────────────────────────── */
function renderProfilePage(profile) {
    const pct     = profile.profile_completion_pct ?? calcPct(profile);
    const photoSrc = profile.profile_photo
        ? `${API_BASE_URL.replace('/api/v1', '')}/${profile.profile_photo}`
        : null;

    const avatarHtml = photoSrc
        ? `<img src="${photoSrc}" alt="Profile photo" class="pf-photo-img" id="photo-preview">`
        : `<div class="pf-avatar-placeholder" id="photo-preview">
               <span>${(profile.full_name || 'S').charAt(0).toUpperCase()}</span>
           </div>`;

    const badgeClass = {
        pending:  'badge-pending',
        approved: 'badge-approved',
        rejected: 'badge-rejected',
    }[profile.verification_status] || 'badge-pending';

    const isTeacher = (typeof currentRole !== 'undefined' && currentRole === 'teacher');
    const academicSectionTitle = isTeacher ? 'Professional Information' : 'Academic Information';

    const viewAcademicFields = isTeacher
        ? `
            ${viewField('Employee ID', profile.employee_id || profile.usn)}
            ${viewField('Department',  profile.department, true)}
            ${viewField('Designation', profile.designation || 'Assistant Professor')}
            ${viewField('Subjects',    Array.isArray(profile.subjects) && profile.subjects.length ? profile.subjects.join(', ') : 'None')}
          `
        : `
            ${viewField('USN',        profile.usn,        true)}
            ${viewField('Department', profile.department, true)}
            ${viewField('Semester',   profile.semester != null ? `Semester ${profile.semester}` : null)}
            ${viewField('Section',    profile.section  ? `Section ${profile.section}` : null)}
          `;

    const editAcademicFields = isTeacher
        ? `
            ${editField('employee_id', 'Employee ID', 'text', profile.employee_id || profile.usn)}
            ${editFieldReadOnly('department', 'Department', profile.department)}
            ${editField('designation', 'Designation', 'text', profile.designation || 'Assistant Professor')}
          `
        : `
            ${editFieldReadOnly('usn',        'USN',        profile.usn)}
            ${editFieldReadOnly('department', 'Department', profile.department)}
            ${editField('semester', 'Semester', 'number',   profile.semester, 'min="1" max="8"')}
            ${editFieldSelect('section', 'Section',
                ['', 'A', 'B', 'C', 'D'],
                ['Select Section', 'A', 'B', 'C', 'D'],
                profile.section)}
          `;

    const html = `
<div id="profile-page">

    <!-- Alert bar -->
    <div class="alert" id="profile-alert" style="display:none;" role="alert"></div>

    <!-- Header row -->
    <div class="d-flex align-items-center justify-content-between mb-4 flex-wrap gap-3">
        <div>
            <h2 class="pf-heading">My Profile</h2>
            <p class="pf-sub">View and update your personal information</p>
        </div>
        <button class="btn-primary-erp" id="btn-edit-profile" onclick="enterEditMode()">
            ✏️ Edit Profile
        </button>
    </div>

    <!-- Top card: photo + identity -->
    <div class="pf-card pf-card-top mb-4">

        <div class="pf-photo-area">
            ${avatarHtml}
            <label class="pf-photo-btn hidden" id="photo-label" for="input-photo" title="Change photo">
                📷
            </label>
            <input type="file" id="input-photo" accept="image/jpeg,image/png,image/jpg"
                   style="display:none" onchange="previewPhoto(this)">
        </div>

        <div class="pf-identity">
            <h3 class="pf-name">${profile.full_name || '—'}</h3>
            <p class="pf-usn">${profile.employee_id || profile.usn || '—'} &nbsp;·&nbsp; ${profile.department || '—'}</p>
            <span class="badge ${badgeClass}">${capitalize(profile.verification_status)}</span>
        </div>

        <div class="pf-completion ms-auto">
            <div class="pf-pct-label">Profile Completion</div>
            <div class="pf-pct-num" id="pf-pct-num">${pct}%</div>
            <div class="progress-bar-track" style="width:160px">
                <div class="progress-bar-fill" id="pf-pct-bar" style="width:${pct}%"></div>
            </div>
        </div>

    </div>

    <!-- Detail cards: view mode -->
    <div id="profile-view-mode">
        <div class="pf-card mb-4">
            <div class="pf-section-title">Personal Information</div>
            <div class="pf-field-grid">
                ${viewField('Full Name',     profile.full_name)}
                ${viewField('Email',         profile.email, true)}
                ${viewField('Phone',         profile.phone)}
                ${viewField('Gender',        profile.gender)}
                ${viewField('Date of Birth', profile.date_of_birth)}
            </div>
        </div>
        <div class="pf-card mb-4">
            <div class="pf-section-title">${academicSectionTitle}</div>
            <div class="pf-field-grid">
                ${viewAcademicFields}
            </div>
        </div>
    </div>

    <!-- Edit form: hidden until Edit is clicked -->
    <div id="profile-edit-mode" style="display:none">
        <form id="profile-form" onsubmit="submitProfileUpdate(event)">
            <div class="pf-card mb-4">
                <div class="pf-section-title">Personal Information</div>
                <div class="pf-field-grid">
                    ${editField('full_name',     'Full Name',      'text',   profile.full_name)}
                    ${editFieldReadOnly('email', 'Email',                    profile.email)}
                    ${editField('phone',         'Phone',          'tel',    profile.phone)}
                    ${editFieldSelect('gender',  'Gender',
                        ['', 'Male', 'Female'],
                        ['Select Gender', 'Male', 'Female'],
                        profile.gender)}
                    ${editField('date_of_birth', 'Date of Birth',  'date',   profile.date_of_birth)}
                </div>
            </div>
            <div class="pf-card mb-4">
                <div class="pf-section-title">${academicSectionTitle}</div>
                <div class="pf-field-grid">
                    ${editAcademicFields}
                </div>
            </div>
            <div class="d-flex gap-3 mt-2">
                <button type="submit" class="btn-primary-erp" id="btn-save">
                    💾 Save Changes
                </button>
                <button type="button" class="btn-secondary-erp" onclick="cancelEditMode()">
                    ✕ Cancel
                </button>
            </div>
        </form>
    </div>

</div><!-- /profile-page -->
    `;

    const container = document.getElementById('main-content');
    if (container) container.innerHTML = html;
}

/* ── View / edit field builders ─────────────────────────────────────────── */
function viewField(label, value, readOnly = false) {
    const display = (value != null && value !== '') ? value : '<span class="not-set">Not Set</span>';
    const badge   = readOnly ? ' <span class="read-only-tag">read-only</span>' : '';
    return `
        <div class="pf-field">
            <div class="pf-field-label">${label}${badge}</div>
            <div class="pf-field-value">${display}</div>
        </div>`;
}

function editField(name, label, type, value, extra = '') {
    const val = (value != null && value !== '') ? value : '';
    return `
        <div class="pf-field">
            <label class="pf-field-label" for="ef-${name}">${label}</label>
            <input id="ef-${name}" name="${name}" type="${type}" class="pf-input"
                   value="${val}" ${extra} autocomplete="off">
        </div>`;
}

function editFieldReadOnly(name, label, value) {
    const val = (value != null && value !== '') ? value : '';
    return `
        <div class="pf-field">
            <label class="pf-field-label" for="ef-${name}">
                ${label} <span class="read-only-tag">read-only</span>
            </label>
            <input id="ef-${name}" name="${name}" type="text" class="pf-input pf-input-readonly"
                   value="${val}" readonly>
        </div>`;
}

function editFieldSelect(name, label, vals, labels, current) {
    const opts = vals.map((v, i) => {
        const sel = (v === current) ? 'selected' : '';
        return `<option value="${v}" ${sel}>${labels[i]}</option>`;
    }).join('');
    return `
        <div class="pf-field">
            <label class="pf-field-label" for="ef-${name}">${label}</label>
            <select id="ef-${name}" name="${name}" class="pf-input">${opts}</select>
        </div>`;
}

/* ── Edit / cancel modes ────────────────────────────────────────────────── */
function enterEditMode() {
    document.getElementById('profile-view-mode').style.display = 'none';
    document.getElementById('profile-edit-mode').style.display = 'block';
    document.getElementById('btn-edit-profile').style.display  = 'none';
    // Show photo change button
    const photoLabel = document.getElementById('photo-label');
    if (photoLabel) photoLabel.classList.remove('hidden');
    profileAlertHide();
}

function cancelEditMode() {
    document.getElementById('profile-view-mode').style.display = 'block';
    document.getElementById('profile-edit-mode').style.display = 'none';
    document.getElementById('btn-edit-profile').style.display  = '';
    const photoLabel = document.getElementById('photo-label');
    if (photoLabel) photoLabel.classList.add('hidden');
    profileAlertHide();
}

/* ── Photo preview ───────────────────────────────────────────────────────── */
function previewPhoto(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = e => {
            const preview = document.getElementById('photo-preview');
            if (!preview) return;
            if (preview.tagName === 'IMG') {
                preview.src = e.target.result;
            } else {
                // Replace placeholder div with an img
                const img = document.createElement('img');
                img.src = e.target.result;
                img.alt = 'Profile photo';
                img.className = 'pf-photo-img';
                img.id = 'photo-preview';
                preview.replaceWith(img);
            }
        };
        reader.readAsDataURL(input.files[0]);
    }
}

/* ── Submit profile update ──────────────────────────────────────────────── */
async function submitProfileUpdate(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-save');
    const originalText = btn.textContent;
    btn.textContent = 'Saving...';
    btn.disabled = true;
    profileAlertHide();

    try {
        const form     = document.getElementById('profile-form');
        const formData = new FormData();

        // Add non-empty, non-readonly text fields
        const textFields = ['full_name', 'phone', 'semester', 'date_of_birth', 'employee_id', 'designation'];
        textFields.forEach(name => {
            const el = form.elements[name];
            if (el && el.value.trim() !== '') {
                formData.append(name, el.value.trim());
            }
        });

        // Dropdowns
        ['gender', 'section'].forEach(name => {
            const el = form.elements[name];
            if (el && el.value !== '') {
                formData.append(name, el.value);
            }
        });

        // Photo
        const photoInput = document.getElementById('input-photo');
        if (photoInput && photoInput.files[0]) {
            formData.append('profile_photo', photoInput.files[0]);
        }

        let updateEndpoint = `${API_BASE_URL}/student/profile`;
        if (typeof currentRole !== 'undefined' && currentRole === 'teacher') {
            updateEndpoint = `${API_BASE_URL}/teacher/profile`;
        }

        const response = await fetch(updateEndpoint, {
            method: 'PUT',
            headers: getAuthHeaders(),  // No Content-Type — FormData sets it automatically
            body: formData,
        });

        const data = await response.json();

        if (response.ok) {
            profileAlert('success', `✅ ${data.message}`);

            // Update completion bar
            const pct = data.profile_completion_pct;
            const barEl = document.getElementById('pf-pct-bar');
            const numEl = document.getElementById('pf-pct-num');
            if (barEl) barEl.style.width = `${pct}%`;
            if (numEl) numEl.textContent = `${pct}%`;

            // Reload fresh profile from backend
            await loadProfilePage();

            // Refresh dashboard nav info
            await refreshDashboardFromAPI();
        } else {
            let msg = data.detail || 'Update failed. Please check your inputs.';
            if (Array.isArray(msg)) msg = msg.map(e => e.msg || e).join('; ');
            profileAlert('danger', `❌ ${msg}`);
            btn.textContent = originalText;
            btn.disabled = false;
        }
    } catch (err) {
        profileAlert('danger', '❌ Network error: Could not connect to the server.');
        console.error(err);
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

/* ── Fetch profile from API and render ──────────────────────────────────── */
async function loadProfilePage() {
    const container = document.getElementById('main-content');
    if (container) {
        container.innerHTML = `
            <div class="d-flex align-items-center justify-content-center" style="min-height:300px">
                <div class="text-center text-muted">
                    <div class="spinner-border text-secondary mb-3" role="status"></div>
                    <p>Loading profile...</p>
                </div>
            </div>`;
    }

    try {
        let endpoint = `${API_BASE_URL}/student/profile`;
        let roleKey = 'student';
        if (typeof currentRole !== 'undefined' && currentRole === 'teacher') {
            endpoint = `${API_BASE_URL}/teacher/me`;
            roleKey = 'teacher';
        }

        const response = await fetch(endpoint, {
            headers: getAuthHeaders(),
        });

        if (response.status === 401) {
            signOut();
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const profile = await response.json();

        if (roleKey === 'teacher') {
            profile.usn = profile.employee_id || 'FACULTY';
            profile.verification_status = profile.verification_status || 'approved';
        }

        // Update localStorage with fresh data
        const stored = JSON.parse(localStorage.getItem(roleKey) || '{}');
        const merged = { ...stored, ...profile };
        localStorage.setItem(roleKey, JSON.stringify(merged));

        renderProfilePage(profile);
    } catch (err) {
        console.error('Failed to load profile:', err);
        if (container) {
            container.innerHTML = `
                <div class="pf-card text-center py-5">
                    <div style="font-size:40px">⚠️</div>
                    <p class="mt-3 text-muted">Failed to load profile. Please try again.</p>
                    <button class="btn-primary-erp mt-3" onclick="loadProfilePage()">Retry</button>
                </div>`;
        }
    }
}

/* ── Refresh dashboard header from API profile ───────────────────────────── */
async function refreshDashboardFromAPI() {
    try {
        let fetchEndpoint = `${API_BASE_URL}/student/profile`;
        const roleKey = (typeof currentRole !== 'undefined' && currentRole === 'teacher') ? 'teacher' : 'student';
        if (roleKey === 'teacher') {
            fetchEndpoint = `${API_BASE_URL}/teacher/me`;
        }
        const response = await fetch(fetchEndpoint, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) return;
        const profile = await response.json();

        localStorage.setItem(roleKey, JSON.stringify(profile));

        if (typeof currentUser !== 'undefined') {
            currentUser = profile;
        }
        if (typeof updateUserStrip === 'function') {
            updateUserStrip();
        }
    } catch (_) {
        // Non-critical — don't throw
    }
}

/* ── Utility ─────────────────────────────────────────────────────────────── */
function capitalize(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}
