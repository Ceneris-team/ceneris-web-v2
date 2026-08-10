// static/js/options_menu.js (Versión de Depuración)

console.log("--- DEBUG: options_menu.js ---");
console.log("✅ Script cargado y listo para escuchar eventos.");

document.addEventListener('DOMContentLoaded', function () {
    console.log("📄 DOM completamente cargado. Adjuntando listener principal al body.");

    document.body.addEventListener('click', function(e) {
        console.log("🖱️ Clic detectado en el body. El objetivo fue:", e.target);

        // Encuentra el botón de opciones en el que se hizo clic (si existe)
        const clickedOptionsButton = e.target.closest('.btn-options');
        
        if (clickedOptionsButton) {
            console.log("🎯 ¡Se hizo clic en un botón de opciones o en uno de sus hijos!");
        } else {
            console.log(" informational: El clic no fue en un botón de opciones.");
        }

        // --- LÓGICA DE CIERRE ---
        const openMenus = document.querySelectorAll('.options-menu.show');
        if (openMenus.length > 0) {
            console.log(`🔎 Encontrados ${openMenus.length} menús abiertos. Intentando cerrar...`);
        }
        
        openMenus.forEach(openMenu => {
            const itsButton = openMenu.closest('.options-container')?.querySelector('.btn-options');
            if (itsButton !== clickedOptionsButton) {
                console.log("❌ Cerrando un menú que no es el actual.");
                openMenu.classList.remove('show');
            } else {
                console.log(" informational: No se cierra el menú actual porque se hizo clic en su propio botón.");
            }
        });

        // --- LÓGICA DE APERTURA ---
        if (clickedOptionsButton) {
            console.log("🔍 Buscando contenedor padre '.options-container'...");
            const container = clickedOptionsButton.closest('.options-container');

            if (container) {
                console.log("✅ Contenedor encontrado:", container);
                console.log("🔍 Buscando menú hijo '.options-menu'...");
                const menu = container.querySelector('.options-menu');
                
                if (menu) {
                    console.log("✅ Menú encontrado:", menu);
                    console.log("🔄 Aplicando .toggle('show'). Estado actual de la clase:", menu.classList.contains('show'));
                    menu.classList.toggle('show');
                    console.log("🆕 Nuevo estado de la clase:", menu.classList.contains('show'));
                } else {
                    console.error("🔥 ERROR: No se encontró un menú con la clase '.options-menu' dentro del contenedor.");
                }
            } else {
                 console.error("🔥 ERROR: No se encontró un contenedor padre con la clase '.options-container' para el botón presionado.");
            }
        }
    });
});