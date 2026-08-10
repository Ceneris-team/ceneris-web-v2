// static/js/timeline_animation.js

document.addEventListener('DOMContentLoaded', function() {
    // 1. Seleccionamos todos los elementos que queremos animar
    const animatedElements = document.querySelectorAll('.animate-on-scroll');

    // 2. Creamos el "observador"
    // IntersectionObserver es una API moderna del navegador que es muy eficiente.
    // Nos avisa cuando un elemento entra o sale de la pantalla.
    const observer = new IntersectionObserver((entries) => {
        // La función se ejecuta cada vez que la visibilidad de un elemento cambia
        
        entries.forEach(entry => {
            // entry.isIntersecting será 'true' si el elemento está en la pantalla
            if (entry.isIntersecting) {
                // Obtenemos el delay que definimos en el HTML (style="--animation-delay: ...")
                const delay = entry.target.style.getPropertyValue('--animation-delay');
                
                // Aplicamos el delay a la transición
                entry.target.style.transitionDelay = delay;

                // 3. Añadimos la clase 'is-visible' para activar la animación CSS
                entry.target.classList.add('is-visible');

                // 4. (Opcional pero recomendado) Dejamos de observar el elemento una vez animado
                // para mejorar el rendimiento.
                observer.unobserve(entry.target);
            }
        });
    }, {
        // Opciones del observador:
        // threshold: 0.1 significa que la animación se activará
        // cuando al menos el 10% del elemento sea visible.
        threshold: 0.3 
    });

    // 5. Le decimos al observador que empiece a "vigilar" cada uno de nuestros elementos
    animatedElements.forEach(element => {
        observer.observe(element);
    });
});