import asyncio
import random


# 模拟真实爬虫的网络请求层
async def fetch_html(url):
    await asyncio.sleep(random.uniform(0.1, 0.5))  # 模拟网络延迟

    if "error" in url:
        # 情况1：日常最常见的 DNS 解析失败/网络阻断
        raise ConnectionError(f"无法连接到服务器: {url} (DNS解析失败)")

    if "timeout" in url:
        # 情况2：请求超时
        raise TimeoutError(f"请求 {url} 超时（超过了设定的 5 秒）")

    # 正常返回HTML
    return f"<html><body><div class='item'>{url}</div></body></html>"


# 模拟真实爬虫的解析层 (类似 BeautifulSoup / lxml)
async def parse_html(url, html):
    await asyncio.sleep(0.1)
    if "empty" in url:
        # 情况3：页面结构发生变化，找不到目标元素
        raise AttributeError(f"在 {url} 中未找到目标 CSS 选择器 '.item-price'")
    return f"{url} -> 成功提取到商品价格: $100"


# 并发处理任务
async def process_url(url):
    html = await fetch_html(url)
    result = await parse_html(url, html)
    print(result)
    return result


async def main_crawl():
    # 真实爬虫的 URL 队列
    urls = [
        "https://shop.com/page1",  # 正常
        "https://shop.com/error",  # 报错：连接失败
        "https://shop.com/empty",  # 报错：解析字段缺失
        "https://shop.com/page2",  # 正常
        "https://shop.com/timeout",  # 报错：超时
    ]

    print("开始使用 asyncio 并发模拟真实爬虫...\n")

    # 真实爬虫中，通常是用 create_task 或 gather 并发执行。
    # 如果没有做异常隔离（即没有 return_exceptions=True），遇到错误会直接中断整个爬虫任务。
    tasks = [
        asyncio.create_task(
            process_url(url),
        )
        for url in urls
    ]

    # 触发崩溃：没有任何捕获，直接抛给系统
    await asyncio.gather(*tasks, return_exceptions=True)

    print("所有爬取任务完成")  # 这行不会执行


if __name__ == "__main__":
    asyncio.run(main_crawl())
