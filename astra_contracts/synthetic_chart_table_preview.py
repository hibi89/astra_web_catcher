"""Generate an offline, read-only Chart/Table HTML preview from synthetic rows.

This is an original demonstration of the observed *presentation idea* only. It is
not a reconstruction of OWID formulas/data, an owner schema migration, or an
implementation authorization. Optional --archive links a strictly pinned public
interaction observation via the existing review-only bridge.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from pathlib import Path

from astra_contracts.synthetic_timeseries_review import review
from astra_contracts.chart_table_synthetic_bridge import combined_review

MAX_ROWS = 240
MAX_ENTITIES = 10
MAX_PERIODS = 24
COLORS = ('#136b93', '#d45a31', '#5d50a2', '#2b8060', '#ad397e',
          '#a46a23', '#257c83', '#735625', '#765fbd', '#b74242')
PERIOD = re.compile(r'^(\d{4})(?:-(\d{2}))?$')


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _safe_rows(schema: dict, rows: list[dict]) -> tuple[list[dict], list[str], list[str], str]:
    """Validate typed synthetic data, not only a structurally compatible schema."""
    mapping = review(schema)
    if mapping['missing_or_incompatible']:
        raise ValueError('missing or incompatible explicit mappings: ' + ', '.join(mapping['missing_or_incompatible']))
    if not isinstance(rows, list) or not (1 <= len(rows) <= MAX_ROWS):
        raise ValueError('preview requires 1..240 synthetic rows')
    columns = {col['name']: col['kind'] for col in schema['columns']}
    bindings = schema['proposed_bindings']
    id_col, time_col, val_col, method_col = (bindings[r] for r in (
        'entity_identifier', 'time_period', 'numeric_measure', 'aggregation_semantics'))
    if len(set((id_col, time_col, val_col, method_col))) != 4:
        raise ValueError('four semantic roles must bind to distinct columns')
    normalized = []
    keys = set(columns)
    for row in rows:
        if not isinstance(row, dict) or set(row) != keys:
            raise ValueError('row does not exactly match declared synthetic columns')
        for field, kind in columns.items():
            value = row[field]
            if kind == 'string':
                if not isinstance(value, str) or not 1 <= len(value.strip()) <= 80:
                    raise ValueError('invalid or empty string value')
            elif kind == 'boolean':
                if type(value) is not bool:
                    raise ValueError('expected boolean value')
            elif kind == 'integer':
                if type(value) is not int or abs(value) > 1_000_000_000:
                    raise ValueError('expected bounded integer value')
            elif kind == 'number':
                if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1_000_000_000:
                    raise ValueError('expected finite bounded numeric value')
        period = row[time_col]
        parsed = PERIOD.fullmatch(period)
        if not parsed or parsed.group(1) == '0000' or (parsed.group(2) is not None
                and not 1 <= int(parsed.group(2)) <= 12):
            raise ValueError('time periods must be ISO YYYY or YYYY-MM')
        normalized.append(row)
    grains = {len(row[time_col]) for row in normalized}
    if len(grains) != 1:
        raise ValueError('mixed time period granularities not supported')
    methods = {row[method_col] for row in normalized}
    if len(methods) != 1:
        raise ValueError('mixed aggregation definitions not supported')
    entities = sorted({row[id_col] for row in normalized})
    periods = sorted({row[time_col] for row in normalized})
    if len(entities) > MAX_ENTITIES or len(periods) > MAX_PERIODS:
        raise ValueError('preview exceeds 10 entities or 24 periods')
    pairs = [(row[id_col], row[time_col]) for row in normalized]
    if len(set(pairs)) != len(pairs):
        raise ValueError('duplicate entity/time-period combination')
    normalized.sort(key=lambda row: (row[time_col], row[id_col]))
    return normalized, entities, periods, methods.pop()


def _chart_svg(rows: list[dict], entities: list[str], periods: list[str], bindings: dict) -> str:
    id_col, time_col, value_col = (bindings[k] for k in ('entity_identifier', 'time_period', 'numeric_measure'))
    width, height = 960, 410
    left, top, plot_width, plot_height = 90, 24, 818, 310
    measures = [float(row[value_col]) for row in rows]
    low, high = min(measures), max(measures)
    pad = (high - low) * .08 if high != low else max(abs(high) * .08, 1)
    bottom, ceiling = low - pad, high + pad
    def x(period: str) -> float:
        return left + (periods.index(period) / (len(periods) - 1) if len(periods) > 1 else .5) * plot_width
    def y(value: float) -> float:
        return top + (ceiling - value) / (ceiling - bottom) * plot_height
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Synthetic numeric measure by period and entity">',
             '<title>Synthetic time-series chart; unapproved test data only</title>']
    for index in range(5):
        val = bottom + (ceiling - bottom) * index / 4
        yy = y(val)
        parts.append(f'<line x1="{left}" y1="{yy:.2f}" x2="{left+plot_width}" y2="{yy:.2f}" stroke="#d6dfeb"/>')
        parts.append(f'<text x="{left-10}" y="{yy+4:.2f}" text-anchor="end" class="tick">{_escape(format(val, ".4g"))}</text>')
    tick_stride = max(1, math.ceil(len(periods) / 9))
    for index, period in enumerate(periods):
        if index % tick_stride == 0 or index == len(periods)-1:
            parts.append(f'<text x="{x(period):.2f}" y="{top+plot_height+24}" text-anchor="middle" class="tick">{_escape(period)}</text>')
    by_entity = {(row[id_col], row[time_col]): float(row[value_col]) for row in rows}
    for index, entity in enumerate(entities):
        color = COLORS[index]
        for left_period, right_period in zip(periods, periods[1:]):
            if (entity, left_period) in by_entity and (entity, right_period) in by_entity:
                parts.append(f'<line x1="{x(left_period):.2f}" y1="{y(by_entity[entity,left_period]):.2f}" '
                             f'x2="{x(right_period):.2f}" y2="{y(by_entity[entity,right_period]):.2f}" '
                             f'stroke="{color}" stroke-width="3"/>')
        for period in periods:
            if (entity, period) in by_entity:
                parts.append(f'<circle cx="{x(period):.2f}" cy="{y(by_entity[entity,period]):.2f}" r="4" fill="{color}"/>')
    parts.append('</svg>')
    return ''.join(parts)


def render_preview(schema: dict, rows: list[dict], *, archive: Path | None = None) -> str:
    """Build static offline HTML; --archive additionally verifies immutable observation proof."""
    # Run strict proof validation before any preview construction when requested.
    linked_proof = combined_review(Path(archive), schema) if archive is not None else None
    normalized, entities, periods, method = _safe_rows(schema, rows)
    bindings = schema['proposed_bindings']
    id_col, time_col, value_col, method_col = (bindings[r] for r in (
        'entity_identifier', 'time_period', 'numeric_measure', 'aggregation_semantics'))
    svg = _chart_svg(normalized, entities, periods, bindings)
    table = ''.join('<tr>' + ''.join(f'<td>{_escape(value)}</td>' for value in (
        row[id_col], row[time_col], format(row[value_col], '.8g'), row[method_col])) + '</tr>' for row in normalized)
    legend = ''.join(f'<span class="legend-item"><i style="background:{COLORS[index]}"></i>{_escape(entity)}</span>'
                     for index, entity in enumerate(entities))
    proof = ('Pinned public UI evidence integrity verified locally; source formulas remain unverified.'
             if linked_proof else 'Original public UI evidence not supplied for this preview.')
    # All dynamic text is escaped; only constant script/style is inserted.
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>ASTRA synthetic Chart / Table preview</title>
<style>
:root{{font-family:system-ui,-apple-system,sans-serif;color:#16283b;background:#f3f6fb}}
body{{margin:0;padding:2.5rem 1rem}}main{{max-width:1080px;margin:auto;background:white;border:1px solid #d6e0ed;border-radius:16px;padding:2rem;box-shadow:0 8px 35px #142b4214}}
h1{{font-size:1.65rem;margin:0 0 .5rem}}p{{line-height:1.5}}.note{{font-size:.88rem;color:#496176}}.status{{color:#8a4a20;font-weight:700}}
button{{background:#eaf0f7;border:1px solid #bcccdc;border-radius:8px;color:#173954;padding:.65rem 1.25rem;margin-right:.5rem;cursor:pointer}}
button[aria-pressed="true"]{{background:#144f79;color:white;border-color:#144f79}}button:focus-visible{{outline:3px solid #d07d34;outline-offset:2px}}
.view{{margin-top:1.25rem;overflow:auto}}svg{{width:100%;min-width:600px;height:auto}}.tick{{font-size:12px;fill:#60748a}}
.legend{{display:flex;flex-wrap:wrap;gap:.7rem 1.25rem;margin-top:1rem}}.legend-item{{display:inline-flex;align-items:center;gap:.4rem;font-size:.84rem}}.legend-item i{{display:inline-block;width:10px;height:10px;border-radius:50%}}
table{{border-collapse:collapse;width:100%;min-width:530px}}th,td{{padding:.7rem;border-bottom:1px solid #d9e1eb;text-align:left}}thead{{background:#eaf0f7}}tr:hover{{background:#f5f8fc}}
[hidden]{{display:none!important}}
</style></head><body><main>
<h1>ASTRA — synthetic Chart / Table preview</h1>
<p class="status">SYNTHETIC DATA · REVIEW ONLY · NOT AUTHORIZED FOR GENERATION OR DEPLOYMENT</p>
<p>Dataset: <strong>{_escape(schema['dataset_id'])}</strong> · {len(normalized)} synthetic rows · {len(entities)} entities · {len(periods)} periods</p>
<p class="note">Metric calculation: unverified. Declared aggregation label: {_escape(method)}. Structural field matches are unapproved. This is not an OWID data reproduction.</p>
<div aria-label="Presentation mode"><button type="button" id="show-chart" aria-controls="chart-view" aria-pressed="true">Chart</button><button type="button" id="show-table" aria-controls="table-view" aria-pressed="false">Table</button></div>
<section class="view" id="chart-view" aria-label="Chart presentation">{svg}<div class="legend">{legend}</div></section>
<section class="view" id="table-view" aria-label="Table presentation" hidden><table><thead><tr><th scope="col">Entity</th><th scope="col">Period</th><th scope="col">Value</th><th scope="col">Aggregation label</th></tr></thead><tbody>{table}</tbody></table></section>
<p class="note">{_escape(proof)} Network: none. Owner DB: disconnected. Implementation approval: false.</p>
</main><script>
'use strict';
const chartButton=document.getElementById('show-chart');
const tableButton=document.getElementById('show-table');
const chart=document.getElementById('chart-view');
const table=document.getElementById('table-view');
function show(mode){{const isChart=mode==='chart';chart.hidden=!isChart;table.hidden=isChart;chartButton.setAttribute('aria-pressed',String(isChart));tableButton.setAttribute('aria-pressed',String(!isChart));}}
chartButton.addEventListener('click',()=>show('chart'));
tableButton.addEventListener('click',()=>show('table'));
</script></body></html>'''


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Explicitly create an offline synthetic chart/table preview')
    parser.add_argument('--fixture', required=True, type=Path, help='Synthetic-only schema JSON')
    parser.add_argument('--rows', required=True, type=Path, help='Synthetic-only JSON array')
    parser.add_argument('--archive', type=Path, help='Optional immutable OWID proof ZIP')
    parser.add_argument('--output', required=True, type=Path, help='New offline HTML file (will not overwrite)')
    args = parser.parse_args(argv)
    try:
        schema = json.loads(args.fixture.read_text(encoding='utf-8'))
        rows = json.loads(args.rows.read_text(encoding='utf-8'))
        markup = render_preview(schema, rows, archive=args.archive)
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(markup)
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(f'Generated synthetic-only preview: {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
