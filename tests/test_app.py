import os
import pytest

os.environ.setdefault("DBHOST", "localhost")
os.environ.setdefault("DBPORT", "3306")
os.environ.setdefault("DBUSER", "root")
os.environ.setdefault("DBPWD", "password")
os.environ.setdefault("DATABASE", "employees")
os.environ.setdefault("STUDENT_NAME", "Test Student")
os.environ.setdefault("BG_IMAGE_URL", "") 


from unittest.mock import patch, MagicMock

@pytest.fixture(scope="session", autouse=True)
def mock_db_and_s3():
    with patch("pymysql.connections.Connection", return_value=MagicMock()), \
         patch("boto3.client", return_value=MagicMock()):
        yield


@pytest.fixture
def client():
    with patch("pymysql.connections.Connection", return_value=MagicMock()), \
         patch("boto3.client", return_value=MagicMock()):
        from app import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200


def test_home_contains_student_name(client):
    response = client.get("/")
    assert b"Test Student" in response.data


def test_about_page_loads(client):
    response = client.get("/about")
    assert response.status_code == 200


def test_getemp_page_loads(client):
    response = client.get("/getemp")
    assert response.status_code == 200


def test_background_image_tag_present(client):
    response = client.get("/")
    assert b"background-image" in response.data
