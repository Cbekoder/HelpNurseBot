from aiogram import Bot, Dispatcher, types
from aiogram import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import ContentTypeFilter
from math import radians, sin, cos, sqrt, atan2
import re
import json
import logging
import math
import requests

with open('env.json', 'r') as d:
    env = json.load(d)
BOT_TOKEN = env['BOT-TOKEN']
BASE_URL = env['BASE_URL']
ADMINS = env['ADMINS'].split(',')[0]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

logging.basicConfig(level=logging.INFO)


def GetBaseData():
    global SERVICES, NURSES, HOSPITALS
    SERVICES = requests.get(BASE_URL + "/services/").json()
    NURSES = requests.get(BASE_URL + "/nurses/").json()
    HOSPITALS = requests.get(BASE_URL + "/hospitals/").json()


class Patient(StatesGroup):
    user_id = State
    name = State()
    age = State()
    gender = State()


class ServiceChoice(StatesGroup):
    service_place = State()
    service = State()
    gender = State()
    long = State()
    lat = State()


class CreateNurse(StatesGroup):
    name = State()
    age = State()
    photo = State()
    gender = State()
    phone = State()
    long = State()
    lat = State()


class CreateHospital(StatesGroup):
    name = State()
    phone = State()
    working_hours = State()
    working_days = State()
    long = State()
    lat = State()


class CreateService(StatesGroup):
    name = State()


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    logging.info(f'Command from user id: {message.from_user.id}: {message.text}')
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [types.InlineKeyboardButton("Ha", callback_data="service_type_1"),
               types.InlineKeyboardButton("Yo'q", callback_data="service_type_2"), ]
    keyboard.add(*buttons)
    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}!\nBu Help Nurse bot, yangi foydalanuvchilarga tibbiy muoalajalarda yordam berishi uchun hamshiralar yoki shifoxonalar topib beradi."
        f"\nFoydalanishdan avval foydalanish qo'llanmasini o'qib chiqing.\n")
    await message.answer("""Policyda shuni ko'rsatadiki, 
bemorlar botdan foydalanganda, ular hamshiralar ma'lumotlarini faqat sog'liq bilan bog'liq maqsadlarda almashishga rozi bo'lishadi. 
Ularga botdan noto'g'ri foydalanish yoki boshqa sabablarga ko'ra hamshiralarni bezovta qilish taqiqlanadi. 
Siz bu policyga rozimisiz?""", reply_markup=keyboard)


