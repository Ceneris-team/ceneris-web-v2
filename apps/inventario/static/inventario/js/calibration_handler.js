document.addEventListener('DOMContentLoaded', function () {
    const csrftoken = getCookie('csrftoken');

    document.querySelectorAll('.btn-calibrado').forEach(button => {
        button.addEventListener('click', function() {
            const url = this.dataset.url;
            const card = this.closest('.notification-card');
            
            if (!confirm('¿Estás seguro de que quieres registrar la calibración para este item?')) {
                return; // Detiene la acción si el usuario cancela
            }

            fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Si tiene éxito, eliminamos la tarjeta de la lista con una animación
                    card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.95)';
                    setTimeout(() => card.remove(), 500);
                    
                    // (Opcional) Mostrar una notificación de éxito tipo "toast"
                    alert(data.message);
                } else {
                    // Muestra el mensaje de advertencia o error del servidor
                    alert(`Advertencia: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Ocurrió un error de red.');
            });
        });
    });
});