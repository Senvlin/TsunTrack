"""手动体验 TsunTrack 的傲娇报错(显式启用, 无需等待 pip 安装后的自动生效)."""


def calculate_discount(price, discount_percent):
    return price * (1 - discount_percent / 100)


def apply_coupon(order_total, coupon_code):
    discount = fetch_discount_from_db(coupon_code)
    return calculate_discount(order_total, discount)


def fetch_discount_from_db(code):
    # 模拟数据库返回错误类型
    return "20"


def main():
    total = 100
    final_price = apply_coupon(total, "SAVE20")
    print(f"最终价格: {final_price}")


if __name__ == "__main__":
    main()
