from fastapi import FastAPI
import asyncio
import time
app = FastAPI()

@app.get("/sync")
def sync_ex():
    print("Before sleep in sync!")
    time.sleep(5)
    print("after sleep in sync")
    return {"msg":"printed in sync"}



@app.get("/async")
async def async_ex():
    print("before from async !")
    time.sleep(5)       #block
    print("After Sleep in async")
    return {"msg":"printed in async"}



@app.get("/asynio")
async def wait_x():
    
    print("before sleep asysio")
    await asyncio.sleep(5)    #non blocking
    print("After sleep asynio")
    return {"msg":"printed in aysio async"}