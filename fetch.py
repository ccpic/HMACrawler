from wsgiref import headers
import requests
import json
import pandas as pd
from termcolor import cprint
import time
from fake_useragent import UserAgent
from numpy import random
from hyper.contrib import HTTP20Adapter
from urllib.parse import urlencode, urlparse
from lxml import etree

HEADERS = {
    # r":authority": "www.drugfuture.com",
    # r":method": "GET",
    # r":path": "/hma",
    # r":scheme": "https",
    # r"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    # r"accept-encoding": "gzip, deflate, br",
    # r"accept-language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
    # r"cache-control": "no-cache",
    # r"cookie": "ASP.NET_SessionId=f2vomffxchuuy3jvh0ncry2e; UM_distinctid=17fdf05f5fbaf-06d3b48b900148-1f343371-1fa400-17fdf05f5fc977; CNZZDATA134747=cnzz_eid%3D945523864-1648705386-%26ntime%3D1648705386; ASPSESSIONIDSWTCBRSA=MCKDFFJCKAMHDHDBNBFNDFHN; __51vcke__JeYGFzNXOyg2JqHb=2e971c74-7216-5dbf-a5ba-91517bc430cf; __51vuft__JeYGFzNXOyg2JqHb=1649830279847; ASPSESSIONIDSUCAASDC=KOBFALLCMIPCKMCGPMEKFJHB; ASPSESSIONIDSWCBCTDD=FLJKIJDDLMBPNDGIGOCAKKHM; __51uvsct__JeYGFzNXOyg2JqHb=3; __vtins__JeYGFzNXOyg2JqHb=%7B%22sid%22%3A%20%22c88b7aab-5c53-5916-a904-0f7f8345de62%22%2C%20%22vd%22%3A%2012%2C%20%22stt%22%3A%20709849%2C%20%22dr%22%3A%2041388%2C%20%22expires%22%3A%201649839906028%2C%20%22ct%22%3A%201649838106028%7D",
    # r"origin": "https://www.drugfuture.com",
    # r"pragma": "no=cache",
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
            http请求头中的引荐网址字段, by default None

        Returns
        -------
        dict
            包含浏览器header参数的字典
        """

        headers = HEADERS.copy()
        if referer is not None:
            headers[r"Referer"] = referer

        ua = UserAgent()
        headers[r"user-agent"] = ua.random

        return headers

    def search(self, search_cond: dict) -> pd.DataFrame:
        """根据搜索条件返回满足条件的批量药物信息

        Parameters
        ----------
        search_cond : dict
            搜索字段和输入条件，同_get_links的参数

        Returns
        -------
        pd.DataFrame
            满足搜索条件的所有药物信息的一个pandas df
        """
        links = self._get_links(search_cond)
        number_of_links = len(links)

        df_combined = pd.DataFrame()
        link_number = 1
        for link in links:
            print(f"{link_number}/{number_of_links}")
            df = self._get_detail(link)
            for key, value in search_cond.items():
                df[key] = value
            df_combined = pd.concat([df_combined, df])

            link_number += 1

        return df_combined

    def _get_links(self, search_cond: dict) -> list:
        """根据搜索条件返回满足条件的药物的详情页url list

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

        Returns
        -------
        list
            满足搜索条件的所有药物详情页url list
        """

        payload = {"SearchType": "AdvancedSearch"}  # 指定搜索条件需要加入SearchType字段
        for key, value in search_cond.items():
            payload[key] = value

        url_origin = "https://www.drugfuture.com/hma/search.aspx"

        # 翻页至最后以获取完整的搜索结果
        search_result = []
        page = 1
        while True:
            payload["page"] = page
            print(payload)
            r = requests.get(url_origin, params=payload)

            if r.text == "":  # 根据返回内容是否为空来判断最后一页
                break
            else:
                root = etree.HTML(r.text)
                links = root.xpath(
                    './/*[@class="content"]/table/tbody/tr/td[1]/a/@href'
                )  # 每个类型为content的表格的第一列单元格有跳转到药物详情页的链接
                for link in links:
                    search_result.append(link)
                page += 1

        search_result = [
            "https://" + urlparse(url_origin).netloc + x for x in search_result
        ]  # 原爬取链接为相对路径，增加domain方便之后使用

        return search_result

    def _get_detail(self, url: str) -> pd.DataFrame:
        """根据药品详情页url获取一个包含所有信息的pandas df

        Parameters
        ----------
        url : str
            药品详情页url

        Returns
        -------
        pd.DataFrame
            一个包含所有信息的pandas df，列为字段，行为数据
        """

        r = requests.get(url)
        html = r.text.replace(
            "<tr><th>申请类型</th>", "</tr><tr><th>申请类型</th>"
        )  # 修复网站本身的一个bug，少了一个</tr>会造成之后的解析错误
        html = html.replace(
            "</li><li>", "</li>, <li>"
        )  # <li>间增加逗号分隔，否则pd.read_html会把相邻<li></li>中的内容连在一起

        root = etree.HTML(html)
        table = root.xpath('.//*[@class="table-1"]')
        table = etree.tostring(table[0], method="html")
        df = (
            pd.read_html(table)[0].set_index(0).transpose()
        )  # 转换为pandas df方便后续处理，一个detail表格转换为df的一行

        return df


if __name__ == "__main__":
    atc_list = [
        "C09DB01",  # valsartan and amlodipine
        "C09DB02",  # olmesartan medoxomil and amlodipine
        "C09DB04",  # telmisartan and amlodipine
        "C09DB05",  # irbesartan and amlodipine
        "C09DB06",  # losartan and amlodipine
        "C09DB07",  # candesartan and amlodipine
        "C09DB08",  # valsartan and lercanidipine
        "C09DB09",  # fimasartan and amlodipine
        "C09DA01",  # losartan and diuretics
        "C09DA02",  # eprosartan and diuretics
        "C09DA03",  # valsartan and diuretics
        "C09DA04",  # irbesartan and diuretics
        "C09DA06",  # candesartan and diuretics
        "C09DA07",  # telmisartan and diuretics
        "C09DA08",  # olmesartan medoxomil and diuretics
        "C09DA09",  # azilsartan medoxomil and diuretics
        "C09DA10",  # fimasartan and diuretics
        "C09DX01",  # valsartan, amlodipine and hydrochlorothiazide
        "C09DX02",  # valsartan and aliskiren
        "C09DX03",  # olmesartan medoxomil, amlodipine and hydrochlorothiazide
        "C09DX04",  # valsartan and sacubitril
        "C09DX05",  # valsartan and nebivolol
        "C09DX06",  # candesartan, amlodipine and hydrochlorothiazide
        "C09DX07",  # irbesartan, amlodipine and hydrochlorothiazide
        "C09BA01",  # captopril and diuretics
        "C09BA02",  # enalapril and diuretics
        "C09BA03",  # lisinopril and diuretics
        "C09BA04",  # perindopril and diuretics
        "C09BA05",  # ramipril and diuretics
        "C09BA06",  # quinapril and diuretics
        "C09BA07",  # benazepril and diuretics
        "C09BA08",  # cilazapril and diuretics
        "C09BA09",  # fosinopril and diuretics
        "C09BA12",  # delapril and diuretics
        "C09BA13",  # moexipril and diuretics
        "C09BA15",  # zofenopril and diuretics
        "C09BB02",  # enalapril and lercanidipine
        "C09BB03",  # lisinopril and amlodipine
        "C09BB04",  # perindopril and amlodipine
        "C09BB05",  # ramipril and felodipine
        "C09BB06",  # enalapril and nitrendipine
        "C09BB07",  # ramipril and amlodipine
        "C09BB10",  # trandolapril and verapamil
        "C09BB12",  # delapril and manidipine
        "C09BX01",  # perindopril, amlodipine and indapamide
        "C09BX02",  # perindopril and bisoprolol
        "C09BX03",  # ramipril, amlodipine and hydrochlorothiazide
        "C09BX04",  # perindopril, bisoprolol and amlodipine
        "C09BX05",  # ramipril and bisoprolol
    ]

    crawler = HMACrawler()
    df_combined = pd.DataFrame()
    for atc in atc_list:
        df = crawler.search({"code": atc})
        df_combined = pd.concat([df_combined, df])
    df_combined.to_excel("test.xlsx")

    # result = crawler._get_detail(
    #     "https://www.drugfuture.com/hma/drugview/5fd5c95b-18de-408d-6060-08d9d454b323"
    # )
    # print(result)
