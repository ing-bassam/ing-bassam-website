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
