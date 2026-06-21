import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from cdss.integrations.clinical_trials import fetch_trials, _parse
from cdss.core.models.trial import ClinicalTrial


_STUDY = {
    "protocolSection": {
        "identificationModule": {"nctId": "NCT001", "briefTitle": "NSCLC Trial"},
        "statusModule": {"overallStatus": "RECRUITING"},
        "descriptionModule": {"briefSummary": "A trial for NSCLC patients."},
        "designModule": {"phases": ["PHASE3"]},
        "contactsLocationsModule": {"locations": [{"facility": {"name": "Mayo Clinic"}}]},
    }
}


def test_parse_valid_study():
    trial = _parse(_STUDY)
    assert isinstance(trial, ClinicalTrial)
    assert trial.nct_id == "NCT001"
    assert "clinicaltrials.gov" in trial.url


def test_parse_bad_study_returns_none():
    assert _parse({}) is None


@pytest.mark.asyncio
async def test_fetch_trials_returns_list():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"studies": [_STUDY]}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        trials = await fetch_trials("NSCLC", ["EGFR"])
    assert len(trials) == 1
    assert trials[0].nct_id == "NCT001"


@pytest.mark.asyncio
async def test_fetch_trials_degrades_on_error():
    with patch("httpx.AsyncClient.get", side_effect=Exception("network error")):
        trials = await fetch_trials("NSCLC", [])
    assert trials == []
