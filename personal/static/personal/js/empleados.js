// Dentro de tu archivo empleados.js
document.addEventListener('DOMContentLoaded', function() {
  // Asegúrate de que jQuery esté cargado ANTES que este script
  // ... tu código de Select2, etc.

  $(".cs-cards figure").each(function() {
    var figure = $(this);
    var imgsrc = figure.find("img.card-img").attr("src");
    
    // Solo si la imagen existe, agrega el div y la imagen de fondo
    if (imgsrc) {
        var imgBgHover = $("<img class='imgbghover' />").attr("src", imgsrc);
        figure.find("figcaption").append(imgBgHover);
    }
  });

});