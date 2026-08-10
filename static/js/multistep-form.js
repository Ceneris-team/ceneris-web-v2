$(document).ready(function() {

    var animating; // Flag to prevent quick multi-click glitches

    // --- LÓGICA DE NAVEGACIÓN Y VALIDACIÓN DEL BOTÓN "SIGUIENTE" ---
    $("#msform .next").on('click', function() {
        if (animating) return;

        var current_fs = $(this).parent();
        var isValid = true;
        
        // Valida solo los campos requeridos y VISIBLES en el fieldset actual
        current_fs.find('input[required], select[required], textarea[required]').filter(':visible').each(function() {
            if ($(this).val() === "" || $(this).val() === null) {
                isValid = false;
                $(this).css('border-color', 'red');
            } else {
                $(this).css('border-color', '#ccc');
            }
        });

        if (!isValid) {
            alert("Por favor, completa todos los campos requeridos en este paso.");
            return;
        }

        animating = true;
        
        var next_fs = current_fs.next('fieldset');
        var progressbar = $('#progressbar');
        
        // Lógica para saltar el paso de controles si no es necesario
        var cantidadControlesInput = $('#id_cantidad_controles');
        var fieldsetControles = $('#fieldset-controles');
        if (next_fs.is(fieldsetControles) && (parseInt(cantidadControlesInput.val(), 10) || 0) === 0) {
            next_fs = next_fs.next('fieldset'); // Saltamos al de documentación
            progressbar.find('li').last().addClass('active');
        } else {
            progressbar.find('li').eq($("fieldset").index(next_fs)).addClass("active");
        }
        
        next_fs.show();
        current_fs.animate({opacity: 0}, {
            step: function(now) {
                var scale = 1 - (1 - now) * 0.2;
                var left = (now * 50) + "%";
                var opacity = 1 - now;
                current_fs.css({'transform': 'scale(' + scale + ')', 'position': 'absolute'});
                next_fs.css({'left': left, 'opacity': opacity});
            },
            duration: 800,
            complete: function(){
                current_fs.hide();
                current_fs.css({'position': 'relative'});
                animating = false;
            },
            easing: 'easeInOutBack'
        });
    });

    // --- LÓGICA DE NAVEGACIÓN DEL BOTÓN "ANTERIOR" ---
    $("#msform .previous").on('click', function() {
        if(animating) return;
        animating = true;

        var current_fs = $(this).parent();
        var previous_fs = current_fs.prev('fieldset');
        var progressbar = $('#progressbar');
        
        // Lógica para saltar el paso de controles hacia atrás
        var cantidadControlesInput = $('#id_cantidad_controles');
        var fieldsetControles = $('#fieldset-controles');
        if (previous_fs.is(fieldsetControles) && (parseInt(cantidadControlesInput.val(), 10) || 0) === 0) {
            previous_fs = previous_fs.prev('fieldset');
        }
        
        progressbar.find('li').eq($("fieldset").index(current_fs)).removeClass("active");
        
        previous_fs.show();
        current_fs.animate({opacity: 0}, {
            step: function(now) {
                var scale = 0.8 + (1 - now) * 0.2;
                var left = ((1-now) * 50)+"%";
                var opacity = 1 - now;
                current_fs.css({'left': left});
                previous_fs.css({'transform': 'scale('+scale+')', 'opacity': opacity});
            },
            duration: 800,
            complete: function(){
                current_fs.hide();
                animating = false;
            },
            easing: 'easeInOutBack'
        });
    });

});