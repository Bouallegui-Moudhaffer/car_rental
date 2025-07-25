# tests/test_homepage.py

from flask import url_for
import pytest
from app.main import app  # adjust import path if needed

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # point at your test database or localhost
    app.config['DB_HOST'] = 'localhost'
    app.config['DB_USER'] = 'root'
    app.config['DB_PASSWORD'] = 'root'
    app.config['DB_NAME'] = 'car_rental'
    with app.test_client() as c:
        yield c

def test_homepage_status_code(client):
    """GET / should return 200 OK."""
    resp = client.get('/')
    assert resp.status_code == 200
