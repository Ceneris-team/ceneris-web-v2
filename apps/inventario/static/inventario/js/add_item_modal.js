// static/inventario/js/add_item_modal.js
document.addEventListener('DOMContentLoaded', function() {
    const openBtn = document.getElementById('open-add-item-modal-btn');
    const modal = document.getElementById('add-item-modal');
    if (!openBtn || !modal) return; // No hacer nada si los elementos no están

    const closeBtn = document.getElementById('close-add-item-modal-btn');
    const cancelBtn = document.getElementById('cancel-add-item-btn');
    const form = modal.querySelector('form');
    
    // Función para abrir el modal
    function openModal() {
        modal.style.display = 'flex';
    }
    // Función para cerrar el modal
    function closeModal() {
        modal.style.display = 'none';
        form.reset();
    }
    
    // Asignar eventos
    openBtn.addEventListener('click', openModal);
    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });
    
    // --- LÓGICA CLAVE PARA ERRORES DE FORMULARIO ---
    // Django renderizará mensajes de error si la validación falla.
    // Buscamos el contenedor de mensajes que configuramos en la plantilla base.
    const messagesContainer = document.querySelector('.messages .alert-error');
    // Si existe un mensaje de error, asumimos que fue por este formulario y lo abrimos.
    if (messagesContainer) {
        // Podríamos añadir una lógica más específica aquí si tenemos múltiples
        // formularios en la página que puedan dar error. Por ahora, esto funciona.
        openModal();
    }
});