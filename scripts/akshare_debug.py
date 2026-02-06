from pathlib import Path
import os
import sys
import traceback
import requests


def test_eastmoney_requests() -> None:
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "100",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "m:1 t:2,m:1 t:23",
        "fields": ",".join(
            [
                "f1",
                "f2",
                "f3",
                "f4",
                "f5",
                "f6",
                "f7",
                "f8",
                "f9",
                "f10",
                "f12",
                "f13",
                "f14",
                "f15",
                "f16",
                "f17",
                "f18",
                "f20",
                "f21",
                "f23",
                "f24",
                "f25",
                "f22",
                "f11",
                "f62",
                "f128",
                "f136",
                "f115",
                "f152",
            ]
        ),
    }
    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cookie": "qgqp_b_id=ed061297d45155cc95afb780e54dbfe6; st_nvi=D4uYzazzkykjA1aS6LNk8cfa5; nid18=0150db99a319419a7da6b5ec8b6f4f0a; nid18_create_time=1764556612431; gviem=88dIb2LEB1wUrffN6IkZcba8e; gviem_create_time=1764556612432; _qimei_uuid42=1a1080c140510053f01f5379bed630916cee005a08; _qimei_i_3=22da2ad7c15c55d3939fab37528772e6f3baf6a0145e038bb7db2b0b7495276c693766943989e2bad2ab; _qimei_fingerprint=8d4be3a8285ba8736a947207f58ecc40; websitepoptg_api_time=1769677835323; st_si=49525768266231; st_asi=delete; fullscreengg=1; fullscreengg2=1; _qimei_h38=b885cc08f01f5379bed630910200000321a11d; st_pvi=70394726546128; st_sp=2025-10-28%2010%3A42%3A20; st_inirUrl=https%3A%2F%2Faisearch.sogou.com%2Flink; st_sn=3; st_psi=20260129223523560-113200301321-3541443859; _qimei_i_1=44c42bd09d5255889297f6665b8525e5f4e9ada3470f0581b48629582493206c6163349739d8e3dd828aafef",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
            (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36 Core/1.116.617.400 QQBrowser/20.1.7235.400"
        ),
    }
    try:
        print("开始进行纯 requests 测试 Eastmoney 接口")
        print("请求 URL:", url)
        print("请求参数:", params)
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print("HTTP 状态码:", response.status_code)
        print("响应头 Content-Type:", response.headers.get("Content-Type", ""))
        text = response.text
        print("响应内容长度:", len(text))
        preview = text[:500]
        print("响应内容前 500 字符:")
        print(preview)
    except Exception as e:
        print("纯 requests 调用 Eastmoney 接口失败")
        print("异常类型:", type(e).__name__)
        print("异常信息:", str(e))
        traceback.print_exc()


def main() -> None:
    print("Python executable:", sys.executable)
    print("Working directory:", os.getcwd())
    env_proxies = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"]
    for key in env_proxies:
        print(f"{key}={os.environ.get(key, '')}")
    try:
        import akshare as ak  # type: ignore
    except Exception as e:
        print("导入 akshare 失败")
        print("异常类型:", type(e).__name__)
        print("异常信息:", str(e))
        traceback.print_exc()
    else:
        print("akshare 版本:", getattr(ak, "__version__", "unknown"))
        try:
            print("开始调用 ak.stock_zh_a_spot_em()")
            df = ak.stock_zh_a_spot_em()
            print("调用成功")
            print("返回行数:", len(df))
            print("返回列:", list(df.columns))
            print("前五行:")
            print(df.head().to_string(index=False))
        except Exception as e:
            print("调用 ak.stock_zh_a_spot_em 失败")
            print("异常类型:", type(e).__name__)
            print("异常信息:", str(e))
            traceback.print_exc()
    print("")
    test_eastmoney_requests()


if __name__ == "__main__":
    main()
