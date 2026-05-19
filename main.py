from playwright.async_api import async_playwright
import re
import asyncio
from typing import TypedDict
from langchain_openrouter import ChatOpenRouter
from langgraph.graph import StateGraph
from deepeval.test_case import LLMTestCase
from deepeval.metrics import FaithfulnessMetric, AnswerRelevancyMetric, HallucinationMetric
from deepeval.models import GeminiModel
from deepeval.models.base_model import DeepEvalBaseLLM


from langfuse import get_client, observe
from langfuse.langchain import CallbackHandler

import os


from dotenv import load_dotenv

load_dotenv()


GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

EMAIL = os.getenv("LOGIN_EMAIL")
PASSWORD = os.getenv("LOGIN_PASSWORD")


llm = ChatOpenRouter(            #llm conf
    model="gpt-4o-mini",
    temperature=0
)


langfuse = get_client()







class AgentState(TypedDict):
    url :str
    section: str
    evaluation : bool
    raw_data: str
    normalized: str
    prompt: str
    output: str
    eval_score: float
    eval_pass : bool
    eval_notes: str









async def extract_section_api(url, section):
    captured_response = []
    captured_mode = {"active" : False}


    async def handle_response(response):
        if not captured_mode["active"]:
            return
        
        api_url = response.url


        if "_next/data" in api_url:           # swap "_next/data with /api/ for rest , /graphql for GraphQL.
            try:
                data = await response.json()
                captured_response.append({
                    "url": api_url,
                    "data":data
                })
                print(f"Captured API for section : {section}")
                print("Url : ", api_url)

            except:
                pass  #ignore non json
            
    def safe_handler(response):
        asyncio.create_task(handle_response(response))

    async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            page.on("response",safe_handler)

            await page.goto(url)
            try:
                await page.wait_for_selector("button.gfg_loginModalBtn", timeout=2000)
                await page.click("button.gfg_loginModalBtn")
            except:
                print("Login button not found")

            try:
                await page.wait_for_selector('input[placeholder="Username or Email"]', timeout=2000)

                await page.fill('input[placeholder="Username or Email"]', EMAIL)

                await page.wait_for_timeout(2000)

                await page.fill('input[type="password"]', PASSWORD)

                await page.click('button:has-text("Sign In")')

                print("Login submitted")

                await page.wait_for_timeout(1000)

            except Exception as e:
                print("Login Failed!", e)


            try:
                await page.wait_for_selector('a[href*="python-programming-language-tutorial"]', timeout=2000)
                await page.click('a[href*="python-programming-language-tutorial"]')

                print("Navigated to python page!")

                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(3000)

            except Exception as e:
                print(f"Python Navigation Failed: {e}")


            

            captured_mode["active"] = True

            try:
                await page.locator(f"text={section}").first.click()
            except:
                print(f"could not Able to find the Section : {section}")
                await browser.close()
                return None
    
            await page.wait_for_timeout(2000)

            await browser.close()

    if captured_response:
        return captured_response[0]
    else:
        print("No ApI Captured")
        return None
    



@observe(name="Extract_api_section")
async def extract_node(state: AgentState):

    result = await extract_section_api(state["url"],state["section"])

    state["raw_data"]=result["data"]

    return state







def clean_html_regex(html: str) -> str:
    # Remove img tags entirely
    text = re.sub(r'<img[^>]+>', '', html)
    
    # Remove anchor tags but keep inner text
    text = re.sub(r'<a[^>]+>(.*?)</a>', r'\1', text, flags=re.DOTALL)
    
    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove URLs 
    text = re.sub(r'https?://\S+', '', text)
    

    text = re.sub(r'\n{3,}', '\n\n', text) #replaces \n * 3 or more times with  \n\n prevent huge gaps

    text = re.sub(r'[ \t]+', ' ', text) #replaces tabspaces (\t) with  empty str
    
    return text.strip()



def normalize(raw:dict)->dict:
    post = raw["pageProps"]["postDataFromWriteApi"]

    return {
        "title": post["post_title"],
        "content" : clean_html_regex(post["post_content"]),
        "modified" : post["post_modified_date"],
        "url" : post["post_url"]
    }



@observe(name="Normalize")
def normalize_node(state:AgentState):
    state["normalized"] = normalize(state["raw_data"])
    return state