@dp.callback_query_handler(lambda query: query.data.startswith('service_type_'))
async def service_type(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    ser_type = query.data.split('_')[-1]
    if ser_type == '1':
        keyboard = types.InlineKeyboardMarkup()
        buttons = [types.InlineKeyboardButton("Uydan", callback_data="service_place_1"),
                   types.InlineKeyboardButton("Shifoxonadan", callback_data="service_place_2"), ]
        keyboard.add(*buttons)
        await query.message.edit_text("Sizga qayerdan muolaja olish qulay:", reply_markup=keyboard)
    elif ser_type == '2':
        await query.message.edit_text(
            "Foydalanish siyosatiga rozilik bermasangiz botdan foydalana olmaysiz.\nPolicyni olish uchun botni qaytadan ishga tushiring: /start",
            reply_markup=types.ReplyKeyboardRemove())


@dp.callback_query_handler(lambda query: query.data.startswith('service_place_'))
async def service_type(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    ser_place = query.data.split('_')[-1]
    if ser_place == '1':
        async with state.proxy() as data:
            data['service_place'] = "home"
    elif ser_place == '2':
        async with state.proxy() as data:
            data['service_place'] = "hospital"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [types.InlineKeyboardButton(service['name'], callback_data=f"service_name_{service['id']}") for service in
               SERVICES]
    keyboard.add(*buttons)
    await query.message.edit_text("Sizga qaysi turdagi muolaja kerak:", reply_markup=keyboard)


@dp.callback_query_handler(lambda query: query.data.startswith('service_name_'))
async def service_name(query: types.CallbackQuery, state: FSMContext):
    ser_type = int(query.data.split('_')[-1])
    async with state.proxy() as data:
        data['service'] = ser_type
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("Joylashuv", request_location=True))
    await query.message.answer("Joriy joylashuvingizni yuboring:", reply_markup=keyboard)
    await ServiceChoice.long.set()


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance


@dp.message_handler(state=ServiceChoice.long, content_types=types.ContentTypes.LOCATION)
async def service_location(message: types.ContentType.LOCATION, state: FSMContext):
    logging.info(message)
    if message.location:
        logging.info(message)
        async with state.proxy() as data:
            data['long'] = message.location.longitude
            data['lat'] = message.location.latitude
            serviceChoice = {
                "service_place": data["service_place"],
                "service": data["service"],
                "long": data["long"],
                "lat": data["lat"]
            }
        await state.finish()
        if serviceChoice["service_place"] == "home":
            url = f"{BASE_URL}/locationalNurse/{str(serviceChoice['long'])}/{str(serviceChoice['lat'])}/{serviceChoice['service']}"
            response = requests.get(url)
            await message.answer("Sizning joylashuvingiz bo'yicha quyidagi hamshiralarni tavsiya qila olaman:")
            if response.status_code == 200:
                lNurse = response.json()
                print(lNurse)
                for nurse in lNurse:
                    res_text = f"Ismi: {nurse['name']}\nYoshi: {nurse['age']}\nJinsi: {nurse['gender']}\nTelefon raqami: {nurse['phone_number']}\nMasofa: {round(nurse['distance'], 2)}km"
                    if nurse['photo'] is not None:
                        photosent = await bot.send_photo(message.from_user.id, nurse["photo"], caption=res_text)
                    else:
                        photosent = await message.answer(res_text)
                    await photosent.reply_location(nurse["lat"], nurse["long"], reply_markup=types.ReplyKeyboardRemove())
            else:
                await message.answer("Hamshiralar topilmadi!")


        elif serviceChoice["service_place"] == "hospital":
            url = f"{BASE_URL}/locationalHospital/{str(serviceChoice['long'])}/{str(serviceChoice['lat'])}/{serviceChoice['service']}"
            response = requests.get(url)
            await message.answer("Sizning joylashuvingiz bo'yicha quyidagi shifoxonalarni tavsiya qila olaman:")
            if response.status_code == 200:
                lHospital = response.json()
                for hospital in lHospital:
                    res_text = f"Nomi: {hospital['name']}\nIsh vaqti: {hospital['working_hours']}\nIsh kunlari: {hospital['working_days']}\nTelefon raqami: {hospital['phone_number']}\n"
                    locat = await bot.send_location(message.from_user.id, hospital["lat"], hospital["long"])
                    await locat.reply(res_text)
            else:
                await message.answer("Shifoxonalar topilmadi!")

    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Joylashuv", request_location=True))
        await message.answer("Joylashuv yuboring:")
        await ServiceChoice.long.set()


############# ADMIN #######################

ADMIN_KEYBOARD = types.InlineKeyboardMarkup()
ADMIN_KEYBOARD.add(types.InlineKeyboardButton("Yangi Hamshira", callback_data="new_1"))
ADMIN_KEYBOARD.add(types.InlineKeyboardButton("Yangi Shifoxona", callback_data="new_2"))
ADMIN_KEYBOARD.add(types.InlineKeyboardButton("Yangi Xizmat", callback_data="new_3"))


@dp.message_handler(commands=["admin"], user_id=ADMINS)
async def cmd_admin(message: types.Message):
    logging.info(f'Command from user id: {message.from_user.id}: {message.text}')
    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}!\nBu Help Nurse bot, va siz admin sifatida belgilangansiz."
        f"\nKerakli bo'limni tanlang:", reply_markup=ADMIN_KEYBOARD)


@dp.callback_query_handler(lambda query: query.data.startswith('new_'))
async def service_type_admin(query: types.CallbackQuery):
    await query.answer()
    pk = query.data.split("_")[-1]
    if pk == "1":
        await query.message.edit_text("Yangi hamshira 👩‍⚕️ ismi familyasini kiriting:")
        await CreateNurse.name.set()
    elif pk == "2":
        await query.message.edit_text("Yangi shifoxona nomini kiriting:")
        await CreateHospital.name.set()
    elif pk == "3":
        await query.message.edit_text("Yangi xizmat turining nomini kiriting:")
        await CreateService.name.set()


