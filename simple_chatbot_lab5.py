import datetime
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.error import BadRequest
import requests
import json
import asyncio
import os


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'WASZ TOKEN OD BOT FATHER')

# Stany konwersacji
PYTANIE = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('👋 Witaj! Jestem botem nawyków i asystentem. Użyj /help aby zobaczyć listę komend.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
    '''                                    
    /start rozpocznij czat 
    /weatherForecast Sprawdź prognozę pogody dla danego miast
    /currentWeather Sprawdź aktualną pogodę dla danego miast
    /geo <miasto> Znajdź współrzędne miejscowości
    /help pomoc
    ''')

async def geo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = context.args[0]
    if city == '':
        await update.message.reply_text(f'Nie podałeś/aś żadnego miasta. Wywołaj komendę /geo z miastem, np. /geo Kraków')
    
    latitude, longitude = getGeoData(city)
    await update.message.reply_text(f'Współrzędne dla miasta: {city} Szerokość geo: {latitude}, długość geo: {longitude} ')

async def weatherForecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Dla jakiego miasta chcesz sprawdzić prognozę pogody?')
    return PYTANIE

async def currentWeather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Dla jakiego miasta chcesz sprawdzić aktualną pogodę?')
    return PYTANIE

def interpret_weather_code(weather_code):
    """Proste mapowanie kodów pogody na opisy (można rozszerzyć)."""
    if weather_code == 0:
        return "Bezchmurnie"
    elif weather_code == 1:
        return "Głównie bezchmurnie"
    elif weather_code == 2:
        return "Częściowe zachmurzenie"
    elif weather_code == 3:
        return "Pochmurno"
    elif weather_code in [45, 48]:
        return "Mgła"
    elif weather_code in [51, 53, 55]:
        return "Mżawka"
    elif weather_code in [56, 57]:
        return "Marznąca mżawka"
    elif weather_code in [61, 63, 65]:
        return "Deszcz"
    elif weather_code in [66, 67]:
        return "Marznący deszcz"
    elif weather_code in [71, 73, 75]:
        return "Opady śniegu"
    elif weather_code in [77]:
        return "Krupa śnieżna"
    elif weather_code in [80, 81, 82]:
        return "Przelotne opady deszczu"
    elif weather_code in [85, 86]:
        return "Przelotne opady śniegu"
    elif weather_code in [95]:
        return "Burza"
    elif weather_code in [96, 99]:
        return "Burza z gradem"
    else:
        return f"Kod pogody: {weather_code}"

def getWeatherDescription(data):
    result = ''
    for index in range(4):
        result += f'''
        Na dzień {data['daily']['time'][index]}
        Temperatura min: {data['daily']['temperature_2m_min'][index]}°C | temperatura max: {data['daily']['temperature_2m_max'][index]}°C
        Opis pogody: {interpret_weather_code(data['daily']['weathercode'][index])}
        '''
    return result

def getGeoData(city):
    locationUrl = f'https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1'
    locationResponse = requests.get(locationUrl)
    if locationResponse.ok:
        data = locationResponse.json()
        latitude = data['results'][0]['latitude']
        longitude = data['results'][0]['longitude']
        return latitude, longitude
    else:
        print(f"Request failed with status code: {locationResponse.status_code}")

async def getWeatherForCity(city, currentWeather: bool):
        latitude, longitude = getGeoData(city)
        urlWeahter = f'https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=weathercode,temperature_2m_max,temperature_2m_min&current_weather=true&forecast_days=4'
        locationResponse = requests.get(urlWeahter)
        data = locationResponse.json()
        print(data)
        if(currentWeather):
            return f'''
            Aktualna prognoza dla miast: {city}.
            Temperatura: {data['current_weather']['temperature']}°C
            Prędkość wiatru: {data['current_weather']['windspeed']}km/h
            Opis pogody: {interpret_weather_code(data['current_weather']['weathercode'])}
            '''
        else:
            return f'''
            Prognoza pogody na dziś i 3 kolejne dni dla miasta {city}
            {getWeatherDescription(data)}
            '''


async def odpowiedzAktualnaPogoda(update, context):
    odpowiedz_uzytkownika = update.message.text
    response = await getWeatherForCity(odpowiedz_uzytkownika, True)
    await update.message.reply_text(response)
    return ConversationHandler.END

async def odpowiedzPrognoza(update, context):
    odpowiedz_uzytkownika = update.message.text
    response = await getWeatherForCity(odpowiedz_uzytkownika, False)
    await update.message.reply_text(response)
    return ConversationHandler.END

async def anuluj(update, context):
    await update.message.reply_text('Anulowano zapytanie.')
    return ConversationHandler.END


def main():
    logger.info('🚀 Bot started')
    app=ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start',start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('geo', geo_command))
    app.add_handler(
        ConversationHandler(
        entry_points=[CommandHandler('weatherForecast', weatherForecast_command)],
        states={
            PYTANIE: [MessageHandler(filters.TEXT & ~filters.COMMAND, odpowiedzPrognoza)]
        },
        fallbacks=[CommandHandler('anuluj', anuluj)]
    ))
    app.add_handler(
    ConversationHandler(
    entry_points=[CommandHandler('currentWeather', currentWeather_command)],
    states={
        PYTANIE: [MessageHandler(filters.TEXT & ~filters.COMMAND, odpowiedzAktualnaPogoda)]
    },
    fallbacks=[CommandHandler('anuluj', anuluj)]
    ))
    app.run_polling()

if __name__=='__main__':
    main()
