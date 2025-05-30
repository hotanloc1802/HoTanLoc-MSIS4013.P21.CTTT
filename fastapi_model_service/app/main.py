# fastapi_model_service/app/main.py
from fastapi import FastAPI, HTTPException # Thêm HTTPException
from pydantic import BaseModel
import datetime
import asyncio
import os
import json
from confluent_kafka import Consumer, KafkaException, KafkaError
import httpx
from sentence_transformers import SentenceTransformer
from elasticsearch import AsyncElasticsearch, NotFoundError

app = FastAPI(
    title="FastAPI Model Service",
    description="Service for processing book events, handling ML models, generating embeddings, and semantic search.",
    version="0.1.0"
)

# --- Khai báo biến toàn cục ---
kafka_consumer_task = None
embedding_model = None
es_client: AsyncElasticsearch | None = None
INDEX_NAME = "books_index"

# --- Pydantic Models ---
class TextToEmbed(BaseModel):
    text: str

class SemanticSearchQuery(BaseModel):
    query_text: str
    top_k: int = 5 # Số lượng kết quả trả về mặc định

# --- Hàm tiện ích (fetch_book_details, create_es_index_if_not_exists giữ nguyên) ---
async def fetch_book_details(book_id: int) -> dict | None:
    # ... (code của bạn)
    books_api_url = f"http://books.api:5000/books/{book_id}"
    try:
        async with httpx.AsyncClient() as client:
            print(f"[KAFKA_CONSUMER] Fetching details for BookId: {book_id} from {books_api_url}")
            response = await client.get(books_api_url)
            response.raise_for_status()
            book_details = response.json()
            print(f"[KAFKA_CONSUMER] Fetched details for BookId {book_id}: {json.dumps(book_details, indent=2, ensure_ascii=False)}")
            return book_details
    except httpx.HTTPStatusError as e:
        print(f"[KAFKA_CONSUMER] HTTP error fetching book {book_id}: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 404:
            print(f"[KAFKA_CONSUMER] BookId {book_id} not found in Books.Api.")
        return None
    except httpx.RequestError as e:
        print(f"[KAFKA_CONSUMER] Request error fetching book {book_id} from {books_api_url}: {e}")
        return None
    except Exception as e:
        print(f"[KAFKA_CONSUMER] General error fetching book {book_id}: {e}")
        return None

async def create_es_index_if_not_exists():
    # ... (code của bạn)
    if not es_client:
        print("[FASTAPI_APP] Elasticsearch client not available. Cannot create index.")
        return
    try:
        if not await es_client.indices.exists(index=INDEX_NAME):
            mapping = {
                "mappings": {
                    "properties": {
                        "book_id": {"type": "integer"},
                        "title": {"type": "text", "analyzer": "standard"},
                        "author": {"type": "keyword"},
                        "description": {"type": "text", "analyzer": "standard"},
                        "isbn": {"type": "keyword"},
                        "book_vector": {
                            "type": "dense_vector",
                            "dims": 384,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "last_updated_in_es": {"type": "date"}
                    }
                }
            }
            await es_client.indices.create(index=INDEX_NAME, body=mapping)
            print(f"[FASTAPI_APP] Index '{INDEX_NAME}' created with mapping successfully.")
        else:
            print(f"[FASTAPI_APP] Index '{INDEX_NAME}' already exists.")
    except Exception as e:
        print(f"[FASTAPI_APP] Error creating/checking Elasticsearch index '{INDEX_NAME}': {e}")


# --- Kafka Consumer Logic (giữ nguyên như bạn đã hoàn thiện ở Bước 7.5) ---
async def consume_book_events():
    # ... (toàn bộ code consumer của bạn, bao gồm cả logic tạo embedding và index vào ES) ...
    consumer_conf = {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
        'group.id': 'fastapi_book_event_consumers_v2',
        'auto.offset.reset': 'earliest',
    }
    consumer = Consumer(consumer_conf)
    topic = "book_events"
    try:
        consumer.subscribe([topic])
        print(f"[KAFKA_CONSUMER] Subscribed to topic: {topic} with group_id: {consumer_conf['group.id']}")
        print(f"[KAFKA_CONSUMER] Waiting for messages...")
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.5)
                continue
            
            book_id_for_error_log = "unknown"

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"[KAFKA_CONSUMER] Reached end of partition for {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
                elif msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    print(f"[KAFKA_CONSUMER] Topic {topic} not found. Waiting...")
                    await asyncio.sleep(5)
                else:
                    print(f"[KAFKA_CONSUMER] Kafka Error: {msg.error()}")
                    await asyncio.sleep(5)
            else:
                try:
                    event_data_str = msg.value().decode('utf-8')
                    event_data = json.loads(event_data_str)
                    
                    book_id = event_data.get('BookId')
                    event_type = event_data.get('EventType')
                    book_id_for_error_log = book_id

                    print(f"[KAFKA_CONSUMER] Received BookEvent (raw): {event_data_str}")
                    print(f"[KAFKA_CONSUMER] Parsed BookEvent: BookId={book_id}, EventType={event_type}, Timestamp={event_data.get('Timestamp')}")

                    if not book_id:
                        print("[KAFKA_CONSUMER] Event missing BookId. Skipping.")
                        continue

                    if event_type in ["BookCreated", "BookUpdated"]:
                        book_details = await fetch_book_details(book_id)
                        if book_details:
                            title = book_details.get('title', '')
                            description = book_details.get('description', '')
                            text_to_embed = f"{title} {description}".strip()

                            if embedding_model and text_to_embed:
                                print(f"[KAFKA_CONSUMER] Text to embed for BookId {book_id}: '{text_to_embed[:200]}...'")
                                vector_embedding = embedding_model.encode(text_to_embed)
                                embedding_list = vector_embedding.tolist()
                                print(f"[KAFKA_CONSUMER] Generated embedding for BookId {book_id}, shape: {vector_embedding.shape}")

                                if es_client:
                                    book_document_for_es = {
                                        "book_id": book_id,
                                        "title": title,
                                        "author": book_details.get('author'),
                                        "description": description,
                                        "isbn": book_details.get('isbn'),
                                        "book_vector": embedding_list,
                                        "last_updated_in_es": datetime.datetime.utcnow().isoformat()
                                    }
                                    try:
                                        await es_client.index(index=INDEX_NAME, id=str(book_id), document=book_document_for_es)
                                        print(f"[KAFKA_CONSUMER] Successfully indexed/updated BookId {book_id} to Elasticsearch index '{INDEX_NAME}'.")
                                    except Exception as e_es:
                                        print(f"[KAFKA_CONSUMER] Error indexing BookId {book_id} to Elasticsearch: {e_es}")
                                else:
                                    print(f"[KAFKA_CONSUMER] Elasticsearch client not available. Skipping indexing for BookId {book_id}.")
                            else:
                                if not embedding_model:
                                    print(f"[KAFKA_CONSUMER] Embedding model not loaded. Skipping embedding for BookId {book_id}.")
                                if not text_to_embed:
                                    print(f"[KAFKA_CONSUMER] No text to embed for BookId {book_id}. Skipping embedding.")
                        else:
                            print(f"[KAFKA_CONSUMER] Could not fetch details for BookId {book_id}. Considering removal from ES.")
                            if es_client and event_type != "BookDeleted":
                                try:
                                    await es_client.delete(index=INDEX_NAME, id=str(book_id), ignore=[404])
                                    print(f"[KAFKA_CONSUMER] Document for BookId {book_id} (not found via API) removed/confirmed_absent from Elasticsearch.")
                                except Exception as e_es_delete:
                                    print(f"[KAFKA_CONSUMER] Error deleting document for BookId {book_id} from Elasticsearch: {e_es_delete}")

                    elif event_type == "BookDeleted":
                        print(f"[KAFKA_CONSUMER] Processing BookDeleted event for BookId {book_id}.")
                        if es_client:
                            try:
                                await es_client.delete(index=INDEX_NAME, id=str(book_id), ignore=[404])
                                print(f"[KAFKA_CONSUMER] Successfully deleted BookId {book_id} from Elasticsearch index '{INDEX_NAME}'.")
                            except Exception as e_es:
                                print(f"[KAFKA_CONSUMER] Error deleting BookId {book_id} from Elasticsearch: {e_es}")
                        else:
                            print(f"[KAFKA_CONSUMER] Elasticsearch client not available. Skipping deletion for BookId {book_id}.")
                    else:
                        print(f"[KAFKA_CONSUMER] Received unhandled event type '{event_type}' or missing BookId for event: {event_data_str}")
                except json.JSONDecodeError:
                    print(f"[KAFKA_CONSUMER] Failed to decode JSON from Kafka message: {msg.value().decode('utf-8') if msg.value() else 'None'}")
                except Exception as e:
                    print(f"[KAFKA_CONSUMER] Error processing message for BookId {book_id_for_error_log}: {e}")
            await asyncio.sleep(0.01)
    except KafkaException as e:
        print(f"[KAFKA_CONSUMER] KafkaException in consumer loop: {e}")
    except Exception as e:
        print(f"[KAFKA_CONSUMER] Unexpected error in consumer loop: {e}")
    finally:
        print("[KAFKA_CONSUMER] Closing Kafka consumer...")
        consumer.close()

# --- Sự kiện Startup và Shutdown (giữ nguyên như bạn đã hoàn thiện) ---
@app.on_event("startup")
async def startup_event_handler():
    # ... (code của bạn)
    global kafka_consumer_task, embedding_model, es_client
    print("[FASTAPI_APP] Application startup...")
    print("[FASTAPI_APP] Loading sentence embedding model...")
    try:
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("[FASTAPI_APP] Sentence embedding model loaded successfully.")
    except Exception as e:
        print(f"[FASTAPI_APP] Error loading sentence embedding model: {e}")
        embedding_model = None
    print("[FASTAPI_APP] Initializing Elasticsearch client...")
    try:
        es_host = os.getenv("ELASTICSEARCH_HOSTS", "http://elasticsearch:9200")
        es_client = AsyncElasticsearch(hosts=[es_host])
        if await es_client.ping():
            print(f"[FASTAPI_APP] Successfully connected to Elasticsearch at {es_host}")
            await create_es_index_if_not_exists()
        else:
            print(f"[FASTAPI_APP] Could not connect to Elasticsearch at {es_host}. Kafka consumer will not start if it depends on ES.")
            es_client = None
    except Exception as e:
        print(f"[FASTAPI_APP] Error initializing Elasticsearch client: {e}")
        es_client = None
    print("[FASTAPI_APP] Initializing Kafka consumer...")
    if es_client and embedding_model:
        kafka_consumer_task = asyncio.create_task(consume_book_events())
        print("[FASTAPI_APP] Kafka consumer task created.")
    else:
        if not es_client:
            print("[FASTAPI_APP] Elasticsearch client not available. Kafka consumer will not be started.")
        if not embedding_model:
            print("[FASTAPI_APP] Embedding model not loaded. Kafka consumer will not be started (as it needs the model).")


@app.on_event("shutdown")
async def shutdown_event_handler():
    # ... (code của bạn)
    global kafka_consumer_task, es_client
    print("[FASTAPI_APP] Application shutdown: Stopping Kafka consumer...")
    if kafka_consumer_task:
        kafka_consumer_task.cancel()
        try:
            await kafka_consumer_task
        except asyncio.CancelledError:
            print("[FASTAPI_APP] Kafka consumer task successfully cancelled.")
        except Exception as e:
            print(f"[FASTAPI_APP] Error during Kafka consumer task shutdown: {e}")
    if es_client:
        print("[FASTAPI_APP] Closing Elasticsearch client connection...")
        await es_client.close()
        print("[FASTAPI_APP] Elasticsearch client connection closed.")

# --- Các Endpoints ---
@app.get("/", tags=["Root"])
async def read_root():
    # ... (code của bạn)
    return {"message": "Welcome to the FastAPI Model Service!"}

@app.get("/health", tags=["Health Check"])
async def health_check():
    # ... (code của bạn)
    return {"status": "ok", "timestamp": datetime.datetime.utcnow()}

@app.post("/embed", tags=["Embedding"])
async def create_embedding(data: TextToEmbed):
    # ... (code của bạn)
    if embedding_model is None:
        raise HTTPException(status_code=503, detail="Embedding model is not loaded.")
    try:
        print(f"[EMBED_ENDPOINT] Received text to embed: '{data.text}'")
        vector_embedding = embedding_model.encode(data.text)
        print(f"[EMBED_ENDPOINT] Generated embedding of shape: {vector_embedding.shape}")
        return {"text": data.text, "embedding": vector_embedding.tolist()}
    except Exception as e:
        print(f"[EMBED_ENDPOINT] Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")

# === ENDPOINT TÌM KIẾM NGỮ NGHĨA MỚI ===
@app.post("/search/semantic", tags=["Search"])
async def semantic_search_books(query: SemanticSearchQuery):
    """
    Nhận một truy vấn văn bản, tạo embedding, và tìm kiếm sách tương đồng trong Elasticsearch.
    """
    if embedding_model is None:
        raise HTTPException(status_code=503, detail="Embedding model is not loaded. Cannot perform semantic search.")
    if es_client is None:
        raise HTTPException(status_code=503, detail="Elasticsearch client is not available. Cannot perform search.")

    print(f"[SEMANTIC_SEARCH] Received query: '{query.query_text}', top_k: {query.top_k}")

    try:
        # 1. Tạo vector embedding cho câu truy vấn
        query_vector = embedding_model.encode(query.query_text).tolist() # Chuyển sang list
        print(f"[SEMANTIC_SEARCH] Generated query vector.")

        # 2. Xây dựng truy vấn k-NN cho Elasticsearch
        # Sử dụng k-NN search (nếu Elasticsearch phiên bản mới) hoặc script_score query
        # Đây là ví dụ sử dụng k-NN search (yêu cầu trường book_vector là k-NN vector field)
        # Nếu bạn dùng ES < 7.10 hoặc không cấu hình k-NN field, bạn cần dùng script_score với cosineSimilarity
        
        # Ví dụ với k-NN search (đơn giản nhất, yêu cầu mapping đúng)
        knn_query_body = {
            "knn": {
                "field": "book_vector",
                "query_vector": query_vector,
                "k": query.top_k,
                "num_candidates": query.top_k + 10 # Thường lớn hơn k một chút
            },
            "_source": ["book_id", "title", "author", "description", "isbn"] # Chỉ lấy các trường cần thiết
        }
        
        # Hoặc ví dụ với script_score (linh hoạt hơn, hoạt động với nhiều phiên bản ES)
        # script_score_query_body = {
        #     "query": {
        #         "script_score": {
        #             "query": {"match_all": {}}, # Có thể kết hợp với query khác ở đây
        #             "script": {
        #                 "source": "cosineSimilarity(params.query_vector, 'book_vector') + 1.0", # +1.0 để score > 0
        #                 "params": {"query_vector": query_vector}
        #             }
        #         }
        #     },
        #     "size": query.top_k,
        #     "_source": ["book_id", "title", "author", "description", "isbn"]
        # }


        print(f"[SEMANTIC_SEARCH] Executing Elasticsearch k-NN query...")
        # response = await es_client.search(index=INDEX_NAME, body=script_score_query_body) # Nếu dùng script_score
        response = await es_client.search(index=INDEX_NAME, knn=knn_query_body["knn"], source=knn_query_body["_source"], size=query.top_k)


        hits = response.get("hits", {}).get("hits", [])
        results = []
        for hit in hits:
            results.append({
                "score": hit.get("_score"),
                "book": hit.get("_source")
            })
        
        print(f"[SEMANTIC_SEARCH] Found {len(results)} results.")
        return {"query": query.query_text, "results": results}

    except NotFoundError:
        print(f"[SEMANTIC_SEARCH] Index '{INDEX_NAME}' not found.")
        raise HTTPException(status_code=404, detail=f"Search index '{INDEX_NAME}' not found.")
    except Exception as e:
        print(f"[SEMANTIC_SEARCH] Error during semantic search: {e}")
        # In ra chi tiết lỗi từ Elasticsearch nếu có
        if hasattr(e, 'meta') and e.meta and hasattr(e.meta, 'body') and e.meta.body:
            print(f"[SEMANTIC_SEARCH] Elasticsearch error body: {e.meta.body}")
        raise HTTPException(status_code=500, detail=f"An error occurred during semantic search: {str(e)}")

