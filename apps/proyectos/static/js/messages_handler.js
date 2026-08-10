// static/js/messages_handler.js

document.addEventListener('DOMContentLoaded', function() {
    // Seleccionamos todos los elementos de alerta que existan en la página
    const alerts = document.querySelectorAll('.alert');

    // Función para cerrar una alerta específica
    function dismissAlert(alertElement) {
        // 1. Añade la clase que activa la animación de salida en el CSS
        alertElement.classList.add('fade-out');

        // 2. Espera a que termine la animación (500ms, igual que en el CSS)
        //    y luego elimina el elemento del DOM para que no ocupe espacio.
        setTimeout(() => {
            alertElement.remove();
        }, 500);
    }

    alerts.forEach(alert => {
        // A. Hacer que la alerta desaparezca sola después de 5 segundos (5000 milisegundos)
        const autoDismissTimer = setTimeout(() => {
            dismissAlert(alert);
        }, 5000);

        // B. Permitir al usuario cerrarla manualmente con el botón '×'
        const closeButton = alert.querySelector('.alert-close');
        if (closeButton) {
            closeButton.addEventListener('click', function() {
                // Si el usuario la cierra, cancelamos el temporizador para evitar errores
                clearTimeout(autoDismissTimer);
                dismissAlert(alert);
            });
        }
    });
});