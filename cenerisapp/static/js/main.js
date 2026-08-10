// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    
    document.querySelectorAll('.message-close').forEach(button => {
        button.addEventListener('click', (e) => {
            e.target.parentElement.style.display = 'none';
        });
    });
    // ===============================================
    // FUNCIONALIDAD #1: BARRA LATERAL (SIDEBAR)
    // ===============================================
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebarToggle = document.querySelector('.sidebar__toggle');
    const overlay = document.querySelector('.overlay');

    // Funcionalidad del menú hamburguesa (móvil)
    if (menuToggle && sidebar && overlay) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('is-open');
            overlay.classList.toggle('is-open');
        });

        overlay.addEventListener('click', () => {
            sidebar.classList.remove('is-open');
            overlay.classList.remove('is-open');
        });
    }

    // Funcionalidad de expandir/colapsar (desktop)
    if (sidebarToggle && sidebar && mainContent) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('is-expanded');
            mainContent.classList.toggle('is-expanded');
            if (sidebar.classList.contains('is-expanded')) {
                sidebarToggle.innerHTML = '<i class="bi bi-caret-left"></i>';
            } else {
                sidebarToggle.innerHTML = '<i class="bi bi-caret-right"></i>';
            }
        });
    }

    console.log("¡Mi script de submenú está cargado y listo!");
    const submenuToggles = document.querySelectorAll('.sidebar__item.has-submenu > a');
    console.log("Elementos de menú encontrados:", submenuToggles);

    submenuToggles.forEach(toggle => {
        toggle.addEventListener('click', function(event) {
            console.log("¡Clic detectado en el menú desplegable!");
            event.preventDefault();
            event.stopPropagation();

            const parentItem = this.parentElement;
            console.log("Intentando aplicar 'active' a este elemento:", parentItem);
            parentItem.classList.toggle('active');

            document.querySelectorAll('.sidebar__item.has-submenu.active').forEach(openItem => {
                if (openItem !== parentItem) {
                    openItem.classList.remove('active');
                }
            });
        });
    });


    const cantidadInputLote = document.getElementById('id_cantIngreso');
    if (cantidadInputLote) {
        const stepperMinus = cantidadInputLote.closest('.quantity-stepper').querySelector('.stepper-btn--minus');
        const stepperPlus = cantidadInputLote.closest('.quantity-stepper').querySelector('.stepper-btn--plus');

        stepperMinus.addEventListener('click', () => {
            let currentValue = parseInt(cantidadInputLote.value, 10);
            if (currentValue > 1) cantidadInputLote.value = currentValue - 1;
        });

        stepperPlus.addEventListener('click', () => {
            let currentValue = parseInt(cantidadInputLote.value, 10);
            cantidadInputLote.value = currentValue + 1;
        });
    }

    
    const cantidadSensoresInput = document.getElementById('id_cantidad_sensores');
    if (cantidadSensoresInput) {
        const stepperContainer = cantidadSensoresInput.closest('.quantity-stepper');
        const stepperMinus = stepperContainer.querySelector('.stepper-btn--minus');
        const stepperPlus = stepperContainer.querySelector('.stepper-btn--plus');

        stepperMinus.addEventListener('click', () => {
            let currentValue = parseInt(cantidadSensoresInput.value, 10);
            if (currentValue > 0) { // Permitimos que llegue a 0
                cantidadSensoresInput.value = currentValue - 1;
            }
        });

        stepperPlus.addEventListener('click', () => {
            let currentValue = parseInt(cantidadSensoresInput.value, 10) || 0;
            cantidadSensoresInput.value = currentValue + 1;
        });
    }

    // =====================================================================
    // FUNCIONALIDAD #3: TARJETA DE INFORMACIÓN DE EMPLEADO
    // =====================================================================
    const trabajadorSelect = document.querySelector('#id_id_trabajador'); 
    const infoBox = document.getElementById('empleado-info-box');
    
    // SOLO ejecutamos si estamos en la página de flujo
    if (trabajadorSelect && infoBox) {
        trabajadorSelect.addEventListener('change', async () => {
            const empleadoId = trabajadorSelect.value;
            if (!empleadoId) {
                infoBox.style.display = 'none';
                return;
            }
            try {
                const response = await fetch(`/api/empleado-info/${empleadoId}/`);
                if (!response.ok) throw new Error('Empleado no encontrado');
                const data = await response.json();
                infoBox.innerHTML = `
                    <h3>Información del Trabajador</h3>
                    <p><strong>Nombre:</strong> ${data.nombre}</p>
                    <p><strong>Puesto:</strong> ${data.puesto}</p>
                    <p><strong>Área de Trabajo:</strong> ${data.area_trabajo}</p>
                `;
                infoBox.style.display = 'block';
            } catch (error) {
                console.error('Error al obtener la info del empleado:', error);
                infoBox.style.display = 'none';
            }
        });
    }

    
    const dispositivoSelect = document.getElementById('dispositivo-select');
    const infoContainer = document.getElementById('info-y-accion');
    const tipoTexto = document.getElementById('tipo-dispositivo-texto');
    const configurarBtn = document.getElementById('configurar-btn');

    if (dispositivoSelect) {
        dispositivoSelect.addEventListener('change', async () => {
            const dispositivoId = dispositivoSelect.value;
            if (!dispositivoId) {
                infoContainer.style.display = 'none';
                return;
            }
            
            try {
                const response = await fetch(`/api/dispositivo-tipo/${dispositivoId}/`);
                const data = await response.json();
                
                // Actualizamos el texto y el enlace del botón
                tipoTexto.textContent = data.tipo;
                configurarBtn.href = `/alarmas/configurar/${dispositivoId}/`; // Usamos la URL base
                
                // Mostramos el contenedor
                infoContainer.style.display = 'block';

            } catch (error) {
                console.error("Error al obtener el tipo de dispositivo:", error);
                infoContainer.style.display = 'none';
            }
        });
    }
    // --- FIN: SCRIPT DE SELECCIÓN DE ALARMA ---
    const componenteNsInput = document.getElementById('id_componente_ns');
    const componenteIdInput = document.getElementById('id_id_componente');
    const suggestionsBoxVentas = document.getElementById('suggestions-box');

    console.log("Buscando elementos para venta:", { componenteNsInput, componenteIdInput, suggestionsBoxVentas });

    if (componenteNsInput && componenteIdInput && suggestionsBoxVentas) {
        console.log("¡Elementos para venta encontrados! Añadiendo listener.");
        
        componenteNsInput.addEventListener('input', async (e) => {
            const query = e.target.value;
            componenteIdInput.value = ''; 
            console.log("Usuario escribió:", query);

            if (query.length < 2) {
                suggestionsBoxVentas.innerHTML = '';
                return;
            }

            const url = `/api/search-componentes-disponibles/?q=${encodeURIComponent(query)}`;
            console.log("Haciendo fetch a:", url);

            try {
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`Error de red: ${response.status}`);
                }
                const data = await response.json();
                console.log("Datos recibidos:", data);
                
                suggestionsBoxVentas.innerHTML = '';

                data.forEach(suggestion => {
                    const div = document.createElement('div');
                    div.textContent = suggestion.text;
                    div.classList.add('suggestion-item');
                    
                    div.addEventListener('click', () => {
                        componenteNsInput.value = suggestion.text;
                        componenteIdInput.value = suggestion.id;
                        suggestionsBoxVentas.innerHTML = '';
                        console.log("Componente seleccionado. ID guardado:", suggestion.id);
                    });

                    suggestionsBoxVentas.appendChild(div);
                });
            } catch (error) {
                console.error('Error durante el fetch de componentes:', error);
            }
        });
    } else {
        console.log("Aviso: No se encontraron los elementos para el autocompletado de ventas en esta página.");
    }

    const dispositivoSelectMod = document.getElementById('id_id_dispositivo');
    // El ID que Django le da a nuestro campo virtual
    const involucradoSelectMod = document.getElementById('id_componente_o_parte_involucrada');

    // Solo ejecutamos si estamos en la página de modificación
    if (dispositivoSelectMod && involucradoSelectMod) {
        
        dispositivoSelectMod.addEventListener('change', async () => {
            const dispositivoId = dispositivoSelectMod.value;
            
            // Deshabilitamos y limpiamos el select de involucrados mientras carga
            involucradoSelectMod.disabled = true;
            involucradoSelectMod.innerHTML = '<option value="">Cargando...</option>';

            if (!dispositivoId) {
                involucradoSelectMod.innerHTML = '<option value="">Selecciona un dispositivo primero</option>';
                return;
            }

            try {
                const url = `/api/get-partes-y-sensores/?dispositivo_id=${dispositivoId}`;
                const response = await fetch(url);
                const opciones = await response.json();

                // Limpiamos de nuevo y añadimos la opción por defecto
                involucradoSelectMod.innerHTML = '<option value="">-- Selecciona una opción --</option>';

                if (opciones.length > 0) {
                    opciones.forEach(opcion => {
                        const optionEl = document.createElement('option');
                        optionEl.value = opcion.id; // ej: 'sensor_5' o 'parte_12'
                        optionEl.textContent = opcion.nombre;
                        involucradoSelectMod.appendChild(optionEl);
                    });
                    involucradoSelectMod.disabled = false; // Habilitamos el select
                } else {
                    involucradoSelectMod.innerHTML = '<option value="">No hay partes o sensores para este dispositivo</option>';
                }

            } catch (error) {
                console.error('Error al cargar componentes y partes:', error);
                involucradoSelectMod.innerHTML = '<option value="">Error al cargar opciones</option>';
            }
        });

        // Disparamos el evento 'change' al cargar la página por si ya hay un dispositivo seleccionado (en modo edición)
        if (dispositivoSelectMod.value) {
            dispositivoSelectMod.dispatchEvent(new Event('change'));
        }
    }

    
    console.log("Inicializando script de menús desplegables..."); // MENSAJE 1

    const actionButtons = document.querySelectorAll('.actions-btn');

    console.log(`Se encontraron ${actionButtons.length} botones de acciones.`); // MENSAJE 2

    actionButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            console.log("¡Botón de acciones presionado!"); // MENSAJE 3
            
            // Detenemos la propagación para que el clic no active el listener de 'window' inmediatamente
            event.stopPropagation();
            
            // Buscamos el contenido del menú que está JUSTO DESPUÉS del botón
            const dropdownContent = button.nextElementSibling;
            
            if (dropdownContent && dropdownContent.classList.contains('dropdown-content')) {
                console.log("Contenido del dropdown encontrado. Mostrando/ocultando..."); // MENSAJE 4
                
                // Cerramos cualquier otro menú que pueda estar abierto
                closeAllDropdowns(dropdownContent);
                
                // Mostramos u ocultamos el menú actual
                dropdownContent.classList.toggle('show-dropdown');
            } else {
                console.error("ERROR: No se encontró el div '.dropdown-content' después del botón.", button);
            }
        });
    });

    // Función para cerrar todos los menús
    const closeAllDropdowns = (exceptThisOne = null) => {
        document.querySelectorAll('.dropdown-content').forEach(dropdown => {
            if (dropdown !== exceptThisOne) {
                dropdown.classList.remove('show-dropdown');
            }
        });
    };

    // Listener para cerrar los menús si se hace clic en cualquier otro lugar
    window.addEventListener('click', (event) => {
        // Obtenemos el elemento donde se originó el clic
        const clickedElement = event.target;
        
        // Obtenemos una referencia a la barra lateral
        const sidebar = document.querySelector('.sidebar');
        
        // --- LÓGICA DE CONTROL ---
        // Verificamos si el clic ocurrió DENTRO de la barra lateral
        // o si el clic fue en un elemento que abre la barra lateral (si lo tienes).
        // .closest('.sidebar') busca si el elemento clickeado o alguno de sus padres es el sidebar.
        if (sidebar && sidebar.contains(clickedElement)) {
            // Si el clic fue DENTRO de la barra lateral, no hacemos nada.
            // El script del submenú se encargará de abrir/cerrar.
            console.log("Clic DENTRO de la barra lateral. No se cierran los menús.");
            return; 
        }
        
        // Si el clic fue FUERA de la barra lateral, entonces sí cerramos todo.
        console.log("Clic FUERA de la barra lateral. Cerrando todos.");
        
        // Llama a tu función para cerrar los DROPDOWNS (no los submenús del sidebar)
        closeAllDropdowns();
        
        // Lógica adicional para cerrar los SUBMENÚS del sidebar si están abiertos
        document.querySelectorAll('.sidebar__item.has-submenu.active').forEach(item => {
            item.classList.remove('active');
        });
    });

    console.log("Script de menús desplegables configurado."); // MENSAJE FINAL
    // --- FIN: SCRIPT PARA MENÚS DESPLEGABLES ---
})