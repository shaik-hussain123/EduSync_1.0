/* frontend/js/timetable.js */
let fullTimetable = [];

async function loadTimetablePage() {
    await fetchTodayTimetable();
    await fetchWeeklyTimetable();
}

async function fetchTodayTimetable() {
    try {
        const response = await fetch(`${API_BASE_URL}/student/timetable/today`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            const data = await response.json();
            const todaySchedule = data.today || { day_of_week: "Today", periods: [] };
            document.getElementById('tt-today-title').textContent = `${todaySchedule.day_of_week}'s Schedule`;
            renderPeriodsList('tt-today-container', todaySchedule.periods);
        }
    } catch (err) {
        console.error(err);
        document.getElementById('tt-today-container').innerHTML = '<div class="text-danger p-4">Failed to load schedule.</div>';
    }
}

async function fetchWeeklyTimetable() {
    try {
        const response = await fetch(`${API_BASE_URL}/student/timetable`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            const data = await response.json();
            fullTimetable = data.timetables || [];
            
            // Set select to today if available
            const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
            const todayStr = days[new Date().getDay()];
            const selectEl = document.getElementById('tt-day-select');
            
            if(todayStr !== "Sunday") {
                selectEl.value = todayStr;
            }
            renderWeeklyDay(selectEl.value);
        }
    } catch (err) {
        console.error(err);
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
