(() => {
  'use strict';

  const meta = (name) => document.querySelector(`meta[name="astra-${name}"]`)?.content;
  const expected = {
    owner: meta('expected-owner'),
    dataset: meta('expected-dataset'),
    count: Number(meta('expected-count')),
    digest: meta('expected-sha256'),
    bindings: {
      entity: meta('binding-entity'),
      period: meta('binding-period'),
      measure: meta('binding-measure'),
      aggregation: meta('binding-aggregation'),
    },
  };
  const status = document.getElementById('client-status');
  const retry = document.getElementById('retry-load');
  const emptyState = document.getElementById('empty-state');
  const visualization = document.getElementById('visualization');
  const chartPanel = document.getElementById('chart-view');
  const tablePanel = document.getElementById('table-view');
  const chartButton = document.getElementById('show-chart');
  const tableButton = document.getElementById('show-table');
  const bindings = expected.bindings;
  const roleFields = Object.values(bindings);
  let requestVersion = 0;
  let loadScheduled = false;

  function setStatus(state, message) {
    status.dataset.state = state;
    status.textContent = message;
  }

  function clearDataView() {
    document.getElementById('chart-grid').replaceChildren();
    document.getElementById('chart-lines').replaceChildren();
    document.getElementById('chart-points').replaceChildren();
    document.getElementById('chart-labels').replaceChildren();
    document.getElementById('table-head').replaceChildren();
    document.getElementById('table-body').replaceChildren();
    visualization.hidden = true;
    emptyState.hidden = true;
    chartButton.disabled = true;
    tableButton.disabled = true;
  }

  function canonicalize(value) {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) return `[${value.map(canonicalize).join(',')}]`;
    return `{${Object.keys(value).sort().map((key) =>
      `${JSON.stringify(key)}:${canonicalize(value[key])}`
    ).join(',')}}`;
  }

  async function sha256(value) {
    if (!globalThis.crypto?.subtle || !globalThis.TextEncoder) {
      throw new Error('integrity_unavailable');
    }
    const bytes = new TextEncoder().encode(value);
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
  }

  function exactKeys(value, expectedKeys) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
    const actual = Object.keys(value).sort();
    const wanted = [...expectedKeys].sort();
    return actual.length === wanted.length && actual.every((key, index) => key === wanted[index]);
  }

  async function validateResponse(data) {
    const topLevel = [
      'source_kind', 'storage', 'owner_scope', 'dataset_id', 'count', 'rows',
      'snapshot_sha256', 'proposed_bindings', 'owner_binding_status',
      'mapping_approved', 'owner_schema_connected', 'code_generation_authorized',
      'deployment_authorized', 'generation_contract',
    ];
    if (!exactKeys(data, topLevel) || data.owner_scope !== expected.owner) {
      throw new Error('owner_mismatch');
    }
    if (data.source_kind !== 'synthetic_fixture' || data.storage !== 'sqlite_in_memory' ||
        data.dataset_id !== expected.dataset || data.owner_binding_status !== 'structurally_compatible_unapproved' ||
        data.mapping_approved !== false || data.owner_schema_connected !== false ||
        data.code_generation_authorized !== false || data.deployment_authorized !== false ||
        data.generation_contract !== 'blocked_pending_review' ||
        !exactKeys(data.proposed_bindings, ['entity_identifier', 'time_period', 'numeric_measure', 'aggregation_semantics']) ||
        data.proposed_bindings.entity_identifier !== bindings.entity ||
        data.proposed_bindings.time_period !== bindings.period ||
        data.proposed_bindings.numeric_measure !== bindings.measure ||
        data.proposed_bindings.aggregation_semantics !== bindings.aggregation ||
        !Number.isSafeInteger(data.count) || data.count < 0 || data.count !== expected.count ||
        !Array.isArray(data.rows) || data.count !== data.rows.length ||
        typeof data.snapshot_sha256 !== 'string' || data.snapshot_sha256 !== expected.digest ||
        !/^[a-f0-9]{64}$/.test(expected.digest)) {
      throw new Error('integrity_mismatch');
    }

    const seen = new Set();
    for (const row of data.rows) {
      if (!exactKeys(row, roleFields)) throw new Error('integrity_mismatch');
      const entity = row[bindings.entity];
      const period = row[bindings.period];
      const measure = row[bindings.measure];
      const aggregation = row[bindings.aggregation];
      if (typeof entity !== 'string' || entity.length === 0 || entity.length > 180 ||
          typeof aggregation !== 'string' || aggregation.length === 0 || aggregation.length > 180 ||
          typeof period !== 'string' || !/^\d{4}(?:-(?:0[1-9]|1[0-2]))?$/.test(period) ||
          typeof measure !== 'number' || !Number.isFinite(measure)) {
        throw new Error('integrity_mismatch');
      }
      const key = `${entity}\u0000${period}`;
      if (seen.has(key)) throw new Error('integrity_mismatch');
      seen.add(key);
    }

    // Hash the complete canonical row snapshot and bind it to the page shell
    // returned for this owner session. Neither count-only nor API-echoed hashes
    // are accepted as proof of an unchanged response.
    if (await sha256(canonicalize(data.rows)) !== expected.digest) {
      throw new Error('integrity_mismatch');
    }
    return data.rows;
  }

  function svgElement(name, attributes = {}) {
    const element = document.createElementNS('http://www.w3.org/2000/svg', name);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
    return element;
  }

  function renderChart(rows) {
    const grid = document.getElementById('chart-grid');
    const lines = document.getElementById('chart-lines');
    const points = document.getElementById('chart-points');
    const labels = document.getElementById('chart-labels');
    const periods = [...new Set(rows.map((row) => row[bindings.period]))].sort();
    const values = rows.map((row) => row[bindings.measure]);
    const low = Math.min(...values);
    const high = Math.max(...values);
    const span = high - low || 1;
    const xAt = (period) => 76 + (periods.indexOf(period) * 570 / Math.max(1, periods.length - 1));
    const yAt = (value) => 250 - ((value - low) / span * 190);
    const palette = ['#315fc3', '#16836b', '#9a5ea8', '#c46b28', '#536b83', '#b34f62'];
    const groups = new Map();
    rows.forEach((row) => {
      const entity = row[bindings.entity];
      if (!groups.has(entity)) groups.set(entity, []);
      groups.get(entity).push(row);
    });

    [0, 1, 2, 3].forEach((step) => {
      const y = 58 + step * 64;
      grid.append(svgElement('line', { x1: 66, x2: 665, y1: y, y2: y, stroke: '#dfe6ef', 'stroke-width': 1 }));
    });
    periods.forEach((period) => {
      const tick = svgElement('text', { x: xAt(period), y: 286, 'text-anchor': 'middle', fill: '#53647d', 'font-size': 12 });
      tick.textContent = period;
      labels.append(tick);
    });
    [...groups.entries()].forEach(([entity, entityRows], groupIndex) => {
      const color = palette[groupIndex % palette.length];
      const ordered = [...entityRows].sort((left, right) => left[bindings.period].localeCompare(right[bindings.period]));
      if (ordered.length > 1) {
        const polyline = svgElement('polyline', {
          points: ordered.map((row) => `${xAt(row[bindings.period])},${yAt(row[bindings.measure])}`).join(' '),
          fill: 'none', stroke: color, 'stroke-width': 2.5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round',
        });
        polyline.setAttribute('aria-label', entity);
        lines.append(polyline);
      }
      ordered.forEach((row) => {
        const circle = svgElement('circle', {
          cx: xAt(row[bindings.period]), cy: yAt(row[bindings.measure]), r: 5,
          fill: color, stroke: '#fff', 'stroke-width': 2,
        });
        const title = svgElement('title');
        title.textContent = `${entity} · ${row[bindings.period]} · ${row[bindings.measure]}`;
        circle.append(title);
        points.append(circle);
      });
    });
  }

  function renderTable(rows) {
    const headings = [bindings.entity, bindings.period, bindings.measure, bindings.aggregation];
    const head = document.getElementById('table-head');
    const body = document.getElementById('table-body');
    headings.forEach((field) => {
      const cell = document.createElement('th');
      cell.scope = 'col';
      cell.textContent = field;
      head.append(cell);
    });
    rows.forEach((row) => {
      const tr = document.createElement('tr');
      headings.forEach((field) => {
        const cell = document.createElement('td');
        cell.textContent = String(row[field]);
        tr.append(cell);
      });
      body.append(tr);
    });
  }

  function setMode(mode) {
    const chart = mode === 'chart';
    chartPanel.hidden = !chart;
    tablePanel.hidden = chart;
    chartButton.setAttribute('aria-selected', String(chart));
    tableButton.setAttribute('aria-selected', String(!chart));
  }

  function bindModeControls() {
    chartButton.addEventListener('click', () => setMode('chart'));
    tableButton.addEventListener('click', () => setMode('table'));
    [chartButton, tableButton].forEach((button) => button.addEventListener('keydown', (event) => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      const next = button === chartButton ? tableButton : chartButton;
      setMode(next === chartButton ? 'chart' : 'table');
      next.focus();
    }));
  }

  function loadData() {
    if (loadScheduled) return;
    loadScheduled = true;
    queueMicrotask(() => {
      loadScheduled = false;
      void fetchAndRender();
    });
  }

  async function fetchAndRender() {
    const version = ++requestVersion;
    clearDataView();
    retry.setAttribute('aria-busy', 'true');
    setStatus('loading', '합성 소유자 API를 불러오는 중입니다.');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch('/api/demo/series', {
        cache: 'no-store', credentials: 'same-origin', signal: controller.signal,
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) throw new Error('api_unavailable');
      const data = await response.json();
      const rows = await validateResponse(data);
      if (version !== requestVersion) return;
      if (rows.length === 0) {
        emptyState.hidden = false;
        setStatus('empty', '데이터를 성공적으로 확인했지만 표시할 행이 없습니다.');
        return;
      }
      renderChart(rows);
      renderTable(rows);
      visualization.hidden = false;
      chartButton.disabled = false;
      tableButton.disabled = false;
      setMode('chart');
      setStatus('success', `${rows.length}개의 합성 행을 검증하고 화면에 표시했습니다.`);
    } catch (error) {
      if (version !== requestVersion) return;
      clearDataView();
      if (error?.message === 'owner_mismatch') {
        setStatus('error', '응답 소유자 정보가 이 화면과 달라 데이터를 표시하지 않았습니다.');
      } else if (error?.message === 'integrity_mismatch' || error?.message === 'integrity_unavailable') {
        setStatus('error', 'API 응답의 무결성을 확인하지 못했습니다. 데이터를 표시하지 않았습니다.');
      } else {
        setStatus('error', 'API 요청에 실패했습니다. 네트워크를 확인한 뒤 다시 시도하세요.');
      }
    } finally {
      clearTimeout(timeout);
      if (version === requestVersion) retry.removeAttribute('aria-busy');
    }
  }

  if (!expected.owner || !expected.dataset || !Number.isSafeInteger(expected.count) ||
      expected.count < 0 || !/^[a-f0-9]{64}$/.test(expected.digest) ||
      roleFields.some((field) => !field) || new Set(roleFields).size !== 4) {
    setStatus('error', '화면의 검증 기준이 올바르지 않습니다.');
    return;
  }
  bindModeControls();
  retry.addEventListener('click', loadData);
  loadData();
})();