######## CREATE NURSE ##########
@dp.message_handler(state=CreateNurse.name)
async def getNurseName(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("Hamshira rasmini yuboring:")
    await CreateNurse.photo.set()


@dp.message_handler(content_types=types.ContentType.PHOTO, state=CreateNurse.photo)
async def getPhoto(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['photo'] = message.photo[-1].file_id
    await message.answer("Hamshira yoshini kiriting:")
    await CreateNurse.age.set()


@dp.message_handler(state=CreateNurse.age)
async def getNurseAge(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        async with state.proxy() as data:
            data['age'] = message.text
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2, resize_keyboard=True)
        buttons = [types.KeyboardButton(text="Erkak"), types.KeyboardButton(text="Ayol"), ]
        keyboard.add(*buttons)
        await message.answer("Hamshira jinsini kiriting:", reply_markup=keyboard)
        await CreateNurse.gender.set()
    else:
        await message.answer("Yosh uchun son kiriting:")
        await CreateNurse.age.set()


@dp.message_handler(state=CreateNurse.gender)
async def getNurseGender(message: types.Message, state: FSMContext):
    async with (state.proxy() as data):
        data['gender'] = message.text
    await message.answer("Hamshira telefon raqamini kiriting:", reply_markup=types.ReplyKeyboardRemove())
    await CreateNurse.phone.set()


@dp.message_handler(state=CreateNurse.phone)
async def getNursePhone(message: types.Message, state: FSMContext):
    if message.contact:
        phone_number = message.contact.phone_number
    else:
        phone_number = message.text
    if re.match(r'^\+[1-9]\d{1,14}$', phone_number):
        async with (state.proxy() as data):
            data['phone'] = phone_number
        await message.answer("Hamshira uchun joylashuv yuboring:",
                             reply_markup=types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True).add(
                                 types.KeyboardButton("Joylashuv yuborish", request_location=True)))
        await CreateNurse.long.set()
    else:
        await message.answer("To'g'ri format yuboring:")


@dp.message_handler(state=CreateNurse.long, content_types=types.ContentTypes.LOCATION)
async def getNurseLong(message: types.ContentType.LOCATION, state: FSMContext):
    if message.location:
        async with state.proxy() as data:
            data['long'] = message.location.longitude
            data['lat'] = message.location.latitude
    await state.finish()
    nurse_data = {
        "name": data["name"],
        "age": data["age"],
        "gender": data["gender"],
        "photo": data["photo"],
        "phone_number": data["phone"],
        "long": data["long"],
        "lat": data["lat"]
    }
    await state.finish()
    url = f"{BASE_URL}/nurses/"
    response = requests.post(url, json=nurse_data)
    if response.status_code == 201:
        GetBaseData()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = [types.InlineKeyboardButton(service['name'],
                                              callback_data=f"nurse_service_{service['id']}_{response.json()['id']}")
                   for service in SERVICES]
        keyboard.add(*buttons)
        await message.answer("Hamshira bajara oladigan xizmatlarni tanlang:", reply_markup=keyboard)
    else:
        await message.answer("Hamshira yaratishda xatolik, qaytadan urinib ko'ring.")
        await message.answer("Yana qo'shimcha nimadir qo'shmoqchimisiz:", reply_markup=ADMIN_KEYBOARD)

@dp.callback_query_handler(lambda query: query.data.startswith('nurse_service_'))
async def service_name_for_nurse(query: types.CallbackQuery):
    ser_type, nurse_id = map(int, query.data.split('_')[-2:])
    url = f"{BASE_URL}/nurse_service/{ser_type}/{nurse_id}/"
    response = requests.get(url)
    if response.status_code == 200:
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = [types.InlineKeyboardButton(service['name'],
                                              callback_data=f"nurse_service_{service['id']}_{nurse_id}")
                                              for service in response.json()]
        keyboard.add(*buttons)
        keyboard.add(types.InlineKeyboardButton('Yakunlash✅', callback_data="service_nurse_done"))
        await query.message.edit_text("Hamshira bajara oladigan xizmatlarni tanlang yoki yakunlang:", reply_markup=keyboard)


@dp.callback_query_handler(lambda query: query.data.startswith('service_nurse_done'))
async def service_name_done(query: types.CallbackQuery):
    await query.message.edit_text("Hamshira muvaffaqqiyatli yaratildi ✅")
    await query.message.answer("Yana qo'shimcha nimadir qo'shmoqchimisiz:", reply_markup=ADMIN_KEYBOARD)


######## CREATE HOSPITAL ##########
@dp.message_handler(state=CreateHospital.name)
async def getHospitalName(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("Shifoxona telefon raqamini kiriting:")
    await CreateHospital.phone.set()


@dp.message_handler(state=CreateHospital.phone)
async def getHospitalPhone(message: types.Message, state: FSMContext):
    if message.contact:
        phone_number = message.contact.phone_number
    else:
        phone_number = message.text
    if re.match(r'^\+[1-9]\d{1,14}$', phone_number):
        async with (state.proxy() as data):
            data['phone'] = phone_number
        await message.answer("Shifoxona uchun ish vaqtini kiriting (masalan: 9:00-16:00):")
        await CreateHospital.working_hours.set()
    else:
        await message.answer("To'g'ri format yuboring:")
        await CreateHospital.phone.set()


@dp.message_handler(state=CreateHospital.working_hours)
async def getHospitalWorkingHours(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['working_hours'] = message.text
    await message.answer("Ish kunlarini kiriting (masalan: Dushanbada-Jumagacha):")
    await CreateHospital.working_days.set()


@dp.message_handler(state=CreateHospital.working_days)
async def getHospitalWorkingDays(message: types.Message, state: FSMContext):
    async with (state.proxy() as data):
        data['working_days'] = message.text
    await message.answer("Shifoxona lokatsiyasini yuboring:",
                         reply_markup=types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True).add(
                             types.KeyboardButton("Joylashuv yuborish", request_location=True)))
    await CreateHospital.long.set()


@dp.message_handler(state=CreateHospital.long, content_types=types.ContentTypes.LOCATION)
async def getHospitalLong(message: types.ContentType.LOCATION, state: FSMContext):
    if message.location:
        async with state.proxy() as data:
            data['long'] = message.location.longitude
            data['lat'] = message.location.latitude
    nurse_data = {
        "name": data["name"],
        "phone_number": data["phone"],
        "working_days": data["working_days"],
        "working_hours": data["working_hours"],
        "long": data["long"],
        "lat": data["lat"]
    }
    await state.finish()
    url = f"{BASE_URL}/hospitals/"
    response = requests.post(url, data=nurse_data)
    if response.status_code == 201:
        GetBaseData()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = [types.InlineKeyboardButton(service['name'],
                                              callback_data=f"hospital_service_{service['id']}_{response.json()['id']}")
                                              for service in SERVICES]
        keyboard.add(*buttons)
        await message.answer("Shifoxona bajara oladigan xizmatlarni tanlang:", reply_markup=keyboard)

    else:
        await message.answer("Shifoxona yaratishda xatolik, qaytadan urinib ko'ring.")
        await message.answer("Yana qo'shimcha nimadir qo'shmoqchimisiz:", reply_markup=ADMIN_KEYBOARD)


@dp.callback_query_handler(lambda query: query.data.startswith('hospital_service_'))
async def service_name_for_nurse(query: types.CallbackQuery):
    ser_type, hospital_id = map(int, query.data.split('_')[-2:])
    url = f"{BASE_URL}/hospital_service/{ser_type}/{hospital_id}/"
    response = requests.get(url)
    if response.status_code == 200:
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = [types.InlineKeyboardButton(service['name'],
                                              callback_data=f"nurse_service_{service['id']}_{hospital_id}")
                                              for service in response.json()]
        keyboard.add(*buttons)
        keyboard.add(types.InlineKeyboardButton('Yakunlash✅', callback_data="service_hospital_done"))
        await query.message.edit_text("Shifoxona bajara oladigan xizmatlarni tanlang yoki yakunlang:",
                                      reply_markup=keyboard)


@dp.callback_query_handler(lambda query: query.data.startswith('service_hospital_done'))
async def service_name_hos_done(query: types.CallbackQuery):
    await query.message.answer("Shifoxona muvaffaqqiyatli yaratildi ✅", reply_markup=types.ReplyKeyboardRemove())
    await query.message.answer("Yana qo'shimcha nimadir qo'shmoqchimisiz:", reply_markup=ADMIN_KEYBOARD)


######## CREATE SERVICE ##########
@dp.message_handler(state=CreateService.name)
async def getServiceName(message: types.Message, state: FSMContext):
    service_name = message.text
    await state.finish()
    url = f"{BASE_URL}/services/"
    response = requests.post(url, data={"name": service_name})
    if response.status_code == 201:
        GetBaseData()
        await message.answer("Xizmat turi muvaffaqqiyatli yaratildi ✅")
        await message.answer("Yana qo'shimcha nimadir qo'shmoqchimisiz:", reply_markup=ADMIN_KEYBOARD)
        return
    else:
        await message.answer("Xizmat turini yaratishda xatolik, qaytadan urinib ko'ring.")


async def shutdown(dp):
    await dp.bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()


if __name__ == "__main__":
    GetBaseData()
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown)
