// static/js/file-upload.js

// Función auto-ejecutable para la subida de archivos
(function ekUpload() {
    function Init() {
        const fileSelect = getFileInput();
        const fileDrag = document.getElementById('file-drag');
        
        if (!fileSelect || !fileDrag) return; // Salir si los elementos no existen

        fileSelect.addEventListener('change', fileSelectHandler, false);

        // Soporte para Drag & Drop
        if (new XMLHttpRequest().upload) {
            fileDrag.addEventListener('dragover', fileDragHover, false);
            fileDrag.addEventListener('dragleave', fileDragHover, false);
            fileDrag.addEventListener('drop', fileSelectHandler, false);
        }
    }

    function fileDragHover(e) {
        e.stopPropagation();
        e.preventDefault();
        e.currentTarget.className = (e.type === 'dragover' ? 'hover' : '');
    }

    function fileSelectHandler(e) {
        // Obtiene la lista de archivos (del input o del drop)
        const files = e.target.files || e.dataTransfer.files;

        // Cancela eventos y estilos de hover
        fileDragHover(e);
        
        // Asigna los archivos arrastrados al input de archivo real
        // Esto es CLAVE para que el formulario de Django los reciba
        const fileInput = getFileInput();
        if (fileInput && e.dataTransfer && files) {
            try {
                fileInput.files = files;
            } catch (err) {
                // Si el navegador bloquea la asignación programática,
                // igual mostramos el nombre para dar feedback.
            }
        }

        // Procesa el primer archivo para mostrar su nombre
        if (files.length > 0) {
            parseFile(files[0]);
        }
    }

    // Muestra el nombre del archivo seleccionado
    function output(msg) {
        document.getElementById('messages').innerHTML = msg;
    }

    function parseFile(file) {
        output('<strong>' + encodeURI(file.name) + '</strong>');
        document.getElementById('start').style.display = 'none';
        document.getElementById('response').style.display = 'block';
    }

    function getFileInput() {
        // Preferimos el input dentro del wrapper (reutilizable en varios formularios)
        const inWrapper = document.querySelector('#file-upload-wrapper input[type="file"]');
        if (inWrapper) return inWrapper;

        // Fallback por compatibilidad con páginas antiguas
        return (
            document.getElementById('id_archivo_subsana') ||
            document.getElementById('id_archivo_confirmacion') ||
            document.querySelector('input[type="file"]')
        );
    }

    // Comprueba si las APIs de archivo son soportadas
    if (window.File && window.FileList && window.FileReader) {
        Init();
    } else {
        document.getElementById('file-drag').style.display = 'none';
    }
})();