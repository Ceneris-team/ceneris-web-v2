// static/js/dashboard_charts.js
document.addEventListener('DOMContentLoaded', function() {
    
    // --- Gráfico 1: Estado de Proyectos (Dona) ---
    const projectStatusData = JSON.parse(document.getElementById('project-status-data').textContent);
    const projectStatusCtx = document.getElementById('projectStatusChart').getContext('2d');
    new Chart(projectStatusCtx, {
        type: 'doughnut',
        data: {
            labels: projectStatusData.labels,
            datasets: [{
                data: projectStatusData.data,
                backgroundColor: ['#3498db', '#2ecc71'],
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    // --- Gráfico 2: Carga de Trabajo (Barras) ---
    const workloadData = JSON.parse(document.getElementById('workload-data').textContent);
    const workloadCtx = document.getElementById('workloadChart').getContext('2d');
    new Chart(workloadCtx, {
        type: 'bar',
        data: {
            labels: workloadData.labels,
            datasets: [{
                label: 'Tareas Pendientes',
                data: workloadData.data,
                backgroundColor: '#e67e22',
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y' } // Barras horizontales
    });

    // --- Gráfico 3: Tendencia de Tareas (Líneas) ---
    const trendData = JSON.parse(document.getElementById('completion-trend-data').textContent);
    const trendCtx = document.getElementById('completionTrendChart').getContext('2d');
    new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: trendData.labels,
            datasets: [{
                label: 'Tareas Completadas',
                data: trendData.data,
                borderColor: '#8e44ad',
                tension: 0.1
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    // --- Gráfico 4: Progreso por Proyecto (Barras) ---
    const progressData = JSON.parse(document.getElementById('progress-data').textContent);
    const progressCtx = document.getElementById('progressChart').getContext('2d');
    new Chart(progressCtx, {
        type: 'bar',
        data: {
            labels: progressData.labels,
            datasets: [{
                label: '% de Progreso',
                data: progressData.data,
                backgroundColor: '#1abc9c',
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } } }
    });

});