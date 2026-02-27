import os
import shutil
import uuid
import json
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status, Header, UploadFile, File
from fastapi.responses import JSONResponse

from pageindex import config, page_index_main

app = FastAPI(title="PageIndex API", description="API Wrapper for PageIndex")

# Secure token from environment variable, with a fallback
API_TOKEN = os.getenv("API_TOKEN", "default-secure-token")

async def verify_api_key(x_api_key: str = Header(None)):
    """
    Dependency to check for X-API-Key header.
    """
    if x_api_key != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return x_api_key

@app.post("/index-pdf", dependencies=[Depends(verify_api_key)])
async def index_pdf(
    file: UploadFile = File(...),
):
    """
    Endpoint to upload a PDF file, save it to /tmp temporarily, 
    and process it using PageIndex.
    """
    if not file.filename.lower().endswith(".pdf"):
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF",
        )

    # Generate a unique temp filename
    tmp_path = f"/tmp/{uuid.uuid4()}_{file.filename}"

    try:
        # Save file to /tmp
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Configure PageIndex options
        # We can also add these as query parameters to the endpoint later if needed
        opt = config(
            model='gpt-4o-2024-11-20',
            toc_check_page_num=20,
            max_page_num_each_node=10,
            max_token_num_each_node=20000,
            if_add_node_id='yes',
            if_add_node_summary='yes',
            if_add_doc_description='no',
            if_add_node_text='no'
        )

        # Process the temporary PDF
        toc_with_page_number = page_index_main(tmp_path, opt)

        return JSONResponse(content=toc_with_page_number)

    except Exception as e:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}",
        )
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/index-md", dependencies=[Depends(verify_api_key)])
async def index_md(
    file: UploadFile = File(...),
):
    """
    Endpoint to upload a Markdown file, save it to /tmp temporarily,
    and process it using PageIndex.
    """
    if not file.filename.lower().endswith(".md"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a Markdown file",
        )

    tmp_path = f"/tmp/{uuid.uuid4()}_{file.filename}"

    try:
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        opt = config(
            model='gpt-4o-2024-11-20',
            toc_check_page_num=20,
            max_page_num_each_node=10,
            max_token_num_each_node=20000,
            if_add_node_id='yes',
            if_add_node_summary='yes',
            if_add_doc_description='no',
            if_add_node_text='no'
        )

        toc_with_page_number = page_index_main(tmp_path, opt)
        return JSONResponse(content=toc_with_page_number)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing MD: {str(e)}",
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/index-txt", dependencies=[Depends(verify_api_key)])
async def index_txt(
    file: UploadFile = File(...),
):
    """
    Endpoint to upload a Text file, save it to /tmp temporarily,
    and process it using PageIndex.
    """
    if not file.filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a Text file",
        )

    tmp_path = f"/tmp/{uuid.uuid4()}_{file.filename}"

    try:
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        opt = config(
            model='gpt-4o-2024-11-20',
            toc_check_page_num=20,
            max_page_num_each_node=10,
            max_token_num_each_node=20000,
            if_add_node_id='yes',
            if_add_node_summary='yes',
            if_add_doc_description='no',
            if_add_node_text='no'
        )

        toc_with_page_number = page_index_main(tmp_path, opt)
        return JSONResponse(content=toc_with_page_number)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing TXT: {str(e)}",
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
