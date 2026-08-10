
document.addEventListener('DOMContentLoaded', function() {
    // --- OBTENCIÓN DE DATOS GLOBALES ---
    const headerContainer = document.querySelector('.header-container');
    const personalSearchUrl = headerContainer?.dataset.personalSearchUrl;
    const insumoSearchUrl = headerContainer?.dataset.insumoSearchUrl;
    
    if (!personalSearchUrl || !insumoSearchUrl) {
        console.error("Error crítico: Faltan los atributos 'data-personal-search-url' o 'data-insumo-search-url' en el div '.header-container'.");
        return;
    }

    // --- SELECCIÓN DE ELEMENTOS DEL MODAL ---
    const modal = document.getElementById('edit-subtask-modal');
    if (!modal) return;

    const form = document.getElementById('edit-subtask-form');
    const closeModalBtn = document.getElementById('close-subtask-modal-btn');
    const errorContainer = document.getElementById('edit-subtask-errors');
    const idInput = document.getElementById('edit-subtask-id');
    const tituloInput = document.getElementById('edit-subtask-titulo');
    const inicioInput = document.getElementById('edit-subtask-inicio');
    const finInput = document.getElementById('edit-subtask-fin');
    
    // Elementos para Personal
    const personalSelect = document.getElementById('edit-subtask-personal');
    const asignadosPersonalContainer = document.getElementById('personal-asignado-lista');

    // Elementos para Insumos
    const addInsumoRowBtn = document.getElementById('btn-add-insumo-row');
    const insumoAdderContainer = document.getElementById('insumo-adder-container');
    let insumoCounter = 0;
    
    let currentUpdateUrl = '';

    // --- INICIALIZACIÓN DE SELECT2 PARA PERSONAL ---
    const personalSelectElement = $(personalSelect).select2({
        placeholder: 'Busca para añadir más personal...',
        ajax: { url: personalSearchUrl, dataType: 'json', delay: 250, processResults: data => ({ results: data.results }), cache: true }
    });

    // --- LÓGICA PARA ABRIR EL MODAL ---
    document.querySelectorAll('.js-edit-subtask-trigger').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const getUrl = this.dataset.getUrl;
            currentUpdateUrl = this.dataset.updateUrl;
            
            fetch(getUrl)
                .then(response => response.json())
                .then(data => {
                    // Rellenar campos básicos
                    idInput.value = data.id;
                    tituloInput.value = data.titulo;
                    inicioInput.value = data.fecha_inicio;
                    finInput.value = data.fecha_fin;
                    errorContainer.innerHTML = '';
                    for (const field in result.errors) {
                        // El error de clean() aparecerá en '__all__'
                        if (field === '__all__') {
                            const p = document.createElement('p');
                            p.textContent = result.errors[field][0]; // Mostramos el primer error
                            p.style.color = 'red';
                            errorContainer.appendChild(p);
                        }
                    }
                    // Rellenar personal ya asignado
                    asignadosPersonalContainer.innerHTML = '';
                    if (data.personal_asignado && data.personal_asignado.length > 0) {
                        data.personal_asignado.forEach(persona => {
                            const el = document.createElement('div');
                            el.innerHTML = `<span>${persona.text}</span>`;
                            el.className = 'asignado-item';asignadosPersonalContainer.appendChild(el);
                        });
                    } else {
                        asignadosPersonalContainer.innerHTML = '<p class="no-asignado">Nadie asignado a esta tarea todavía.</p>';
                    }
                    personalSelectElement.html('').trigger('change');

                    // Limpiar contenedor de añadir insumos para la nueva apertura
                    insumoAdderContainer.innerHTML = '';
                    insumoCounter = 0;

                    modal.style.display = 'flex';
                })
                .catch(error => console.error('Error al obtener datos de la subtarea:', error));
        });
    });

    // --- LÓGICA PARA AÑADIR FILAS DE INSUMOS ---
    addInsumoRowBtn.addEventListener('click', function() {
        const insumoIndex = insumoCounter++;
        const newRow = document.createElement('div');
        newRow.className = 'insumo-row';
        newRow.innerHTML = `
            <select class="insumo-search" name="insumo_id_${insumoIndex}"></select>
            <input type="number" name="insumo_cantidad_${insumoIndex}" placeholder="Cant." min="1" required>
            <button type="button" class="btn-remove-insumo-row">&times;</button>
        `;
        insumoAdderContainer.appendChild(newRow);

        $(newRow.querySelector('.insumo-search')).select2({
            placeholder: 'Busca un insumo...',
            ajax: { url: insumoSearchUrl, dataType: 'json', delay: 250, processResults: data => ({ results: data.results }), cache: true }
        });

        newRow.querySelector('.btn-remove-insumo-row').addEventListener('click', () => newRow.remove());
    });

    // --- LÓGICA PARA CERRAR EL MODAL ---
    function closeModal() {
        modal.style.display = 'none';
        errorContainer.style.display = 'none';
    }
    closeModalBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    // --- LÓGICA PARA ENVIAR EL FORMULARIO ---
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Recoger IDs de personal a AÑADIR
        data.personal_asignado = $(personalSelect).val();

        // Recoger insumos a AÑADIR
        data.nuevos_insumos = [];
        document.querySelectorAll('#insumo-adder-container .insumo-row').forEach(row => {
            const insumoId = $(row.querySelector('.insumo-search')).val();
            const cantidad = row.querySelector('input[type="number"]').value;
            if (insumoId && cantidad) {
                data.nuevos_insumos.push({ id: insumoId, cantidad: cantidad });
            }
        });
        
        fetch(currentUpdateUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                window.location.reload();
                closeModal();
            } else {
                // Mostrar errores de validación
                errorContainer.innerHTML = '';
                for (const field in result.errors) {
                    result.errors[field].forEach(error => {
                        const p = document.createElement('p');
                        p.textContent = error;
                        errorContainer.appendChild(p);
                    });
                }
                errorContainer.style.display = 'block';
            }
        });
    });
});

