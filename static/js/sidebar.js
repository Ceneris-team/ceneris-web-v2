// static/js/sidebar.js

document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const buttonText = document.getElementById('btn-menu-text');

    // Función para actualizar el texto del botón
    function updateButtonText() {
        // La barra está OCULTA si tiene la clase 'active'
        if (sidebar.classList.contains('active')) {
            buttonText.textContent = 'Abrir Menú';
        } else {
            buttonText.textContent = 'Cerrar Menú';
        }
    }

    // Por defecto, la barra empieza oculta, así que establece el texto inicial.
    // Daremos la clase 'active' por defecto en el HTML.
    updateButtonText(); 

    // Event listener para el clic en el botón
    sidebarCollapse.addEventListener('click', function() {
        // Alterna la clase 'active' en la barra lateral
        sidebar.classList.toggle('active');

        // Actualiza el texto del botón
        updateButtonText();
    });
});