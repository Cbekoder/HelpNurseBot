from aiogram import Bot, Dispatcher, types
from aiogram import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import json
import logging
import math

with open('env.json', 'r') as d:
    env = json.load(d)
BOT_TOKEN = env['BOT-TOKEN']
ADMINS = env['ADMINS'].split(',')[0]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

logging.basicConfig(level=logging.INFO)

with open('data.json', 'r') as d:
    data = json.load(d)
    allServices = data['services']
    NURSES = data['nurses']


class Patient(StatesGroup):
    user_id = State
    name = State()
    age = State()
    gender = State()

class ServiceChoice(StatesGroup):
    service_type = State()
    service_place = State()
    service = State()
    gender = State()
    long = State()
    lat = State()

class CreateNurse(StatesGroup):
    name = State()
    age = State()
    gender = State()
    long = State()
    lat = State()

class CreateHospital(StatesGroup):
    name = State()
    long = State()
    lat = State()
    services = State()

class CreateService(StatesGroup):
    name = State()
    type = State()

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    logging.info(f'Command from user id: {message.from_user.id}: {message.text}')
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [types.InlineKeyboardButton("Bir martalik muolajalar", callback_data="service_type_1"),
               types.InlineKeyboardButton("Davomiy mualajalar", callback_data="service_type_2"),]
    keyboard.add(*buttons)
    await message.answer(f"Assalomu alaykum, {message.from_user.first_name}!\nBu Help Nurse bot, yangi foydalanuvchilarga tibbiy muoalajalarda yordam berishi uchun hamshiralar yoki shifoxonalar topib beradi."
                         f"\nSizga qanday yordam bera olaman.\nKerakli bo'limni tanlang", reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data.startswith('service_type_'))
async def service_type(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    ser_type = query.data.split('_')[-1]
    if ser_type == '1':
        async with state.proxy() as data:
            data['service_type'] = "Bir martalik muolajalar"
    elif ser_type == '2':
        async with state.proxy() as data:
            data['service_type'] = "Davomiy mualajalar"
    keyboard = types.InlineKeyboardMarkup()
    buttons = [types.InlineKeyboardButton("Uydan", callback_data="service_place_1"),
               types.InlineKeyboardButton("Shifoxonadan", callback_data="service_place_2"), ]
    keyboard.add(*buttons)
    await query.message.answer("Sizga qayerdan muolaja olish qulay:", reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data.startswith('service_place_'))
async def service_type(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    ser_place = query.data.split('_')[-1]
    if ser_place == '1':
        async with state.proxy() as data:
            data['service_place'] = "Uydan"
    elif ser_place == '2':
        async with state.proxy() as data:
            data['service_place'] = "Shifoxonadan"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [types.InlineKeyboardButton(allServices[i], callback_data=f"service_name_{i}") for i in allServices]
    keyboard.add(*buttons)
    await query.message.edit_text("Sizga qaysi turdagi muolaja kerak:", reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data.startswith('service_name_'))
async def service_type(query: types.CallbackQuery, state: FSMContext):
    await bot.delete_message(query.message.chat.id, query.message.message_id)
    ser_type = query.data.split('_')[-1]
    async with state.proxy() as data:
        data['service'] = allServices[ser_type]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Joylashuv", request_location=True))
    await query.message.answer("Joriy joylashuvingizni yuboring:", reply_markup=keyboard)
    await ServiceChoice.long.set()

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c

    return distance
@dp.message_handler(state=ServiceChoice.long)
async def service_location(message: types.Message, state: FSMContext):
    if message.location:
        async with state.proxy() as data:
            data['long'] = message.location.longitude
            data['lat'] = message.location.latitude
            serviceChoice = {
                "service_type" : data["service_type"],
                "service_place" : data["service_place"],
                "service" : data["service"],
                "long" : data["long"],
                "lat" : data["lat"]
            }
            await state.finish()
            if serviceChoice["service_place"] == "Uydan":
                min_length = {}
                for i in NURSES:
                    print(NURSES[i])


    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Joylashuv", request_location=True))
        await message.answer("Joylashuv yuboring:")
        await ServiceChoice.long.set()



async def send_nearest_choice(user_location, choices):
    min_distance = float('inf')
    nearest_choice = None
    for choice in choices:
        distance = calculate_distance(user_location.latitude, user_location.longitude, choice['lat'], choice['long'])
        if distance < min_distance:
            min_distance = distance
            nearest_choice = choice
    return nearest_choice

async def send_nearest_nurse_or_hospital(message, choices):
    user_location = message.location
    nearest_choice = await send_nearest_choice(user_location, choices)

    if nearest_choice:
        await message.answer(f"The nearest {nearest_choice['type']} is {nearest_choice['name']} located at {nearest_choice['long']}, {nearest_choice['lat']}")
    else:
        await message.answer("No nearby nurses or hospitals found.")




@dp.message_handler(commands=["admin"], user_id=ADMINS)
async def cmd_admin(message: types.Message):
    logging.info(f'Command from user id: {message.from_user.id}: {message.text}')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Yangi Hamshira",callback_data="new_1"))
    keyboard.add(types.InlineKeyboardButton("Yangi Shifoxona",callback_data="new_2"))
    keyboard.add(types.InlineKeyboardButton("Yangi Xizmat",callback_data="new_3"))
    await message.answer(f"Assalomu alaykum, {message.from_user.first_name}!\nBu Help Nurse bot, va siz admin sifatida belgilangansiz."
                         f"\nKerakli bo'limni tanlang:", reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data.startswith('new_'))
async def service_type_admin(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    pk = query.data.split("_")[-1]
    if pk == "1":
        await query.message.answer("Yangi hamshira ismi familyasini kiriting:")
        await CreateNurse.name.set()
    elif pk == "2":
        await query.message.answer("Yangi shifoxona nomini kiriting:")
        await CreateHospital.name.set()
    elif pk == "3":
        await query.message.answer("Yangi xizmat nomini kiriting:")
        await CreateService.name.set()

@dp.message_handler(state=CreateNurse.name)
async def getNurseName(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("Hamshira uchun joylashuv yuboring:", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("Joylashuv yuborish", request_location=True)))
    await CreateNurse.long.set()

@dp.message_handler(state=CreateNurse.long)
async def getNurseLong(message: types.Location, state: FSMContext):
    logging.info(message)
    if message.location:
        print(message.location)
        async with state.proxy() as data:
            data['long'] = message.location.longitude
            data['lat'] = message.location.latitude
    logging.info(data['long'], data['lat'])


async def shutdown(dp):
    await dp.bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown)