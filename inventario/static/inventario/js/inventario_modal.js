


document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('edit-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const form = document.getElementById('edit-insumo-form');
    const modalTitle = document.getElementById('modal-title');
    const modalStockInput = document.getElementById('modal-stock-input');
    const modalCostoInput = document.getElementById('modal-costo-input');
    const modalErrors = document.getElementById('modal-errors');
    
    let currentUpdateUrl = '';
    let currentInsumoId = null;

    // Abrir el modal
    document.querySelectorAll('.btn-edit').forEach(button => {
        button.addEventListener('click', function() {
            const data = this.dataset;
            currentUpdateUrl = data.url;
            currentInsumoId = data.id;

            modalTitle.textContent = `Editar "${data.nombre}"`;
            modalStockInput.value = data.stock;
            modalCostoInput.value = data.costo;
            
            modalErrors.style.display = 'none';
            modal.style.display = 'flex';
        });
    });

    // Cerrar el modal
    function closeModal() {
        modal.style.display = 'none';
    }
    closeModalBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Enviar el formulario con Fetch (AJAX)
    form.addEventListener('submit', function(e) {
        e.preventDefault(); // Evita que la página se recargue

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        fetch(currentUpdateUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                // 🎉 La única línea que necesitas cambiar 🎉
                window.location.reload(); 
            } else {
                // Mostrar errores
                modalErrors.innerHTML = '';
                for (const field in result.errors) {
                    result.errors[field].forEach(error => {
                        const p = document.createElement('p');
                        p.textContent = error;
                        modalErrors.appendChild(p);
                    });
                }
                modalErrors.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            modalErrors.textContent = 'Ocurrió un error de red.';
            modalErrors.style.display = 'block';
        });
    });
});