import os, json
import pymongo as pm
from datetime import datetime as dt
from typing import List, Callable, Union, Any, Type
from functools import lru_cache

@lru_cache(maxsize=1)
def get_mdb_client(uri: str) -> pm.MongoClient:
    return pm.MongoClient(uri)

@lru_cache(maxsize=1)
def get_db(name: str) -> pm.database.Database:
    client = get_mdb_client()
    return client[name]

def write_one_to_mdb(collection_name: str, data: dict) -> pm.results.InsertOneResult:
    db = get_db()
    collection = db[collection_name]
    return collection.insert_one(data)

def update_one_object(collection_name: str, query: dict, update: dict) -> pm.results.UpdateResult:
    db = get_db()
    collection = db[collection_name]
    return collection.update_one(query, {"$set": update})

def read_from_mdb(collection_name: str, query: dict) -> List[dict]:
    db = get_db()
    collection = db[collection_name]
    return list(collection.find(query))
