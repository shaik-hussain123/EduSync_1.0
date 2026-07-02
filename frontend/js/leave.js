/* frontend/js/leave.js */
let leaveTypes = [];

async function loadLeavePage() {
    await fetchLeaveTypes();
    await fetchLeaveHistory();
    
    // Set min date to today for inputs
    const todayStr = new Date().toISOString().split('T')[0];
    document.getElementById('leave-from').setAttribute('min', todayStr);
    document.getElementById('leave-to').setAttribute('min', todayStr);
}

async function fetchLeaveTypes() {
    try {
        const response = await fetch(`${API_BASE_URL}/student/leave/types`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            const data = await response.json();
            leaveTypes = data.leave_types || [];
            
            const select = document.getElementById('leave-type-select');
            select.innerHTML = '<option value="">Select type...</option>';
            leaveTypes.forEach(lt => {
                select.innerHTML += `<option value="${lt.leave_type_id}">${lt.name} (Max ${lt.max_days} days)</option>`;
            });
        }
    } catch (err) {
        console.error(err);
    }
}

function checkAttachmentRequirement() {
    const selectedId = document.getElementById('leave-type-select').value;
    const type = leaveTypes.find(t => t.leave_type_id === selectedId);
    const reqSpan = document.getElementById('attachment-req');
    const input = document.getElementById('leave-attachment');
    
    if (type && type.requires_attachment) {
        reqSpan.textContent = '(Required)';
        reqSpan.className = 'text-danger small';
        input.required = true;
    } else {
        reqSpan.textContent = '(Optional)';
        reqSpan.className = 'text-muted small';
        input.required = false;
    }
}

function calculateTotalDays() {
    const fromStr = document.getElementById('leave-from').value;
    const toStr = document.getElementById('leave-to').value;
    const totalEl = document.getElementById('leave-total-days');
    
    if (fromStr && toStr) {
        const fromDate = new Date(fromStr);
        const toDate = new Date(toStr);
        
        if (toDate >= fromDate) {
            const diffTime = Math.abs(toDate - fromDate);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
            totalEl.textContent = diffDays;
        } else {
            totalEl.textContent = 'Invalid dates';
        }
    } else {
        totalEl.textContent = '0';
    }
}

async function submitLeaveRequest() {
    const btn = document.getElementById('btn-submit-leave');
    btn.disabled = true;
    btn.textContent = 'Submitting...';
    
    try {
        const formData = new FormData();
        formData.append('leave_type_id', document.getElementById('leave-type-select').value);
        formData.append('from_date', document.getElementById('leave-from').value);
        formData.append('to_date', document.getElementById('leave-to').value);
        formData.append('reason', document.getElementById('leave-reason').value);
        
        const fileInput = document.getElementById('leave-attachment');
        if (fileInput.files.length > 0) {
            formData.append('attachment', fileInput.files[0]);
        }
        
        const response = await fetch(`${API_BASE_URL}/student/leave/apply`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
            body: formData
        });
        
        const data = await response.json();
        if (response.ok) {
            leaveAlert('success', data.message || 'Leave applied successfully.');
            document.getElementById('form-leave-apply').reset();
            document.getElementById('leave-total-days').textContent = '0';
            checkAttachmentRequirement();
            await fetchLeaveHistory();
        } else {
            leaveAlert('danger', data.detail || 'Failed to apply for leave.');
        }
    } catch (err) {
        console.error(err);
        leaveAlert('danger', 'Network error while submitting request.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Submit Request';
    }
}

async function fetchLeaveHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/student/leave/history`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            const data = await response.json();
            renderLeaveHistory(data.history || []);
        }
    } catch (err) {
        console.error(err);
    }
}

function renderLeaveHistory(history) {
    const tbody = document.getElementById('leave-history-body');
    if (history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No leave history found.</td></tr>';
        return;
    }
    
    let html = '';
    history.forEach(r => {
        const appliedDate = new Date(r.applied_at).toLocaleDateString();
        
        let remarksHtml = '';
        if (r.teacher_remarks) remarksHtml += `<div class="remarks-box"><b>Teacher:</b> ${r.teacher_remarks}</div>`;
        if (r.admin_remarks) remarksHtml += `<div class="remarks-box"><b>Admin:</b> ${r.admin_remarks}</div>`;
        
        let actionHtml = '';
        if (r.status === 'Pending') {
            actionHtml = `<button class="btn btn-sm btn-outline-danger" onclick="cancelLeave('${r.leave_id}')">Cancel</button>`;
        }
        
        let attachmentHtml = '';
        if (r.attachment_path) {
            // Placeholder link for attachment (since we don't have static file serving setup in this snippet yet)
            attachmentHtml = `<div class="mt-1 small"><a href="/${r.attachment_path}" target="_blank">📎 View Attachment</a></div>`;
        }

        html += `
            <tr>
                <td>${appliedDate}</td>
                <td>
                    <div class="fw-bold">${r.leave_type_name}</div>
                    <div class="small text-muted">${r.from_date} to ${r.to_date} (${r.total_days} days)</div>
                    ${attachmentHtml}
                </td>
                <td>
                    <span class="leave-status ${r.status}">${r.status}</span>
                    ${remarksHtml}
                </td>
                <td>${actionHtml}</td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

async function cancelLeave(leaveId) {
    if(!confirm("Are you sure you want to cancel this leave request?")) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/student/leave/cancel/${leaveId}`, {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        
        if (response.ok) {
            leaveAlert('success', 'Leave request cancelled.');
            await fetchLeaveHistory();
        } else {
            const data = await response.json();
            leaveAlert('danger', data.detail || 'Failed to cancel leave.');
        }
    } catch (err) {
        console.error(err);
        leaveAlert('danger', 'Network error.');
    }
}

function leaveAlert(type, msg) {
    const el = document.getElementById('leave-alert');
    el.className = `alert alert-${type} mb-4`;
    el.textContent = msg;
    el.style.display = 'block';
    setTimeout(() => el.style.display = 'none', 5000);
}

window.loadLeavePage = loadLeavePage;
