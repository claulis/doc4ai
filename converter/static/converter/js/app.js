(function () {
  var I18N = JSON.parse(document.getElementById('js-i18n').textContent);

  var ERROR_MESSAGES = {
    no_file: I18N.errorNoFile,
    too_large: I18N.errorTooLarge,
    unsupported_type: I18N.errorUnsupportedType,
    corrupted: I18N.errorCorrupted,
    conversion_failed: I18N.errorConversionFailed,
    no_content: I18N.errorNoContent,
    ocr_timeout: I18N.errorOcrTimeout
  };

  /* ── tema ── */
  var STORAGE_KEY = 'doc4ai-theme';
  var themeToggle = document.getElementById('themeToggle');
  var iconMoon = document.getElementById('iconMoon');
  var iconSun = document.getElementById('iconSun');
  var html = document.documentElement;

  function setTheme(theme) {
    html.setAttribute('data-theme', theme);
    if (theme === 'dark') {
      iconMoon.style.display = 'none';
      iconSun.style.display = '';
    } else {
      iconMoon.style.display = '';
      iconSun.style.display = 'none';
    }
    try { localStorage.setItem(STORAGE_KEY, theme); } catch (_) {}
  }

  var saved;
  try { saved = localStorage.getItem(STORAGE_KEY); } catch (_) { saved = null; }
  setTheme(saved === 'dark' ? 'dark' : 'light');

  themeToggle.addEventListener('click', function () {
    setTheme(html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });

  /* ── idioma ── */
  var langToggle = document.getElementById('langToggle');
  var langMenu = document.getElementById('langMenu');

  langToggle.addEventListener('click', function (e) {
    e.stopPropagation();
    var expanded = langToggle.getAttribute('aria-expanded') === 'true';
    langToggle.setAttribute('aria-expanded', String(!expanded));
    langMenu.hidden = expanded;
  });

  document.addEventListener('click', function (e) {
    if (!langMenu.hidden && !langMenu.contains(e.target) && e.target !== langToggle) {
      langMenu.hidden = true;
      langToggle.setAttribute('aria-expanded', 'false');
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !langMenu.hidden) {
      langMenu.hidden = true;
      langToggle.setAttribute('aria-expanded', 'false');
    }
  });

  /* ── elementos ── */
  var dropzone = document.getElementById('dropzone');
  var fileInput = document.getElementById('fileInput');
  var fileInfo = document.getElementById('fileInfo');
  var fileName = document.getElementById('fileName');
  var convertBtn = document.getElementById('convertBtn');
  var uploadSection = document.getElementById('uploadSection');
  var progressSection = document.getElementById('progressSection');
  var progressFill = document.getElementById('progressFill');
  var progressText = document.getElementById('progressText');
  var resultSection = document.getElementById('resultSection');
  var successState = document.getElementById('successState');
  var errorState = document.getElementById('errorState');
  var errorMessage = document.getElementById('errorMessage');
  var downloadBtn = document.getElementById('downloadBtn');
  var resetBtn = document.getElementById('resetBtn');
  var errorResetBtn = document.getElementById('errorResetBtn');

  var selectedFile = null;
  var mdContent = '';
  var mdFilename = '';
  var estimateSecs = 0;
  var countdownTimer = null;

  /* ── estimativa de tempo ── */
  var timeEstimate = document.getElementById('timeEstimate');
  var timeEstimateText = document.getElementById('timeEstimateText');

  var EST_RATES = {
    pdf:  [2, 3],
    docx: [1, 1],   doc:  [1, 1.2],
    pptx: [2, 1.5], ppt:  [2, 1.8],
    xlsx: [1, 0.8], xls:  [1, 1],
    html: [0.5, 0.3], htm: [0.5, 0.3],
    csv:  [0.5, 0.2], json: [0.5, 0.2], xml: [0.5, 0.3],
    txt:  [0.3, 0.1], md:  [0.3, 0.1],
    jpg:  [3, 2], jpeg: [3, 2], png: [3, 2],
    gif:  [3, 2], bmp:  [3, 2], tiff: [4, 2.5], tif: [4, 2.5],
    epub: [2, 1.5],
    zip:  [3, 2],
    mp3:  [5, 4], wav: [5, 5],
    msg:  [1, 1]
  };

  function calcEstimate(file) {
    var ext = (file.name.split('.').pop() || '').toLowerCase();
    var r = EST_RATES[ext] || [2, 1.5];
    return r[0] + (file.size / (1024 * 1024)) * r[1];
  }

  function formatSecs(s) {
    if (s < 5)  return I18N.lessThan5s;
    if (s < 60) return I18N.secondsFormat.replace('%s', Math.ceil(s / 5) * 5);
    var m = Math.ceil(s / 60);
    return I18N.minutesFormat.replace('%s', m);
  }

  /* ── dropzone ── */
  function dzEnter(e) { e.preventDefault(); e.stopPropagation(); dropzone.classList.add('dragover'); }
  function dzLeave(e) { e.preventDefault(); e.stopPropagation(); dropzone.classList.remove('dragover'); }

  dropzone.addEventListener('dragenter', dzEnter);
  dropzone.addEventListener('dragover', dzEnter);
  dropzone.addEventListener('dragleave', dzLeave);
  dropzone.addEventListener('drop', function (e) {
    dzLeave(e);
    if (e.dataTransfer.files.length > 0) selectFile(e.dataTransfer.files[0]);
  });
  dropzone.addEventListener('click', function () { fileInput.click(); });
  dropzone.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInput.click();
    }
  });
  fileInput.addEventListener('change', function () {
    if (fileInput.files.length > 0) selectFile(fileInput.files[0]);
  });

  function selectFile(f) {
    if (f.size > 50 * 1024 * 1024) {
      alert(I18N.tooLarge);
      return;
    }
    selectedFile = f;
    fileName.textContent = f.name + ' (' + (f.size / 1024 / 1024).toFixed(2) + ' MB)';
    fileInfo.hidden = false;
    estimateSecs = calcEstimate(f);
    timeEstimateText.textContent = formatSecs(estimateSecs);
    timeEstimate.classList.add('visible');
    convertBtn.disabled = false;
  }

  /* ── conversão ── */
  convertBtn.addEventListener('click', function () {
    if (selectedFile) convert();
  });

  function getCSRF() {
    if (!document.cookie) return null;
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
      var c = cookies[i].trim();
      if (c.substring(0, 10) === 'csrftoken=') {
        return decodeURIComponent(c.substring(10));
      }
    }
    return null;
  }

  function convert() {
    uploadSection.style.display = 'none';
    progressSection.classList.add('visible');
    resultSection.classList.remove('visible');
    progressFill.className = 'progress-fill';
    progressFill.style.width = '0%';
    progressText.textContent = I18N.uploading;

    var fd = new FormData();
    fd.append('document', selectedFile);

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/convert/');

    var csrf = getCSRF();
    if (csrf) xhr.setRequestHeader('X-CSRFToken', csrf);

    xhr.upload.addEventListener('progress', function (e) {
      if (!e.lengthComputable) return;
      var pct = Math.round((e.loaded / e.total) * 100);
      progressFill.className = 'progress-fill';
      progressFill.style.width = pct + '%';
      progressText.textContent = I18N.uploadingPct.replace('%s', pct);
    });

    xhr.upload.addEventListener('loadend', function () {
      progressFill.className = 'progress-fill indeterminate';
      progressFill.style.width = '';
      var remaining = Math.ceil(estimateSecs);
      progressText.textContent = I18N.converting.replace('%s', formatSecs(remaining));
      clearInterval(countdownTimer);
      countdownTimer = setInterval(function () {
        remaining = Math.max(0, remaining - 1);
        progressText.textContent = remaining > 0
          ? I18N.converting.replace('%s', formatSecs(remaining))
          : I18N.finalizing;
        if (remaining === 0) clearInterval(countdownTimer);
      }, 1000);
    });

    xhr.addEventListener('load', function () {
      try {
        var resp = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300 && resp.success) {
          mdContent = resp.content;
          mdFilename = resp.filename || 'documento.md';
          showSuccess();
        } else {
          showError(resp.error);
        }
      } catch (_) {
        showError();
      }
    });

    xhr.addEventListener('abort', function () { showError(); });
    xhr.addEventListener('error', function () { showError(); });

    xhr.send(fd);
  }

  /* ── resultado ── */
  function showSuccess() {
    clearInterval(countdownTimer);
    progressSection.classList.remove('visible');
    resultSection.classList.add('visible');
    successState.hidden = false;
    errorState.hidden = true;
  }

  function showError(reason) {
    clearInterval(countdownTimer);
    progressSection.classList.remove('visible');
    resultSection.classList.add('visible');
    successState.hidden = true;
    errorState.hidden = false;
    errorMessage.textContent = ERROR_MESSAGES[reason] || I18N.errorGeneric;
  }

  /* ── reset ── */
  function resetUI() {
    selectedFile = null;
    mdContent = '';
    mdFilename = '';
    fileInput.value = '';
    fileInfo.hidden = true;
    timeEstimate.classList.remove('visible');
    convertBtn.disabled = true;
    clearInterval(countdownTimer);
    progressFill.className = 'progress-fill';
    progressFill.style.width = '0%';
    uploadSection.style.display = '';
    progressSection.classList.remove('visible');
    resultSection.classList.remove('visible');
  }

  /* ── download ── */
  downloadBtn.addEventListener('click', function () {
    if (!mdContent) return;
    var blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = mdFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
  });

  resetBtn.addEventListener('click', resetUI);
  errorResetBtn.addEventListener('click', resetUI);
})();
