from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from databases import Database

DATABASE_URL = "postgresql://localhost:5432/testdb"  # You can change this to another database URL

metadata = MetaData()

items = Table(
    "items",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("name", String, index=True),
    Column("description", String),
)

engine = create_engine(DATABASE_URL)
metadata.create_all(engine)

database = Database(DATABASE_URL)

class Item(BaseModel):
    name: str
    description: str

app = FastAPI()

# Setup event handler to connect to the database before the application starts
@app.on_event("startup")
async def startup_db_client():
    await database.connect()

# Setup event handler to disconnect from the database after the application shuts down
@app.on_event("shutdown")
async def shutdown_db_client():
    await database.disconnect()

@app.post("/items/", response_model=Item)
async def create_item(item: Item):
    query = items.insert().values(name=item.name, description=item.description)
    item_id = await database.execute(query)
    return {"id": item_id, **item.dict()}

@app.get("/items/{item_id}", response_model=Item)
async def read_item(item_id: int):
    query = items.select().where(items.c.id == item_id)
    item = await database.fetch_one(query)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/items/", response_model=list[Item])
async def read_all_items():
    query = items.select()
    return await database.fetch_all(query)

@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: Item):
    query = items.update().where(items.c.id == item_id).values(name=item.name, description=item.description)
    await database.execute(query)
    updated_item = await database.fetch_one(items.select().where(items.c.id == item_id))
    if updated_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated_item

@app.delete("/items/{item_id}", response_model=Item)
async def delete_item(item_id: int):
    delete_query = items.delete().where(items.c.id == item_id)
    get_query = items.select().where(items.c.id == item_id)
    deleted_item = await database.fetch_one(get_query)
    if not deleted_item:
        raise HTTPException(status_code=404, detail="Item not found")

    await database.execute(delete_query)
    return deleted_item