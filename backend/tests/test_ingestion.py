"""
Unit tests for data ingestion and datatype inference service.
"""

import pytest
import pandas as pd
from app.services.ingestion import process_file_upload, sanitize_table_name, sanitize_column_name

def test_sanitize_names():
    assert sanitize_column_name("Sales Revenue ($)") == "sales_revenue"
    assert sanitize_column_name("Order-Date 2024!") == "order_date_2024"
    assert sanitize_table_name("Quarterly Sales 2024.csv").startswith("tbl_quarterly_sales_2024_")

def test_process_csv_upload():
    csv_content = b"category,sales,units,order_date\nElectronics,150.5,2,2024-01-15\nFurniture,200.0,1,2024-01-16\nElectronics,300.0,4,2024-01-17\n"
    filename = "test_sales.csv"
    
    table_name, metadata, df = process_file_upload(csv_content, filename)
    
    assert table_name.startswith("tbl_test_sales_")
    assert metadata.row_count == 3
    assert metadata.column_count == 4
    assert metadata.total_missing_percentage == 0.0
    assert len(metadata.columns) == 4
    assert len(metadata.sample_rows) == 3
