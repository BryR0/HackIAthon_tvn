/**
 * Señal TVN - Controlador Front-End en Vanilla JS (Sin dependencias externas ni CDN)
 * Cumple con CSP default-src 'self' y funcionamiento 100% offline (T10).
 * Manejo accesible de modales, tour interactivo paso a paso y micro-animaciones.
 */

(function () {
  'use strict';

  // =========================================================================
  // Control de Modales Accesibles
  // =========================================================================

  function abrirModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add('activo');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    // Foco automático en el primer elemento interactivo
    const focusable = modal.querySelector('button, [href], input, select, textarea');
    if (focusable) focusable.focus();
  }

  function cerrarModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.remove('activo');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  function cerrarModalActivo() {
    const activo = document.querySelector('.modal-dialog.activo');
    if (activo) {
      cerrarModal(activo.id);
    }
  }

  // Delegación de eventos para botones de apertura y cierre
  document.addEventListener('click', function (evento) {
    const btnAbre = evento.target.closest('[data-abre-modal]');
    if (btnAbre) {
      evento.preventDefault();
      const modalId = btnAbre.getAttribute('data-abre-modal');
      abrirModal(modalId);
      return;
    }

    const btnCierra = evento.target.closest('[data-cierra-modal]');
    if (btnCierra) {
      evento.preventDefault();
      const modalId = btnCierra.getAttribute('data-cierra-modal');
      cerrarModal(modalId);
      return;
    }

    // Cierre al hacer click en el backdrop oscuro
    if (evento.target.classList.contains('modal-dialog')) {
      cerrarModal(evento.target.id);
    }
  });

  // Cierre con la tecla Escape y atajo de búsqueda rápida
  document.addEventListener('keydown', function (evento) {
    if (evento.key === 'Escape') {
      cerrarModalActivo();
    }
    // Atajo "/" o "Ctrl+K" para abrir modal de consulta rápida si no se está escribiendo
    if ((evento.key === '/' || (evento.key === 'k' && (evento.ctrlKey || evento.metaKey))) &&
        !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
      evento.preventDefault();
      abrirModal('modal-consulta');
    }
  });

  // =========================================================================
  // Tour Guiado Interactivo Paso a Paso (Inspirado en Next.js GuidedTourModal)
  // =========================================================================

  const PASOS_TOUR = [
    {
      paso: 1,
      titulo: '1. Agrupamiento de Señales',
      tag: 'Triage & Ingesta Automática',
      subtitulo: 'Monitoreo de medios en tiempo real',
      descripcion: 'El sistema agrupa noticias de múltiples medios panameños por similitud semántica y temporal, evitando duplicados y detectando la primera aparición de cada evento noticioso.',
      tip: 'Cobertura de Panamá: agencias y titulares replicados se contabilizan una sola vez para medir procedencias independientes.',
      svg: '<svg width="84" height="84" viewBox="0 0 120 120" fill="none"><circle cx="60" cy="60" r="54" fill="#eff6ff"/><rect x="28" y="28" width="64" height="64" rx="14" fill="#ffffff" stroke="#2563eb" stroke-width="3"/><circle cx="60" cy="50" r="12" fill="#2563eb"/><path d="M42 84 C42 72, 78 72, 78 84" stroke="#2563eb" stroke-width="3" stroke-linecap="round"/><circle cx="82" cy="38" r="8" fill="#059669"/><path d="M79 38 L81 40 L85 36" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>'
    },
    {
      paso: 2,
      titulo: '2. Ponderación Multidimensional',
      tag: 'Motor Clínico-Periodístico',
      subtitulo: 'Prioridad matemática auditable',
      descripcion: 'Aplica la fórmula ponderada P = 30R + 25I + 20U + 15N + 10E (Relevancia, Impacto, Urgencia, Novedad y Evidencia). Los desempates se resuelven por mayor urgencia y luego por identificador de evento.',
      tip: 'Cero cajas negras: cada peso responde a reglas versionadas e invariantes para garantizar imparcialidad.',
      svg: '<svg width="84" height="84" viewBox="0 0 120 120" fill="none"><circle cx="60" cy="60" r="54" fill="#fffbeb"/><rect x="30" y="34" width="60" height="52" rx="10" fill="#ffffff" stroke="#d97706" stroke-width="3"/><line x1="42" y1="48" x2="78" y2="48" stroke="#2563eb" stroke-width="3" stroke-linecap="round"/><line x1="42" y1="60" x2="68" y2="60" stroke="#059669" stroke-width="3" stroke-linecap="round"/><line x1="42" y1="72" x2="74" y2="72" stroke="#d97706" stroke-width="3" stroke-linecap="round"/><circle cx="84" cy="82" r="14" fill="#2563eb"/><text x="84" y="87" text-anchor="middle" fill="#fff" font-size="12" font-weight="bold" font-family="sans-serif">Σ</text></svg>'
    },
    {
      paso: 3,
      titulo: '3. Verificación y Flujo Humano',
      tag: 'Políticas Anti-Alucinación',
      subtitulo: 'Fuentes oficiales y control editorial',
      descripcion: 'Cruza datos con fuentes oficiales (Banco Mundial, INEC, sismos del USGS). Toda cifra en conflicto se señala explícitamente y ningún borrador se publica sin la revisión de un editor humano.',
      tip: 'Garantía TVN: La IA redacta y valida citas; la persona revisora aprueba o descarta con firma registrada.',
      svg: '<svg width="84" height="84" viewBox="0 0 120 120" fill="none"><circle cx="60" cy="60" r="54" fill="#ecfdf5"/><rect x="32" y="26" width="56" height="68" rx="10" fill="#ffffff" stroke="#059669" stroke-width="3"/><circle cx="60" cy="58" r="18" fill="#059669"/><path d="M53 58 L57 62 L67 52" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/><line x1="44" y1="38" x2="76" y2="38" stroke="#cbd5e1" stroke-width="2.5" stroke-linecap="round"/></svg>'
    }
  ];

  let pasoActual = 0;

  function renderizarPasoTour(indice) {
    pasoActual = Math.max(0, Math.min(PASOS_TOUR.length - 1, indice));
    const p = PASOS_TOUR[pasoActual];

    const numBadge = document.getElementById('tour-paso-badge');
    const subtitulo = document.getElementById('tour-subtitulo');
    const ilustracion = document.getElementById('tour-ilustracion');
    const tag = document.getElementById('tour-tag');
    const titulo = document.getElementById('tour-titulo');
    const descripcion = document.getElementById('tour-descripcion');
    const tip = document.getElementById('tour-tip');
    const btnAnt = document.getElementById('tour-btn-anterior');
    const btnSig = document.getElementById('tour-btn-siguiente');
    const puntos = document.querySelectorAll('.tour-punto');

    if (numBadge) numBadge.textContent = p.paso;
    if (subtitulo) subtitulo.textContent = `Guía interactiva · ${p.paso} de ${PASOS_TOUR.length}`;
    if (ilustracion) ilustracion.innerHTML = p.svg;
    if (tag) tag.textContent = p.tag;
    if (titulo) titulo.textContent = p.titulo;
    if (descripcion) descripcion.textContent = p.descripcion;
    if (tip) tip.textContent = p.tip;

    if (btnAnt) {
      btnAnt.disabled = pasoActual === 0;
    }

    if (btnSig) {
      if (pasoActual === PASOS_TOUR.length - 1) {
        btnSig.textContent = 'Comenzar a explorar';
      } else {
        btnSig.textContent = 'Siguiente →';
      }
    }

    puntos.forEach((pto, idx) => {
      if (idx === pasoActual) {
        pto.classList.add('activo');
      } else {
        pto.classList.remove('activo');
      }
    });
  }

  // Controles de navegación del tour
  document.addEventListener('DOMContentLoaded', function () {
    renderizarPasoTour(0);

    const btnAnt = document.getElementById('tour-btn-anterior');
    if (btnAnt) {
      btnAnt.addEventListener('click', function () {
        renderizarPasoTour(pasoActual - 1);
      });
    }

    const btnSig = document.getElementById('tour-btn-siguiente');
    if (btnSig) {
      btnSig.addEventListener('click', function () {
        if (pasoActual >= PASOS_TOUR.length - 1) {
          cerrarModal('modal-tour');
        } else {
          renderizarPasoTour(pasoActual + 1);
        }
      });
    }

    const puntos = document.querySelectorAll('.tour-punto');
    puntos.forEach((pto, idx) => {
      pto.addEventListener('click', function () {
        renderizarPasoTour(idx);
      });
    });

    // Indicador animado de progreso al enviar formularios y control de doble envío
    const forms = document.querySelectorAll('form');
    let envioEnCurso = false;

    function activarEstadoCarga(form, chipActivo) {
      if (envioEnCurso) return false;
      envioEnCurso = true;

      form.classList.add('form-submitting');

      // Indicador explícito de consulta RAG si existe
      const loadingIndicator = document.getElementById('consulta-loading-indicator');
      if (loadingIndicator) {
        loadingIndicator.style.display = 'flex';
      }

      // Deshabilitar todos los chips para prevenir spam de clics
      const allChips = document.querySelectorAll('.chip-consulta');
      allChips.forEach(function (c) {
        c.disabled = true;
        c.classList.add('chip-disabled');
      });

      if (chipActivo) {
        chipActivo.classList.add('chip-loading');
        chipActivo.innerHTML = '<span class="chip-spinner"></span> <span>Consultando...</span>';
      }

      // Botón submit
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        const textoOriginal = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-btn-inline"></span> <span>Consultando...</span>';

        // Restaurar en caso de cancelación o respuesta abortada tras timeout
        setTimeout(function () {
          envioEnCurso = false;
          submitBtn.disabled = false;
          submitBtn.innerHTML = textoOriginal;
          form.classList.remove('form-submitting');
          if (loadingIndicator) loadingIndicator.style.display = 'none';
          allChips.forEach(function (c) {
            c.disabled = false;
            c.classList.remove('chip-disabled');
            c.classList.remove('chip-loading');
          });
        }, 35000);
      }
      return true;
    }

    forms.forEach(function (form) {
      form.addEventListener('submit', function (e) {
        if (envioEnCurso) {
          e.preventDefault();
          return false;
        }
        activarEstadoCarga(form, null);
      });
    });

    // Ejecución directa de pruebas rápidas en /consulta con feedback visual
    const chipsConsulta = document.querySelectorAll('.chip-consulta[data-consulta]');
    chipsConsulta.forEach(function (chip) {
      chip.addEventListener('click', function (e) {
        e.preventDefault();
        if (envioEnCurso) return;

        const form = document.querySelector('form.rag-command-card') || this.closest('form') || document.querySelector('form[action="/consulta"]');
        if (!form) return;

        const consultaTexto = this.getAttribute('data-consulta') || '';
        const modalidad = this.getAttribute('data-modalidad') || '';

        const inputConsulta = form.querySelector('input[name="q"]');
        if (inputConsulta) {
          inputConsulta.value = consultaTexto;
        }

        if (modalidad) {
          let inputMod = form.querySelector('input[name="modalidad"]');
          if (!inputMod) {
            inputMod = document.createElement('input');
            inputMod.type = 'hidden';
            inputMod.name = 'modalidad';
            form.appendChild(inputMod);
          }
          inputMod.value = modalidad;
        }

        if (activarEstadoCarga(form, chip)) {
          if (typeof form.requestSubmit === 'function') {
            form.requestSubmit();
          } else {
            form.submit();
          }
        }
      });
    });

    // Rellenado rápido en chips de sugerencia (modales)
    const chipsSugerida = document.querySelectorAll('[data-consulta-sugerida]');
    chipsSugerida.forEach(function (chip) {
      chip.addEventListener('click', function (e) {
        e.preventDefault();
        const form = this.closest('form') || document;
        const inputConsulta = form.querySelector('input[name="q"]') || document.querySelector('input[name="q"]');
        if (inputConsulta) {
          inputConsulta.value = this.getAttribute('data-consulta-sugerida');
          inputConsulta.focus();
        }
      });
    });

    // Filtrado instantáneo en vivo de filas en la bandeja
    const inputBusquedaRapida = document.getElementById('f-busqueda');
    if (inputBusquedaRapida) {
      inputBusquedaRapida.addEventListener('input', function () {
        const query = this.value.toLowerCase().trim();
        const filas = document.querySelectorAll('.tvn-row-item');
        filas.forEach(function (fila) {
          if (!query) {
            fila.style.display = '';
            return;
          }
          const texto = fila.textContent.toLowerCase();
          fila.style.display = texto.includes(query) ? '' : 'none';
        });
      });
    }
  });

  // Exponer API global
  window.SenalUI = {
    abrirModal: abrirModal,
    cerrarModal: cerrarModal,
    irAPasoTour: renderizarPasoTour
  };

})();
