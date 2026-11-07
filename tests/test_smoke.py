import os
os.environ.setdefault('SECRET_KEY','testing-key')
os.environ.setdefault('ADMIN_PASSWORD','testing-password')
from app import app

def test_home():
    app.config['TESTING']=True
    response=app.test_client().get('/')
    assert response.status_code==200

def test_dashboard():
    app.config['TESTING']=True
    response=app.test_client().get('/dashboard')
    assert response.status_code in (200,302)
