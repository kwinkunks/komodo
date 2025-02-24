import pathlib
import sys
from unittest.mock import MagicMock

import pytest
import requests
import yaml
from packaging import version
from yaml.cyaml import CLoader

from komodo import check_up_to_date_pypi
from komodo.check_up_to_date_pypi import (
    compatible_versions,
    get_pypi_packages,
    insert_upgrade_proposals,
    yaml_parser,
)


@pytest.mark.parametrize(
    "input_dict",
    [
        pytest.param({"1.0.0": []}, id="Just valid tag"),
        pytest.param({"1.0.0": [], "2.0.0a0": []}, id="Pre-release tag"),
        pytest.param({"1.0.0": [], "2.0.0.dev": []}, id="Dev tag"),
        pytest.param(
            {"1.0.0": [], "2.0.0": [{"requires_python": ">3.7"}]},
            id="Too high python requirement on 2.0",
        ),
        pytest.param(
            {
                "1.0.0": [{"requires_python": ">3"}],
                "2.0.0": [{"requires_python": ">3.7"}],
            },
            id="Latest version not compatible",
        ),
    ],
)
def test_compatible_versions(input_dict):
    result = compatible_versions(input_dict, "3.6.10")
    assert result == [version.parse("1.0.0")]


@pytest.mark.parametrize(
    "input_release, input_repo",
    [
        pytest.param(
            {"dummy_package": "1.0.0"},
            {"dummy_package": {"1.0.0": {"source": "pypi"}}},
            id="Minimum requirement",
        ),
        pytest.param(
            {"dummy_package": "1.0.0", "custom_package": "1.1.1"},
            {
                "dummy_package": {"1.0.0": {"source": "pypi"}},
                "custom_package": {"1.1.1": {"source": "not_pypi"}},
            },
            id="Not all pypi",
        ),
        pytest.param(
            {"dummy_package": "1.0.0", "custom_package": "1.1.1"},
            {
                "dummy_package": {"1.0.0": {"source": "pypi"}},
                "custom_package": {"1.1.1": {"maintainer": "some_person"}},
            },
            id="No source for one package",
        ),
    ],
)
def test_get_pypi_packages(input_release, input_repo):
    result = get_pypi_packages(input_release, input_repo)
    assert result == ["dummy_package"]


@pytest.mark.parametrize(
    "release, repository, suggestions, expected",
    [
        pytest.param(
            {"dummy_package": "1.0.0", "custom_package": "1.1.1"},
            {
                "dummy_package": {"1.0.0": {}},
                "custom_package": {"1.1.1": {}},
            },
            {"dummy_package": {"suggested": "2.0.0", "previous": "1.0.0"}},
            {
                "release": {"dummy_package": "2.0.0", "custom_package": "1.1.1"},
                "repo": {
                    "dummy_package": {"1.0.0": {}, "2.0.0": {}},
                    "custom_package": {"1.1.1": {}},
                },
            },
            id="Base line test",
        ),
        pytest.param(
            {"dummy_package": "1.0.0", "custom_package": "1.1.1"},
            {
                "dummy_package": {"1.0.0": {}, "2.0.0": {}},
                "custom_package": {"1.1.1": {}},
            },
            {"dummy_package": {"suggested": "2.0.0", "previous": "1.0.0"}},
            {
                "release": {"dummy_package": "2.0.0", "custom_package": "1.1.1"},
                "repo": {
                    "dummy_package": {"1.0.0": {}, "2.0.0": {}},
                    "custom_package": {"1.1.1": {}},
                },
            },
            id="Nothing to add to repository",
        ),
        pytest.param(
            {"dummy_package": "1.0.0+py23", "custom_package": "1.1.1"},
            {
                "dummy_package": {"1.0.0+py23": {}},
                "custom_package": {"1.1.1": {}},
            },
            {"dummy_package": {"suggested": "2.0.0", "previous": "1.0.0+py23"}},
            {
                "release": {"dummy_package": "2.0.0", "custom_package": "1.1.1"},
                "repo": {
                    "dummy_package": {"1.0.0+py23": {}, "2.0.0": {}},
                    "custom_package": {"1.1.1": {}},
                },
            },
            id="Test with +something marker on version",
        ),
    ],
)
def test_insert_upgrade_proposals(release, repository, suggestions, expected):
    yaml = yaml_parser()
    repository = yaml.load(str(repository))
    release = yaml.load(str(release))
    insert_upgrade_proposals(
        suggestions,
        repository,
        release,
    )
    assert {"release": release, "repo": repository} == expected


