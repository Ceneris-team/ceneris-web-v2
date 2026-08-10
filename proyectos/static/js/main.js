function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Declaramos la constante UNA SOLA VEZ para que esté disponible globalmente
const csrftoken = getCookie('csrftoken');
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    // ¡LA CLAVE! Seleccionamos el span por su nuevo ID
    const buttonText = document.getElementById('btn-menu-text'); 

    function updateButtonText() {
        if (sidebar.classList.contains('active')) {
            // Cambiamos el texto solo del span
            buttonText.innerHTML = '<i class="fa fa-times"></i>';
        } else {
            // Cambiamos el texto solo del span
            buttonText.innerHTML = '<i class="fa fa-bars"></i>';
        }
    }

    // Establece el texto inicial correcto
    updateButtonText(); 

    sidebarCollapse.addEventListener('click', function() {
        sidebar.classList.toggle('active');
        // Llama a la función para actualizar el texto
        updateButtonText();

        // Lógica de Animate.css (esta no cambia)
        const links = sidebar.querySelectorAll('ul li');
        if (sidebar.classList.contains('active')) {
            links.forEach((link, index) => {
                link.classList.add('animate__animated', 'animate__fadeInLeft');
                link.style.animationDelay = `${index * 0.1}s`;
            });
        } else {
            links.forEach(link => {
                link.classList.remove('animate__animated', 'animate__fadeInLeft');
                link.style.animationDelay = '';
            });
        }
    });
});