PROMPT_TEMPLATES = {

    "Python Tutorial": """
You are a senior Python developer with 10 years of experience.

Explain and summarize the topic "{section}" in a structured way:

- What the concept is
- Core syntax and explanation
- Simple example (code snippet)
- Where it is used in real-world applications
- Common beginner mistakes

Content:
{content}
""",

    "Data Types": """
You are a senior Python developer with 10 years of experience.

Summarize "{section}" with a strong focus on understanding:

- Definition of the data type
- Different types (if applicable)
- Syntax and examples
- Use cases in real programs
- Differences from similar data types

Content:
{content}
""",

    "Interview Questions": """
You are a senior Python interviewer.

Summarize and explain "{section}" in a way useful for interview preparation:

- Key questions and answers
- Concept explanations behind each question
- Sample answers (clear and concise)
- Tips to answer confidently in interviews
- Common pitfalls candidates make

Content:
{content}
"""
}


@observe(name="prompt_node")
def prompt_node(state: AgentState):

    section = state["section"]

    template = PROMPT_TEMPLATES.get(section)

    state["prompt"] = template.format(
        section = section,
        content = state["normalized"]["content"]
    )

    return state


@observe(name="LLm_summary")
def summarization_node(state:AgentState):

    response = llm.invoke(state["prompt"])

    state["output"] = response.content

    if not state["evaluation"]:
        state["eval_score"] = None
        state["eval_pass"] = None
        state["eval_notes"] = "Evaluation is set as False"


    return state



class OpenRouterDeepEvalModel(DeepEvalBaseLLM):   #inherits the baseclass from DeepEval for proper structure
    def __init__(self, model): #takes llm obj and store it in model
        self.model = model

    #deepEval Expected formats 

    def load_model(self):    
        return self.model

    def generate(self, prompt: str) -> str:
        response = self.model.invoke(prompt)
        return response.content

    async def a_generate(self, prompt: str) -> str:
        response = await self.model.ainvoke(prompt)
        return response.content

    def get_model_name(self) -> str:
        return "openrouter-gpt-4o-mini"

deep_llm = OpenRouterDeepEvalModel(model=llm)


@observe(name="Evaluation")
def evaluation_node(state:AgentState):


    test_case = LLMTestCase(
        input = state["section"],
        actual_output=state["output"],
        retrieval_context=[state["normalized"]["content"]],
        context=[state["normalized"]["content"]]
    )


    faithfulness = FaithfulnessMetric(model = deep_llm)   #checks does the answer sticks to the context
    relevancy = AnswerRelevancyMetric(model = deep_llm)   #checks how relevant the answer is to the user’s question.
    hallucination = HallucinationMetric(model = deep_llm) #checks whether the model produces result irrelevant to the context

    faithfulness.measure(test_case)
    relevancy.measure(test_case)
    hallucination.measure(test_case)

    score = (faithfulness.score + relevancy.score + (1-hallucination.score)) / 3



    passed = (
    faithfulness.score >= 0.7 and
    relevancy.score >= 0.7 and
    hallucination.score < 0.3
    )

    eval_res = f"Faithfulness  : {faithfulness.score} , Relevancy : {relevancy.score}, Hallucination : {hallucination.score}"


    state["eval_score"] = round(score,3)
    state["eval_pass"] = passed
    state["eval_notes"] = eval_res

    langfuse.score_current_trace(name="faithfulness", value=faithfulness.score)
    langfuse.score_current_trace(name="relevancy", value=relevancy.score)
    langfuse.score_current_trace(name="hallucination", value=hallucination.score)
    langfuse.score_current_trace(name="final_score", value=state["eval_score"])



    return state


def evaluation_router(state: AgentState):
    if state["evaluation"]:
        return "evaluation_node"
    else:
        return "end"


graph = StateGraph(AgentState)

graph.add_node("extract_node", extract_node)

graph.add_node("normalize_node",normalize_node)

graph.add_node("prompt_node",prompt_node)

graph.add_node("summarization_node",summarization_node)

graph.add_node("evaluation_node",evaluation_node)




graph.set_entry_point("extract_node")

graph.add_edge("extract_node","normalize_node")

graph.add_edge("normalize_node","prompt_node")

graph.add_edge("prompt_node","summarization_node")

graph.add_conditional_edges("summarization_node", evaluation_router,
                            {
                                "evaluation_node" : "evaluation_node",
                                "end" : "__end__"
                            })

graph.set_finish_point("evaluation_node")

agent = graph.compile()






if __name__ == "__main__":
    result = extract_section_api(
        url="https://www.geeksforgeeks.org/software-engineering/",
        section="Software Engineering Tutorial"
    )

    res = normalize(result["data"])
    print(res)


