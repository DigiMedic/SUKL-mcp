# Project Summary: SUKL MCP Server

## Overview
The SUKL MCP Server is a production-ready FastMCP server designed to provide AI agents (like Claude, GPT-4) with access to the official Czech database of medicinal products (SÚKL - Státní ústav pro kontrolu léčiv). It serves as a bridge between AI models and pharmaceutical data.

## Key Features
- **Comprehensive Data Access**: Access to 68,000+ medicinal products.
- **Document Parsing**: Automatic extraction of text from PIL (Patient Information Leaflet) and SPC (Summary of Product Characteristics) documents (PDF/DOCX).
- **Smart Search**: Multi-level search pipeline with fuzzy matching to handle typos.
- **Price Calculation**: Logic for calculating prices, reimbursements, and patient co-payments.
- **Intelligent Alternatives**: Recommendation system for finding substitute medicines based on multiple criteria.
- **FastMCP Implementation**: Built using the FastMCP framework for efficient MCP server implementation.

## Architecture
- **Language**: Python 3.10+
- **Core Framework**: FastMCP (based on FastAPI/Pydantic)
- **Data Handling**: pandas for efficient data processing.
- **Deployment**: Supports FastMCP Cloud (stdio) and Smithery (HTTP/Docker).

## Data Source
- SÚKL Open Data (updated monthly).
- Contains data on medicinal products, active ingredients, ATC codes, and prices.
