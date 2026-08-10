
document.addEventListener('DOMContentLoaded', function() {
    // --- SELECCIÓN DE ELEMENTOS DEL MODAL ---
    const modal = document.getElementById('devolver-insumo-modal');
    // Si el modal no existe en la página, detenemos el script para evitar errores.
    if (!modal) {
        return;
    }

    const form = document.getElementById('devolver-insumo-form');
    const closeModalBtn = modal.querySelector('.modal-close-btn');
    const insumoNombreEl = document.getElementById('devolver-insumo-nombre');
    const subtareaNombreEl = document.getElementById('devolver-subtarea-nombre');
    const cantidadActualEl = document.getElementById('devolver-cantidad-actual');
    const cantidadInput = document.getElementById('cantidad_a_devolver');
    const errorListEl = document.getElementById('devolver-error-list');
    
    let currentDevolverUrl = ''; // Guardará la URL del API para la devolución

    // --- LÓGICA PARA ABRIR EL MODAL ---
    document.querySelectorAll('.btn-devolver-insumo').forEach(button => {
        button.addEventListener('click', function() {
            const getUrl = this.dataset.urlGet;
            currentDevolverUrl = this.dataset.urlDevolver;
            
            // 1. Pide los datos de la asignación al servidor
            fetch(getUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('No se pudieron cargar los datos de la asignación.');
                    }
                    return response.json();
                })
                .then(data => {
                    // 2. Rellena el modal con la información recibida
                    insumoNombreEl.textContent = data.insumo_nombre;
                    subtareaNombreEl.textContent = data.subtarea_titulo;
                    cantidadActualEl.textContent = data.cantidad_asignada;
                    
                    // 3. Configura el input de cantidad
                    cantidadInput.max = data.cantidad_asignada; // No se puede devolver más de lo asignado
                    cantidadInput.value = data.cantidad_asignada; // Pre-rellena con la cantidad máxima
                    
                    // 4. Muestra el modal
                    modal.style.display = 'flex';
                })
                .catch(error => {
                    console.error("Error al obtener datos de asignación:", error);
                    alert(error.message);
                });
        });
    });

    // --- LÓGICA PARA CERRAR EL MODAL ---
    function closeModal() {
        modal.style.display = 'none';
        form.reset(); // Limpia el formulario
        errorListEl.style.display = 'none'; // Oculta errores previos
        errorListEl.textContent = '';
    }

    closeModalBtn.addEventListener('click', closeModal);

    // Cerrar al hacer clic en el fondo oscuro
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Cerrar al presionar la tecla 'Escape'
    document.addEventListener('keydown', function(e) {
        if (e.key === "Escape" && modal.style.display !== 'none') {
            closeModal();
        }
    });


    // --- LÓGICA PARA ENVIAR EL FORMULARIO DE DEVOLUCIÓN ---
    form.addEventListener('submit', function(e) {
        e.preventDefault(); // Evita que la página se recargue
        
        const cantidad = cantidadInput.value;
        const csrftoken = getCookie('csrftoken');

        fetch(currentDevolverUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({ cantidad_a_devolver: cantidad })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Si la devolución es exitosa, muestra el mensaje y recarga la página
                alert(data.message);
                window.location.reload(); 
            } else {
                // Si hay un error de validación, lo muestra en el modal
                errorListEl.textContent = data.message;
                errorListEl.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error en la devolución:', error);
            errorListEl.textContent = 'Ocurrió un error de red. Inténtalo de nuevo.';
            errorListEl.style.display = 'block';
        });
    });
});