// --- LÓGICA PARA EL MODAL DE ELIMINACIÓN DE SUBTAREA ---

// Seleccionamos los elementos del nuevo modal de eliminación
const deleteModal = document.getElementById('delete-subtask-modal');
const cancelDeleteBtn = document.getElementById('cancel-delete-subtask-btn');
const confirmDeleteBtn = document.getElementById('confirm-delete-subtask-btn');
const deleteModalText = document.getElementById('delete-subtask-text');

let deleteUrl = '';
let subtareaIdToDelete = null;

// Abrir el modal de confirmación
document.querySelectorAll('.btn-delete-subtask').forEach(button => {
    button.addEventListener('click', function(e) {
        e.preventDefault();
        
        deleteUrl = this.dataset.url;
        subtareaIdToDelete = this.dataset.id;
        const subtareaNombre = this.dataset.nombre;
        
        deleteModalText.innerHTML = `¿Estás seguro de que quieres eliminar la subtarea "<strong>${subtareaNombre}</strong>"? Los insumos asignados volverán al inventario. Esta acción no se puede deshacer.`;
        
        deleteModal.style.display = 'flex';
    });
});

// Cerrar el modal de eliminación
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
    // La función getCookie debe estar definida en este script (ya la tienes)
    const csrftoken = getCookie('csrftoken'); 

    fetch(deleteUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Si se eliminó, buscamos la tarjeta para eliminarla de la vista
            // La tarjeta es el elemento .timeline-card padre del botón que se clickeó
            // Para encontrarlo, necesitamos una referencia al botón original. 
            // Esto es un poco más complejo, pero la recarga es una solución simple y efectiva por ahora.
            
            window.location.reload(); // Recarga la página para ver los cambios
        } else {
            // Aunque nuestra vista actual no devuelve errores, es bueno tener esto
            alert('Ocurrió un error al eliminar la subtarea.');
        }
        closeDeleteModal();
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Ocurrió un error de red.');
    });
});