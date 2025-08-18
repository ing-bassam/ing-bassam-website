
(function () {
  document.querySelectorAll('form').forEach(function (f) {
    var ts = f.querySelector('#ts-footer');
    if (ts) ts.value = new Date().toISOString();
  });
  function setStatus(form, msg, ok) {
    var box = form.querySelector('.form-status');
    if (!box) return;
    box.textContent = msg;
    box.classList.remove('ok','err');
    box.classList.add(ok ? 'ok' : 'err');
  }
  document.querySelectorAll('form[action^="https://formspree.io/"]').forEach(function (form) {
    form.addEventListener('submit', async function (ev) {
      ev.preventDefault();
      setStatus(form,'Sende …',true);
      try {
        const data = new FormData(form);
        const resp = await fetch(form.action, { method:'POST', body:data, headers:{'Accept':'application/json'} });
        if (resp.ok) {
          setStatus(form,'Vielen Dank! Ihre Nachricht ist angekommen.',true);
          form.reset();
          if (window.hcaptcha && form.querySelector('.h-captcha')) { try { hcaptcha.reset(); } catch(e){} }
        } else {
          let j={}; try{ j = await resp.json(); }catch(e){}
          setStatus(form, (j && j.error) ? j.error : 'Senden fehlgeschlagen. Bitte später erneut versuchen.', false);
        }
      } catch(e) {
        setStatus(form, 'Netzwerkfehler. Bitte Verbindung prüfen.', false);
      }
    });
  });
})();
