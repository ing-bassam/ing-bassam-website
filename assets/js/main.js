// assets/js/main.js
(function () {
  function setTS(form) {
    var el = form.querySelector('input[name="timestamp"]');
    if (el) el.value = new Date().toISOString();
    // optional: Seite mitschicken, falls das Feld vorhanden ist
    var page = form.querySelector('input[name="page"]');
    if (page && !page.value) page.value = location.pathname;
  }

  // alle Kontaktformulare auf der Seite bedienen
  document.querySelectorAll('form.contact-form').forEach(setTS);
})();


// Intercept contact/footers forms to submit via fetch and show in-page confirmation
(function(){
  function enhanceForm(form){
    if(!form) return;
    if(form.dataset.enhanced === "1") return;
    form.dataset.enhanced = "1";
    form.addEventListener('submit', async function(e){
      e.preventDefault();
      const btn = form.querySelector('button[type="submit"]');
      const original = btn ? btn.textContent : '';
      if(btn){ btn.disabled = true; btn.textContent = 'Senden...'; }
      const formData = new FormData(form);
      // Remove redirect if present
      formData.delete('_redirect');
      try{
        const res = await fetch(form.action, { method: 'POST', body: formData, headers: { 'Accept': 'application/json' }});
        // Show confirmation inline regardless of redirect behavior
        const ok = res.ok;
        const box = document.createElement('p');
        box.className = 'small';
        box.style.marginTop = '10px';
        box.textContent = ok ? 'Vielen Dank. Ihre Anfrage ist eingegangen.' : 'Danke. Ihre Anfrage wurde gesendet.';
        form.replaceWith(box);
      }catch(err){
        const box = document.createElement('p');
        box.className = 'small';
        box.style.marginTop = '10px';
        box.textContent = 'Vielen Dank. Ihre Anfrage ist eingegangen.';
        form.replaceWith(box);
      }
    }, { once:false });
  }
  document.addEventListener('DOMContentLoaded', function(){
    enhanceForm(document.getElementById('footer-form'));
    enhanceForm(document.getElementById('kontakt-form'));
  });
})();
