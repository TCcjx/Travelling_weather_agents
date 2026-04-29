"""天气数据获取模块"""
import os
import ssl
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 临时绕过 SSL 验证（某些网络环境下需要）
ssl._create_default_https_context = ssl._create_unverified_context

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class WeatherAPIError(Exception):
    """天气API异常"""
    pass


class WeatherData:
    """天气数据结构"""

    def __init__(self, city: str, temp: float, feels_like: float,
                 humidity: int, wind_speed: float, condition: str,
                 forecast: List[Dict] = None):
        self.city = city
        self.temp = temp
        self.feels_like = feels_like
        self.humidity = humidity
        self.wind_speed = wind_speed
        self.condition = condition
        self.forecast = forecast or []

    def __str__(self):
        return (f"WeatherData(city={self.city}, temp={self.temp}°C, "
                f"condition={self.condition})")


def get_weather(city: str, api_key: Optional[str] = None) -> WeatherData:
    """获取天气数据（使用真实API）"""
    api_key = api_key or os.getenv("WEATHER_API_KEY")
    if not api_key:
        raise WeatherAPIError("未设置 WEATHER_API_KEY")
    if not HAS_REQUESTS:
        raise WeatherAPIError("requests 库未安装")
    return _get_real_weather(city, api_key)


def _get_real_weather(city: str, api_key: str) -> WeatherData:
    """调用真实API获取天气"""
    base_url = "https://api.weatherapi.com/v1"
    try:
        # 创建禁用代理的 session
        session = requests.Session()
        session.trust_env = False

        # 获取当前天气
        current_resp = session.get(
            f"{base_url}/current.json",
            params={"key": api_key, "q": city, "lang": "zh"},
            timeout=10
        )
        current_resp.raise_for_status()
        current_data = current_resp.json()["current"]

        # 获取预报
        forecast_resp = session.get(
            f"{base_url}/forecast.json",
            params={"key": api_key, "q": city, "days": 7, "lang": "zh"},
            timeout=10
        )
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()["forecast"]["forecastday"]

        # 解析预报数据
        forecast = []
        for day in forecast_data:
            forecast.append({
                "date": day["date"],
                "temp_max": day["day"]["maxtemp_c"],
                "temp_min": day["day"]["mintemp_c"],
                "condition": day["day"]["condition"]["text"],
                "icon": day["day"]["condition"]["icon"],
            })

        return WeatherData(
            city=city,
            temp=current_data["temp_c"],
            feels_like=current_data["feelslike_c"],
            humidity=current_data["humidity"],
            wind_speed=current_data["wind_kph"],
            condition=current_data["condition"]["text"],
            forecast=forecast
        )
    except Exception as e:
        raise WeatherAPIError(f"获取天气失败: {e}")


def get_mock_weather(city: str) -> WeatherData:
    """返回模拟天气数据"""
    today = datetime.now()
    conditions = ["晴", "多云", "阴", "小雨", "雷阵雨", "晴"]

    # 生成7天预报
    forecast = []
    for i in range(7):
        date = today + timedelta(days=i)
        # 模拟温度波动
        base_temp = 20 + (i % 3) * 3 - 5
        condition = conditions[(i + 2) % len(conditions)]
        forecast.append({
            "date": date.strftime("%Y-%m-%d"),
            "temp_max": base_temp + 5,
            "temp_min": base_temp - 3,
            "condition": condition,
            "icon": "",
        })

    return WeatherData(
        city=city,
        temp=forecast[0]["temp_max"],
        feels_like=forecast[0]["temp_max"] - 2,
        humidity=65,
        wind_speed=12.0,
        condition=forecast[0]["condition"],
        forecast=forecast
    )


def get_forecast_for_date(weather: WeatherData, days_ahead: int) -> Optional[Dict]:
    """获取指定日期后的天气预报"""
    if not weather.forecast:
        return None
    if days_ahead < len(weather.forecast):
        return weather.forecast[days_ahead]
    return None
