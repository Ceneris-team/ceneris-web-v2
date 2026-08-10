// static/js/task_assignment.js (VERSIÓN FINAL Y ROBUSTA CON MÁS DEPURACIÓN)
document.addEventListener('DOMContentLoaded', function() {
    console.log("--- DEBUG: task_assignment.js ---");
    console.log("✅ Script cargado. Esperando a que el DOM esté completo.");
    
    // --- ELEMENTOS GLOBALES Y DATOS ---
    const mainTasksWrapper = document.getElementById('main-tasks-wrapper');
    const addMainTaskBtn = document.getElementById('add-main-task-btn');
    const mainTaskTemplate = document.getElementById('main-task-template');
    const subtaskTemplate = document.getElementById('subtask-template');
    const insumoRowTemplate = document.getElementById('insumo-row-template');
    const taskForm = document.getElementById('task-form');

    // Verificación crítica de elementos base
    if (!mainTaskTemplate || !subtaskTemplate || !insumoRowTemplate || !taskForm) {
        console.error("🔥 ERROR CRÍTICO: Faltan elementos de plantilla o formulario. El script no puede continuar.");
        return;
    }
    
    const insumoSearchUrl = taskForm.dataset.insumoSearchUrl;
    const personalSearchUrl = taskForm.dataset.personalSearchUrl;
    const itemsToDelete = { main_tasks: [], subtareas: [], asignaciones: [] };
    let mainTaskCounter = 0;

    function updateDeleteInput() {
        const deleteInput = document.getElementById('items-to-delete-input');
        if (deleteInput) {
            deleteInput.value = JSON.stringify(itemsToDelete);
        }
    }

    function initializeSelect2(element, url, placeholder) {
        if (!element || element.length === 0) {
            console.warn(`⚠️ Advertencia: Se intentó inicializar Select2 en un elemento no válido.`);
            return;
        }
        console.log(`🚀 Inicializando Select2 en:`, element[0], `con URL: ${url}`);
        element.select2({
            placeholder: placeholder,
            width: '100%',
            ajax: { url: url, dataType: 'json', delay: 250, processResults: data => ({ results: data.results }), cache: true }
        });
    }

    // --- FUNCIÓN PARA CREAR UN BLOQUE DE INSUMO ---
    function createInsumoRow(mainIndex, subIndex, insumoData = null) {
        const insumoClone = insumoRowTemplate.content.cloneNode(true);
        const insumoRow = insumoClone.querySelector('.insumo-row');
        let insumoCounter = Date.now();
        
        const insumoAsignacionIdInput = insumoRow.querySelector('input[name^="insumo_asignacion_id"]');
        if (insumoAsignacionIdInput) {
            insumoAsignacionIdInput.name = `insumo_asignacion_id_${mainIndex}_${subIndex}_${insumoCounter}`;
            if (insumoData?.asignacion_id) insumoAsignacionIdInput.value = insumoData.asignacion_id;
        }

        const select = insumoRow.querySelector('.insumo-search');
        if (select) {
            select.name = `insumo_id_${mainIndex}_${subIndex}_${insumoCounter}`;
        }
        
        const cantidadInput = insumoRow.querySelector('input[type="number"]');
        if (cantidadInput) {
            cantidadInput.name = `insumo_cantidad_${mainIndex}_${subIndex}_${insumoCounter}`;
            if (insumoData) cantidadInput.value = insumoData.cantidad || '';
        }

        const removeInsumoBtn = insumoRow.querySelector('.btn-remove-insumo');
        if (removeInsumoBtn) {
            removeInsumoBtn.addEventListener('click', function() {
                if (insumoAsignacionIdInput?.value) { itemsToDelete.asignaciones.push(insumoAsignacionIdInput.value); updateDeleteInput(); }
                this.closest('.insumo-row').remove();
            });
        }
        
        console.log("    ➕ Fila de insumo creada con datos:", insumoData);

        return insumoRow;
    }

    // --- FUNCIÓN PARA CREAR UN BLOQUE DE SUBTAREA ---
    function createSubtaskBlock(mainIndex, subtaskData = null) {
        let subTaskCounter = Date.now();
        const subIndex = subTaskCounter++;
        console.log(`  🏗️ Creando bloque de Subtarea. Índice: ${mainIndex}_${subIndex}`);
        console.log("  📥 Datos de subtarea recibidos:", subtaskData);

        const subtaskClone = subtaskTemplate.content.cloneNode(true);
        const subtaskBlock = subtaskClone.querySelector('.subtask-block');
        
        const subTaskIdInput = subtaskBlock.querySelector('input[name^="subtask_id"]');
        if (subTaskIdInput) {
            subTaskIdInput.name = `subtask_id_${mainIndex}_${subIndex}`;
            if (subtaskData?.id) subTaskIdInput.value = subtaskData.id;
        }

        const subtaskTituloInput = subtaskBlock.querySelector('input[name^="subtask_titulo"]');
        if (subtaskTituloInput) {
            subtaskTituloInput.name = `subtask_titulo_${mainIndex}_${subIndex}`;
            if (subtaskData?.titulo) subtaskTituloInput.value = subtaskData.titulo;
        }
        
        const subtaskInicioInput = subtaskBlock.querySelector('input[name^="subtask_inicio"]');
        if (subtaskInicioInput) {
            subtaskInicioInput.name = `subtask_inicio_${mainIndex}_${subIndex}`;
            if (subtaskData?.inicio) subtaskInicioInput.value = subtaskData.inicio;
        }

        const subtaskFinInput = subtaskBlock.querySelector('input[name^="subtask_fin"]');
        if (subtaskFinInput) {
            subtaskFinInput.name = `subtask_fin_${mainIndex}_${subIndex}`;
            if (subtaskData?.fin) subtaskFinInput.value = subtaskData.fin;
        }

        const removeSubBtn = subtaskBlock.querySelector('.btn-remove-sub');
        if (removeSubBtn) {
            removeSubBtn.addEventListener('click', function() {
                const idInput = subtaskBlock.querySelector(`input[name="subtask_id_${mainIndex}_${subIndex}"]`);
                if (idInput?.value && !idInput.value.startsWith('new_')) { itemsToDelete.subtareas.push(idInput.value); updateDeleteInput(); }
                this.closest('.subtask-block').remove();
            });
        }
        
        const addInsumoBtn = subtaskBlock.querySelector('.btn-add-insumo');
        const insumosList = subtaskBlock.querySelector('.insumos-list');
        if (addInsumoBtn) {
            addInsumoBtn.addEventListener('click', function() {
                const newInsumoRow = createInsumoRow(mainIndex, subIndex);
                insumosList.appendChild(newInsumoRow);
                initializeSelect2($(newInsumoRow.querySelector('.insumo-search')), insumoSearchUrl, 'Busca un insumo...');
            });
        }
        
        if (subtaskData?.insumos) {
            console.log("    🔍 Subtarea tiene insumos. Procesando:", Object.keys(subtaskData.insumos).length, "elementos.");
            Object.values(subtaskData.insumos).forEach(insumoData => {
                const insumoRow = createInsumoRow(mainIndex, subIndex, insumoData);
                insumosList.appendChild(insumoRow);
                const selectElement = $(insumoRow.querySelector('.insumo-search'));
                if (selectElement.length > 0 && insumoData.id && insumoData.text) {
                    const newOption = new Option(insumoData.text, insumoData.id, true, true);
                    selectElement.append(newOption).trigger('change');
                }
            });
        }
        
        const personalSelect = subtaskBlock.querySelector('.personal-search');
        if (personalSelect) {
            personalSelect.name = `personal_asignado_${mainIndex}_${subIndex}`;
            if (subtaskData?.personal_asignado) {
                console.log("    👥 Subtarea tiene personal. Procesando:", subtaskData.personal_asignado.length, "elementos.");
                subtaskData.personal_asignado.forEach(persona => {
                    const newOption = new Option(persona.text, persona.id, true, true);
                    $(personalSelect).append(newOption);
                });
            }
        }
        
        return subtaskBlock;
    }

    // --- FUNCIÓN PRINCIPAL PARA CREAR TAREAS ---
    function addMainTask(initialData = null) {
        const mainIndex = mainTaskCounter++;
        console.log("➕ Creando Tarea Principal. Índice:", mainIndex);
        console.log("📥 Datos de tarea principal recibidos:", initialData);
        
        const mainTaskClone = mainTaskTemplate.content.cloneNode(true);
        const mainTaskCard = mainTaskClone.querySelector('.main-task-card');

        if (!mainTaskCard) {
            console.error("Error crítico: No se pudo encontrar '.main-task-card' en la plantilla. Revisa tu HTML.");
            return;
        }

        const mainTaskIdInput = mainTaskCard.querySelector('input[name^="main_task_id"]');
        if (mainTaskIdInput) {
            mainTaskIdInput.name = `main_task_id_${mainIndex}`;
            if (initialData?.id) mainTaskIdInput.value = initialData.id;
        }

        const mainTaskTituloInput = mainTaskCard.querySelector('input[name^="main_task_titulo"]');
        if (mainTaskTituloInput) {
            mainTaskTituloInput.name = `main_task_titulo_${mainIndex}`;
            if (initialData?.titulo) mainTaskTituloInput.value = initialData.titulo;
        }

        const removeMainBtn = mainTaskCard.querySelector('.btn-remove-main');
        if (removeMainBtn) {
            removeMainBtn.addEventListener('click', function() {
                if (mainTaskIdInput?.value && !mainTaskIdInput.value.startsWith('new_')) {
                    itemsToDelete.main_tasks.push(mainTaskIdInput.value);
                    updateDeleteInput();
                }
                this.closest('.main-task-card').remove();
            });
        }
        
        // 1. AÑADIMOS la tarjeta principal al DOM.
        mainTasksWrapper.appendChild(mainTaskCard);
        
        // 2. OBTENEMOS los contenedores que ahora SÍ existen en la página.
        const subtasksContainer = mainTaskCard.querySelector('.subtasks-container');
        const addSubtaskBtn = mainTaskCard.querySelector('.btn-add-subtask');
        
        // 3. POBLAMOS la tarjeta con sus hijos.
        if (initialData?.subtareas && Object.keys(initialData.subtareas).length > 0) {
            console.log("  🔄 Procesando", Object.keys(initialData.subtareas).length, "subtareas de los datos iniciales.");
            Object.values(initialData.subtareas).forEach(subData => {
                subtasksContainer.appendChild(createSubtaskBlock(mainIndex, subData));
            });
        } else {
            console.log("  ⚠️ No se encontraron subtareas en los datos iniciales, creando una por defecto.");
            subtasksContainer.appendChild(createSubtaskBlock(mainIndex));
        }

        // 4. AÑADIMOS los listeners e inicializamos las librerías.
        if (addSubtaskBtn) {
            addSubtaskBtn.addEventListener('click', function() {
                console.log(`🔘 Botón 'Añadir Subtarea' presionado en Tarea Principal ${mainIndex}`);
                const newSubtaskBlock = createSubtaskBlock(mainIndex);
                subtasksContainer.appendChild(newSubtaskBlock);
                // Inicializamos Select2 para el nuevo bloque
                const selectElements = $(newSubtaskBlock).find('.personal-search, .insumo-search');
                selectElements.each(function() {
                    const element = $(this);
                    const url = element.hasClass('personal-search') ? personalSearchUrl : insumoSearchUrl;
                    const placeholder = element.hasClass('personal-search') ? 'Busca y asigna personal...' : 'Busca un insumo...';
                    initializeSelect2(element, url, placeholder);
                });
            });
        }

        // Inicializamos Select2 en todos los selectores que acabamos de añadir en esta tarea principal.
        $(mainTaskCard).find('.personal-search, .insumo-search').each(function() {
            const element = $(this);
            const url = element.hasClass('personal-search') ? personalSearchUrl : insumoSearchUrl;
            const placeholder = element.hasClass('personal-search') ? 'Busca y asigna personal...' : 'Busca un insumo...';
            initializeSelect2(element, url, placeholder);
        });
    }

    // --- LÓGICA DE CARGA INICIAL ---
    const formDataElement = document.getElementById('submitted-form-data');
    if (formDataElement) {
        try {
            const submittedData = JSON.parse(formDataElement.textContent);
            console.log("--- DEBUG: Datos del formulario cargados ---");
            console.log(submittedData);
            if (Object.keys(submittedData).length > 0) {
                Object.values(submittedData).forEach(mainTaskData => addMainTask(mainTaskData));
            } else {
                console.log("    Formulario vacío, creando una tarea principal por defecto.");
                addMainTask();
            }
        } catch (e) {
            console.error("🔥 Error al parsear datos del formulario, iniciando formulario vacío.", e);
            addMainTask();
        }
    } else {
        console.log("--- DEBUG: No se encontraron datos iniciales, creando formulario vacío ---");
        addMainTask();
    }

    if (addMainTaskBtn) {
        addMainTaskBtn.addEventListener('click', () => addMainTask());
    }
});