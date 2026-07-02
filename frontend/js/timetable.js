/* frontend/js/timetable.js */
let fullTimetable = [];

async function loadTimetablePage() {
    const btn = document.getElementById('btn-add-timetable');
    if (btn && (typeof currentRole !== 'undefined') && (currentRole === 'admin' || currentRole === 'teacher')) {
        btn.classList.remove('hidden');
    }
    await fetchTodayTimetable();
    await fetchWeeklyTimetable();
}

async function fetchTodayTimetable() {
    try {
        let endpoint = `${API_BASE_URL}/student/timetable/today`;
        if (typeof currentRole !== 'undefined' && (currentRole === 'admin' || currentRole === 'teacher')) {
            endpoint = `${API_BASE_URL}/${currentRole}/timetable?department=CSE&semester=5&section=A`;
        }
        const response = await fetch(endpoint, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            const data = await response.json();
            if (data.today) {
                const todaySchedule = data.today;
                document.getElementById('tt-today-title').textContent = `${todaySchedule.day_of_week}'s Schedule`;
                renderPeriodsList('tt-today-container', todaySchedule.periods);
            } else if (data.timetables) {
                const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
                const todayStr = days[new Date().getDay()];
                const dayMatch = data.timetables.find(t => t.day_of_week === todayStr);
                document.getElementById('tt-today-title').textContent = `${todayStr}'s Schedule`;
                renderPeriodsList('tt-today-container', dayMatch ? dayMatch.periods : []);
            }
        }
    } catch (err) {
        console.error(err);
        document.getElementById('tt-today-container').innerHTML = '<div class="text-danger p-4">Failed to load schedule.</div>';
    }
}

async function fetchWeeklyTimetable() {
    try {
        let endpoint = `${API_BASE_URL}/student/timetable`;
        if (typeof currentRole !== 'undefined' && (currentRole === 'admin' || currentRole === 'teacher')) {
            endpoint = `${API_BASE_URL}/${currentRole}/timetable?department=CSE&semester=5&section=A`;
        }
        const response = await fetch(endpoint, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            const data = await response.json();
            fullTimetable = data.timetables || [];
            
            const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
            const todayStr = days[new Date().getDay()];
            const selectEl = document.getElementById('tt-day-select');
            
            if (selectEl && todayStr !== "Sunday") {
                selectEl.value = todayStr;
            }
            if (selectEl) renderWeeklyDay(selectEl.value);
        }
    } catch (err) {
        console.error(err);
    }
}

function openAddTimetableModal() {
    const modalEl = document.getElementById('addTimetableModal');
    if (!modalEl) return;
    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    modal.show();
}

async function submitTimetableForm(e) {
    e.preventDefault();
    const payload = {
        department: document.getElementById('tt-modal-dept').value.trim(),
        semester: parseInt(document.getElementById('tt-modal-sem').value),
        section: document.getElementById('tt-modal-sec').value.trim().toUpperCase(),
        day_of_week: document.getElementById('tt-modal-day').value,
        period_no: parseInt(document.getElementById('tt-modal-period-no').value),
        start_time: document.getElementById('tt-modal-start').value,
        end_time: document.getElementById('tt-modal-end').value,
        subject_id: document.getElementById('tt-modal-subject').value.trim(),
        room: document.getElementById('tt-modal-room').value.trim()
    };

    try {
        const roleEndpoint = (typeof currentRole !== 'undefined' && currentRole === 'admin') ? 'admin' : 'teacher';
        const response = await fetch(`${API_BASE_URL}/${roleEndpoint}/timetable/upsert`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (response.ok) {
            alert(data.message || 'Timetable period updated successfully!');
            const modalEl = document.getElementById('addTimetableModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            await loadTimetablePage();
        } else {
            alert(`Error: ${data.detail || 'Failed to update timetable'}`);
        }
    } catch (err) {
        console.error("Failed to submit timetable", err);
        alert("Network error updating timetable.");
    }
}

function renderWeeklyDay(dayStr) {
    const container = document.getElementById('tt-weekly-container');
    const daySchedule = fullTimetable.find(t => t.day_of_week === dayStr);
    
    if (daySchedule && daySchedule.periods && daySchedule.periods.length > 0) {
        renderPeriodsList('tt-weekly-container', daySchedule.periods, false);
    } else {
        container.innerHTML = '<div class="text-center text-muted p-4">No classes scheduled.</div>';
    }
}

function getPeriodStatus(startStr, endStr, isToday) {
    if (!isToday) return '';
    
    const now = new Date();
    const currentMins = now.getHours() * 60 + now.getMinutes();
    
    const parseTime = (tStr) => {
        const [h, m] = tStr.split(':').map(Number);
        return h * 60 + m;
    };
    
    const startMins = parseTime(startStr);
    const endMins = parseTime(endStr);
    
    if (currentMins > endMins) return 'completed';
    if (currentMins >= startMins && currentMins <= endMins) return 'current';
    return 'upcoming';
}

function renderPeriodsList(containerId, periods, isToday = true) {
    const container = document.getElementById(containerId);
    if (!periods || periods.length === 0) {
        container.innerHTML = '<div class="text-center text-muted p-4">No classes scheduled.</div>';
        return;
    }
    
    let html = '<div class="tt-grid">';
    
    periods.forEach(p => {
        let status = '';
        if (p.is_cancelled) {
            status = 'cancelled';
        } else {
            status = getPeriodStatus(p.start_time, p.end_time, isToday);
        }
        
        const badgeLabel = p.is_cancelled ? "Cancelled" : 
                           status === 'current' ? "Ongoing" : 
                           status === 'completed' ? "Completed" : 
                           status === 'upcoming' ? "Upcoming" : "";
                           
        const badgeHtml = badgeLabel ? `<span class="tt-status-badge ${status}">${badgeLabel}</span>` : "";
        
        html += `
            <div class="tt-period ${status}">
                <div class="tt-time">
                    <div>${p.start_time}</div>
                    <div class="text-muted small">to ${p.end_time}</div>
                </div>
                <div class="tt-details">
                    <div class="tt-subject">${p.subject_name} (${p.subject_code})</div>
                    <div class="tt-meta">
                        <span>👨‍🏫 ${p.faculty_name}</span> | <span>🚪 ${p.room}</span>
                        ${p.cancel_reason ? `<br><span class="text-danger small">Reason: ${p.cancel_reason}</span>` : ''}
                    </div>
                </div>
                <div class="tt-status">
                    ${badgeHtml}
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

window.loadTimetablePage = loadTimetablePage;
