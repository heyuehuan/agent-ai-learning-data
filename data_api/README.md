# Data API Module

## Overview

The `data_api` module provides functionality to interact with Weaviate, a vector database, for efficient data storage and retrieval. It supports batch processing, automatic vectorization, and various search capabilities.

## Features

- **Batch Processing**: Insert data into Weaviate collections in fixed-size batches for improved performance.
- **Automatic Vectorization**: Leverages Weaviate's model provider integration for text vectorization.
- **Search Capabilities**: Supports similarity searches, keyword searches, hybrid searches, and filtered searches.

## Usage

1. **Data Insertion**:

   - Reads processed data from `processed_entities.csv`.
   - Maps CSV fields to Weaviate collection properties.
   - Inserts data into the `DemoCollection` with automatic vectorization.

2. **Search**:

   - Perform various types of searches to retrieve relevant data based on vector similarity or keywords.

3. **Error Handling**:
   - Tracks failed objects during batch insertion and provides detailed error reporting.

## Example

Refer to the `explore.ipynb` notebook for detailed examples of data insertion and search operations using the `data_api` module.
