#!/usr/bin/env python3
"""联网的接口契约检查（金丝雀）：只在 NP_LIVE=1 时运行，共 6 个请求。

脚本依赖几条实测得来的接口行为；数据源改了接口时，离线测试（录制件）发现不了，这里能发现：
  1. OpenAlex 列表：title_and_abstract.search 照原样接受 AND / OR / 引号短语，meta.x_query 给出解析结果，响应形状不变；
  2. OpenAlex 不支持通配符：截断词返回 400（所以 search.py 把截断词换成完整词，见 queries.truncation）；
  3. Semantic Scholar bulk 检索：响应有 total / token / data；
  4. Semantic Scholar batch：POST 按 DOI 批量取记录；
  5. Crossref /works/<doi>：响应形状不变；
  6. Crossref /works/<doi>/agency：arXiv 的 DOI 由 DataCite 登记（verify.py 据此改走 OpenAlex）。
运行：NP_LIVE=1 python3 -m unittest tests.test_live_contract -v
请求经 novelty_probe/http.py 的客户端（按主机限速、重试），User-Agent 是通用的客户端名，不带个人信息；
缓存写到临时目录，不进仓库。S2 在重试后仍返回 429 时记为跳过（限流不是接口变化）。
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_offline import load  # noqa: E402

from novelty_probe import config, runtime, schemas  # noqa: E402
from novelty_probe.http import Client, ClientError, RateLimited  # noqa: E402

LIVE = os.environ.get("NP_LIVE") == "1"
search = load("search") if LIVE else None


@unittest.skipUnless(LIVE, "联网检查：设置 NP_LIVE=1 才运行")
class TestLiveContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = tempfile.TemporaryDirectory()
        cls.client = Client("live", cache_dir=cls.cache.name, user_agent=runtime.user_agent(config.defaults()))
        from novelty_probe.http import set_default_client
        set_default_client(cls.client)

    @classmethod
    def tearDownClass(cls):
        cls.cache.cleanup()

    def test_1_openalex_boolean_list(self):
        meta, records = search.search_openalex({"id": "Q1", "query": '("generative AI" OR "large language models") AND homogeniz*'},
                                               None, top_n=2)
        self.assertEqual(meta["warnings"], [])                       # 响应形状与解析核对都没有警告
        self.assertIn(" AND ", meta["api_interpretation"])
        self.assertIsInstance(meta["total_hits"], int)
        self.assertLessEqual(len(records), 2)

    def test_2_openalex_rejects_wildcards(self):
        with self.assertRaises(ClientError) as cm:
            self.client.get_json("https://api.openalex.org/works",
                                 params={"filter": "title_and_abstract.search:scientist*", "per-page": 1})
        self.assertEqual(cm.exception.status, 400)

    def test_3_semantic_scholar_bulk(self):
        try:
            data = self.client.get_json("https://api.semanticscholar.org/graph/v1/paper/search/bulk",
                                        params={"query": '"homogenization" + "large language models" + creativity',
                                                "fields": "title,year,externalIds", "sort": "citationCount:desc"})
        except RateLimited as e:
            self.skipTest(f"Semantic Scholar rate-limited after retries: {e}")
        self.assertEqual(schemas.s2_bulk(data), [])

    def test_4_semantic_scholar_batch(self):
        try:
            data = self.client.post_json("https://api.semanticscholar.org/graph/v1/paper/batch",
                                         {"ids": ["DOI:10.1126/sciadv.adn5290"]}, params={"fields": "title,year,externalIds"})
        except RateLimited as e:
            self.skipTest(f"Semantic Scholar rate-limited after retries: {e}")
        self.assertEqual(schemas.s2_batch(data, 1), [])
        self.assertEqual(data[0]["externalIds"]["DOI"].lower(), "10.1126/sciadv.adn5290")

    def test_5_crossref_work(self):
        data = self.client.get_json("https://api.crossref.org/works/10.1126/sciadv.adn5290")
        self.assertEqual(schemas.crossref_work(data), [])
        self.assertEqual(data["message"]["DOI"].lower(), "10.1126/sciadv.adn5290")

    def test_6_crossref_agency_for_arxiv_doi(self):
        data = self.client.get_json("https://api.crossref.org/works/10.48550/arXiv.2312.00506/agency")
        self.assertEqual(schemas.crossref_agency(data), [])
        self.assertEqual(data["message"]["agency"]["id"], "datacite")


if __name__ == "__main__":
    unittest.main()
