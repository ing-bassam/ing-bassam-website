// assets/js/main.js
(function(){
  // setzt einen Zeitstempel fürs Formular, nützlich gegen Spam
  var ff = document.getElementById('footer-form');
  if(ff){
    var ts = ff.querySelector('#ts-footer');
    if(ts){ ts.value = new Date().toISOString(); }
  }
})();
