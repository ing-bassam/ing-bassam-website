// assets/js/main.js — small helpers
(function(){
  var ff = document.getElementById('footer-form');
  if(ff){
    var ts = ff.querySelector('#ts-footer');
    if(ts){ ts.value = new Date().toISOString(); }
  }
})();
