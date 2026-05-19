from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from main import extract_section_api, normalize, agent, langfuse
from langfuse import observe,propagate_attributes
from langfuse.langchain import CallbackHandler
import os



langfuse_handler = CallbackHandler()



app = FastAPI()




class ExtractRequest(BaseModel):
    url : str
    section : str
    evaluation : bool


@app.get("/")
def root():
    return {"Message":"Api is Running"}

@app.post("/extract")
async def extract_data(req_fields: ExtractRequest):
    try:
        raw = await extract_section_api(req_fields.url,req_fields.section)

        if not raw:
            raise HTTPException(status_code=404, detail="No API data captured")
        
        aft_normalize = normalize(raw["data"])

        return{
            "status" : "success",
            "data" : aft_normalize
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/llm_test")
async def summarize(url:str, section:str, evaluation: bool):
    with langfuse.start_as_current_observation(
        as_type="span",name="Summary_Agent",input={"url":url,"section":section}
    ) as root_span:
        
        with propagate_attributes(session_id=f"Session_{section}_03"):

            langfuse_handler = CallbackHandler()


            state = {
                "url": url,
                "section": section,
                "evaluation" : evaluation,
                "raw_data": None,
                "normalized": None,
                "prompt": None,
                "output": None,
                "eval_score": None,
                "eval_pass" : None,
                "eval_notes": None,
            }

            result = await agent.ainvoke(state,config={"callbacks":[langfuse_handler]})

            root_span.update(
                output={
                    "summary":result["output"],
                    "eval_score":result["eval_score"],
                    "eval_pass":result["eval_pass"]
                }
            )

            trace_id = root_span.trace_id
    
    langfuse.flush()



    return{
        "section" : section,
        "summary": result["output"],
        "eval_score" : result["eval_score"],
        "eval_pass":result["eval_pass"],
        "eval_notes":result["eval_notes"],
        "trace_id":trace_id
    }




if __name__ == "__main__":
    uvicorn.run(
        "server:app",          # module:FastAPI-instance
        host="0.0.0.0",
        port=8000,
        loop="asyncio",     # uses ProactorEventLoop on Windows — supports subprocesses
    )