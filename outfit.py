"""穿搭推荐模块"""
from weather import WeatherData


# 温度区间定义
TEMP_RULES = [
    {"min": 28, "max": 100, "top": "短袖", "bottom": "短裤/薄裙",
     "shoes": "凉鞋/运动鞋", "accessories": ["太阳镜", "防晒霜"]},
    {"min": 22, "max": 28, "top": "短袖/薄长袖", "bottom": "长裤/裙子",
     "shoes": "运动鞋", "accessories": []},
    {"min": 15, "max": 22, "top": "长袖/薄外套", "bottom": "长裤",
     "shoes": "运动鞋", "accessories": []},
    {"min": 5, "max": 15, "top": "毛衣/卫衣", "bottom": "厚长裤",
     "shoes": "靴子", "accessories": ["围巾"]},
    {"min": -100, "max": 5, "top": "羽绒服/厚外套", "bottom": "棉裤",
     "shoes": "棉靴", "accessories": ["手套", "帽子", "围巾"]},
]


def _get_temp_rule(temp: float) -> dict:
    """根据温度获取穿搭规则"""
    for rule in TEMP_RULES:
        if rule["min"] <= temp < rule["max"]:
            return rule
    return TEMP_RULES[-1]


def _get_condition_accessory(condition: str) -> list:
    """根据天气状况获取额外配件建议"""
    condition = condition.lower()
    if "雨" in condition:
        return ["🌂 雨伞", "防水鞋"]
    if "雪" in condition:
        return ["🧤 手套", "保暖配件"]
    if "风" in condition or "大风" in condition:
        return ["🧢 防风帽", "防风外套"]
    if "晴" in condition and "太阳" not in condition:
        return ["🕶️ 太阳镜"]
    return []


def _format_accessories(base_accessories: list, extra_accessories: list) -> str:
    """格式化配件列表"""
    all_items = base_accessories + extra_accessories
    if not all_items:
        return "无"
    return "、".join(all_items)


class OutfitRecommender:
    """穿搭推荐器"""

    def recommend(self, weather: WeatherData, days_ahead: int = 0) -> dict:
        """推荐穿搭

        Args:
            weather: 天气数据
            days_ahead: 预报天数（0=今天）

        Returns:
            穿搭建议字典
        """
        if days_ahead > 0 and weather.forecast:
            # 获取预报日的温度
            if days_ahead < len(weather.forecast):
                forecast_day = weather.forecast[days_ahead]
                temp = (forecast_day["temp_max"] + forecast_day["temp_min"]) / 2
                condition = forecast_day["condition"]
            else:
                return self._default_recommend()
        else:
            temp = weather.temp
            condition = weather.condition

        temp_rule = _get_temp_rule(temp)
        extra_acc = _get_condition_accessory(condition)

        return {
            "top": temp_rule["top"],
            "bottom": temp_rule["bottom"],
            "shoes": temp_rule["shoes"],
            "accessories": _format_accessories(temp_rule["accessories"], extra_acc),
            "temperature": temp,
            "condition": condition,
        }

    def _default_recommend(self) -> dict:
        """默认推荐"""
        return {
            "top": "长袖",
            "bottom": "长裤",
            "shoes": "运动鞋",
            "accessories": "无",
            "temperature": 20,
            "condition": "未知",
        }


def recommend_outfit(weather: WeatherData, days_ahead: int = 0) -> dict:
    """便捷函数：推荐穿搭"""
    recommender = OutfitRecommender()
    return recommender.recommend(weather, days_ahead)
