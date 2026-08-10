

document.addEventListener('DOMContentLoaded', function () {
    // Escuchamos clics en todos los botones de 'check' de la página
    document.querySelectorAll('.btn-toggle-complete').forEach(button => {
        button.addEventListener('click', function() {
            const url = this.dataset.url;
            const subtareaId = this.dataset.id;
            const csrftoken = getCookie('csrftoken');
            const contentCard = this.closest('.content-left, .content-right');
            
            if (!contentCard) {
                console.error("No se pudo encontrar el contenedor de la tarjeta de contenido.");
                return;
            }
            // 1. Enviamos la petición para cambiar el estado en el backend
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    contentCard.classList.toggle('is-completed', data.subtarea_completada); 
                } else {
                    alert('No se pudo actualizar el estado de la tarea.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Ocurrió un error de red.');
            });
        });
    });
});