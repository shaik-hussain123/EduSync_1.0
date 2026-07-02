/**
 * frontend/js/notification.js
 * EduSync — Smart Campus ERP | Student Notifications Module
 */

const NOTIFICATIONS_API_BASE = `${API_BASE_URL}/notifications`;
let currentNotificationFilter = 'all';
let notificationState = [];

function getNotificationHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
    };
}

function notificationAlert(type, msg) {
    const el = document.getElementById('notifications-alert');
    if (!el) return;
    el.className = `alert alert-${type} mb-3`;
    el.textContent = msg;
    el.style.display = 'block';
    if (type === 'success') {
        setTimeout(() => { el.style.display = 'none'; }, 3000);
    }
}

function formatNotificationDate(value) {
    if (!value) return '—';
    const d = new Date(value);
    return isNaN(d.getTime()) ? value : d.toLocaleString();
}

function getFilteredNotifications() {
    if (currentNotificationFilter === 'unread') {
        return notificationState.filter(n => !n.is_read);
    }
    if (currentNotificationFilter === 'read') {
        return notificationState.filter(n => n.is_read);
    }
    return notificationState;
}

function renderNotificationList() {
    const container = document.getElementById('notifications-list');
    if (!container) return;

    const items = getFilteredNotifications();
    if (!items.length) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">🔔</div><div class="empty-msg">No notifications available.</div></div>';
        return;
    }

    container.innerHTML = items.map(n => `
        <div class="notification-item ${n.is_read ? 'read' : 'unread'}">
            <div class="notification-icon">${getNotificationIcon(n.type)}</div>
            <div class="notification-content">
                <div class="notification-top">
                    <div class="notification-title">${n.title}</div>
                    <div class="notification-meta">
                        <span class="badge bg-${getPriorityClass(n.priority)}">${n.priority || 'Normal'}</span>
                        <span class="notification-date">${formatNotificationDate(n.created_at)}</span>
                    </div>
                </div>
                <div class="notification-message">${n.message}</div>
                <div class="notification-actions">
                    ${!n.is_read ? `<button class="btn btn-sm btn-outline-primary me-2" data-action="read" data-id="${n.notification_id}">Mark as Read</button>` : ''}
                    <button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${n.notification_id}">Delete</button>
                </div>
            </div>
        </div>
    `).join('');
}

function getNotificationIcon(type) {
    const icons = {
        'Attendance Marked': '✅',
        'Attendance Missed': '⚠️',
        'Leave Approved': '📝',
        'Leave Rejected': '❌',
        'Leave Cancelled': '🚫',
        'Timetable Updated': '🗓️',
        'Holiday Announcement': '🎉',
        'Profile Reminder': '👤',
        'Face Registration Reminder': '📷',
        'General Announcement': '📢'
    };
    return icons[type] || '🔔';
}

function getPriorityClass(priority) {
    const map = {
        'Low': 'secondary',
        'Normal': 'primary',
        'High': 'warning',
        'Critical': 'danger'
    };
    return map[priority] || 'primary';
}

async function fetchNotifications() {
    try {
        const response = await fetch(NOTIFICATIONS_API_BASE, { headers: getNotificationHeaders() });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Unable to load notifications.');
        notificationState = data.notifications || [];
        renderNotificationList();
        updateNotificationBell();
    } catch (error) {
        console.error(error);
        notificationAlert('danger', error.message || 'Unable to load notifications.');
    }
}

async function markNotificationRead(notificationId) {
    try {
        const response = await fetch(`${NOTIFICATIONS_API_BASE}/${notificationId}/read`, {
            method: 'PUT',
            headers: getNotificationHeaders()
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Unable to update notification.');
        notificationAlert('success', data.message || 'Notification marked as read.');
        await fetchNotifications();
    } catch (error) {
        console.error(error);
        notificationAlert('danger', error.message || 'Unable to update notification.');
    }
}

async function markAllNotificationsRead() {
    try {
        const response = await fetch(`${NOTIFICATIONS_API_BASE}/read-all`, {
            method: 'PUT',
            headers: getNotificationHeaders()
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Unable to update notifications.');
        notificationAlert('success', data.message || 'All notifications marked as read.');
        await fetchNotifications();
    } catch (error) {
        console.error(error);
        notificationAlert('danger', error.message || 'Unable to update notifications.');
    }
}

async function deleteNotification(notificationId) {
    try {
        const response = await fetch(`${NOTIFICATIONS_API_BASE}/${notificationId}`, {
            method: 'DELETE',
            headers: getNotificationHeaders()
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Unable to delete notification.');
        notificationAlert('success', data.message || 'Notification deleted.');
        await fetchNotifications();
    } catch (error) {
        console.error(error);
        notificationAlert('danger', error.message || 'Unable to delete notification.');
    }
}

async function refreshNotificationBadge() {
    try {
        const response = await fetch(`${NOTIFICATIONS_API_BASE}/unread-count`, { headers: getNotificationHeaders() });
        const data = await response.json();
        if (!response.ok) return;
        const bell = document.querySelector('.topbar-notif');
        if (bell) {
            const badge = bell.querySelector('.notif-dot');
            if (badge) {
                badge.style.display = data.unread_count > 0 ? 'inline-block' : 'none';
            }
        }
    } catch (error) {
        console.error(error);
    }
}

function updateNotificationBell() {
    const bell = document.querySelector('.topbar-notif');
    if (!bell) return;
    const badge = bell.querySelector('.notif-dot');
    if (badge) {
        const unread = notificationState.filter(n => !n.is_read).length;
        badge.style.display = unread > 0 ? 'inline-block' : 'none';
    }
}

function attachNotificationEvents() {
    const list = document.getElementById('notifications-list');
    if (list) {
        list.addEventListener('click', async (event) => {
            const btn = event.target.closest('button[data-action]');
            if (!btn) return;
            const action = btn.getAttribute('data-action');
            const id = btn.getAttribute('data-id');
            if (action === 'read') {
                await markNotificationRead(id);
            } else if (action === 'delete') {
                await deleteNotification(id);
            }
        });
    }

    document.querySelectorAll('[data-filter]').forEach((btn) => {
        btn.addEventListener('click', () => {
            currentNotificationFilter = btn.getAttribute('data-filter');
            document.querySelectorAll('[data-filter]').forEach((b) => b.classList.remove('btn-primary-erp'));
            btn.classList.add('btn-primary-erp');
            renderNotificationList();
        });
    });

    const markAllBtn = document.getElementById('btn-mark-all-read');
    if (markAllBtn) {
        markAllBtn.addEventListener('click', markAllNotificationsRead);
    }
}

async function loadNotificationsPage() {
    attachNotificationEvents();
    await fetchNotifications();
    await refreshNotificationBadge();
}

function initNotificationsPage() {
    loadNotificationsPage();
}

window.initNotificationsPage = initNotificationsPage;
window.refreshNotificationBadge = refreshNotificationBadge;
