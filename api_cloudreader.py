# -*- coding: utf-8 -*-
'''
CloudReader 玩安卓接口调试脚本 (requests, 不需要 Appium)

对应 CloudReader 里 app/src/main/java/.../http/HttpClient.java 的接口:
  POST /user/login                 登录           表单: username, password
  POST /user/register              注册           表单: username, password, repassword
  GET  /user/logout/json           退出
  POST /article/query/{page}/json  搜索文章       表单: k
  GET  /article/list/{page}/json   首页文章列表
  GET  /hotkey/json                热门搜索词
  GET  /lg/collect/list/{page}/json 收藏列表      需要登录(带 Cookie)
  GET  /lg/coin/userinfo/json       个人积分      需要登录(带 Cookie)

脚本用同一个 requests.Session 保存 JSESSIONID 等 Cookie, 所以登录后的接口才能拿到数据。
Postman 里想复现: 先 POST /user/login, 再从响应头 Set-Cookie 里把 Cookie 复制到后续请求。

用法:
  python api_cloudreader.py                          # 登录 + 查询
  python api_cloudreader.py --register               # 先注册再登录
  python api_cloudreader.py -u test00300 -p 123456 -k Android
'''

import argparse
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")   # 控制台中文输出
except Exception:
    pass

import requests

BASE_URL = "https://www.wanandroid.com/"
DEFAULT_USERNAME = "test00300"
DEFAULT_PASSWORD = "123456"

session = requests.Session()
session.headers.update({"User-Agent": "CloudReader-AutoTest/1.0"})


def show_response(name, response):
    '''统一打印: HTTP 状态 + errorCode / errorMsg'''
    print("[%s]" % name)
    print("  HTTP", response.status_code)
    try:
        body = response.json()
    except ValueError:
        print("  非 JSON 响应:", response.text[:200].replace("\n", " "))
        return None
    print("  errorCode=%s errorMsg=%s" % (body.get("errorCode"), body.get("errorMsg")))
    return body


def register(username, password):
    response = session.post(BASE_URL + "user/register", data={
        "username": username,
        "password": password,
        "repassword": password,
    })
    return show_response("注册 POST /user/register", response)


def login(username, password):
    response = session.post(BASE_URL + "user/login", data={
        "username": username,
        "password": password,
    })
    body = show_response("登录 POST /user/login", response)
    if body and body.get("errorCode") == 0 and body.get("data"):
        data = body["data"]
        print("  用户:", data.get("nickname") or data.get("username"), "| id:", data.get("id"))
        print("  Cookie:", session.cookies.get_dict())
    return body


def logout():
    return show_response("退出 GET /user/logout/json", session.get(BASE_URL + "user/logout/json"))


def search(keyword, page=0):
    url = BASE_URL + "article/query/{0}/json".format(page)
    body = show_response("搜索 POST /article/query/%d/json (k=%s)" % (page, keyword),
                         session.post(url, data={"k": keyword}))
    if body and body.get("data"):
        datas = body["data"].get("datas") or []
        print("  命中", body["data"].get("total"), "条, 本页", len(datas), "条:")
        for item in datas[:5]:
            print("    -", item.get("title"))
    return body


def article_list(page=0):
    url = BASE_URL + "article/list/{0}/json".format(page)
    body = show_response("首页文章 GET /article/list/%d/json" % page, session.get(url))
    if body and body.get("data"):
        datas = body["data"].get("datas") or []
        print("  本页", len(datas), "条", ("| 首条: %s" % datas[0].get("title")) if datas else "")
    return body


def hotkey():
    body = show_response("热门搜索词 GET /hotkey/json", session.get(BASE_URL + "hotkey/json"))
    if body and body.get("data"):
        print("  ", " / ".join(item.get("name", "") for item in body["data"][:8]))
    return body


def collect_list(page=0):
    url = BASE_URL + "lg/collect/list/{0}/json".format(page)
    body = show_response("收藏列表 GET /lg/collect/list/%d/json" % page, session.get(url))
    if body and body.get("data"):
        datas = body["data"].get("datas") or []
        print("  已收藏", body["data"].get("total"), "条", ("| 首条: %s" % datas[0].get("title")) if datas else "")
    return body


def coin_userinfo():
    body = show_response("个人积分 GET /lg/coin/userinfo/json", session.get(BASE_URL + "lg/coin/userinfo/json"))
    if body and body.get("data"):
        data = body["data"]
        print("  %s | 积分: %s | 排名: %s" % (data.get("username"), data.get("coinCount"), data.get("rank")))
    return body


def main():
    parser = argparse.ArgumentParser(description="CloudReader 玩安卓接口调试脚本")
    parser.add_argument("-u", "--username", default=DEFAULT_USERNAME, help="玩安卓账号")
    parser.add_argument("-p", "--password", default=DEFAULT_PASSWORD, help="玩安卓密码")
    parser.add_argument("-k", "--keyword", default="Android", help="搜索关键词")
    parser.add_argument("--register", action="store_true", help="先调用注册接口再登录")
    parser.add_argument("--logout", action="store_true", help="结束后调用退出接口")
    args = parser.parse_args()

    try:
        if args.register:
            register(args.username, args.password)

        body = login(args.username, args.password)
        if not body or body.get("errorCode") != 0:
            print("登录失败, 下面需要登录的接口会返回 -1001 (未登录)")

        search(args.keyword)
        article_list()
        hotkey()
        collect_list()
        coin_userinfo()

        if args.logout:
            logout()
    except requests.RequestException as exc:
        print("请求异常:", exc)
        print("请确认网络能访问", BASE_URL)

    print("=== 接口调试结束 ===")


if __name__ == "__main__":
    main()
