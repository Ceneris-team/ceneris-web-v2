document.addEventListener('DOMContentLoaded', function() {
    // Seleccionamos los elementos clave
    const openModalBtn = document.getElementById('open-add-personal-modal-btn');
    const modal = document.getElementById('add-personal-modal');
    const closeModalBtn = document.getElementById('close-add-personal-modal-btn');
    const form = document.getElementById('add-personal-form');

    // Si no encontramos los elementos en la página, no hacemos nada
    if (!openModalBtn || !modal || !closeModalBtn) {
        return; 
    }

    // Función para abrir el modal
    function openModal() {
        modal.style.display = 'flex';
    }

    // Función para cerrar el modal
    function closeModal() {
        modal.style.display = 'none';
        // Opcional: Limpia el formulario al cerrar para la próxima vez
        if (form) {
            form.reset();
        }
    }

    // Asignamos los eventos
    openModalBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);

    // Cerrar el modal si se hace clic en el fondo oscuro
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Cerrar el modal si se presiona la tecla Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === "Escape" && modal.style.display !== 'none') {
            closeModal();
        }
    });

    // Si Django recarga la página con errores, el modal debe permanecer abierto
    const errorList = document.querySelector('#add-personal-errors');
    if (errorList && errorList.children.length > 0) {
        openModal();
    }
});