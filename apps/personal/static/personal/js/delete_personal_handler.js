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
    const modal = document.getElementById('delete-personal-modal');
    if (!modal) return;

    const modalText = document.getElementById('delete-personal-text');
    const modalError = document.getElementById('delete-personal-error');
    const confirmBtn = document.getElementById('confirm-delete-personal-btn');
    const cancelBtn = document.getElementById('cancel-delete-personal-btn');
    
    let deleteUrl = '';
    let personalIdToDelete = null;

    // Abrir el modal de confirmación
    document.querySelectorAll('.btn-delete-personal').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            deleteUrl = this.dataset.url;
            personalIdToDelete = this.dataset.id;
            const personaNombre = this.dataset.nombre;
            
            modalText.innerHTML = `¿Estás seguro de que quieres eliminar permanentemente el registro de <strong>${personaNombre}</strong>? Esta acción no se puede deshacer.`;
            modalError.style.display = 'none'; // Ocultar errores previos
            modal.style.display = 'flex';
        });
    });

    // Cerrar el modal
    function closeModal() { modal.style.display = 'none'; }
    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    // Enviar la petición de borrado
    confirmBtn.addEventListener('click', function() {
        if (!deleteUrl) return;
        
        const csrftoken = getCookie('csrftoken');
        fetch(deleteUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken }
        })
        .then(response => {
            // Comprobamos si la respuesta fue exitosa (2xx) o un error (4xx, 5xx)
            if (response.ok) {
                return response.json();
            } else {
                // Si es un error, leemos el JSON del error para obtener el mensaje
                return response.json().then(errorData => {
                    throw new Error(errorData.message || 'Error desconocido del servidor.');
                });
            }
        })
        .then(data => {
            if (data.status === 'success') {
                const rowToRemove = document.getElementById(`personal-row-${personalIdToDelete}`);
                if (rowToRemove) {
                    rowToRemove.classList.add('fade-out'); // Usa la clase CSS que ya tienes
                    setTimeout(() => rowToRemove.remove(), 500);
                }
                closeModal();
                // Opcional: mostrar una notificación de éxito tipo "toast"
                alert(data.message);
            }
        })
        .catch(error => {
            // Mostramos el mensaje de error (ej: 'No se puede eliminar porque está asignado...')
            modalError.textContent = error.message;
            modalError.style.display = 'block';
        });
    });
});