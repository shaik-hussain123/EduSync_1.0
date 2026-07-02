/* frontend/js/attendance.js */
let html5QrcodeScanner = null;

async function loadAttendancePage() {
    await fetchAttendanceHistory();
    await fetchAttendanceSummary();
}

async function fetchAttendanceHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/student/attendance/history`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            const data = await response.json();
            updateHistoryTable(data.history);
        }
    } catch (err) {
        console.error(err);
    }
}

async function fetchAttendanceSummary() {
    try {
        const response = await fetch(`${API_BASE_URL}/student/attendance/summary`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            const data = await response.json();
            document.getElementById('sum-total').textContent = data.total_classes;
            document.getElementById('sum-present').textContent = data.present;
            document.getElementById('sum-pct').textContent = `${data.percentage}%`;
        }
    } catch (err) {
        console.error(err);
    }
}

function updateHistoryTable(history) {
    const tbody = document.getElementById('att-history-body');
    if(history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">No attendance records found.</td></tr>';
        return;
    }
    
    let html = '';
    history.forEach(r => {
        const d = new Date(r.timestamp);
        const dateStr = d.toLocaleDateString([], {month:'short', day:'numeric'}) + ' ' + d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        html += `
            <tr>
                <td>${r.subject}</td>
                <td><span class="badge bg-${r.status === 'Present' ? 'success' : 'danger'}">${r.status}</span></td>
                <td>${dateStr}</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function startScanner() {
    const student = JSON.parse(localStorage.getItem('student') || '{}');
    if (!student.profile_completed) {
        attAlert('danger', 'Please complete your profile before marking attendance.');
        return;
    }
    if (!student.face_registered) {
        attAlert('danger', 'Please complete face registration before marking attendance.');
        return;
    }

    document.getElementById('start-scan-wrapper').style.display = 'none';
    document.getElementById('scanner-wrapper').style.display = 'block';

    html5QrcodeScanner = new Html5QrcodeScanner(
        "reader",
        { fps: 10, qrbox: {width: 250, height: 250} },
        /* verbose= */ false
    );
    html5QrcodeScanner.render(onScanSuccess, onScanFailure);
}

function stopScanner() {
    if (html5QrcodeScanner) {
        html5QrcodeScanner.clear().then(() => {
            document.getElementById('start-scan-wrapper').style.display = 'block';
            document.getElementById('scanner-wrapper').style.display = 'none';
        }).catch(error => {
            console.error("Failed to clear html5QrcodeScanner. ", error);
        });
    }
}

async function onScanSuccess(decodedText, decodedResult) {
    // Stop scanning immediately to prevent multiple API calls
    stopScanner();
    
    try {
        const response = await fetch(`${API_BASE_URL}/student/attendance/scan`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}` 
            },
            body: JSON.stringify({ qr_token: decodedText })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            attAlert('success', 'Attendance marked successfully!');
            await loadAttendancePage();
        } else {
            attAlert('danger', data.detail || 'Failed to mark attendance.');
        }
    } catch (err) {
        console.error(err);
        attAlert('danger', 'Network error. Please try again.');
    }
}

function onScanFailure(error) {
    // Handle scan failure, usually better to ignore and keep scanning
    // console.warn(`Code scan error = ${error}`);
}

function attAlert(type, msg) {
    const el = document.getElementById('att-alert');
    el.className = `alert alert-${type} mb-4`;
    el.textContent = msg;
    el.style.display = 'block';
    setTimeout(() => el.style.display = 'none', 5000);
}

window.loadAttendancePage = loadAttendancePage;
