import pytest
from PIL import Image

from Utils.image_utils import resize_image


def resize(tmp_path, image):
    original = tmp_path / 'original.png'
    resized = tmp_path / 'resized.jpg'
    image.save(original, 'TIFF' if image.mode == 'CMYK' else 'PNG')

    resize_image(original, resized, 8, 8)

    return Image.open(resized)


@pytest.mark.parametrize('mode', ['RGB', 'RGBA', 'LA', 'L', 'P', '1', 'CMYK'])
def test_every_common_mode_can_be_resized(tmp_path, mode):
    result = resize(tmp_path, Image.new(mode, (16, 16)))

    assert result.format == 'JPEG'
    assert result.size == (8, 8)


def assert_nearly_white(pixel):
    assert all(channel >= 250 for channel in pixel), pixel


def test_transparency_becomes_white(tmp_path):
    result = resize(tmp_path, Image.new('RGBA', (16, 16), (0, 0, 0, 0)))

    assert_nearly_white(result.getpixel((4, 4)))


def test_palette_transparency_becomes_white(tmp_path):
    image = Image.new('P', (16, 16), 0)
    image.info['transparency'] = 0

    result = resize(tmp_path, image)

    assert_nearly_white(result.getpixel((4, 4)))
