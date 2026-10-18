"""Review opinions are explicitly NOT permission grants or verified consent."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from astra_contracts.data_mapping import MappingReport, OwnedSchemaDeclaration, compare_mappings
from astra_contracts.functional_spec import FunctionalSpecDraft
from astra_contracts.generation_contract import fingerprint
from astra_contracts.reviewer_decisions import (
    ReviewPacket, ReviewRecord, ReviewSubmission, build_packet, record_opinions, main,
)

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'fixtures'
SPEC = F / 'jp_nail_functional_spec_draft_20261018.json'
SCHEMA = F / 'synthetic_owned_schema_mapping_20261018.json'
MAPPING = F / 'synthetic_mapping_report_20261018.json'
PACKET = F / 'synthetic_review_packet_20261018.json'


def inputs():
    return (FunctionalSpecDraft.model_validate_json(SPEC.read_text()),
            OwnedSchemaDeclaration.model_validate_json(SCHEMA.read_text()),
            MappingReport.model_validate_json(MAPPING.read_text()))


def packet():
    return build_packet(*inputs())


def decision_for(kind, decision='needs_more_evidence', field=None, **updates):
    item = next(x for x in packet().items if x.kind.value == kind and (field is None or x.field_name == field))
    result = {'item_id': item.item_id, 'decision': decision,
              'rationale': 'Manual review requires more direct evidence.'}
    result.update(updates)
    return result


def submit(*decisions):
    return ReviewSubmission.model_validate({
        'version': '0.1', 'packet_sha256': fingerprint(packet()),
        'reviewer_claimed_label': 'Example reviewer, unverified',
        'responses': list(decisions),
    })


def test_packet_counts_provenance_and_golden_example():
    p = packet()
    assert len(p.items) == 13
    assert sum(x.kind.value == 'observed_behavior' for x in p.items) == 1
    assert sum(x.kind.value == 'unresolved_behavior' for x in p.items) == 2
    assert sum(x.kind.value == 'field_semantics' for x in p.items) == 10
    assert p == ReviewPacket.model_validate_json(PACKET.read_text())
    assert p.status == 'pending_human_review'
    assert not p.approval_verified and not p.implementation_ready
    assert len(set(x.item_id for x in p.items)) == 13


def test_archive_only_is_not_presented_as_direct_browser_evidence():
    observed = next(x for x in packet().items if x.kind.value == 'observed_behavior')
    assert observed.archived_evidence_only
    assert observed.evidence_refs == ['evidence/jp_nail_brand_filter_source_20261018.md']


def test_all_mapping_fields_and_reasons_are_in_review_packet():
    fields = {x.field_name: x for x in packet().items if x.kind.value == 'field_semantics'}
    assert len(fields) == 10
    assert fields['analyzed_posts'].mapping_status == 'structurally_compatible_unapproved'
    assert fields['average_reactions_displayed'].mapping_status == 'type_conflict'
    assert fields['reported_reels_percent'].mapping_status == 'unmapped'
    assert fields['sheet_posts'].mapping_status == 'missing_resource_field'


def test_one_decision_is_a_claimed_opinion_and_12_remain_pending():
    result = record_opinions(packet(), submit(decision_for('field_semantics', field='average_reactions_displayed')))
    assert result.recorded_opinion_count == 1 and result.pending_count == 12
    assert result.reviewer_claimed_label == 'Example reviewer, unverified'
    assert sum(x.review_state == 'recorded_opinion' for x in result.items) == 1
    assert result.status == 'opinion_record_only_not_authorization'
    assert not result.reviewer_identity_verified and not result.user_approval_verified


def test_packet_is_deterministic_without_timestamp_or_network():
    assert packet().model_dump_json() == packet().model_dump_json()
    assert len(fingerprint(packet())) == 64


def test_stale_packet_fingerprint_rejected():
    resp = submit(decision_for('unresolved_behavior'))
    altered = resp.model_dump(mode='json')
    altered['packet_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='mismatched'):
        record_opinions(packet(), ReviewSubmission.model_validate(altered))


def test_changed_spec_recomputes_packet_and_rejects_old_submission():
    spec, schema, report = inputs()
    changed = spec.model_copy(deep=True)
    changed.candidate_features[0].claim = 'Another recorded claim'
    changed_report = compare_mappings(changed, schema)
    new_packet = build_packet(changed, schema, changed_report)
    with pytest.raises(ValueError, match='stale'):
        record_opinions(new_packet, submit(decision_for('unresolved_behavior')))


def test_report_tampering_rejected_before_human_review():
    spec, schema, report = inputs()
    altered = report.model_copy(deep=True)
    altered.findings[0].status = 'unmapped'
    with pytest.raises(ValueError, match='mapping report differs'):
        build_packet(spec, schema, altered)


def test_duplicate_response_rejected():
    d = decision_for('unresolved_behavior')
    with pytest.raises(ValidationError, match='duplicate review response'):
        submit(d, copy.deepcopy(d))


def test_missing_item_id_rejected():
    d = decision_for('unresolved_behavior')
    d['item_id'] = 'made-up:id'
    with pytest.raises(ValueError, match='nonexistent item'):
        record_opinions(packet(), submit(d))


def test_unknown_behavior_cannot_be_marked_supported():
    with pytest.raises(ValueError, match='unknown behavior'):
        record_opinions(packet(), submit(decision_for('unresolved_behavior','supported_as_proposal')))


def test_missing_or_conflicting_mapping_cannot_be_marked_supported():
    with pytest.raises(ValueError, match='mapping cannot'):
        record_opinions(packet(), submit(decision_for('field_semantics','supported_as_proposal',field='average_reactions_displayed')))


def test_unbound_mapping_cannot_be_marked_supported():
    with pytest.raises(ValueError, match='mapping cannot'):
        record_opinions(packet(), submit(decision_for('field_semantics','supported_as_proposal',field='reported_reels_percent')))


def test_archive_only_observation_not_supported_as_proposal():
    with pytest.raises(ValueError, match='archived report'):
        record_opinions(packet(), submit(decision_for('observed_behavior','supported_as_proposal')))


def test_compatible_mapping_still_never_grants_approval():
    d = decision_for('field_semantics','supported_as_proposal',field='analyzed_posts')
    result = record_opinions(packet(), submit(d))
    assert result.recorded_opinion_count == 1
    assert not result.code_generation_authorized and not result.database_access_authorized
    assert not result.source_changes_authorized and not result.deployment_authorized
    assert not result.field_meanings_verified and not result.reference_behavior_verified


def test_reviewer_cannot_claim_external_evidence_reference_checked():
    d = decision_for('observed_behavior', evidence_refs_checked=['unseen/raw.png'])
    with pytest.raises(ValueError, match='evidence not attached'):
        record_opinions(packet(), submit(d))


def test_reviewer_may_reference_declared_archive_as_checked_but_cannot_authorize():
    d = decision_for('observed_behavior', 'needs_more_evidence',
                     evidence_refs_checked=['evidence/jp_nail_brand_filter_source_20261018.md'])
    result = record_opinions(packet(), submit(d))
    assert result.recorded_opinion_count == 1
    assert not result.reference_behavior_verified


def test_blank_reason_and_unknown_value_rejected():
    d = decision_for('unresolved_behavior')
    d['rationale'] = 'short'
    with pytest.raises(ValidationError):
        submit(d)
    d['rationale'] = 'A reviewer should check the original source.'
    d['decision'] = 'authorize_deploy'
    with pytest.raises(ValidationError):
        submit(d)


def test_no_review_identity_verification_even_when_all_fields_decided():
    packet_obj = packet()
    responses = []
    for item in packet_obj.items:
        responses.append({'item_id': item.item_id, 'decision':'needs_more_evidence',
                          'rationale':'Additional original measurements are needed.'})
    result = record_opinions(packet_obj, submit(*responses))
    assert result.pending_count == 0 and result.recorded_opinion_count == 13
    assert not result.user_approval_verified and not result.code_generation_authorized


def test_forged_positive_authorization_on_result_cannot_validate():
    obj = record_opinions(packet(), submit(decision_for('unresolved_behavior'))).model_dump(mode='json')
    for name in ('source_changes_authorized', 'deployment_authorized', 'database_access_authorized',
                 'user_approval_verified', 'reviewer_identity_verified', 'field_meanings_verified'):
        forged = copy.deepcopy(obj)
        forged[name] = True
        with pytest.raises(ValidationError):
            ReviewRecord.model_validate(forged)


def test_cli_packet_output_and_record_output(capsys, tmp_path):
    paths = [str(SPEC),str(SCHEMA),str(MAPPING)]
    assert main(['packet',*paths]) == 0
    assert ReviewPacket.model_validate_json(capsys.readouterr().out) == packet()
    submission = submit(decision_for('unresolved_behavior'))
    filename = tmp_path / 'submission.json'
    filename.write_text(submission.model_dump_json(),encoding='utf-8')
    assert main(['record',*paths,str(filename)]) == 0
    result = ReviewRecord.model_validate_json(capsys.readouterr().out)
    assert result.recorded_opinion_count == 1
    assert list(tmp_path.iterdir()) == [filename]


def test_cli_invalid_stale_submission_fails_without_json_stdout(capsys,tmp_path):
    fake = submit(decision_for('unresolved_behavior')).model_dump(mode='json')
    fake['packet_sha256'] = 'f'*64
    p = tmp_path/'stale.json'
    p.write_text(json.dumps(fake), encoding='utf-8')
    assert main(['record',str(SPEC),str(SCHEMA),str(MAPPING),str(p)]) == 1
    output = capsys.readouterr()
    assert output.out == '' and output.err.startswith('FAIL:')


def test_no_automatic_file_write_database_calls_or_network():
    src=(ROOT/'astra_contracts/reviewer_decisions.py').read_text(encoding='utf-8')
    for forbidden in ('import sqlite3', 'import requests', 'import subprocess', 'import socket',
                      '.write_text(', '.write_bytes(', '.unlink(', 'os.system(', 'openai'):
        assert forbidden not in src
