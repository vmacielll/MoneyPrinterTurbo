# -*- coding: utf-8 -*-
"""Pexels 图片搜索：请求构造、响应解析与按画幅容差过滤。"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.config import config
from app.models.schema import VideoAspect
from app.services import material


def _photo(
    photo_id,
    width,
    height,
    photographer="Creator Name",
    photographer_url="https://www.pexels.com/@creator/",
):
    return {
        "id": photo_id,
        "width": width,
        "height": height,
        "url": f"https://www.pexels.com/photo/example-{photo_id}/?token=drop",
        "photographer": photographer,
        "photographer_url": photographer_url,
        "src": {
            "large2x": (
                f"https://images.pexels.com/photos/{photo_id}/"
                f"pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&w=1920"
            ),
            "medium": (
                f"https://images.pexels.com/photos/{photo_id}/"
                f"pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&h=350"
            ),
        },
    }


def _search_response(photos):
    return SimpleNamespace(json=lambda: {"photos": photos})


class TestSearchImagesPexels(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)
        self.original_proxy_config = dict(config.proxy)
        config.app["pexels_api_keys"] = ["pexels-key"]
        config.app.pop("tls_verify", None)
        config.proxy.clear()

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)
        config.proxy.clear()
        config.proxy.update(self.original_proxy_config)

    def test_search_images_pexels_builds_request_and_parses_response(self):
        """请求必须命中 Photos Search 端点，带 raw key 的 Authorization 头，
        返回的 MaterialInfo 必须携带图片源信息。"""
        photo = _photo(111, 1080, 1920)

        with patch(
            "app.services.material.requests.get",
            return_value=_search_response([photo]),
        ) as get:
            results = material.search_images_pexels(
                "cat", video_aspect=VideoAspect.portrait
            )

        self.assertEqual(len(results), 1)
        item = results[0]
        self.assertEqual(item.provider, "pexels")
        self.assertEqual(item.url, photo["src"]["large2x"])
        self.assertEqual(item.duration, 0)
        self.assertEqual(item.material_type, "image")

        get.assert_called_once()
        self.assertEqual(
            get.call_args.args[0],
            "https://api.pexels.com/v1/search?query=cat&per_page=20&orientation=portrait",
        )
        self.assertEqual(
            get.call_args.kwargs["headers"]["Authorization"], "pexels-key"
        )
        self.assertNotIn(
            "Bearer", get.call_args.kwargs["headers"]["Authorization"]
        )
        self.assertEqual(get.call_args.kwargs["proxies"], {})
        self.assertTrue(get.call_args.kwargs["verify"])
        self.assertEqual(get.call_args.kwargs["timeout"], (30, 60))

        source = item.source_info
        self.assertEqual(source["provider"], "pexels")
        self.assertEqual(source["search_term"], "cat")
        self.assertEqual(source["asset_id"], "111")
        # source_page/thumbnail 必须剥离查询参数与凭据
        self.assertEqual(
            source["source_page"],
            "https://www.pexels.com/photo/example-111/",
        )
        self.assertEqual(
            source["thumbnail"],
            "https://images.pexels.com/photos/111/pexels-photo-111.jpeg",
        )
        self.assertEqual(
            source["creator"],
            {
                "name": "Creator Name",
                "profile_page": "https://www.pexels.com/@creator/",
            },
        )
        self.assertEqual(
            source["rendition"], {"id": None, "width": 1080, "height": 1920}
        )

    def test_search_images_pexels_filters_by_aspect_ratio(self):
        """图片按目标画幅的宽高比容差带过滤：错向照片丢弃，容差带内的近
        目标构图保留。"""
        photos = [
            _photo(1, 1920, 1080),  # 横屏 16:9，竖屏任务丢弃
            _photo(2, 1080, 1920),  # 竖屏 9:16，精确匹配
            _photo(3, 1100, 1955),  # 9:16 容差带内
            _photo(4, 810, 1080),  # 3:4，超出容差带
            _photo(5, 1000, 1000),  # 方形，竖屏任务丢弃
        ]

        with patch(
            "app.services.material.requests.get",
            return_value=_search_response(photos),
        ):
            results = material.search_images_pexels(
                "city", video_aspect=VideoAspect.portrait
            )

        self.assertEqual(
            [item.source_info["asset_id"] for item in results], ["2", "3"]
        )

    def test_search_images_pexels_drops_low_resolution_photos(self):
        """低于最小边长的低清缩略图不能进入候选列表。"""
        photos = [_photo(7, 400, 711), _photo(8, 1080, 1920)]

        with patch(
            "app.services.material.requests.get",
            return_value=_search_response(photos),
        ):
            results = material.search_images_pexels(
                "cat", video_aspect=VideoAspect.portrait
            )

        self.assertEqual(
            [item.source_info["asset_id"] for item in results], ["8"]
        )

    def test_search_images_pexels_returns_empty_on_error(self):
        """请求异常、坏 JSON 或缺少 photos 键都必须按素材源约定返回空列表。"""
        def raise_json():
            raise ValueError("no json body")

        config.app["pexels_api_keys"] = ["pexels-key"]
        # 网络异常
        with patch(
            "app.services.material.requests.get",
            side_effect=Exception("boom"),
        ):
            self.assertEqual(material.search_images_pexels("cat"), [])
        # 坏 JSON
        with patch(
            "app.services.material.requests.get",
            return_value=SimpleNamespace(json=raise_json),
        ):
            self.assertEqual(material.search_images_pexels("cat"), [])
        # 缺少 photos 键
        with patch(
            "app.services.material.requests.get",
            return_value=SimpleNamespace(
                json=lambda: {"total_results": 0}
            ),
        ):
            self.assertEqual(material.search_images_pexels("cat"), [])


if __name__ == "__main__":
    unittest.main()