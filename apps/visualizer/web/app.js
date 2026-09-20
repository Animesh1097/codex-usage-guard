(() => {
  const shell = document.querySelector('.shell');
  const actionsBar = document.querySelector('#actionsBar');
  const turnsBar = document.querySelector('#turnsBar');
  const actionsValue = document.querySelector('#actionsValue');
  const turnsValue = document.querySelector('#turnsValue');
  const tokensValue = document.querySelector('#tokensValue');
  const liveStatus = document.querySelector('#liveStatus');
  const phaseSteps = [...document.querySelectorAll('.phase-rail i')];
  const statusLight = document.querySelector('.status-light');

  const phaseOrder = ['analyze', 'plan', 'work', 'verify'];
  const phaseAliases = { route: 'plan', judge: 'plan', execute: 'work' };
  let lastAnnouncement = '';

  const percent = (used, limit) => limit > 0 ? Math.min(100, Math.max(0, (used / limit) * 100)) : 0;
  const formatTokens = value => Number.isFinite(value) ? new Intl.NumberFormat().format(value) : '—';

  function normalizePhase(snapshot) {
    if (snapshot.status === 'completed') return 'complete';
    if (['failed', 'blocked', 'abandoned'].includes(snapshot.status)) return 'failed';
    const phase = phaseAliases[snapshot.phase] || snapshot.phase || 'analyze';
    return ['analyze', 'plan', 'work', 'verify', 'complete', 'failed'].includes(phase) ? phase : 'analyze';
  }

  function render(snapshot) {
    const phase = normalizePhase(snapshot);
    shell.dataset.phase = phase;
    shell.dataset.kind = snapshot.taskKind || 'general';

    actionsValue.textContent = `${snapshot.actionsUsed} / ${snapshot.actionsLimit}`;
    turnsValue.textContent = `${snapshot.turnsUsed} / ${snapshot.turnsLimit}`;
    actionsBar.style.width = `${percent(snapshot.actionsUsed, snapshot.actionsLimit)}%`;
    turnsBar.style.width = `${percent(snapshot.turnsUsed, snapshot.turnsLimit)}%`;
    tokensValue.textContent = formatTokens(snapshot.tokenDelta);

    const effective = phase === 'complete' ? 'verify' : phase;
    const activeIndex = Math.max(0, phaseOrder.indexOf(effective));
    phaseSteps.forEach((step, index) => {
      const active = index <= activeIndex;
      step.style.background = active ? 'var(--accent)' : '#122235';
      step.style.borderColor = active ? 'var(--accent)' : '#40576d';
      step.style.boxShadow = index === activeIndex ? '0 0 14px var(--accent)' : 'none';
    });

    statusLight.style.background = phase === 'failed' ? 'var(--danger)' : phase === 'complete' ? 'var(--success)' : 'var(--accent)';

    const announcement = `${phase}. ${snapshot.activity || ''}`;
    if (announcement !== lastAnnouncement) {
      liveStatus.textContent = announcement;
      lastAnnouncement = announcement;
    }
  }

  async function readSnapshot() {
    try {
      const invoke = window.__TAURI__?.core?.invoke;
      if (!invoke) return;
      const snapshot = await invoke('get_task_snapshot');
      render(snapshot);
    } catch (_) {
      // The visualizer is deliberately non-critical. Core work continues if this view cannot refresh.
    }
  }

  readSnapshot();
  setInterval(readSnapshot, 250);
})();
