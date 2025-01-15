import requests
from datetime import datetime, timedelta
from flask import Blueprint, jsonify
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
weather_bp = Blueprint('weather', __name__, url_prefix='/api/weather')

class WeatherClient:
    def __init__(self):
        """Initialize the OpenMeteo client."""
        self.base_url = "https://api.open-meteo.com/v1"
        # Manchester, UK coordinates
        self.lat = 53.4808
        self.lon = -2.2426
        
    def get_weather(self):
        """Get current weather and forecast for Manchester."""
        try:
            # Get current weather and hourly forecast
            forecast_url = f"{self.base_url}/forecast"
            params = {
                'latitude': self.lat,
                'longitude': self.lon,
                'current_weather': True,
                'hourly': 'temperature_2m,apparent_temperature,precipitation_probability,weathercode,windspeed_10m',
                'timezone': 'Europe/London',
                'forecast_days': 2
            }
            
            response = requests.get(forecast_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Process current weather
            current = data['current_weather']
            current_weather = {
                'temp': round(current['temperature']),
                'wind_speed': current['windspeed'],
                'description': self._get_weather_description(current['weathercode'])
            }
            
            # Process hourly forecasts
            hourly = data['hourly']
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            
            today_forecasts = []
            tomorrow_forecasts = []
            
            for i in range(len(hourly['time'])):
                forecast_time = datetime.fromisoformat(hourly['time'][i])
                forecast_date = forecast_time.date()
                
                if forecast_time < datetime.now():
                    continue
                    
                forecast_info = {
                    'time': forecast_time.strftime('%H:%M'),
                    'temp': round(hourly['temperature_2m'][i]),
                    'feels_like': round(hourly['apparent_temperature'][i]),
                    'description': self._get_weather_description(hourly['weathercode'][i]),
                    'wind_speed': hourly['windspeed_10m'][i],
                    'precipitation_prob': hourly['precipitation_probability'][i]
                }
                
                if forecast_date == today:
                    today_forecasts.append(forecast_info)
                elif forecast_date == tomorrow:
                    tomorrow_forecasts.append(forecast_info)
            
            return {
                'current': current_weather,
                'today': today_forecasts,
                'tomorrow': tomorrow_forecasts
            }
            
        except Exception as e:
            logger.error(f"Error getting weather data: {str(e)}")
            raise
            
    def _get_weather_description(self, code):
        """Convert WMO Weather code to description."""
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        return weather_codes.get(code, "Unknown")

@weather_bp.route('/manchester', methods=['GET'])
def get_manchester_weather():
    """Get weather information for Manchester."""
    try:
        weather = WeatherClient()
        weather_data = weather.get_weather()
        
        return jsonify({
            'status': 'success',
            'data': weather_data
        })
        
    except Exception as e:
        logger.error(f"Error in get_manchester_weather: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 