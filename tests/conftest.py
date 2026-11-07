import pytest

from Server import image_proxy_server


@pytest.fixture
def assets_dir(tmp_path, monkeypatch):
    path = tmp_path / 'assets'
    path.mkdir()
    monkeypatch.setattr(image_proxy_server, 'PATH_TO_ASSETS', f'{path}/')
    return path


@pytest.fixture
def client(assets_dir):
    return image_proxy_server.app.test_client()
