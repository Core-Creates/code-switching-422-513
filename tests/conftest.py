"""Tests run against the repo root: modules import flat and encoder.stim lives there."""
import os
import sys

import pytest
import stim

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(scope="session")
def encoder_circuit():
    return stim.Circuit.from_file(os.path.join(ROOT, "encoder.stim"))


@pytest.fixture(scope="session")
def U(encoder_circuit):
    return stim.Tableau.from_circuit(encoder_circuit)


@pytest.fixture(scope="session")
def enc(encoder_circuit):
    import flagsearch as FS
    return FS.Encoder(encoder_circuit)
