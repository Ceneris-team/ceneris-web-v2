

document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('delete-project-modal');
    if (!modal) return;

    const modalText = document.getElementById('delete-project-text');
    const confirmBtn = document.getElementById('confirm-delete-project-btn');
    const cancelBtn = document.getElementById('cancel-delete-project-btn');
    
    let deleteUrl = '';
    let projectIdToDelete = null;

    document.querySelectorAll('.btn-delete-project').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            deleteUrl = this.dataset.url;
            projectIdToDelete = this.dataset.id;
            const projectName = this.dataset.nombre;
            
            modalText.innerHTML = `¿Estás seguro de que quieres eliminar permanentemente el proyecto "<strong>${projectName}</strong>"? Esta acción es irreversible y borrará todas sus tareas y asignaciones asociadas.`;
            modal.style.display = 'flex';
        });
    });

    function closeModal() { modal.style.display = 'none'; }
    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    confirmBtn.addEventListener('click', function() {
        if (!deleteUrl || !projectIdToDelete) return;
        
        const csrftoken = getCookie('csrftoken');
        fetch(deleteUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const cardToRemove = document.getElementById(`project-card-${projectIdToDelete}`);
                if (cardToRemove) {
                    cardToRemove.classList.add('fade-out');
                    setTimeout(() => cardToRemove.remove(), 500);
                }
                closeModal();
            } else {
                alert(`Error: ${data.message}`);
                closeModal();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Ocurrió un error de red.');
            closeModal();
        });
    });
});