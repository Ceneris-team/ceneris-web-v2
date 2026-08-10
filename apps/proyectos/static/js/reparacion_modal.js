// static/proyectos/js/reparacion_modal.js
document.addEventListener('DOMContentLoaded', function() {
    const modalOverlay = document.getElementById('reparacion-modal-overlay');
    if (!modalOverlay) return;

    // --- SELECCIÓN DE ELEMENTOS DEL MODAL (CON LA LÍNEA CORREGIDA) ---
    const modalContent = modalOverlay.querySelector('.custom-modal-content');
    const closeBtn = modalOverlay.querySelector('.close-btn');
    const cancelBtn = modalOverlay.querySelector('.btn-cancel');
    const form = modalOverlay.querySelector('.reparacion-form');
    
    const insumoNombreEl = document.getElementById('modal-insumo-nombre');
    const insumoIdInput = document.getElementById('modal-insumo-id'); // Este es el input oculto para el Insumo PADRE
    
    // ¡LA LÍNEA QUE FALTABA!
    // Seleccionamos el <select> para los números de serie.
    const itemInsumoSelect = document.getElementById('modal-item-insumo-select');

    // --- FUNCIÓN PARA ABRIR EL MODAL (Ahora funcionará) ---
    function openModal(insumoId, insumoNombre) {
        // Rellenar el título del modal
        insumoNombreEl.textContent = insumoNombre;
        
        // ¡LA LÓGICA DE CARGA DE NÚMEROS DE SERIE AHORA FUNCIONA!
        // Como 'itemInsumoSelect' ya está definida, esta línea es válida.
        itemInsumoSelect.innerHTML = '<option value="">Cargando números de serie...</option>';
        
        fetch(`/api/insumo/${insumoId}/items/`)
            .then(response => {
                if (!response.ok) throw new Error('Error de red al buscar items.');
                return response.json();
            })
            .then(data => {
                itemInsumoSelect.innerHTML = '<option value="">Selecciona un número de serie</option>';
                if (data.items && data.items.length > 0) {
                    data.items.forEach(item => {
                        const option = new Option(item.numero_serie, item.id);
                        itemInsumoSelect.add(option);
                    });
                } else {
                    itemInsumoSelect.innerHTML = '<option value="" disabled>No hay items específicos para este insumo</option>';
                }
            })
            .catch(error => {
                console.error(error);
                itemInsumoSelect.innerHTML = '<option value="" disabled>Error al cargar items</option>';
            });

        modalOverlay.style.display = 'flex';
    }

    // --- FUNCIÓN PARA CERRAR EL MODAL ---
    function closeModal() {
        modalOverlay.style.display = 'none';
        form.reset();
    }

    // --- EVENT LISTENERS (Sin cambios) ---
    document.querySelectorAll('.btn-reparacion').forEach(button => {
        button.addEventListener('click', function() {
            const insumoId = this.dataset.insumoId; 
            const insumoNombre = this.dataset.insumoNombre;
            openModal(insumoId, insumoNombre);
        });
    });

    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', function(e) {
        if (e.target === modalOverlay) {
            closeModal();
        }
    });
});