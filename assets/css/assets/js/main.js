// assets/js/main.js
(function(){
  var setTS = function(form, id){
    var el = form.querySelector(id);
    if(el){ el.value = new Date().toISOString(); }
  };
  // Footer form
  var ff = document.getElementById('footer-form');
  if(ff){ setTS(ff, '#ts-footer'); }
})();
