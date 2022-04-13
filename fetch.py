import requests
import json
import pandas as pd
from termcolor import cprint
import time
from fake_useragent import UserAgent
from numpy import random
from hyper.contrib import HTTP20Adapter

HEADERS = {
    ":authority": "www.drugfuture.com",
    ":method": "GET",
    ":path": "/hma",
    ":scheme": "https",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
    "cache-control": "no-cache",
    "cookie": "ASP.NET_SessionId=f2vomffxchuuy3jvh0ncry2e; UM_distinctid=17fdf05f5fbaf-06d3b48b900148-1f343371-1fa400-17fdf05f5fc977; CNZZDATA134747=cnzz_eid%3D945523864-1648705386-%26ntime%3D1648705386; ASPSESSIONIDSWTCBRSA=MCKDFFJCKAMHDHDBNBFNDFHN; __51vcke__JeYGFzNXOyg2JqHb=2e971c74-7216-5dbf-a5ba-91517bc430cf; __51vuft__JeYGFzNXOyg2JqHb=1649830279847; ASPSESSIONIDSUCAASDC=KOBFALLCMIPCKMCGPMEKFJHB; ASPSESSIONIDSWCBCTDD=FLJKIJDDLMBPNDGIGOCAKKHM; __51uvsct__JeYGFzNXOyg2JqHb=3; __vtins__JeYGFzNXOyg2JqHb=%7B%22sid%22%3A%20%22c88b7aab-5c53-5916-a904-0f7f8345de62%22%2C%20%22vd%22%3A%2012%2C%20%22stt%22%3A%20709849%2C%20%22dr%22%3A%2041388%2C%20%22expires%22%3A%201649839906028%2C%20%22ct%22%3A%201649838106028%7D",
    "origin": "https://www.drugfuture.com",
    "pragma": "no=cache",
}


class HMACrawler:
    """面向drugfuture网站欧盟HMA药品数据库的爬虫
    https://www.drugfuture.com/hma

    """

    def __init__(self) -> None:
        """初始化"""
        pass

    def _headers(self, referer: str = None) -> dict:
        """生成一个浏览器header，包括使用fake_useragent包随机生成一个User-Agent

        Parameters
        ----------
        referer : str, optional
            http请求头, by default None

        Returns
        -------
        dict
            包含浏览器header参数的字典
        """
        headers = HEADERS.copy()
        if referer is not None:
            headers["Referer"] = referer

        ua = UserAgent()
        headers["user-agent"] = ua.random

    def _search(self, search_cond: dict, page: int = 1) -> str:
        """根据搜索条件和指定页数返回满足条件的药物列表html

        Parameters
        ----------
        search_cond : dict
            搜索字段和输入条件，drugfuture网站共提供了下列高级搜索字段
            name: 药品名称（商品名/通用名）
            innName: 活性成分
            productKey: MR编号
            doseFormName: 剂型
            maHolder: 上市许可持有人
            RMScountryName: 参考成员国
            code: ATC编码
            outcome: 市场状态(Positive/Withdrawn)
            dateOfOutcomeStart: 许可日期开始
            dateOfOutcomeEnd: 许可日期结束

        page : int, optional
            搜索结果的页数, 每页有20条结果 by default 1

        Returns
        -------
        str
            满足搜索调和和指定页数的搜索结果html
        """

        payload = {"SearchType": "AdvancedSearch", "page": page}
        for key, value in search_cond.items():
            payload[key] = value
        headers = self._headers("https://www.drugfuture.com/hma/")
        r = requests.get(
            "https://www.drugfuture.com/hma/search.aspx",
            params=payload,
            headers=headers,
        )
        return r.text


if __name__ == "__main__":
    crawler = HMACrawler()
    result = crawler._search({"code": "C09DB01"},1)
    print(result)