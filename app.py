import os
import shutil
import uuid
import json
import asyncio
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status, Header, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.openapi.utils import get_openapi

from pageindex import config, page_index_main

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

app = FastAPI(
    title="PageIndex API",
    description=(
        "A lightweight API wrapper around **PageIndex** — an LLM-powered document "
        "structure extraction engine.\n\n"
        "## Supported Formats\n"
        "| Endpoint | File Type | Extension |\n"
        "|---|---|---|\n"
        "| `POST /index-pdf` | PDF | `.pdf` |\n"
        "| `POST /index-md` | Markdown | `.md` |\n"
        "| `POST /index-txt` | Plain Text | `.txt` |\n\n"
        "## Authentication\n"
        "All endpoints require an `X-API-Key` header. Click the **Authorize** button "
        "above and enter your API token."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "PageIndex",
        "url": "https://github.com/billchizhang/PageIndex",
    },
    license_info={
        "name": "MIT",
    },
)

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to Swagger docs."""
    return RedirectResponse(url="/docs")

@app.get("/health", tags=["System"], summary="Health check")
async def health():
    """Returns service status. Used by Azure for liveness/readiness probes."""
    return {"status": "healthy"}

# Secure token from environment variable, with a fallback
API_TOKEN = os.getenv("API_TOKEN", "default-secure-token")

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """
    Security dependency: validates the X-API-Key header.
    """
    if api_key != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key

@app.post(
    "/index-pdf",
    dependencies=[Depends(verify_api_key)],
    tags=["Document Indexing"],
    summary="Index a PDF document",
    description=(
        "Upload a PDF file to extract its hierarchical structure using PageIndex. "
        "The file is temporarily stored, processed via LLM-powered analysis, "
        "and the structured JSON tree is returned."
    ),
    responses={
        200: {"description": "Structured JSON tree of the document"},
        400: {"description": "File is not a PDF"},
        401: {"description": "Invalid or missing API Key"},
        500: {"description": "Internal processing error"},
    },
)
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

        # Process the temporary PDF in a separate thread to avoid
        # asyncio.run() conflict with Uvicorn's event loop
        toc_with_page_number = await asyncio.to_thread(page_index_main, tmp_path, opt)

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

@app.post(
    "/index-md",
    dependencies=[Depends(verify_api_key)],
    tags=["Document Indexing"],
    summary="Index a Markdown document",
    description=(
        "Upload a Markdown file to extract its hierarchical structure using PageIndex. "
        "The file is temporarily stored, processed via LLM-powered analysis, "
        "and the structured JSON tree is returned."
    ),
    responses={
        200: {"description": "Structured JSON tree of the document"},
        400: {"description": "File is not a Markdown file"},
        401: {"description": "Invalid or missing API Key"},
        500: {"description": "Internal processing error"},
    },
)
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

        toc_with_page_number = await asyncio.to_thread(page_index_main, tmp_path, opt)
        return JSONResponse(content=toc_with_page_number)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing MD: {str(e)}",
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post(
    "/index-txt",
    dependencies=[Depends(verify_api_key)],
    tags=["Document Indexing"],
    summary="Index a Text document",
    description=(
        "Upload a plain text file to extract its hierarchical structure using PageIndex. "
        "The file is temporarily stored, processed via LLM-powered analysis, "
        "and the structured JSON tree is returned."
    ),
    responses={
        200: {"description": "Structured JSON tree of the document"},
        400: {"description": "File is not a Text file"},
        401: {"description": "Invalid or missing API Key"},
        500: {"description": "Internal processing error"},
    },
)
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

        toc_with_page_number = await asyncio.to_thread(page_index_main, tmp_path, opt)
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
