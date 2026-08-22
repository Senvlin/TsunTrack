import random
import threading
import time


def process_data(data_id):
    """模拟数据处理函数，根据 data_id 决定是否出错"""
    time.sleep(random.uniform(0.1, 0.5))  # 模拟耗时操作
    if data_id % 3 == 0:
        # 故意抛出不同类型的异常
        if data_id % 6 == 0:
            raise ValueError(f"数据 {data_id} 的值非法")
        else:
            raise KeyError(f"数据 {data_id} 缺少必要字段")
    return data_id * 10


def worker(data_id):
    try:
        result = process_data(data_id)
        print(f"处理成功: {data_id} -> {result}")
    except Exception:
        raise


def main():
    threads = []
    for i in range(1, 11):  # 启动 10 个线程
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    # 等待所有线程结束
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
    raise RuntimeError("主线程故意抛出一个异常")
