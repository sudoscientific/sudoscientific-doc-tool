import os

import git
import pytest
from typer.testing import CliRunner
from sdt.main import app

runner = CliRunner()

FILENAME = "sdt.json"


@pytest.fixture(scope="function")
def tmp_folder_no_git(tmp_path_factory):
    test_dir = tmp_path_factory.mktemp("test_dir")
    os.chdir(test_dir)
    yield


@pytest.fixture(scope="function")
def tmp_folder_no_init(tmp_path_factory):
    test_dir = tmp_path_factory.mktemp("test_dir")
    os.chdir(test_dir)
    git.Repo.init()
    yield


@pytest.fixture(scope="function")
def add_fixture(tmp_path_factory):
    test_dir = tmp_path_factory.mktemp("test_dir")
    os.chdir(test_dir)
    git.Repo.init()
    runner.invoke(app, ["init"])
    os.mkdir("sub_dir")
    with open("file.txt", "w") as f:
        f.write("Test Content")

    with open("sub_dir/file.txt", "w") as f:
        f.write("Sub Dir Test Content ")

    yield


@pytest.fixture(scope="function")
def update_rm_fixture(tmp_path_factory):
    test_dir = tmp_path_factory.mktemp("test_dir")
    os.chdir(test_dir)
    git.Repo.init()
    runner.invoke(app, ["init"])
    with open("file.txt", "w") as f:
        f.write("Test Content")
    with open("file2.txt", "w") as f:
        f.write("Test Content")
    runner.invoke(app, ["add", "Doc Name", "file.txt"])
    runner.invoke(app, ["add", "Doc Name", "file2.txt"])
    yield


# init tests
def test_init_no_git_repo(tmp_folder_no_git):
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    assert "Parent directory is not a git repository" in result.stdout


def test_init(tmp_folder_no_init):
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert f"{FILENAME} generated" in result.stdout


def test_init_existing(add_fixture):
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    assert f"{FILENAME} already exists" in result.stdout


# add tests
def test_add(add_fixture):
    result = runner.invoke(app, ["add", "Doc Name", "file.txt"])
    assert "Entry made" in result.stdout
    assert "Doc Name" in result.stdout
    assert "file.txt" in result.stdout
    assert result.exit_code == 0


def test_add_same_path(add_fixture):
    runner.invoke(app, ["add", "Doc Name", "file.txt"])
    result = runner.invoke(app, ["add", "Doc Name", "file.txt"])
    assert "Entry already made" in result.stdout
    assert result.exit_code == 1


def test_add_same_doc(add_fixture):
    runner.invoke(app, ["add", "Doc Name", "file.txt"])
    result = runner.invoke(app, ["add", "Doc Name", "sub_dir/file.txt"])
    assert "Path added to entry" in result.stdout
    assert result.exit_code == 0

    result = runner.invoke(app, ["add", "Doc Name", "sub_dir/file.txt"])
    assert "Entry already made" in result.stdout
    assert result.exit_code == 1


def test_add_shared_path(add_fixture):
    runner.invoke(app, ["add", "Doc Name", "sub_dir"])
    result = runner.invoke(app, ["add", "Doc Name", "sub_dir/file.txt"])
    assert "Path overlaps with an existing path for this document" in result.stdout
    assert result.exit_code == 1


def test_add_malformed_doc_name(add_fixture):
    runner.invoke(app, ["add", "   Doc Name          ", "file.txt"])
    result = runner.invoke(app, ["ls"])
    assert "Entries" in result.stdout
    assert "docname" in result.stdout
    assert "Doc Name" in result.stdout
    assert "file.txt" in result.stdout
    assert result.exit_code == 0


# test list
def test_list_empty_file(add_fixture):
    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 1


# test rm
def test_rm(update_rm_fixture):
    result = runner.invoke(app, ["rm", "docname", "--path", "file.txt"])
    assert "Path deleted" in result.stdout
    assert result.exit_code == 0


def test_rm_no_path(update_rm_fixture):
    result = runner.invoke(app, ["rm", "docname"])
    assert "Cannot remove a document with paths" in result.stdout
    assert "file.txt" in result.stdout
    assert "file2.txt" in result.stdout
    assert "Please run rm with the --path flag" in result.stdout
    assert result.exit_code == 1


def test_rm_whole_entry(update_rm_fixture):
    runner.invoke(app, ["rm", "docname", "--path", "file.txt"])
    runner.invoke(app, ["rm", "docname", "--path", "file2.txt"])
    result = runner.invoke(app, ["rm", "docname"])
    assert "Entry deleted" in result.stdout
    assert "docname deleted" in result.stdout
    assert result.exit_code == 0


# test update
def test_update(update_rm_fixture):
    first_result = runner.invoke(app, ["ls"])
    runner.invoke(app, ["update", "docname"])
    second_result = runner.invoke(app, ["ls"])
    assert first_result.stdout != second_result.stdout


def test_update_no_entry(update_rm_fixture):
    result = runner.invoke(app, ["update", "does-not-exist"])
    assert result.exit_code == 1
    assert "not present in sdt.json" in result.stdout
