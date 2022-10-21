from peewee import *

db = SqliteDatabase('my_database.db')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    """
    class User. Parent - Base Model
     Attributes:
        :id(int): user id
        :username(str): username
        :language(str): the language selected by the user
        :state(int): current user's state
        :locale(str): user's location code
        :currency(str):  the currency selected by the user
        :order(str): required way of sorting hotels
        :dest_id(str): destination id
        :destination_name(str): destination name
        :check_in(str): check in date
        :check_out(str): check out date
        :quantity(str): required number of hotels
        :min_price(str): minimum price
        :max_price(str): maximum price
        :distance(str): distance from the city center
        :photo_amt(str): required number of hotel photos
    """
    id = IntegerField(unique=True)
    username = CharField()
    language = CharField()
    state = IntegerField()
    locale = CharField()
    currency = CharField()
    order = CharField()
    dest_id = CharField()
    destination_name = CharField()
    check_in = CharField()
    check_out = CharField()
    quantity = CharField()
    min_price = CharField()
    max_price = CharField()
    distance = CharField()
    photo_amt = IntegerField()


class SearchHistory(BaseModel):
    """
    class SearchHistory. Parent - BaseModel
    Attributes:
        :id(int): id
        :user_id(int): user id
        :history(str): the last 3 user's requests
    """
    id = IntegerField(primary_key=True, unique=True)
    user_id = IntegerField(unique=True)
    history = CharField()


db.connect()
User.create_table()
SearchHistory.create_table()
db.close()
