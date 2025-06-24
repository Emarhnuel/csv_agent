# get_field_names.py
import fitz
import os

def get_pdf_field_names(pdf_path):
    """Opens a PDF and prints the names of all form fields."""
    if not os.path.exists(pdf_path):
        print(f"Error: The file was not found at {pdf_path}")
        return

    try:
        with fitz.open(pdf_path) as doc:
            print(f"--- Fields in: {os.path.basename(pdf_path)} ---")
            found_fields = False
            for page_num, page in enumerate(doc):
                widgets = list(page.widgets())
                if widgets:
                    found_fields = True
                    print(f"\n--- Page {page_num + 1} ---")
                    for widget in page.widgets():
                        print(f"  - Name: '{widget.field_name}', Type: '{widget.field_type_string}'")
            
            if not found_fields:
                print("No fillable fields found in this document.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # The path to your fillable PDF template
    pdf_file = r"C:\Users\user\Downloads\RAG_ai_agent\rag_agent\template\ub-40-.pdf"
    get_pdf_field_names(pdf_file)
