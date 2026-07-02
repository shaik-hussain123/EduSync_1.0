/**
 * frontend/js/settings.js
 * EduSync — Smart Campus ERP | Student Settings Module
 */

const SETTINGS_API_BASE = `${API_BASE_URL}/settings`;

function getSettingsHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
    };
}

function settingsAlert(type, msg) {
    const el = document.getElementById('settings-alert');
    if (!el) return;
    el.className = `alert alert-${type} mb-4`;
    el.textContent = msg;
    el.style.display = 'block';
    if (type === 'success') {
        setTimeout(() => { el.style.display = 'none'; }, 4000);
    }
}

function populateSettingsView(data) {
    const account = data.account || {};
    const profile = data.profile || {};
    const prefs = data.preferences || {};
    const session = data.session || {};

    document.getElementById('acc-full-name').textContent = account.full_name || '—';
    document.getElementById('acc-usn').textContent = account.usn || '—';
    document.getElementById('acc-email').textContent = account.email || '—';
    document.getElementById('acc-department').textContent = account.department || '—';
    document.getElementById('acc-semester').textContent = account.semester != null ? `Semester ${account.semester}` : '—';
    document.getElementById('acc-section').textContent = account.section ? `Section ${account.section}` : '—';

    document.getElementById('settings-full-name').value = profile.full_name || '';
    document.getElementById('settings-phone').value = profile.phone || '';
    document.getElementById('settings-gender').value = profile.gender || '';
    document.getElementById('settings-dob').value = profile.date_of_birth || '';

    document.getElementById('settings-theme').value = prefs.theme || 'light';
    document.getElementById('settings-language').value = prefs.language || 'English';
    document.getElementById('settings-date-format').value = prefs.date_format || 'DD/MM/YYYY';
    document.getElementById('settings-time-format').value = prefs.time_format || '24h';

    document.getElementById('notif-attendance').checked = prefs.attendance_notifications !== false;
    document.getElementById('notif-leave').checked = prefs.leave_notifications !== false;
    document.getElementById('notif-timetable').checked = prefs.timetable_notifications !== false;
    document.getElementById('notif-general').checked = prefs.general_notifications !== false;

    document.getElementById('session-login-time').textContent = session.login_time ? new Date(session.login_time).toLocaleString() : '—';
    document.getElementById('session-browser').textContent = session.browser || '—';
    document.getElementById('session-jwt-expiry').textContent = session.jwt_expiry || '—';
}

async function loadSettingsPage() {
    try {
        const response = await fetch(`${SETTINGS_API_BASE}`, {
            headers: getSettingsHeaders()
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Unable to load settings.');
        }

        populateSettingsView(data);
    } catch (error) {
        console.error(error);
        settingsAlert('danger', error.message || 'Unable to load settings.');
    }
}

async function saveSettings() {
    try {
        const payload = {
            full_name: document.getElementById('settings-full-name').value.trim(),
            phone: document.getElementById('settings-phone').value.trim(),
            gender: document.getElementById('settings-gender').value || null,
            date_of_birth: document.getElementById('settings-dob').value || null,
            theme: document.getElementById('settings-theme').value,
            language: document.getElementById('settings-language').value,
            date_format: document.getElementById('settings-date-format').value,
            time_format: document.getElementById('settings-time-format').value,
            attendance_notifications: document.getElementById('notif-attendance').checked,
            leave_notifications: document.getElementById('notif-leave').checked,
            timetable_notifications: document.getElementById('notif-timetable').checked,
            general_notifications: document.getElementById('notif-general').checked,
        };

        const response = await fetch(`${SETTINGS_API_BASE}`, {
            method: 'PUT',
            headers: getSettingsHeaders(),
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Unable to save settings.');
        }

        populateSettingsView(data);
        settingsAlert('success', data.message || 'Settings updated successfully.');
    } catch (error) {
        console.error(error);
        settingsAlert('danger', error.message || 'Unable to save settings.');
    }
}

async function changePassword() {
    try {
        const payload = {
            current_password: document.getElementById('settings-current-password').value,
            new_password: document.getElementById('settings-new-password').value,
            confirm_password: document.getElementById('settings-confirm-password').value,
        };

        const response = await fetch(`${API_BASE_URL}/settings/change-password`, {
            method: 'PUT',
            headers: getSettingsHeaders(),
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Unable to change password.');
        }

        document.getElementById('settings-current-password').value = '';
        document.getElementById('settings-new-password').value = '';
        document.getElementById('settings-confirm-password').value = '';
        settingsAlert('success', data.message || 'Password updated successfully.');
    } catch (error) {
        console.error(error);
        settingsAlert('danger', error.message || 'Unable to change password.');
    }
}

function logoutFromSettings() {
    localStorage.removeItem('student');
    localStorage.removeItem('teacher');
    localStorage.removeItem('admin');
    localStorage.removeItem('access_token');
    localStorage.removeItem('token_type');
    localStorage.removeItem('user');
    window.location.href = 'signin.html';
}

function attachSettingsEvents() {
    const saveBtn = document.getElementById('btn-save-settings');
    if (saveBtn) saveBtn.addEventListener('click', saveSettings);

    const passwordBtn = document.getElementById('btn-change-password');
    if (passwordBtn) passwordBtn.addEventListener('click', changePassword);

    const logoutBtn = document.getElementById('btn-logout');
    if (logoutBtn) logoutBtn.addEventListener('click', logoutFromSettings);
}

function initSettingsPage() {
    attachSettingsEvents();
    loadSettingsPage();
}

window.initSettingsPage = initSettingsPage;