def test_run(monkeypatch):
    release = {"dummy_package": "1.0.0", "custom_package": "1.1.1"}
    repository = {
        "dummy_package": {"1.0.0": {"source": "pypi"}},
        "custom_package": {"1.1.1": {"maintainer": "some_person"}},
    }

    response_mock = MagicMock(return_value=[("dummy_package", MagicMock())])
    compatible_versions = MagicMock(return_value=["2.0.0"])
    monkeypatch.setattr(check_up_to_date_pypi, "get_pypi_info", response_mock)
    monkeypatch.setattr(
        check_up_to_date_pypi, "compatible_versions", compatible_versions
    )
    result = check_up_to_date_pypi.get_upgrade_proposal(release, repository, "3.6.8")
    assert result == {"dummy_package": {"previous": "1.0.0", "suggested": "2.0.0"}}


def test_main_happy_path(monkeypatch, tmpdir):
    with tmpdir.as_cwd():
        arguments = [
            "script_name",
            "release_file",
            "repository_file",
            "--propose-upgrade",
            "new_file",
        ]
        monkeypatch.setattr(sys, "argv", arguments)
        monkeypatch.setattr(pathlib.Path, "is_file", MagicMock(return_value=True))
        monkeypatch.setattr(check_up_to_date_pypi, "load_from_file", MagicMock())
        output_mock = MagicMock(return_value={})
        monkeypatch.setattr(check_up_to_date_pypi, "get_upgrade_proposal", output_mock)
        check_up_to_date_pypi.main()


def test_main_upgrade_proposal(monkeypatch):
    arguments = [
        "script_name",
        "release_file",
        "repository_file",
    ]
    monkeypatch.setattr(sys, "argv", arguments)
    input_mock = MagicMock()
    monkeypatch.setattr(check_up_to_date_pypi, "load_from_file", input_mock)
    monkeypatch.setattr(pathlib.Path, "is_file", MagicMock(return_value=True))
    output_mock = MagicMock(
        return_value={"dummy_package": {"previous": "1.0.0", "suggested": "2.0.0"}}
    )
    monkeypatch.setattr(check_up_to_date_pypi, "get_upgrade_proposal", output_mock)
    with pytest.raises(
        SystemExit,
        match="dummy_package not at latest pypi version: 2.0.0, is at: 1.0.0",
    ):
        check_up_to_date_pypi.main()


def test_main_file_output(monkeypatch, tmpdir):
    with tmpdir.as_cwd():
        arguments = [
            "script_name",
            "release_file",
            "repository_file",
            "--propose-upgrade",
            "new_file",
        ]
        monkeypatch.setattr(sys, "argv", arguments)
        monkeypatch.setattr(pathlib.Path, "is_file", MagicMock(return_value=True))
        yaml = yaml_parser()
        input_mock = MagicMock()
        input_mock.side_effect = [
            yaml.load("""{"dummy_package": "1.0.0", "custom_package": "1.1.1"}"""),
            yaml.load(
                """{
                "dummy_package": {"1.0.0": {"source": "pypi"}},
                "custom_package": {"1.1.1": {"maintainer": "some_person"}},
            }"""
            ),
        ]
        monkeypatch.setattr(check_up_to_date_pypi, "load_from_file", input_mock)
        output_mock = MagicMock(
            return_value={"dummy_package": {"previous": "1.0.0", "suggested": "2.0.0"}}
        )
        monkeypatch.setattr(check_up_to_date_pypi, "get_upgrade_proposal", output_mock)
        with pytest.raises(
            SystemExit,
            match="dummy_package not at latest pypi version: 2.0.0, is at: 1.0.0",
        ):
            check_up_to_date_pypi.main()

        result = {}
        with open("new_file") as fin:
            result["suggestions"] = yaml.load(fin)
        with open("repository_file") as fin:
            result["updated_repo"] = yaml.load(fin)

        assert result == {
            "suggestions": {"dummy_package": "2.0.0", "custom_package": "1.1.1"},
            "updated_repo": {
                "dummy_package": {
                    "2.0.0": {"source": "pypi"},
                    "1.0.0": {"source": "pypi"},
                },
                "custom_package": {"1.1.1": {"maintainer": "some_person"}},
            },
        }


