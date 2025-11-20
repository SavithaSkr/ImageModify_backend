import os
from modules.image_composer import compose_image

def process_sheet(sheet, BASE_URL):
    """
    Process each row in the Google Sheet, create edited images,
    save locally, and update the sheet with the public URL.
    """

    values = sheet.get_all_values()

    # Assuming row[0] = image URL, row[1] = price text
    # Change this mapping if different
    IMAGE_URL_COL = 1      # column A
    PRICE_COL = 2          # column B
    OUTPUT_COL = 3         # column C for edited image URL

    edited_folder = "images/edited"
    os.makedirs(edited_folder, exist_ok=True)

    # Row index starts at 1 for Google Sheets
    for row_index, row in enumerate(values, start=1):

        image_url = row[IMAGE_URL_COL - 1]
        price_text = row[PRICE_COL - 1]

        # Skip empty rows
        if not image_url:
            continue

        output_filename = f"edited_{row_index}.png"
        output_path = os.path.join(edited_folder, output_filename)

        try:
            # Use your existing image composer logic
            compose_image(
                image_path=image_url,
                price_text=price_text,
                output_path=output_path
            )

            # Public URL served by FastAPI static mount
            public_url = f"{BASE_URL}/images/edited/{output_filename}"

            # Update the sheet
            sheet.update_cell(row_index, OUTPUT_COL, public_url)

            print(f"Row {row_index}: Updated {public_url}")

        except Exception as e:
            print(f"Error processing row {row_index}: {e}")
            continue

    print("Processing completed.")
