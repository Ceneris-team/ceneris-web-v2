
function getCookie(name) { let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('unassign-confirm-modal');
    if (!modal) return;

    const modalText = document.getElementById('unassign-modal-text');
    const confirmBtn = document.getElementById('confirm-unassign-btn');
    const cancelBtn = document.getElementById('cancel-unassign-btn');
    
    let unassignUrl = '';
    let cardToRemove = null;

    // Abrir el modal de confirmación
    document.querySelectorAll('.btn-unassign-personal').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            unassignUrl = this.dataset.url;
            const personaNombre = this.dataset.nombrePersona;
            const subtareaNombre = this.dataset.nombreSubtarea;
            
            // Guardamos una referencia a la tarjeta para poder eliminarla después
            cardToRemove = this.closest('.col-12'); 

            modalText.innerHTML = `¿Estás seguro de que quieres desasignar a <strong>${personaNombre}</strong> de la tarea "<em>${subtareaNombre}</em>"?`;
            modal.style.display = 'flex';
        });
    });

    // Cerrar el modal
    function closeModal() { modal.style.display = 'none'; }
    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    // Enviar la petición de desasignación
    confirmBtn.addEventListener('click', function() {
        if (!unassignUrl || !cardToRemove) return;
        
        const csrftoken = getCookie('csrftoken');
        fetch(unassignUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Si tiene éxito, eliminamos la tarjeta de la vista con una animación
                cardToRemove.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                cardToRemove.style.opacity = '0';
                cardToRemove.style.transform = 'scale(0.9)';
                setTimeout(() => cardToRemove.remove(), 500); // Elimina del DOM después de la animación
            } else {
                alert('Ocurrió un error al desasignar.');
            }
            closeModal();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error de red al intentar desasignar.');
            closeModal();
        });
    });
});