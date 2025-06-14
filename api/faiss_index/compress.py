import json
import os
import sys
import gzip # We'll remind you to use this manually later, but it's good to have if you automate the gzipping.

def remove_embeddings_from_metadata_json(input_filepath, output_filepath):
    """
    Loads an uncompressed JSON metadata file, removes the 'embedding' field from each document,
    and saves the modified data to a new uncompressed JSON file.

    Args:
        input_filepath (str): Path to the original metadatas.json file.
        output_filepath (str): Path where the new, cleaned metadatas.json will be saved.
    """
    print(f"Loading metadata from {input_filepath}...")
    
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        print(f"Loaded {len(metadata)} documents.")
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_filepath}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from {input_filepath}. Is it valid JSON? Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while loading: {e}", file=sys.stderr)
        sys.exit(1)

    modified_count = 0
    for doc in metadata:
        if "embedding" in doc:
            del doc["embedding"]
            modified_count += 1
            
    print(f"Removed 'embedding' field from {modified_count} documents.")

    print(f"Saving modified metadata to {output_filepath}...")
    
    try:
        # Create directory if it doesn't exist (though it should exist if you're running from inside it)
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)

        with open(output_filepath, 'w', encoding='utf-8') as f:
            # Use indent=None and separators to make the JSON as compact as possible
            json.dump(metadata, f, ensure_ascii=False, indent=None, separators=(',', ':'))
        print("✅ New metadata file saved successfully.")
        
        # Optionally print original vs new file size
        original_size = os.path.getsize(input_filepath)
        new_size = os.path.getsize(output_filepath)
        print(f"Original size: {original_size / (1024*1024):.2f} MB")
        print(f"New size (without embeddings): {new_size / (1024*1024):.2f} MB")

    except Exception as e:
        print(f"An error occurred while saving the file: {e}", file=sys.stderr)
        sys.exit(1)

# --- How to use this script ---
if __name__ == "__main__":
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Define the input and output file paths relative to this script's location.
    # Assuming 'metadata.json' is directly in the same directory as this script.
    input_json_file = os.path.join(current_dir, 'metadatas.json') 
    
    # This will overwrite the original 'metadata.json' with the smaller version.
    # Make sure you have a backup of your original 'metadata.json' before running this,
    # as this operation is destructive for the original content.
    output_json_file = os.path.join(current_dir, 'metadata.json') 
    
    # If you prefer to save to a NEW file (e.g., 'metadata_cleaned.json')
    # to avoid overwriting, uncomment the line below and comment out the one above:
    # output_json_file = os.path.join(current_dir, 'metadata_cleaned.json')

    remove_embeddings_from_metadata_json(input_json_file, output_json_file)

    print("\n--- Next CRITICAL Steps ---")
    print("1. Your 'metadata.json' file (or 'metadata_cleaned.json' if you chose that option) is now smaller.")
    print("2. You MUST now **gzip** this new JSON file into a '.gz' format.")
    print("   Your `rag.py` expects the file to be named `metadatas.json.gz` (plural 'metadatas').")
    print(f"   If your output file was {os.path.basename(output_json_file)}, you will run:")
    print(f"   `gzip -k {output_json_file}`")
    print(f"   This will create a new file named `{output_json_file}.gz` (e.g., `metadata.json.gz` or `metadata_cleaned.json.gz`).")
    print("   If the resulting file is `metadata.json.gz`, you're good.")
    print("   If it's `metadata_cleaned.json.gz`, you might need to rename it to `metadatas.json.gz` manually.")
    print("3. Upload the newly created `metadatas.json.gz` file (the gzipped version) to Google Drive.")
    print("4. Get its new public shareable ID.")
    print("5. Go to your Render dashboard -> Service -> Environment Variables.")
    print("6. Update the 'GDRIVE_METADATA_ID' environment variable with the new ID.")
    print("7. Ensure your `rag.py` file is updated (as provided in my previous response) to use FAISS distances for re-ranking, because the 'embedding' field will no longer be present in the metadata.")
    print("8. Commit all your code changes (especially `rag.py` and ensure the `metadatas.json.gz` is prepared for download by Render) to your Git repository to trigger a Render redeploy.")
    print("Monitor your Render logs closely for memory usage after deployment.")