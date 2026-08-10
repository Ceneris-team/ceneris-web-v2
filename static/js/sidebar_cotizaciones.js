// Esperamos a que el documento esté listo para asegurar que jQuery está cargado
$(document).ready(function(){
  $('#msbo').on('click', function(){
    $('body').toggleClass('msb-x');
  });
});