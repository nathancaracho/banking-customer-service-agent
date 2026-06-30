import httpx


class EmbeddingError(RuntimeError):
    pass


async def create_embeddings(
    base_url: str,
    api_key: str,
    model: str,
    texts: list[str],
    dimensions: int,
) -> list[list[float]]:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{base_url}/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "input": texts, "dimensions": dimensions},
            )
            response.raise_for_status()
        data = sorted(response.json()["data"], key=lambda item: item["index"])
        embeddings = [item["embedding"] for item in data]
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        raise EmbeddingError("Embedding generation failed") from error

    if len(embeddings) != len(texts) or any(
        len(embedding) != dimensions for embedding in embeddings
    ):
        raise EmbeddingError("Embedding response has unexpected dimensions")

    return embeddings
