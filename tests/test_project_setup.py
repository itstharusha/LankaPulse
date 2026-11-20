from pathlib import Path

from functions.shared.config import settings

ROOT = Path(__file__).parents[1]


def test_phase_zero_scaffold_exists() -> None:
    expected_paths = [
        ROOT / "README.md",
        ROOT / "requirements.txt",
        ROOT / ".github" / "workflows" / "ci.yml",
        ROOT / "tests" / "sample_data" / "fx_sample.json",
        ROOT / "tests" / "sample_data" / "weather_sample.json",
        ROOT / "tests" / "sample_data" / "sltda_manifest.csv",
    ]

    assert all(path.exists() for path in expected_paths)


def test_local_configuration_defaults_to_non_azure_paths() -> None:
    assert settings.environment == "local"
    assert settings.timezone == "Asia/Colombo"
    assert settings.raw_root == Path("data/raw")