@pytest.mark.parametrize(
    "release, repository, request_json, expected",
    [
        pytest.param(
            {"dummy_package": "1.0.0", "custom_package": "1.1.1"},
            {
                "dummy_package": {"1.0.0": {"source": "pypi"}},
                "custom_package": {"1.1.1": {"maintainer": "some_person"}},
            },
            {
                "releases": {"2.0.0": []},
            },
            {
                "release": {"dummy_package": "2.0.0", "custom_package": "1.1.1"},
                "repo": {
                    "dummy_package": {
                        "2.0.0": {"source": "pypi"},
                        "1.0.0": {"source": "pypi"},
                    },
                    "custom_package": {"1.1.1": {"maintainer": "some_person"}},
                },
            },
            id="Base line test",
        ),
        pytest.param(
            {"dummy_package": "1.0.0", "komodo_version_package": "1.*"},
            {
                "dummy_package": {"1.0.0": {"source": "pypi"}},
                "komodo_version_package": {"1.*": {"source": "pypi"}},
            },
            {
                "releases": {"2.0.0": []},
            },
            {
                "release": {"dummy_package": "2.0.0", "komodo_version_package": "1.*"},
                "repo": {
                    "dummy_package": {
                        "2.0.0": {"source": "pypi"},
                        "1.0.0": {"source": "pypi"},
                    },
                    "komodo_version_package": {"1.*": {"source": "pypi"}},
                },
            },
            id="With komodo package alias not updated",
        ),
        pytest.param(
            {"dummy_package": "1.0.0+py27"},
            {
                "dummy_package": {"1.0.0+py27": {"source": "pypi"}},
            },
            {
                "releases": {"2.0.0": []},
            },
            {
                "release": {"dummy_package": "2.0.0"},
                "repo": {
                    "dummy_package": {
                        "2.0.0": {"source": "pypi"},
                        "1.0.0+py27": {"source": "pypi"},
                    },
                },
            },
            id="Using version suffix",
        ),
        pytest.param(
            {"dummy_package": "1.0.0"},
            {
                "dummy_package": {"1.0.0": {"source": "pypi"}},
            },
            {
                "releases": {"2.2.0": [{"yanked": True}], "2.0.0": []},
            },
            {
                "release": {"dummy_package": "2.0.0"},
                "repo": {
                    "dummy_package": {
                        "2.0.0": {"source": "pypi"},
                        "1.0.0": {"source": "pypi"},
                    },
                },
            },
            id="Yanked from pypi",
        ),
    ],
)
def test_integration(monkeypatch, tmpdir, release, repository, request_json, expected):
    with tmpdir.as_cwd():
        arguments = [
            "script_name",
            "release_file",
            "repository_file",
            "--propose-upgrade",
            "new_file",
        ]
        monkeypatch.setattr(sys, "argv", arguments)
        with open("repository_file", "w") as fout:
            fout.write(str(repository))
        with open("release_file", "w") as fout:
            fout.write(str(release))
        request_mock = MagicMock()
        request_mock.json.return_value = request_json
        monkeypatch.setattr(requests, "get", MagicMock(return_value=request_mock))

        with pytest.raises(
            SystemExit,
            match="dummy_package not at latest pypi version: 2.0.0, is at: 1.0.0",
        ):
            check_up_to_date_pypi.main()

        result = {}
        with open("new_file") as fin:
            result["release"] = yaml.load(fin, Loader=CLoader)
        with open("repository_file") as fin:
            result["repo"] = yaml.load(fin, Loader=CLoader)

        assert result == expected
