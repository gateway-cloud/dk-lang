const API = '/api';
let currentUser = 1;
let currentFilter = '';

async function fetchJSON(url) {
  const res = await fetch(url);
  return res.ok ? res.json() : [];
}

async function loadDashboard() {
  const stats = await fetchJSON(API+'/dashboard?user_id='+currentUser);
  document.getElementById('stat-total').textContent = stats.tasks?.total || 0;
  document.getElementById('stat-progress').textContent = stats.tasks?.in_progress || 0;
  document.getElementById('stat-done').textContent = stats.tasks?.done || 0;
  document.getElementById('stat-urgent').textContent = stats.tasks?.urgent || 0;
}

async function loadTasks(filter) {
  currentFilter = filter || '';
  let url = API+'/tasks?user_id='+currentUser;
  if (filter) url += '&status='+filter;
  const tasks = await fetchJSON(url);
  const container = document.getElementById('task-container');
  if (!tasks.length) {
    container.innerHTML = '<div class="empty-state">暂无任务</div>';
    return;
  }
  const priorityColors = {1:'#10b981',2:'#3b82f6',3:'#f59e0b',4:'#ef4444'};
  container.innerHTML = tasks.map(t => {
    const pc = priorityColors[t.priority]||'#94a3b8';
    const statusLabel = {todo:'待办',in_progress:'进行中',done:'已完成'};
    return `<div class="task-item ${t.status}" onclick="showTask(${t.id})">
      <div class="priority" style="background:${pc}"></div>
      <div class="task-info">
        <div class="task-title">${t.title}</div>
        <div class="task-meta">${t.category||''} | ${t.due_date||'无截止'} | ${statusLabel[t.status]||t.status}</div>
      </div>
      ${t.priority>=3?'<span class="badge badge-high">紧急</span>':''}
    </div>`;
  }).join('');
}

function showTask(id) {
  alert('任务详情 #'+id);
}

function showNewTaskModal() {
  document.getElementById('modal').classList.add('show');
}
function hideModal() {
  document.getElementById('modal').classList.remove('show');
}

function setActiveNav(el, filter) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  el.classList.add('active');
  loadTasks(filter);
}

loadDashboard(); loadTasks();
