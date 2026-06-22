import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("cdss.integrations.clinical_trials.AsyncSession", return_value=mock_session):
        trials, error = await fetch_trials("NSCLC", ["EGFR"])
    assert error is None
    assert len(trials) == 1
    assert trials[0].nct_id == "NCT001"


@pytest.mark.asyncio
async def test_fetch_trials_degrades_on_error():
    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=Exception("network error"))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("cdss.integrations.clinical_trials.AsyncSession", return_value=mock_session):
        trials, error = await fetch_trials("NSCLC", [])
    assert trials == []
    assert error is not None
    assert "Trials API error" in error


@pytest.mark.asyncio
async def test_fetch_trials_skips_without_condition():
    trials, error = await fetch_trials("", [])
    assert trials == []
    assert error is not None
    assert "no condition" in error.lower()
