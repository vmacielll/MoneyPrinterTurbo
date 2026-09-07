# -*- coding: utf-8 -*-
"""_download_image_file：落盘、PIL 校验、代理/TLS/UA 透传。"""
import io
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from app.config import config
from app.services import material


def _jpeg_bytes(width=1, height=1):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (255, 0, 0)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _download_response(content, content_type="image/jpeg", status_code=200):
    return SimpleNamespace(
        content=content,
        headers={"Content-Type": content_type},
        status_code=status_code,
    )


class TestDownloadImageFile(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)
        self.original_proxy_config = dict(config.proxy)
        self.save_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.save_dir, ignore_errors=True)
        config.app.pop("tls_verify", None)
        config.proxy.clear()

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)
        config.proxy.clear()
        config.proxy.update(self.original_proxy_config)

    def test_download_image_file_saves_with_correct_extension(self):
        """image/jpeg 内容必须以 .jpg 扩展名落盘，且文件内容与下载字节一致。"""
        payload = _jpeg_bytes()

        with patch(
            "app.services.material.requests.get",
            return_value=_download_response(payload),
        ) as get:
            image_path = material._download_image_file(
                "https://cdn.example.com/photo.jpeg", self.save_dir
            )

        self.assertIsNotNone(image_path)
        self.assertTrue(image_path.endswith(".jpg"))
        self.assertTrue(image_path.startswith(self.save_dir))
        self.assertTrue(os.path.isfile(image_path))
        with open(image_path, "rb") as f:
            self.assertEqual(f.read(), payload)
        with Image.open(image_path) as saved:
            self.assertEqual(saved.size, (1, 1))

    def test_download_image_file_returns_none_on_bad_payload(self):
        """Content-Type 是 image/jpeg 但 body 不是图片（HTML 错误页）时必须
        返回 None，且不能留下任何文件。"""
        payload = b"<html>gateway error page</html>"

        with patch(
            "app.services.material.requests.get",
            return_value=_download_response(payload),
        ):
            image_path = material._download_image_file(
                "https://cdn.example.com/fake.jpg", self.save_dir
            )

        self.assertIsNone(image_path)
        self.assertEqual(os.listdir(self.save_dir), [])

    def test_download_image_file_respects_proxy_and_tls_verify(self):
        """下载请求必须把代理与 TLS 校验配置传给 requests。"""
        config.proxy.update(
            {"http": "http://proxy.local:8080", "https": "http://proxy.local:8080"}
        )
        config.app["tls_verify"] = False
        payload = _jpeg_bytes()

        with patch(
            "app.services.material.requests.get",
            return_value=_download_response(payload),
        ) as get:
            material._download_image_file(
                "https://cdn.example.com/photo.jpeg", self.save_dir
            )

        self.assertEqual(
            get.call_args.kwargs["proxies"],
            {"http": "http://proxy.local:8080", "https": "http://proxy.local:8080"},
        )
        self.assertFalse(get.call_args.kwargs["verify"])

    def test_download_image_file_uses_configured_user_agent(self):
        """下载请求必须携带与搜索一致的用户代理，并以流式方式读取。"""
        payload = _jpeg_bytes()

        with patch(
            "app.services.material.requests.get",
            return_value=_download_response(payload),
        ) as get:
            material._download_image_file(
                "https://cdn.example.com/photo.jpeg", self.save_dir
            )

        self.assertEqual(
            get.call_args.kwargs["headers"]["User-Agent"],
            material._PEXELS_USER_AGENT,
        )
        self.assertTrue(get.call_args.kwargs["stream"])
        self.assertEqual(get.call_args.kwargs["timeout"], (30, 60))

    def test_download_image_file_returns_none_on_http_error(self):
        """非 2xx 状态码必须返回 None 而不落盘。"""
        payload = _jpeg_bytes()

        with patch(
            "app.services.material.requests.get",
            return_value=_download_response(payload, status_code=404),
        ):
            image_path = material._download_image_file(
                "https://cdn.example.com/missing.jpg", self.save_dir
            )

        self.assertIsNone(image_path)
        self.assertEqual(os.listdir(self.save_dir), [])


if __name__ == "__main__":
    unittest.main()