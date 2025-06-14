from flask import Flask, request, jsonify
import os
import sys
import json

# Add the current directory to sys.path so rag can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import all necessary functions from rag.py
from rag import (
    load_index_and_metadata, get_embedding, retrieve_and_prioritize_documents,
    build_prompt, query_chat_completion, clean_json_response,
    encode_image_to_base64_data_uri, format_discourse_url, clean_content_for_prompt
)

app = Flask(__name__)

# Global variables to store the FAISS index and metadata
rag_index = None
rag_metadata = None

@app.route('/healthz')
def health_check():
    return 'OK', 200

@app.route('/api/', methods=['POST'])
def answer_question_api():
    """
    API endpoint to receive a question and optional image, then return an answer and links.
    Expected JSON input: {"question": "...", "image": "base64_string_or_url_string"}
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    question = data.get("question")
    image_base64_data = data.get("image")

    if not question:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    if rag_index is None or rag_metadata is None:
        # User-facing message if RAG assets are not loaded
        return jsonify({"answer": "Server is still initializing. Please try again in a moment.", "links": []}), 503

    image_url_for_llm = None
    if image_base64_data:
        mime_type = "application/octet-stream"
        if image_base64_data.startswith("/9j/"):
            mime_type = "image/jpeg"
        elif image_base64_data.startswith("iVBORw0KGgo"):
            mime_type = "image/png"
        elif image_base64_data.startswith("UklGR"):
            mime_type = "image/webp"
        
        if image_base64_data.startswith("http://") or image_base64_data.startswith("https://"):
            image_url_for_llm = image_base64_data
        else:
            image_url_for_llm = f"data:{mime_type};base64,{image_base64_data}"
            # This specific warning can stay if it's considered helpful for debugging image issues
            # print(f"WARNING: Could not reliably determine MIME type for base64 image. Using {mime_type}. This might cause issues for the LLM.", file=sys.stderr)

    try:
        q_embed = get_embedding(question)
    except Exception as e:
        print(f"Error in embedding generation: {e}", file=sys.stderr) # Keep error logs
        return jsonify({"answer": f"Error generating question embedding: {e}", "links": []}), 500

    try:
        # top_k_initial=750 and top_k_final=5 are reasonable values to provide context to the LLM.
        # The final link count (2) is enforced by clean_json_response in rag.py
        relevant_docs = retrieve_and_prioritize_documents(q_embed, rag_index, rag_metadata, top_k_initial=750, top_k_final=5)
    except Exception as e:
        print(f"Error in document retrieval: {e}", file=sys.stderr) # Keep error logs
        return jsonify({"answer": f"Error retrieving relevant information: {e}", "links": []}), 500

    if not relevant_docs:
        return jsonify({"answer": "Sorry, I couldn't find any relevant information in the knowledge base.", "links": []}), 200

    try:
        messages_for_llm = build_prompt(question, relevant_docs, image_url=image_url_for_llm)
        raw_llm_response = query_chat_completion(messages_for_llm)
    except Exception as e:
        print(f"Error during LLM interaction: {e}", file=sys.stderr) # Keep error logs
        return jsonify({"answer": f"Error communicating with AI model: {e}", "links": []}), 500
            
    # clean_json_response will enforce exactly 2 links based on its internal logic and padding
    answer_data = clean_json_response(raw_llm_response, relevant_docs)

    if not answer_data or not answer_data.get("answer"):
        print(f"WARNING: LLM returned malformed or empty answer. Raw: {raw_llm_response}", file=sys.stderr) # Keep warning
        fallback_answer_text = "I couldn't generate a specific answer from the provided context. However, here's some potentially relevant information:\n"
        fallback_links = []
        # Adjusted to ensure max 2 links even in fallback
        for doc in relevant_docs[:min(2, len(relevant_docs))]: 
            cleaned_content_snippet = clean_content_for_prompt(doc.get("content", ""))
            snippet = cleaned_content_snippet[:150].rsplit(' ', 1)[0] + '...' if len(cleaned_content_snippet) > 150 else cleaned_content_snippet
            fallback_links.append({"url": doc["url"], "text": snippet})
        
        if fallback_links:
            for link in fallback_links:
                fallback_answer_text += f"- \"{link['text']}\" (Source: {link['url']})\n"
        else:
            fallback_answer_text += "No relevant specific snippets found to cite."

        return jsonify({"answer": fallback_answer_text.strip(), "links": fallback_links}), 200
    
    answer_data["answer"] = answer_data["answer"].replace("\n", " ").strip()
    
    return jsonify(answer_data), 200

# Load FAISS index and metadata at import time (works for Render too)
try:
    rag_index, rag_metadata = load_index_and_metadata()
    print("RAG assets loaded successfully.")
except Exception as e:
    print(f"FATAL ERROR: Failed to load RAG assets on startup: {e}", file=sys.stderr)
    sys.exit(1)
