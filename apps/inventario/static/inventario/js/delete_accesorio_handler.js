// static/inventario/js/delete_accesorio_handler.js

// Función getCookie (siempre necesaria para peticiones POST en Django)
function getCookie(name) {
    let cookieValue = null;
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
    const modal = document.getElementById('delete-accesorio-modal');
    if (!modal) return; // No hacer nada si el modal no está en la página

    // Seleccionar elementos del modal
    const modalText = document.getElementById('delete-accesorio-text');
    const modalError = document.getElementById('delete-accesorio-error');
    const confirmBtn = document.getElementById('confirm-delete-accesorio-btn');
    const cancelBtn = document.getElementById('cancel-delete-accesorio-btn');
    
    let deleteUrl = '';
    let accesorioIdToDelete = null;

    // Abrir el modal de confirmación
    document.querySelectorAll('.btn-delete-accesorio').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            deleteUrl = this.dataset.url;
            accesorioIdToDelete = this.dataset.id;
            const accesorioNombre = this.dataset.nombre;
            
            modalText.innerHTML = `¿Estás seguro de que quieres eliminar permanentemente el accesorio "<strong>${accesorioNombre}</strong>"?`;
            modalError.style.display = 'none';
            modal.style.display = 'flex';
        });
    });

    // Cerrar el modal
    function closeModal() {
        modal.style.display = 'none';
    }
    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    // Enviar la petición de borrado
    confirmBtn.addEventListener('click', function() {
        if (!deleteUrl || !accesorioIdToDelete) return;
        
        const csrftoken = getCookie('csrftoken');
        fetch(deleteUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message) });
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                const rowToRemove = document.getElementById(`accesorio-row-${accesorioIdToDelete}`);
                if (rowToRemove) {
                    rowToRemove.classList.add('fade-out');
                    setTimeout(() => rowToRemove.remove(), 500);
                }
                closeModal();
            }
        })
        .catch(error => {
            modalError.textContent = error.message;
            modalError.style.display = 'block';
        });
    });
});