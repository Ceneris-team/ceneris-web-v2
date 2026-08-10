// static/personal/js/project_finder.js
document.addEventListener('DOMContentLoaded', function() {
    const projectSelect = $('#project-search-select');
    // Buscamos el formulario por su clase específica
    const projectForm = $('.project-filter-form'); 

    // Si el formulario no existe, no hacemos nada.
    if (!projectForm.length || !projectSelect.length) {
        return;
    }

    // Obtenemos la URL del data-attribute del formulario una sola vez.
    const searchUrl = projectForm.data('searchUrl');
    
    if (!searchUrl) {
        console.error("Error: El formulario '.project-filter-form' no tiene el atributo 'data-search-url'.");
        return;
    }

    projectSelect.select2({
        placeholder: 'Escribe el nombre de un proyecto...',
        minimumInputLength: 1,
        ajax: {
            url: searchUrl, // Usamos la variable que ya obtuvimos
            dataType: 'json',
            delay: 250,
            processResults: data => ({ results: data.results }),
            cache: true
        }
    });

        // --- LÓGICA PARA MANTENER EL VALOR SELECCIONADO ---
        // Si la página se recarga con un proyecto ya seleccionado, lo mostramos
    const urlParams = new URLSearchParams(window.location.search);
    const proyectoId = urlParams.get('proyecto_id');

    if (proyectoId) {
            // Hacemos una petición para obtener los datos del proyecto seleccionado
            // y lo añadimos como una opción pre-seleccionada en Select2.
            // Esta es una técnica avanzada pero muy profesional.
        $.ajax({
            type: 'GET',
            url: `/api/proyectos/search/?term_id=${proyectoId}` // Necesitarás adaptar el API para esto
        }).then(function(data) {
            if (data.results.length > 0) {
                const project = data.results[0];
                const option = new Option(project.text, project.id, true, true);
                projectSelect.append(option).trigger('change');
            }
        });
    }
});