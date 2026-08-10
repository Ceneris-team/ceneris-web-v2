// static/inventario/js/delete_item_handler.js

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
    // --- LÓGICA PARA EL MODAL DE ELIMINACIÓN DE ITEM ---
    const deleteModal = document.getElementById('delete-confirm-modal'); // Mismo ID de modal que antes
    if (!deleteModal) return;

    // Seleccionamos los elementos del modal por sus IDs
    const deleteModalText = document.getElementById('delete-modal-text');
    const deleteModalError = document.getElementById('delete-modal-error');
    const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    
    let deleteUrl = '';
    let itemIdToDelete = null;

    // ¡CORRECCIÓN #1!
    // Buscamos los botones con la clase correcta: .btn-delete-item
    document.querySelectorAll('.btn-delete-item').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Leemos los datos del botón que fue presionado
            deleteUrl = this.dataset.url;
            itemIdToDelete = this.dataset.id;
            const itemNombre = this.dataset.nombre;
            
            // Personalizamos el mensaje de confirmación
            deleteModalText.innerHTML = `¿Estás seguro de que quieres eliminar el item con S/N: <strong>${itemNombre}</strong>? Esta acción no se puede deshacer.`;
            deleteModalError.style.display = 'none';
            deleteModal.style.display = 'flex';
        });
    });

    // Cerrar el modal
    function closeDeleteModal() {
        deleteModal.style.display = 'none';
    }
    cancelDeleteBtn.addEventListener('click', closeDeleteModal);
    deleteModal.addEventListener('click', function(e) {
        if (e.target === deleteModal) {
            closeDeleteModal();
        }
    });

    // Enviar la petición de borrado al confirmar
    confirmDeleteBtn.addEventListener('click', function() {
        if (!deleteUrl || !itemIdToDelete) return;
        
        const csrftoken = getCookie('csrftoken'); 

        fetch(deleteUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => { throw new Error(errorData.message); });
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // ¡CORRECCIÓN #2!
                // Buscamos la fila a eliminar con el formato de ID correcto: item-row-X
                const rowToRemove = document.getElementById(`item-row-${itemIdToDelete}`);
                if (rowToRemove) {
                    rowToRemove.classList.add('fade-out'); // Clase para la animación de salida
                    setTimeout(() => {
                        rowToRemove.remove();
                    }, 500);
                }
                closeDeleteModal();
            }
        })
        .catch(error => {
            // Mostramos errores de validación (ej: "No se puede eliminar porque está instalado")
            deleteModalError.textContent = error.message;
            deleteModalError.style.display = 'block';
        });
    });
});